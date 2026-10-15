# Task 46.7: YouTube motion and more expressive dialogue characters

Owner request: accept the richer motion, apply it to YouTube 16:9, and improve stiff character movement/gesture variety during a conversation. The current packs each contain 29 pictures including seven closed/open gesture pairs. Current rendering can hold a single gesture for an entire 15–20 second line.

Owner selected: use the existing picture packs, with more flexible dialogue-driven performance. No new rig or generated character assets in this task.

## Plan and allowed_files
- renderer/src/Episode.tsx, Sprites.tsx, MotionAccents.tsx: share the accepted motion with 16:9 using wide-specific geometry and short caption pages; preserve the current 9:16 safe layout.
- renderer/src/motionLayout.ts and motionLayout.test.ts: wide/vertical caption and decoration layout rules.
- renderer/src/conversationMotion.ts and conversationMotion.test.ts: timed phrase-level gesture cues and bounded whole-character movement using only existing assets, subject to the owner's implementation preference.
- renderer/src/spriteTimeline.ts and spriteTimeline.test.ts: integrate phrase gestures/reactions while keeping real mouth timing, missing-pose fallback, frame determinism and sprite proportions.
- This task card and docs/operations/youtube-dialogue-motion.md.
- Disposable previews, props and QA under data/tmp/youtube-dialogue-motion/.
- Snapshot workspace DB and both existing MP4/SRT formats under data/backups/ before normal horizontal/vertical regeneration and the existing export hooks.

## Design and risk
Reuse scene reveal/light sweep, speaker spotlight/meters, learning-card entrance, caption/word motion/progress and bokeh across formats. Wide captions use a centered lower band with larger page capacity than portrait; wide decoration scales to the actual canvas. Keep identity, audio, transcript, existing project folder and intro/outro timing.

Character work uses phrase-timed bursts, neutral rests, semantic pose selection and intermittent listener reactions; never hold a greeting wave through an entire monologue. Use bounded whole-picture drift/lean while preserving scale and mouth/pose matching. Existing full-picture assets cannot provide true articulated arm/hand interpolation; a rig or intermediate animation frames is a separate asset-level upgrade. The owner was asked which level they prefer while independent YouTube work proceeds.

Risk: frequent pose changes can look abrupt, literal gesture selection can be inappropriate, and transforms may cross the safe limits. Limit gesture frequency/duration, anchor to word/sentence boundaries, gate poses on actual pack availability, and test/read actual cue schedules before rendering. Do not blend dissimilar body pictures or fabricate poses. Legacy/minimal packs keep their existing fallback.

## Verification
- Render-budget amendment: the first full landscape render completed its 7,484 frames in 724 seconds, exceeding the historical 600-second limit. Allow backend/core/config.py, backend/media/video_renderer_remotion.py, tests/test_video_service_remotion.py and .env.example to make the shared render deadline configurable (default 1,800 seconds, bounded 60–7,200), document the measured regression and test override/retry behavior. Keep atomic publication and the same two-attempt ceiling.
- Portrait measurement amendment: the running full portrait job reached frame 5,255/7,484 after roughly 24 minutes, projecting beyond the 1,800-second budget already passed to subprocess.run. Preserve this exact job's completed staging output with a second NTFS link under the task's disposable artifacts if it times out; do not publish an incomplete render. After the renderer exits, require full duration/codec/audio verification before atomic publication and existing vertical-path/export service calls. Raise the future configurable default to 3,600 seconds (same 60–7,200 bounds), documenting the actual measured cost. No new public endpoint or new model job.
- Renderer typecheck and Vitest: geometry, timing/identity/fallbacks, mouth matching, determinism and bounded movement; existing media service/API tests if their interface is affected.
- Actual episode DOM scans in both sizes for captions/cards, representative phrase/reaction stills, and motion previews with the existing soundtrack.
- Snapshot then render full Ep. 2 horizontal and vertical versions as needed. Probe dimensions/duration, compare audio bitstream to the originals, verify source/export hashes and retain the old outputs.
- No external AI job, new dependency, EXE build/release, commit/push or self-acceptance of pending owner gates.

## Result: implemented_verified_pending_pm

- Shared accepted motion with YouTube 16:9; added short centered caption pages and wide-specific motion geometry.
- Existing character pictures now use phrase gestures, neutral rests, listener reactions, small whole-picture drift/lean and imported head-offset compensation. Actual Ep. 2 audit: 64 speaking bursts / 53 listener reactions; the initial 19.608-second turn has five bursts instead of a held greeting wave.
- TypeScript and 89 Vitest tests passed. Backend video/export/API suite: 49 passed; deadline change rechecked with 21 bridge tests. Ruff and diff whitespace checks passed. Both actual Episode DOM scans sampled 757 frames, with zero caption/card overflow failures.
- Full YouTube output succeeded via normal API in 768.178 s. Portrait completed in 2058.309 s after the old in-flight 1800 s deadline; its exact finished staging file was preserved, fully decoded and audio-verified before existing publisher/path/export services recovered it. No incomplete output or fabricated successful HTTP result.
- Both outputs are 249.514667 s H.264/AAC (1280x720 / 1080x1920), audio bitstreams identical to their backups, SRT unchanged, source/export hashes equal, job complete and export error null. Final dialogue/learning/insert/outro frames inspected. Render time remains a documented limitation; configurable future default is 3600 s, with the same bounded retry policy.
- Source server restarted with current code at http://127.0.0.1:8001. Backup retained at data/backups/youtube-dialogue-20261015-120722/. Artifacts and explicit recovery evidence: data/tmp/youtube-dialogue-motion/. Report: docs/operations/youtube-dialogue-motion.md.
- No new model call, dependency, EXE build/release, commit/push or formal owner acceptance.
