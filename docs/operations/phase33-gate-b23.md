# Phase 33 — Gate B-23 (owner review)

Date: 2026-10-12. Project: `Gate B-23: weekend plans with three friends` (`afbc299e-2362-4b8b-8d65-65ca01984f47`).

## Real app switch-over

- Backups: `data/backups/app-before-phase33-real-20261012-222423.db`,
  `data/backups/library-characters-sprites-before-phase33-20261012-222423.tgz`.
- The real app (port 8000) restarted on the Phase 33 code: migrations 018–020 applied; Lina and Alex kept their IDs, assets and
  the Demo Episode cast (seed profiles, American voices); 58 legacy sprites registered; `PRAGMA foreign_key_check` clean.
- Jack (made by the owner in the sandbox copy with the Quick create + slot flow) copied into the real data: 40 asset rows, no
  missing file; his video pack holds 26 pictures. Left out by the pack checks: `gesture-wave` and `gesture-wave__open` (head
  moved 14 px sideways against the base: it would jump), and `gesture-think__open` (still waiting for review).

## The project (production API, script `scratchpad/gate_b23.py`)

| Step | Result |
|---|---|
| Step 1 equivalent | 3 speakers cast by ID: Alex, Lina, Jack |
| Script (AI job) | 111.5 s, 9 lines, 3 per speaker, order Alex → Lina → Jack ×3 |
| Audio | 18 s, 120.448 s long, `lines_without_words` 0 |
| Storyboard | AI proposal approved as is: 4 beats (cafe scenes, one insert) |
| Video | `podcast_sprites`, Remotion, 144.8 s render, 136.384 s, full decode clean |

## What to check (frames in `data/video/<project>/phase33_evidence/sheet.png`)

| Line | On screen | Rule |
|---|---|---|
| 1 Alex | Alex left, Lina right | D81 man left, woman right |
| 2 Lina | Alex left, Lina right | — |
| 3 Jack | Jack left, Lina right | Jack replaces Alex for his line (Task 33.8 segments) |
| 4 Alex | Alex left, Jack right, Jack mirrored | D81 same gender: speaker order; D82 facing each other |

Seen in passing (not part of B-23): the AI script still greets with the old name "Daily Intel English Studio".

## Owner review and re-render (2026-10-13, Task 33.10)

Owner: "video rất tốt nhưng tôi không thấy hình minh họa và từ vựng hiển thị lên?" Causes: the gate script skipped Step 3
(no learning pack, so no vocabulary cards), and the only storyboard insert ("searching for travel accommodation") matched no
Activity Library picture. Fixed in Task 33.10 (the storyboard prompt lists the library activities; Step 5 names inserts
without a picture; missing ones can be drawn on the GPU or made with an outside AI, D102).

Re-render on the real app (restarted with the owner's permission after a DB backup,
`data/backups/app-before-migrations-021-022-20261013-095651.db`; migrations 021-022 applied, integrity ok), same script and
audio (`scratchpad/gate_b23_rerun.py`):

| Step | Result |
|---|---|
| Learning pack | 15 s: 4 vocabulary, 2 idioms, 1 collocation, 1 phrasal verb, 1 pattern, 3 questions |
| Storyboard (AI) | 4 beats: talk (lines 0-2), insert "find hotel" (3-4), insert "packing" (5), talk (6-8) |
| Illustrations | both inserts matched library pictures (generic) -- nothing to draw |
| Video | Remotion, 90.8 s render, `video_remotion.mp4` |

Frames (`data/video/<project>/phase33_evidence/rerun_sheet.png`): vocabulary cards (getaway, scenic, secluded, on board)
with Vietnamese meanings, karaoke highlight, the hotel and packing pictures behind the speakers on their lines. The
greeting still says "Daily Intel English Studio": the script was kept on purpose (new scripts use the new name, Task 35.1).
