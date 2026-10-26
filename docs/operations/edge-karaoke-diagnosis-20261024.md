# Edge karaoke synchronization diagnosis — 2026-10-24

Owner asks whether Phase77 affected karaoke after observing Edge speech and captions out of sync. The initial diagnosis below was read-only. The subsequent owner request explicitly authorized the repair recorded at the end of this document.

## What changed in Phase77

TTS dispatch, legacy-tag cleanup, cue-part joining removal and cache fingerprint inputs changed. The native Edge word capture still divides offset/duration by 10,000,000; that formula did not change. `audio_service.py`, `video_renderer_remotion.py`, `renderer/src/karaoke.ts` and `Episode.tsx` have no Phase77 diff. Thus unchanged renderer code is established, but is not evidence of correct end-to-end synchronization.

## Actual current file

Project `5b1667a3-b47b-4c4b-b989-dddd3cb44b03`, The Office Startup. Both voices use Edge at speed0.9 (Christopher/Jenny). Audio completed at 08:12Z and video at 08:35Z on 2026-10-24, after restoration. It has 25 lines, about290.56s of dialogue. The current MP4 is `data/video/5b1667a3-b47b-4c4b-b989-dddd3cb44b03/fc7c23af30444adf8132d80a6712ef72/video_remotion.mp4`. This is not an old invalidated output.

## Measurements

- Six video/stem audio correlation windows, spanning lines0,1,8,12,18,24: video speech is **7.8025–7.80275s** after the voice stem. The subtitle/intro clock starts speech at **7.760s**. Audio is therefore **42.5–42.75ms late** relative to that clock. This matches the earlier isolated mux-delay observation; no growing audio drift was detected in these six windows.
- Five current cached line MP3s were greedily decoded using the already-local English Wav2Vec2 model. Matching words have median native Edge-minus-acoustic onsets of **-112.0, -114.9, -123.0, -117.7 and -108.15ms**. In these samples the Edge timings lead acoustic word estimates. These are CTC estimates, not human-labelled truth; word onset depends on phonetics/model resolution.
- Two **pre-restoration**, unannotated Edge caches referenced by `data/backups/edge-plain-speech-20261024/app.before-restoration.db` have corresponding medians of **-106.00ms** and **-105.54ms**. The native timing lead predates Phase77 in those samples. Different texts limit causal comparisons; do not claim all past videos had exactly the same perceptual offset.
- Estimated combined current caption lead is roughly **150–165ms**, explaining the owner's perception. It is not a validated universal correction for every voice/rate/export.

Data/scripts: `data/tmp/edge-karaoke-diagnosis-20261024/` (`snapshot.json`, `report.json`, `pre_restore_report.json`). Only local data and CPU inference were used. No database rows/media were changed.

## Conclusion and remaining work

The synchronization problem is real. The evidence shows an existing native timestamp lead plus final MP4 audio lag, rather than establishing a direct renderer regression from the restoration. The previous handoff's static checks did not validate synchronization; assuming Edge's native timestamps were sufficient was an omission.

A correction should handle actual output mux delay and validate the audio/word timebase at multiple voices/rates and at beginning/middle/end. A blind fixed delay or another regeneration of the same inputs is not evidence of a solution. Keep Edge/plain dialogue as requested; no emotion or local speech engine is needed. This was the diagnosis-stage conclusion; implementation follows below.

AAC delay context: [Apple's AAC priming explanation](https://developer.apple.com/documentation/quicktime-file-format/background_aac_encoding). The specific42.75ms value above comes from the local media measurement, not that general documentation.

## Owner-authorized repair

Plan: `.viepilot/phases/77-edge-plain-speech/SYNC-FIX.md`. English voices Christopher, Jenny, Ryan and Sonia were synthesized at rates0.75/0.9/1.0/1.25 (16 independent captures). Estimated median native onset lead ranged80–147ms. A calibration of `0.100 / speech_rate` seconds reduced the per-capture median residual to an overall median5.0ms, maximum absolute16.5ms. Individual words still vary; greedy CTC is not human-labelled ground truth, and this does not establish accuracy for every Edge voice or rate.

- `AudioService.get_audio_job` converts raw boundaries once on read, including old mixes. The recipe marker makes the conversion idempotent. New mixes capture their synthesis rate; old unmarked mixes use the saved speaker rate. Provider MP3s, raw sidecars and stored raw job timestamps remain unchanged. If a speaker's rate was changed since an old mix was produced, regenerate that mix as usual.
- `render_audio.mux_timeline_audio` rebuilds AAC from the original composition sources before atomic publication. It copies video frames, preserves branding/music and normal encoder skip metadata, and trims nonzero inclusive clip frame ranges before resetting PTS. It does not shift or trim speech to conceal the word-boundary error.
- Video soundtracks now use lossless WAV. Python frame positions match JavaScript `Math.round`, including half-frame values. SRT intro offsets use the same rounded frame clock.

### Debugging measurements after repair

- A real landscape male/female render: source-to-MP4 audio residuals -0.167ms/+0.083ms (4kHz correlation resolution).
- A real portrait render of frames150–269: +0.083ms. No-music branding probes: greeting0.0ms and dialogue+0.083ms.
- The full 25-line episode was rendered through the production path with music, branding, sprites and corrected word props. Six windows at lines0/1/8/12/18/24: **-0.167 to +0.083ms**, versus the previous42.5–42.75ms delay. These numbers measure container/source alignment, not word recognition accuracy.
- A frame at8.0s confirms the first word `Hello` is highlighted after its corrected onset; source props contain the recipe-adjusted words. Human listening acceptance remains pending.
- Python AST, scoped Ruff and diff whitespace checks succeeded. No unrelated historical test suite was run.

The fixed current video is `data/video/5b1667a3-b47b-4c4b-b989-dddd3cb44b03/edge-sync-004f489d014849f0a6fe2cedbbe2a431/video_remotion.mp4`. Publication used optimistic input/video revision checks after the idle preflight and SQLite backup at `data/backups/edge-karaoke-sync-20261024/app.before-fix.db`. Previous video files were retained. Existing selected exports were synchronized through the normal export service.

Evidence in `data/tmp/edge-karaoke-diagnosis-20261024/`: `matrix-results.json`, `fix-verification.json`, `episode-verification.json`, `publication.json`, `episode-props.json`, and the landscape/portrait preview files.

### Package and installed app

Full/Lite2.0.0 completed at `dist/2.0-edge-sync-20261024/` (exit0, ZIP CRC and SHA256 checks). `bundles-verification.json` confirms all four modified production modules match current source bytecode in both EXEs. Full was installed with the guarded installer and backup `data/backups/desktop-20261024-163016-755/`. Windows CIM omitted the old process, so the exact installed process was identified through `Get-Process.Path` and stopped only after the idle preflight/online backup; the normal installer then backed up and replaced the distribution.

The new Full app started as PID30980. `installed-check.json` records matching EXE/metadata build identity `bb3a2e8f66cb08c8f68733e3e9405e295821ed6df0d7b936ef4db4e7cc905f70`, dashboard200, the repaired current video, live111.111ms word correction at rate0.9, unchanged raw stored timings, SQLite integrity ok and40projects retained. No commit/push/public release or owner listening acceptance is implied.
