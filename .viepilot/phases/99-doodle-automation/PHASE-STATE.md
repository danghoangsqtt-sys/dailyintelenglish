# Phase 99 state

Status: implemented_verified (2026-11-06) — see the last section for the real automatic run. [Plan](PLAN.md).
Owner: "hoàn thành luôn Phase 98 99 và cài bản mới nhất" (`/vp-auto`). Branch `claude/phase98-99-doodle`.

| Task | Scope | Status |
|---|---|---|
| 99.1 | Series keeps its story type; projects from a Doodle series (D168) | done — migration 042, schema, service; tests |
| 99.2 | The batch makes a Doodle story series (D169) | done — template, request fields, prompt rule; tests |
| 99.3 | Night runner: story skips the fact check (D170); picture time and no-picture stop (D171) | done — tests; the no-picture stop seen in a real run |
| 99.3b | Target words repaired across the story (D172) | done — found by real run 1; tests |
| 99.3c | Editor keeps the story's words (D173); Channel stories read at their level's pace (D174) | done — found by real run 2; tests |
| 99.4 | Channel plan and batch page offer Doodle story | done — checked in the browser on an isolated copy |
| 99.5 | Full tests and one real automatic Doodle run | done — full pytest 2434 passed, Vitest 220, type check clean; run 3 below |

## Real automatic runs (isolated copy of the production database, port 8011, cloud AI from the workspace `.env`)

All runs: a Channel-plan series (short story, 3 minutes, B1, narrator Lina) with one episode, made by the night runner's own `Producer`.

| Run | Outcome | What it showed |
|---|---|---|
| 1 (code 03319806) | stopped at script twice: `doodle_vocabulary_incomplete` | one repair of one section cannot reach 3 uses per word → D172 |
| 2 (D172) | script, learning, audio passed; stopped at the plan: ".venv-image missing" → "Draw or upload the story's pictures" | D171 stop works; the editor rewrite lost the story's notes and the profile speed 1.0 made 338 words last 115.7 s → D173, D174 |
| 3 (D172-D174, c2cac553) | **waiting for review**, 1123.5 s end to end | script 36.0 s (both sections word-repaired, 6 words kept, none dropped), learning 9.0 s, audio 14.2 s, plan + 26 Qwen pictures 939.4 s, render 119.3 s, thumbnail 2.8 s, YouTube 2.6 s. The editor's rewrite (260 words, no target words) was refused by D173; narrator speed 0.85 (D174). |

Run 3 MP4: 151.767 s, 1920x1080, 30 fps, H.264/AAC, A/V diff 0.000 s, no black span >= 2 s, no silence >= 3 s inside, SRT valid.
Frames at 20 s and 75 s: the same hero (glasses, yellow backpack) in different pictures; the pill caption shows the target word "integrity".

**Known limit (BUG-056 territory, not fixed here):** the narration lasted 143.3 s for a 3-minute story. 360 words at the B1 speed run about
151 words a minute, faster than the 125 the script length assumes; a 0.796 tempo would be needed, beyond the 0.82 the Doodle fit allows, so the
story stays shorter than chosen. A longer script for Doodle (or a calibrated words-per-minute) is the follow-up.

**Other observations:** fault-free cloud runs; the first Read Along run (Phase 100) timed out while Qwen held the GPU because its script call
fell back to the local model; see Phase 100 state.

Evidence (git-ignored, worktree of this branch): `data/tmp/phase98-99-close/auto-run*.txt`, `auto-verify.json`, `auto-20.jpg`, `auto-75.jpg`.

