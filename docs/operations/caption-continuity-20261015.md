# Subtitle continuity fix — BUG-041

**2026-10-15 · Phase 47 / Task 47.1 · technically verified, owner visual review pending.**

## What changed

Caption pages now consider sentence endings, clause punctuation, grammatical boundary cues and balanced page lengths instead of filling a page until the next word crosses its limit. The existing learning pack supplies protected idioms and multiword vocabulary. Fitting phrases are kept together; overlong/overlapping phrases degrade deterministically within the available space.

The production composition memoizes page construction for each line/layout/phrase list. Only choosing the current page and highlighted word depends on the frame. No new NLP dependency, provider call or backend schema is involved.

| Area | Files |
|---|---|
| Pure segmentation and page selection | `renderer/src/captionPaging.ts` |
| Compatible captionPage entry point | `renderer/src/karaoke.ts` |
| Learning phrases and memoization | `renderer/src/Episode.tsx` |
| Regression coverage | `renderer/src/captionPaging.test.ts` |

Existing font size, safe-area geometry, word/character limits and caption motion remain as configured. The transcript, original audio, speaker and word timings are retained.

## Actual Episode 3 result

Project `6b8c5068-5c52-4bd5-9203-8953bec7b197`, **The Dinner Party Challenge · Ep. 3: Cooking the Final Dish**.

| Layout | Previous page cut | Result |
|---|---|---|
| 16:9 | `…in the / kitchen under pressure.` | `to truly test our culinary skills in the kitchen under pressure.` appears on one page |
| 16:9 | `…a total piece / of cake…` | `I am confident that it ends up being a total piece of cake` appears on one page |
| 9:16 | `…in the / kitchen under pressure.` | `in the kitchen under pressure.` appears on one page |
| 9:16 | `Alex. This will be…` | The first sentence stays together; a sentence tail is no longer joined to the next sentence |
| 9:16 | Capacity could separate `difficult / recipe` | General modifier/grammar preferences retain `a notoriously difficult recipe` together |

For the narrower layout, preserving a grammatical unit can require an extra page. Known learning phrases are protected only when they fit the existing limits. The English cues are heuristics, not a complete syntactic parser or a guarantee that every possible sentence has an ideal break.

## Verification

- **Before the fix:** four new regressions failed against the original code, reproducing both screenshot sentences across the two layouts; the four original paging tests still passed.
- **After the fix:** all **104 renderer tests / 14 files passed**; TypeScript `tsc --noEmit` passed. Caption paging now has 19 tests, including phrase identity, capacity fallback, overlapping phrases, Unicode punctuation, abbreviations, empty/short lines, reversed seeking and Edge/script number mismatches.
- **Real episode data:** checked all **22 lines × 2 layouts = 44 partitions**. Every token object, word order and timing was preserved; every page stayed within existing word/character limits. One measured pass over the 44 partitions took ~4.55 ms on this machine; this is a helper measurement, not a claim about full-episode rendering speed.
- **Production previews:** rendered 8 PNGs and 4 short H.264/AAC clips using the actual `Episode` composition, actual images, actual learning pack and stored word timings. Inspected representative horizontal/vertical frames around the reported cuts; text was legible and inside the caption area.
- **Media integrity:** all four clips decoded fully; frame counts are 150/186 per layout (5.0/6.2 s of video); MP4 container durations include ~0.05 s of AAC padding. All PNG dimensions match 1280×720 or 1080×1920.
- **Data preservation:** SQLite used `mode=ro` and `PRAGMA query_only=ON`, zero connection changes. Source MP3/WAV SHA-256 hashes match before/after previews. Existing project MP4/SRT files were not overwritten.
- No backend code changed; no full Python suite or full-episode regeneration was needed for this renderer-only fix. Older owner gates remain pending.

Commands from the repository root:

```powershell
Push-Location renderer
npm.cmd test
npm.cmd run typecheck
Pop-Location
node data/tmp/caption-fix-20261015/check_pages.mjs
python data/tmp/caption-fix-20261015/verify_media.py
git diff --check
```

## Preview and evidence locations

Local artifacts (runtime data is excluded from Git): `data/tmp/caption-fix-20261015/`.

- `horizontal-alex-final.mp4`, `horizontal-lina-final.mp4`: YouTube boundary previews.
- `vertical-alex-final.mp4`, `vertical-lina-final.mp4`: portrait boundary previews.
- `*-before-final.png`, `*-after-final.png`: timestamps immediately around the **old** problematic cuts; both show the **fixed** renderer, not an old/new software comparison.
- `real-pages-after.json`, `production-checks.json`, `source-media.json`, `media-verification.json`, `rendered-previews.json`.
- `prepare_props.py`, `check_pages.mjs`, `render_previews.cjs`, `verify_media.py`: disposable verification scripts. They are local evidence tools, not a required production dependency.
- Audit baseline: `.viepilot/audit/caption-continuity-20261015.md` and `data/tmp/caption-audit-20261015/real-pages.json`.

## Using the fix

The installed Windows trial links to this workspace's `renderer/` through `studio-runtime.json`; new renders from this installation use the updated renderer. Existing MP4s contain the old burned-in text and need to be rendered again to show the new pages. This task provides short review clips and does not replace the full exported episode.

The published `v1.4.0-rc.1` tag, ZIP and release source remain unchanged. The source fix is recorded under **Unreleased** on the owner branch; a fresh installation made from the old release tag alone does not include this patch. No new EXE or release-version claim is made for this task.
