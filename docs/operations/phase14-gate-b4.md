# Phase 14 Gate B-4 — Local-Only Trial at the Calibrated Targets (after 14.10 + 14.11)

- **Task:** 14.12 (PM execution). Protocol = Gate B-3 (Phase 13 §8 13.9 verbatim), now at the
  D13 targets: B1 8-min = **1,000 words** (5 × 200); the runner's per-run range derives from
  the constant (900–1,100). Thresholds unchanged.
- **Run date:** 2026-09-22 (02:4x–03:16Z UTC)
- **Code HEAD:** `394a794` (14.11). Runner unchanged since `dec4913`.
- **Evidence (gitignored):** `data/quality_reviews/phase14/gate-b4/` (copied from the runner's
  fixed `gate-b2/` output path, as in B-3). SHA-256 of the evidence file:
  `7cd8704b7e24fa7fe243f9f9ed89b6a185908cd11b6fd74336b873510bf4a5ce`.

## 1. Preflight

| Check | Result |
|---|---|
| Git | `394a794`, worktree clean, upstream `origin/main`; Coder idle |
| Full suite | **891 passed**, 0 failed, 6m15s; `ruff` clean |
| Calibration | `compute_target_words("B1", 8) == 1000`, `plan_sections == [200]*5` |
| Ollama | digest `6488c96fa5fa`; health `cloud_enabled: false` |
| GPU | 11.7 GB was held by two orphaned `llama-server.exe` runners left by the 14.6 drill (parents dead); the PM could not stop them (auto-mode permission), the owner cleared them; 1,163 MiB before the run |

## 2. Primary set — five B1 eight-minute jobs at 1,000 words

| Run | Status | `error_code` | Seconds | Words | Repairs | Note |
|---|---|---|---:|---:|---:|---|
| 1 | **complete** | — | 232.1 | **991** | 4 | all 7 content checks pass |
| 2 | error | `global_validation_failed` | 208.0 | (983) | 5 | **repeated 8-gram ratio 1.02% ≥ 1%** |
| 3 | **complete** | — | 162.8 | **984** | 3 | all pass |
| 4 | error | `global_validation_failed` | 162.8 | (979) | 3 | **repeated 8-gram ratio 4.32% ≥ 1%** |
| 5 | **complete** | — | 153.8 | **915** | 6 | all pass; one length-only repair (291 → 193) |

Aggregates: completion 3/5; content pass 3/3 of completed; **infra 0, `handler_exception`
0, max attempts 2** (one transient absorbed); per-section within ±15% of nominal 52%;
repair success **65%** (13/20; B-3 45%); σ 25.8%; mean −3.2%; totals in range 3/3.

**The word-count problem is solved at 1,000 words too** — every one of the 25 primary
sections landed the job inside ±10% or was on its way to; neither failure is a word-count
failure. **The new dominant failure is repetition**: the global "repeated 8-gram ratio
< 1%" check killed 2/5 primary runs (one at 1.02%, one at 4.32%) and 2/4 samples (A2
1.69%, C1 1.77%). At 1,000 words a 1% ratio is ≈ 10 repeated 8-word windows; the local
model's verbal tics (repeated framing phrases across sections) cross it more often as
scripts get longer. There is currently **no repair path** for this check — it is a global
hard error with no targeted retry, unlike word count (final-section budget repair).

Samples: B1 10-min **complete** (1,245 / 1,250 words, all checks pass, 7 sections, 8
repairs); B1 5-min structural (`unknown speaker_id` — a truncated UUID hallucinated by the
model — plus consecutive lines); A2 and C1 died on the 8-gram ratio.

## 3. Learning — **3/3** (gate satisfied on the completed set)

All three packs complete on the first pass; `dropped_items` empty (14.11's removal path
was not needed this time; it is exercised by tests).

## 4. Media (winning project = run 1, 991 words, 45 lines)

| Step | Result |
|---|---|
| Real Edge TTS | 45/45 |
| Mix | 200; **376.81 s**, −16.01 LUFS; MP3 7,537,964 bytes, `69b106ef…` |
| Render | 200; **376.81 s**; MP4 6,289,859 bytes, h264/aac, `b3b92a9d…` |
| Checks | codecs ✔; **A/V diff 0.00 s ✔ (D14 fix confirmed — was 2.48–2.52 s)**; duration 376.8 s ∉ [432, 528] ✘ |

**Why the duration still fails — a runner defect, not a D13 defect.** The runner builds
its test speakers with `"speed": 1.0` hard-coded (`run_ai_operational_trial.py` ≈ line
164), so 14.10's per-level default (B1 → 0.85) never applied; the audio was rendered at
speed 1.0 (991 words / 376.8 s ≈ 158 wpm). Scaling by the measured 0.85 / 1.0 ratio
(350.7 / 301.5) predicts **≈ 438 s at the B1 default — inside 432–528** — but that is a
prediction, not a measurement, and is not credited. The runner must send no `speed` (as
the UI now does) so the level default applies; Gate B-5 measures it.

## 5. Decision (Phase 13 rule, unchanged)

| Gate | Result |
|---|---|
| Script 5/5 complete, ≥ 4/5 pass | **FAIL — 3/5** (both deaths: 8-gram repetition) |
| Learning 5/5 on completed scripts | PASS 3/3 |
| Media 432–528 s, A/V ≤ 1.0 s, codecs | **FAIL on duration** (runner speed defect); A/V and codecs PASS |
| Timing / infra | PASS |

**Overall Gate B-4: FAIL.** D11 remains an owner override. No threshold was changed.

## 6. PM decisions (delegated authority, D17–D18) and next steps

- **D17 — Repetition repair (Task 14.13, Coder).** When `validate_global` fails **only** on
  the repeated-8-gram check, locate the section(s) contributing the most repeated windows
  and regenerate the single worst one once through the repair prompt with the offending
  phrases named ("do not reuse these phrases: …"); bounded by a new
  `SCRIPT_PIPELINE_MAX_REPETITION_REPAIRS = 1`; re-run `validate_global`; still failing →
  `global_validation_failed` as today. Also add the prior sections' most frequent 8-grams to
  the section prompt's continuity note so the model is told what not to repeat. The 1%
  threshold and the check itself are **unchanged**.
- **D18 — Runner speed (14.4a-d, Coder, `scripts/run_ai_operational_trial.py` only).** Stop
  hard-coding `"speed": 1.0`; omit the field so the API applies `CEFR_DEFAULT_TTS_SPEED`
  exactly as the UI does. Record the resolved speed in the run evidence.
- **Gate B-5 (14.14, PM)** after both land: same protocol; media must be measured at the
  level default.

## 7. Evidence

| File | SHA-256 / note |
|---|---|
| `gate-b4/gate-b4-local-20260922T031554Z.json` | `7cd8704b7e24fa7fe243f9f9ed89b6a185908cd11b6fd74336b873510bf4a5ce` |
| `gate-b4/local-matrix-console.log` | server + runner console; no key, no prompt text |
| MP3 / MP4 of project `964abd65…` | `69b106ef5f1d6bd9…` / `b3b92a9d635db57f…` |
| `gate-b2/trial-data/app.db` | shared trial DB |
