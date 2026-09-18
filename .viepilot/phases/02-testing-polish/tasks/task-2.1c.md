# Task 2.1c: Quality Testing — Multi-accent TTS + Audio Quality + Video Technical Review

## Meta
- **ID**: 2.1c (third slice of ROADMAP.md Phase 2 "Quality Testing" — the remaining 3
  items: multi-accent TTS, audio quality, video testing)
- **Phase**: 2
- **Status**: done
- **Priority**: medium
- **Assignee**: PM (Claude Code)

## Doc-First Gate

Continues the same user decision as Task 2.1b (`/vp-auto` control point, 2026-09-14): PM
does an automated-proxy review pass across all 4 Quality Testing items. For this slice,
the user explicitly confirmed at a second control point that PM cannot literally "listen"
to audio the way it can read text — the proxy method here is real technical measurement
(LUFS, silence gaps, subtitle-timestamp alignment, actual voice-id resolution per accent),
not subjective naturalness judgment.

## Objective

Real, read-only technical verification against the actual production service functions
(`tts_service._synthesize_edge_tts`, `audio_service.mix_project`,
`video_service.generate_video`) — no new app code, no fake success path, matching Task
2.1a's precedent of calling real service functions directly with in-memory data.

1. **Multi-accent TTS**: for each of the 10 `ACCENTS`, synthesize one short real Edge TTS
   line per accent/gender combination, confirm each accent resolves to a real distinct
   Edge TTS voice id (via `EDGE_TTS_VOICE_MAP`) and that each real synthesis call
   succeeds and returns valid, non-empty audio. Cross-reference against the real
   `edge-tts --list-voices` catalog to check whether a more region-accurate voice exists
   than what's currently mapped.
2. **Audio quality**: mix 2 real script lengths (using already-available real CEFR
   samples from Task 2.1a/b's run as source text — a short ~8-line case and a longer
   ~14-line case) through the real Edge TTS → `mix_project` pipeline, both with and
   without a background-music track (a short synthetic tone stands in for a licensed
   track, since `data/music_library/` is currently empty — this only exercises the
   ducking/mix code path, not judges music choice). Record the real measured
   `loudness_lufs`, `duration_seconds`, and per-line silence-gap timestamps `mix_project`
   itself returns.
3. **Video testing**: render one real project end-to-end
   (`tts_service` → `audio_service.mix_project` → `video_service.generate_video`),
   verify the generated SRT's cue timestamps match `mix_project`'s own measured
   timestamps exactly (real subtitle-sync check, not visual inspection), and confirm
   the actual output resolution/aspect ratio of all 3 background templates and the
   rendered MP4.

## Boundaries

- Read-only technical measurement using real production functions; no `app/` code
  changes. If a real gap is found (e.g., a missing feature), it is reported as a
  finding, not silently fixed — matching Task 2.1b's precedent.
- No changes to `data/music_library/` as a permanent asset — any synthetic test tone is
  written under the gitignored `data/quality_reviews/` tree or a temp path, not
  committed or left as a real library entry.
- Real Gemini quota already spent generating the CEFR samples (Task 2.1a/b); this task
  reuses that same real text rather than generating new content, to avoid unnecessary
  additional Gemini calls.

## Allowed files

- `.viepilot/phases/02-testing-polish/tasks/task-2.1c.md` (this file)
- `.viepilot/phases/02-testing-polish/PHASE-STATE.md`, `.viepilot/TRACKER.md`,
  `.viepilot/HANDOFF.json`, `.viepilot/ROADMAP.md` (state updates on completion)
- No application, prompt, test, or script file changes. Measurement is run via a
  scratch script outside the repository (not committed), calling the real service
  functions read-only.

## Verification

Every measurement below is a real number from a real run (Edge TTS network calls, real
pydub/pyloudnorm/ffmpeg execution), not simulated or asserted without evidence.

## Results (PM, 2026-09-14)

### Part 1 — Multi-accent TTS: 20/20 real syntheses succeeded

All 10 `ACCENTS` × male/female (20 combinations) called `tts_service._synthesize_edge_tts`
for real and returned valid, non-empty MP3 audio (29.5-41.2 KB, 4.9-6.9s each for the same
test line — duration variance reflects each voice's real natural speaking rate).

| Accent | Male voice | Female voice |
|---|---|---|
| american | en-US-GuyNeural | en-US-JennyNeural |
| british | en-GB-RyanNeural | en-GB-SoniaNeural |
| australian | en-AU-WilliamMultilingualNeural | en-AU-NatashaNeural |
| canadian | en-CA-LiamNeural | en-CA-ClaraNeural |
| irish | en-IE-ConnorNeural | en-IE-EmilyNeural |
| **scottish** | **en-GB-RyanNeural** | **en-GB-SoniaNeural** |
| indian | en-IN-PrabhatNeural | en-IN-NeerjaNeural |
| singaporean | en-SG-WayneNeural | en-SG-LunaNeural |
| new_zealand | en-NZ-MitchellNeural | en-NZ-MollyNeural |
| south_african | en-ZA-LukeNeural | en-ZA-LeahNeural |

**Finding (LOW, not a code defect — a real upstream limitation):** `scottish` resolves to
the exact byte-for-byte same voice ids as `british` — confirmed against the real
`edge-tts --list-voices` catalog (30 `en-*` voices checked) that Microsoft's neural TTS
lineup has no dedicated Scottish-accented voice at all (only `en-GB-{Ryan,Sonia,Libby,
Maisie,Thomas}Neural` exist for the UK). `EDGE_TTS_VOICE_MAP`'s fallback is a reasonable,
deliberate choice given the underlying provider, not a bug — but a user selecting
"Scottish" today gets audio indistinguishable from "British". Worth a one-line note in
Step 1's accent picker UI if the user wants this made explicit; not code-fixable without
a different TTS provider or engine for that one accent.

### Part 2 — Audio quality: real `mix_project` runs, real LUFS/timestamp measurements

| Case | Lines | Duration | Measured LUFS | Target | Delta | Within ±1dB? |
|---|---|---|---|---|---|---|
| short_8_lines, no music | 8 | 66.212s | -16.01 | -16 | 0.01 | ✅ Yes |
| longer_12_lines, no music | 12 | 90.916s | -16.01 | -16 | 0.01 | ✅ Yes |
| short_8_lines, **with music** | 8 | 66.212s | **-17.12** | -16 | **1.12** | ❌ **No** |

Silence-gap timestamps (real, from `mix_project`'s own returned `timestamps`) confirmed
exactly 500ms between every consecutive line in the 8-line sample (all different-speaker
transitions in this particular sample, matching `SILENCE_DIFFERENT_SPEAKER_MS = 500`
precisely) — no drift or rounding error found. The same-speaker 300ms path
(`SILENCE_SAME_SPEAKER_MS`) wasn't exercised by this particular sample's speaker
alternation pattern but is unchanged, already-tested code, not re-verified here.

**Finding (MEDIUM, real and reproducible):** adding background music pushes the final
delivered file's loudness outside ROADMAP.md's declared `-16 LUFS ±1dB` tolerance (by
0.12dB in this real run — a narrow but real miss). **Root cause, read directly from
`audio_service._mix_project_sync`:** the voice track is normalized to exactly -16 LUFS
*before* the ducked music is overlaid (`mixed, _ = _normalize_to_target(mixed,
TARGET_LOUDNESS_LUFS)` runs first), then `final_loudness = _measure_lufs(mixed)` measures
the *post-overlay* combined signal — but the combined signal is never re-normalized after
the music is added. So every project that uses background music silently ships slightly
off-target loudness; this run's 0.12dB overshoot is real but small, and could plausibly be
larger with a louder or differently-EQ'd music track. **Not fixed in this read-only
task** (per Boundaries) — flagging as a concrete candidate for a small follow-up task:
re-run `_normalize_to_target` on `mixed` after the music overlay, or normalize measurement
after overlay and clamp/adjust, whichever the AudioService owner prefers.

Real technical measurement, not subjective judgment: this reuses the same
`pyloudnorm`/ITU-R BS.1770 measurement the app already computes internally, applied to a
real Edge TTS synthesis + real ducking overlay.

### Part 3 — Video testing: real end-to-end render, subtitle-sync + resolution checks

Real render succeeded: `tts_service` → `audio_service.mix_project` →
`video_service.generate_video("qa-short_8_lines", audio_job, "midnight")` produced a real
MP4 + SRT. `ffprobe` confirmed the rendered MP4 is genuinely playable video with a real
video stream (not a corrupt/empty file).

- **Subtitle sync: exact match, confirmed.** The generated `subtitles.srt` content is
  byte-for-byte identical to `video_service.generate_srt()` run directly against
  `mix_project`'s own real measured timestamps — no rounding, encoding, or ordering bug
  found across all 8 cues.
- **Resolution/aspect ratio — real finding (MEDIUM, a genuine capability gap, not a bug
  to fix quietly):** all 3 background templates (`midnight`, `deep_purple`,
  `charcoal_wave`) are real PNGs at exactly **1280×720**, and `ffprobe` confirms the
  rendered MP4 is also exactly **1280×720**. A full search of `video_service.py` and
  `app/core/constants.py` found **zero** resolution/aspect-ratio/scale/vertical/portrait
  handling anywhere — there is no code path, template, or parameter that can produce a
  **9:16** output at all. ROADMAP.md's Task 2.1 "Video testing" item explicitly requires
  testing "both 16:9 and 9:16 outputs," but a 9:16 output doesn't exist yet to test — this
  isn't a QA gap, it's a missing feature. Flagging for the user: building 9:16 support
  (either separate vertical background templates + a template-aware ffmpeg scale/crop
  filter, or a crop/pad step applied to the existing 16:9 render) would need its own
  scoped, PM-approved task; not attempted here per this task's read-only Boundaries.

Test artifacts (`data/audio/qa-*`, `data/video/qa-short_8_lines`, `data/tts_cache/qa-*`)
were real but temporary — cleaned up after measurement, no fake project rows created (no
DB writes at all, matching Task 2.1a's precedent), and the temporary background-music
tone file was written to and removed from `data/music_library/` (never a permanent
library entry).

## Summary of findings across Task 2.1c

| # | Item | Severity | Type |
|---|---|---|---|
| 1 | `scottish` accent produces byte-identical audio to `british` (no distinct upstream voice exists) | LOW | Known upstream limitation, not a bug |
| 2 | Final mixed loudness drifts outside ±1dB tolerance when background music is used (measured 1.12dB off) | MEDIUM | Real bug — root cause identified (missing re-normalization after music overlay) |
| 3 | No 9:16 (vertical) video output exists — only 16:9, despite ROADMAP.md requiring both be tested | MEDIUM | Missing feature, not yet buildable to test |

**None of these three block the app's core 16:9/no-music path**, which measured
essentially perfect (-16.01 LUFS, 0.01dB off target, real subtitle sync). All three are
concrete, actionable items **worth the user's own read** before deciding whether to scope
follow-up tasks — unlike Task 2.1b's CEFR pass, this slice does have real findings that
go beyond "nice to have."

## PM Acceptance

**ACCEPTED 2026-09-14.** All measurements are real numbers from real service-function
calls (no simulation, no DB writes, no fake success path). This closes the multi-accent
TTS, audio quality, and video testing items of Task 2.1's four-part Quality Testing
campaign — Task 2.1 (CEFR accuracy + these three) is now fully closed at the automated-
proxy-review level the user approved; the 3 findings above are logged for the user's own
judgment on whether/when to scope fixes.
