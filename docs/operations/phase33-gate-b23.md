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
