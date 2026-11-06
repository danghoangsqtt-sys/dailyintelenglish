# Phase 98 state

Status: implemented_verified (2026-11-06): official Studio exports of Lantern and Apollo 11 pass; committed on `claude/phase98-99-doodle` (f5be5647). [Plan](PLAN.md).

| Task | Scope | Status |
|---|---|---|
| 98.1 | The `doodle` kind and its four story types | Implemented. The 7-second 16:9 clip from Lantern is available in Create and Step 1. Verified in Studio. |
| 98.2 | Script: target words first, one whole arc, checks | Outline selects 5-8 terms. Validation requires three spoken uses per term. Arc and ending await real review. |
| 98.3 | Plan and pictures | Picture spans use actual speech timing. Qwen batches currently use 20 pictures and persist per batch. |
| 98.4 | Scene, crossfade, term card, `pill` captions | Implemented in Remotion. Preview and full video await visual review. |
| 98.5 | Truth by kind, editing on Step 5 | Fact check, picture editing and review implemented in source. Workflow awaits live verification. |
| 98.6 | YouTube word list | Uses the learning pack vocabulary. Original fiction adds a disclosure. |
| 98.7 | Tests and three real videos for the owner | Renderer type check, preview build and 218 Vitest tests passed. An offline Python regression run passed 256 tests, including 25 Doodle tests. Three VOX HTTP integration fixtures could not start under the offline test loop. Full pytest is pending. The first live myth run passed through script, learning, TTS, storyboard, Qwen and MP4 export in Studio on port 8001. The fiction run also reached MP4 export and passed Studio playback. The history run also reached MP4 export and passed Studio playback. Fiction and history ran short. The owner accepted Icarus and asked to continue with Lantern and Apollo 11. Apollo 11 review and the duration and picture-quality checks remain open. |
| 98.8 | Verify duration and picture corrections (BUG-056, BUG-057) | done 2026-11-06: official Studio exports of Lantern and Apollo 11 from the committed code (see below). |

## First live run

Icarus and the Wax Wings, project `76fc8165-bef3-4500-b418-47b8aeef7730`. 31 Qwen illustrations, 172.5 seconds of narration, and a 181.4-second 1920×1080 H.264/AAC export. Doodle prompts now end on the story and request repeated target words. Two storyboard jobs went stale under a different worker from the one that completed the third job.

## Fiction and history live runs

The Lantern in the Rain, project `f68cec76-ae64-435d-a342-8c0a29431d8a`: 25 Qwen images, 150.864 seconds of narration, 159.8-second 1080p export. Studio playback showed pictures and captions. A black-frame scan found no black span of 0.3 seconds or more. Qwen drew stray lettering in at least one picture.

Apollo 11, project `e0ebf25a-27aa-4e0d-9658-462e8a33dcde`: the first audio used combined date events that the exact timing validator rejected. Spelled out the dates and revised the narrative against NASA's mission overview. The revised narration lasts 424.176 seconds, and the storyboard has 62 scenes. All 62 Qwen images were saved and the plan was approved. The 1080p H.264/AAC export runs 432.633 seconds. Studio playback showed pictures and captions. The full scan found no black span of 0.3 seconds or more. The sample includes stylized illustrations that should not be treated as documentary visuals.

## Resume audit (2026-11-06)

The previous renders are the baseline. Close the Step 1 clip gap using the real fiction render, correct the Doodle defaults in Step 1, and surface measured narration versus the configured duration in Step 5 before a new picture batch. Keep the CEFR word target and use the normal long-script tolerance. Revise Doodle-only prompts to distribute vocabulary across story beats, avoid reintroducing the story, and leave text out of fiction and myth pictures. Keep the review gate open until corrected renders have been checked.

Studio verification: Create opens Doodle in Step 1, shows the example, and defaults to 8 minutes. Apollo 11 opens in Step 5 with 7:04 narration against an 8:00 target. FFprobe confirms all three exports are 1080p H.264/AAC. A full blackdetect scan found no black span of at least 0.3 seconds in any of the three. A sampled-frame review found stray writing in Lantern and visual inaccuracies in Apollo 11 (Eagle rendered as a bird, Columbia splashdown illustrated as a person). The updated prompts distinguish named hardware from common nouns and leave generated lettering out of new myth and fiction picture plans. The three exported MP4s predate these changes.

Open follow-ups: [BUG-056 duration](../../requests/BUG-056.md) and [BUG-057 picture accuracy](../../requests/BUG-057.md).

Latest checks: 162 focused offline pytest tests, 218 Vitest tests, renderer type check and preview build passed. A wider Python run passed 206 tests with five integration fixture setup errors. Full pytest remains unverified. Apollo 11 was handed off as a smaller 1080p review copy with the original audio and the same 432.633-second duration.

## Task 98.8 verification (2026-11-06)

The owner rated the existing Apollo 11 video quite good. The original projects and exports are review baselines. The duration target applies to narration, before the branded ending.

| Sample | Previous narration | Fitted narration | Timed words | Scenes | Longest scene |
|---|---:|---:|---:|---:|---:|
| The Lantern in the Rain | 150.864 s | 179.973 s | 353 | 25 | 9.571 s |
| Apollo 11 | 424.176 s | 479.974 s | 965 | 62 | 11.147 s |

Both mixes reused the projects' cached speech. Word and line timings map to the fitted audio. No scene token anchor changed. The real Qwen worker generated replacement scenes for Lantern pic-3 and Apollo pic-24/pic-55. Inspection found no invented lettering in the selected Lantern picture and no extra people in the selected Eagle and Columbia pictures. Both isolated plans passed the app's asset, timing and geometry checks with the replacements.

89 focused pytest tests, 218 Vitest tests and the renderer type check passed. Remotion's isolated MP4 smoke run failed at the browser connection. An independent loopback test could listen but received EACCES when connecting. The test plans are ready for an export outside this execution environment. The working tree and upstream persistence gate remains open. No complete tag was created.

## Offline MP4 review checkpoint

Both approved snapshots were exported as separate offline review copies using their validated scene and narration timings, the renderer's caption pagination and card timing, and the existing branded endings. The exports are 1080p at 30 fps with H.264/AAC. Lantern is 188.900 s and Apollo 11 is 488.433 s. A complete black-frame scan found no spans of at least 0.3 seconds. Checked the three replaced scenes and sampled the Apollo vocabulary overlay in the actual encoded file.

Apollo's isolated learning pack had three unrelated entries and no matching card entries for the seven selected terms. The isolated review now has seven bilingual entries pinned to its approved snapshot. The production learning validator now requires each selected Doodle headword and routes missing items through the existing repair attempt. The focused learning and Doodle suite passed 57 tests.

These are offline review exports. The original projects and original MP4s remain the comparison baselines. Official Studio export still needs a working Remotion browser connection. Git persistence is pending.

## Studio and Git close-out retry

The original Studio rendering path reached the Remotion child process on the approved Lantern smoke fixture and failed at the browser connection again. Git could not create the primary repository index lock. A separate local checkpoint is used to preserve the Phase 98 changes while leaving the primary checkout and final completion tag pending.

## Official Studio export close-out (2026-11-06)

The Remotion connection that failed in the earlier execution environment works on this machine. Both approved projects were exported the
owner's way, on isolated copies of their approval databases (port 8011/8012, code of `claude/phase98-99-doodle`): the audio regenerated through
`/audio/generate` (the Doodle fit applied), the stale plan saved as a new revision and approved unchanged, then `/video/generate`.
The illustration rows were pointed at copied asset folders inside each copy (same bytes; the asset hash check still runs).

| Sample | Narration (target) | Render wall time | MP4 | Checks |
|---|---:|---:|---|---|
| The Lantern in the Rain | 179.973 s (180 s) | 154.1 s | 188.900 s, 1920x1080, 30 fps, H.264/AAC, -16.5 LUFS | A/V diff 0.000 s; no black span >= 2 s; no silence >= 3 s inside; SRT 17 cues ending 179.973 s |
| Apollo 11 | 479.974 s (480 s) | 398.4 s | 488.433 s, 1920x1080, 30 fps, H.264/AAC, -16.5 LUFS | A/V diff 0.000 s; no black span >= 2 s; no silence >= 3 s inside; SRT valid, ending 479.974 s |

Two Lantern frames (40 s, 100 s) were looked at: pictures with the red-scarf hero, no generated lettering, pill captions readable.
Evidence: `data/tmp/phase98-99-close/{lantern,apollo}-export.txt`, `{lantern,apollo}-verify.json`, `lantern-40s.jpg`, `lantern-100s.jpg`
(git-ignored, in the worktree that made them). The owner's own view of the corrected videos is still the acceptance gate (D165).
