# Task 46.5: Balance and animate the vertical episode

Owner follow-up 2026-10-15: the 9:16 episode feels left-heavy and the top picture does not blend with the lower stage. Owner selected the more lively style, with clearer transitions and word emphasis.

## Plan and allowed_files
- renderer/src/safeZone.ts and safeZone.test.ts: keep the existing platform exclusion limits; center caption/card/chip columns and the pair of faces within them.
- renderer/src/Sprites.tsx: blend the scene into a full-frame deep-green ambient background, add deterministic image movement and soft stage lighting; keep sprites as whole undistorted pictures.
- renderer/src/Episode.tsx: vertical-only speaker alignment, exact card box sizing, caption page entrance and active-word emphasis.
- renderer/src/verticalMotion.ts and verticalMotion.test.ts: bounded frame-driven scene/caption animation helpers.
- renderer/src/karaoke.ts and karaoke.test.ts: optional character budget for narrow caption pages after real DOM measurement found two overflowing long pages; retain all tokens/times and the existing default behavior.
- This task card and docs/operations/vertical-visual-polish.md.
- Disposable stills/clips/evidence under data/tmp/vertical-visual-polish/.
- Snapshot existing Ep. 2 output under data/backups/ before normal vertical-generation API writes and its configured episode export hook.

## Design and risks
Use the existing brand green/yellow palette, a scene-colored ambient fill and soft light behind the figures. Preserve full-bleed imagery (the owner previously rejected framed picture windows). Keep the scene/cutaway cross-fades and add gentle lateral movement/zoom. Center the character pair on x=540; center the narrow caption and vocabulary columns on x=540 while retaining x<=864 below y=900. Speech overlays/faces also fit the supplied ads reference (x48..888, y288..1248). The platform-safe region is asymmetric; decoration fills the canvas, while key content remains clear of controls. Existing soundtrack, word timing, intro/outro and horizontal behavior remain unchanged.

Narrower captions can wrap more: reduce page length and verify actual rendered text boxes against the reserved area. Animation must be deterministic and small enough to preserve safe-zone bounds. Avoid unbounded blur effects and avoid changing sprite mouth/gesture timing.

## Verification
- Renderer typecheck and existing Vitest suite, including safe-zone and sprite regressions; add assertions for visual centering and motion limits.
- Inspect actual Ep. 2 stills at speech, vocabulary, scene transition and pauses; render a motion sample with its existing soundtrack.
- Then regenerate the real vertical episode, probe streams/duration and inspect extracted output frames. Verify exported file hash; preserve originals via snapshot. No commit/release or self-acceptance of pending owner gates.

## Result: implemented_verified_pending_pm

- Owner's lively style implemented: centered speech columns and character pair, ambient green scene blend/light, deterministic drift/zoom, animated caption pages and yellow active-word emphasis.
- 79 Vitest tests passed and TypeScript clean. Real DOM scan: 620 samples, 619 visible caption measurements across 88 pages, 176 vocabulary measurements, zero remaining overflow failures. The initial scan found two long caption regressions and the character budget resolved them.
- Visually inspected speech, vocabulary, long captions and activity inserts. A first full render revealed separate-image mask ghosting; applying one mask to the composited scene group corrected it. The corrected final full render completed in 419.607 s: 1080x1920 H.264/AAC, 249.514667 s; A/V difference 0.048 s.
- Source/export video hashes match; AAC bitstream matches the previous version exactly. Horizontal MP4 and SRT unchanged. Export API reports no error. Corrected motion preview and final measurements retained under data/tmp/vertical-visual-polish/.
- Original DB and media snapshot: data/backups/vertical-polish-20261015-100335/. The new motion increases the full video to about 470 MB under the existing encoding settings; this is documented rather than changing encoding policy without scope.
- Report: docs/operations/vertical-visual-polish.md. No EXE build, commit/push, release or owner gate acceptance declared.
