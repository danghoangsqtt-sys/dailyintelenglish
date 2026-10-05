# Task 22.4: Smart music bed: fit to the video, duck under the voice, fade out at the end (D51, doc-first card)

## Objective

When an episode has background music, the music:

- **covers the whole video.**
  - Enhanced: intro 2.5 s + speech + outro 5 s.
  - Standard: speech + a 4 s music tail.
- **starts at the track's own beginning, then fits the length.** If the track is longer, it is
  cut. If it is shorter, it is looped with 3 s equal-power crossfades. A hard cut never happens.
- **sits under the voice.** Each track is loudness-normalised first, so every file starts at the
  same level.
  - The music is *open* during the intro, the outro and pauses ≥ 2.5 s.
  - It is *ducked* well under speech, with smooth ramps that finish before a line starts.
  - Short gaps stay ducked, so the music does not pump.
- **fades in over 2 s** and **fades out over 4 s, ending exactly at the last frame**.
- **No music selected:** the output is identical to today's on both renderers.

## Paths

- `app/services/music_bed.py` (new; pure numpy, no I/O except decoding)
- `app/core/constants.py`
- `app/services/audio_service.py`
- `app/services/video_service.py`
- `app/services/video_renderer_remotion.py`
- `video-renderer/src/types.ts`
- `video-renderer/src/Episode.tsx`
- `tests/test_music_bed.py` (new)
- `tests/test_audio_service.py` (or a new `tests/test_music_soundtrack.py`)
- `tests/test_video_soundtrack.py` (new)

## File-Level Plan

1. **`music_bed.py`.** Everything runs on float32 arrays `(channels, samples)` at 44.1 kHz stereo.
   - `decode(path)`: pydub → float array at 44.1 kHz stereo.
   - `normalise(music, target_lufs)`: pyloudnorm with a gain clamp. A silent track stays silent.
   - `fit(music, samples, sr)`:
     - trim when the music is longer;
     - otherwise repeat with equal-power crossfades of `MUSIC_CROSSFADE_S`;
     - a track shorter than 2 × crossfade is looped plainly.
   - `envelope(samples, sr, speech_spans, offset_s)`: the per-sample gain, built on a 10 ms grid,
     then interpolated to samples.
     - **Ducked windows:** each span is widened by attack 0.3 s before and release 0.8 s after,
       and windows less than 2.5 s apart are merged.
     - **Smoothing:** the target-dB curve is smoothed with a moving average of the ramp length, so
       each transition is a linear dB ramp that is complete before speech.
     - **Fades:** a 2 s fade-in, and a 4 s fade-out ending at the last sample.
   - `build_bed(...)` = normalise → fit → envelope.
   - `mix(voice, bed)`:
     - adds the two signals;
     - normalises the mix to −16 LUFS (as today);
     - applies a peak guard that scales down if the peak would pass −1 dBFS.
2. **Constants:**
   - `MUSIC_BED_LUFS` = −20, the open level;
   - `MUSIC_DUCK_DB` = −14, under speech, so ≈ 18 LU under the voice;
   - attack, release, merge gap, fade-in, fade-out, crossfade;
   - `STANDARD_MUSIC_TAIL_S` = 4.

   These are starting values. The owner's ears decide at Gate B-17.
3. **`audio_service`:**
   - `_mix_project_sync` writes **`voice.wav`**: the voice-only stem, normalised as the mix voice.
   - With music, the Step 4 `mix.mp3` uses `build_bed` over the speech span only. Its durations and
     timestamps are unchanged, it fades in at 0, and it fades out at the end.
   - `_loop_to_length` and `_duck_music` stay for the no-`voice.wav` fallback only.
   - New `build_soundtrack(audio_job, lead_in_s, tail_s, output)` makes **`soundtrack.mp3`**:
     - lead-in + voice + tail, with the bed over all of it;
     - the voice placed at `lead_in_s`;
     - the length is exact to the sample.
     - It returns None when there is no music or no `voice.wav` (an old job).
4. **Standard path** (`video_service`): with a soundtrack (tail 4 s), the render uses it as the
   audio, with `-t` = the soundtrack length. The SRT timings are unchanged, since the lead-in is 0.
5. **Remotion path:** the soundtrack uses lead-in = intro and tail = outro, and its total length
   equals the composition's length.
   - It is copied to `public/remotion-render/audio/{id}_soundtrack.mp3`.
   - The new prop `soundtrackPath` makes `Episode.tsx` play one top-level `<Audio>` from frame 0.
   - `AudioWindowContent` then skips its own `<Audio>` through a `playAudio` flag.
   - Without the prop, the render is unchanged.
6. **Tests:**
   - unit tests for fit (trim; crossfade loop length and no click at the seam), envelope (ducked
     inside speech, open in intro/outro/long gaps, merged short gaps, fade-in, fade-out reaches 0
     at the last sample) and normalise;
   - Step 4 mix with music writes `voice.wav` and keeps timestamps and duration;
   - soundtrack length = lead-in + voice + tail; the old-job fallback;
   - the Remotion props include `soundtrackPath` only with music;
   - the ffmpeg `-t` uses the soundtrack length.

## Best practices

- Pure functions for the signal math, unit-tested on synthetic signals.
- Heavy work in `asyncio.to_thread`.
- No new dependencies (numpy, pyloudnorm and pydub are already used).
- The no-music path is untouched.
- Every ffmpeg and Remotion call keeps its existing timeout.

## Verification

- Unit and integration tests, plus the full suite.
- **A real check on one real project** (DB copy, real Edge TTS cache, a real downloaded free
  track):
  - Step 4 mix + Standard video + Enhanced video;
  - measure the music level in intro, under speech and in the outro (ffmpeg `ebur128` momentary
    loudness);
  - check the fade reaches silence at the last frame;
  - check video length = intro + speech + outro;
  - the owner listens.

## Results (2026-10-06)

- **Built as planned.**
  - `app/services/music_bed.py` is the pure signal code.
  - The Step 4 mix uses the bed over the speech span and writes `voice.wav`.
  - `audio_service.build_soundtrack` builds the full-video soundtrack.
  - Standard renders voice + a 4 s tail. Enhanced renders a soundtrack sized to the composition,
    played from frame 0 (the `soundtrackPath` prop, with `playAudio=false` on the speech window).
  - `introSec` / `outroSec` are now sent explicitly (2.5 / 5.0).
- **Deviation (measured, then fixed):** through the real pipeline, a 2 s fade-in with a 2.5 s intro
  meant the music never reached its open level. The fade-out was 4 s and the release + ramp took
  1.1 s, which left the outro the same. Retuned to fade-in 1.0 s, release 0.5 s, fade-out 3.0 s:
  - the intro is open from 1.0 to 1.9 s;
  - the outro is open for ~1.2 s before the fade.
- **Test-signal note:** a crossfade of a sine *with itself* can be up to +3 dB (correlated phases).
  Equal-power is right for real music, so the level test uses a track longer than the video, and
  the loop is covered by its own unit test.
- **Real check** on the real project `b330d37f` (30 real cached Edge TTS lines, mix 176.02 s):
  - on a sqlite backup copy in a temp `DATA_DIR`;
  - with a synthetic 90 s chord track, so the episode needs a crossfade loop. There are no real
    downloaded tracks yet.

  | | Video length | Expected | Music open (intro) | Speech section | Music open (outro) | Last 0.5 s |
  |---|---|---|---|---|---|---|
  | Step 4 mix | 176.02 s, −16.0 LUFS | — | — | — | — | — |
  | Standard | 180.04 s | 180.02 | — | −21.5 LUFS (M) | −23.9 | −39.1 |
  | Enhanced | 183.59 s (92 s render) | 183.52 | −22.7 | −21.0 | −23.1 | −37.9 |

  - Values are ffmpeg `ebur128` momentary loudness.
  - Neither render fell back.
  - The open music sits ~7 LU under the −16 LUFS voice, and ~14 dB lower again under speech.
  - The videos were copied to `data/tmp/music-bed-check/` (synthetic music) to check the timing.
    The owner judges the real levels at Gate B-17 with real tracks. `MUSIC_BED_LUFS` and
    `MUSIC_DUCK_DB` are single constants.
- **Tests:**
  - `tests/test_music_bed.py` (10);
  - `tests/test_music_soundtrack.py` (4);
  - `tests/test_video_soundtrack.py` (5, including a real ffmpeg render: video = audio + 4 s,
    silent on the last frame).
  - vitest 42 and `tsc` clean.
- **Full suite: 1399 passed;** vitest 42 passed (2026-10-06).
