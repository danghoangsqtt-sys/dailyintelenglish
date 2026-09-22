# Phase 14 Gate B-5 — Final Local-Only Trial (after 14.4a-d + 14.13)

- **Task:** 14.14 (PM execution). Protocol = Gate B-4 (Phase 13 §8 13.9 verbatim at the D13
  targets; B1 8-min = 1,000 words); the runner now applies the per-level default speaker
  speed (14.4a-d). Thresholds unchanged. **Phase 14 closes after this gate regardless of
  verdict** (plan §14).
- **Run date:** 2026-09-22 (06:2x–07:22Z UTC)
- **Code HEAD:** `a6169a6` (14.13). Runner `9b8d0be` (14.4a-d).
- **Evidence (gitignored):** `data/quality_reviews/phase14/gate-b5/gate-b5-local-20260922T072229Z.json`,
  SHA-256 `2398d93f101faa1b64074778da5346861c3e3cfc9ce768feaddaf4d87498fedb`;
  `local-matrix-console.log`.

## 1. Preflight

| Check | Result |
|---|---|
| Git | `a6169a6`, clean, upstream `origin/main`; Coder idle |
| Full suite | **902 passed**, 0 failed, 6m11s; `ruff` clean |
| Ollama / GPU | digest `6488c96fa5fa`; 1,217 MiB used; no orphaned `llama-server.exe` |
| Health | `mode: local`, `cloud_enabled: false` |

## 2. Primary set — five B1 eight-minute jobs at 1,000 words

| Run | Status | Seconds | Words | Repairs (semantic / length / repetition) | Speakers' speed |
|---|---|---:|---:|---|---|
| 1 | **complete** | 195.8 | **933** | 5 / 0 / 0 | 0.85 / 0.85 |
| 2 | **complete** | 225.9 | **969** | 3 / 0 / 0 | 0.85 / 0.85 |
| 3 | **complete** | 346.4 | **981** | 5 / 0 / 0 | 0.85 / 0.85 |
| 4 | **complete** | 216.9 | **1,002** | 2 / 0 / 0 | 0.85 / 0.85 |
| 5 | **complete** | 403.6 | **1,046** | 5 / 1 / **1** | 0.85 / 0.85 |

**5/5 complete, 5/5 pass all seven content checks.** Infra 0, `handler_exception` 0, max
attempts 2. Aggregates: within ±15% of nominal 44%; repair success 60%; σ 18.9% (B-2:
55.7%, B-3: 22.9%, B-4: 25.8%); total repairs 22.

**The D17 repetition repair fired three times in this trial (run 5, B1 10-min, C1) and
every one of those jobs completed** — the exact failure class that killed 2/5 primary runs
and 2/4 samples in Gate B-4. Job time rose where it fired (run 5: 404 s; still < 20 min).

### Samples — **4/4 complete, all checks pass** (first time)

| Run | Words / target | Repairs | Speed (level default) |
|---|---|---|---|
| B1 5-min | 573 / 625 | 4 | 0.85 |
| B1 10-min | 1,264 / 1,250 | 7 + 1 repetition | 0.85 |
| A2 8-min | 881 / 888 | 4 | 0.75 |
| C1 8-min | 1,128 / 1,160 | 4 + 1 length + 1 repetition | 1.00 |

## 3. Learning — **5/5** (gate satisfied; no dropped items needed)

## 4. Media (winning project = run 1, 933 words, 52 lines, speed 0.85 — the level default, now measured)

| Step | Result |
|---|---|
| Real Edge TTS | 52/52 |
| Mix | 200; **413.29 s**, −16.01 LUFS; MP3 8,267,564 bytes, `cc5e13a1…` |
| Render | 200; **413.29 s**; MP4 6,539,843 bytes, h264/aac, `4566fe37…` |
| Checks | codecs ✔; **A/V diff 0.00 s ✔**; duration **413.3 s ∉ [432, 528] ✘** (−4.3% below the floor) |

**Why it missed, measured not guessed.** 933 words / 413.3 s = **135 wpm at speed 0.85**,
versus the D13 calibration of 125 wpm at 0.85 (measured on one 730-word / 43-line script).
Two deviations compounded: the winning script sat at −6.7% of the 1,000-word target
(inside the ±10% gate), and this script's real pace was ≈ 8% faster than the
single-script calibration (line length, punctuation and voice all move the pace). Runs 4
and 5 (1,002 / 1,046 words) would play ≈ 445–465 s at the same pace — but the runner
evaluates the first passing run only, and the PM does not credit unmeasured numbers.

## 5. Decision (Phase 13 Gate B rule, unchanged)

| Gate | Result |
|---|---|
| Script 5/5 complete, ≥ 4/5 pass | **PASS 5/5, 5/5** (at 1,000 words; second consecutive script-gate pass) |
| Learning 5/5 | **PASS 5/5** |
| Media 432–528 s, A/V ≤ 1.0 s, codecs | **FAIL on duration only** (413.3 s); A/V 0.00 s and codecs PASS |
| Timing / infra | PASS |

**Overall Gate B-5: FAIL, on the media duration alone.** Every other gate passes. No
threshold was changed. Per plan §12/§14: D11 (local as primary) remains an owner override,
recorded as such; Phase 14 closes here.

## 6. Where Phase 14 leaves the system (for the record)

| Measure | Phase 13 Gate B | Gate B-5 |
|---|---|---|
| B1 8-min jobs complete | 1/5 | **5/5** |
| … passing all content checks | 0/5 | **5/5** |
| Samples complete | 0/4 | **4/4** |
| Learning | 1/1 | **5/5** |
| Infra failures | — (Gemini 0/2 on 503) | **0**; one transient absorbed |
| Repair measurable | no | yes (60% success; three repair classes) |
| Media pipeline | never ran | runs end to end; A/V exact; duration −4.3% |
| Cloud dependency | Gemini primary, free-tier quota | none |

**Recommended for a follow-up phase (not started, not decided here):** calibrate the
WPM table on ≥ 5 scripts per level (mean pace with its spread) instead of one; evaluate
the media gate on the completed run closest to the target (or on every completed run)
rather than the first passing run — a protocol change to be declared before it is used;
the deterministic fix for the ">5 consecutive lines" structural failure (not seen in B-5,
seen in B-3/B-4 samples); and the `_record_dropped_items` layering cleanup noted in 14.11.

## 7. Evidence

| File | SHA-256 / note |
|---|---|
| `gate-b5/gate-b5-local-20260922T072229Z.json` | `2398d93f101faa1b64074778da5346861c3e3cfc9ce768feaddaf4d87498fedb` |
| `gate-b5/local-matrix-console.log` | server + runner console; no key, no prompt text |
| MP3 / MP4 of project `0f12f884…` | `cc5e13a16bb32183…` / `4566fe375569a0f9…` |
| `gate-b2/trial-data/app.db` | shared trial DB (Gate B-2 … B-5) |
