# Phase 14 Summary — AI Gateway Resilience and Section Budget Rebalancing

- **Status:** complete
- **Started:** 2026-09-21
- **Closed:** 2026-09-22
- **Controlling plan:** `docs/implementation/phase-14-ai-gateway-resilience.md`
- **Full state/evidence log:** `PHASE-STATE.md` (this folder)

## Objective

Phase 13 closed with an unresolved AI-provider decision: Gate B (Task 13.9) measured
1/5 real local-only script completions against Gemini as the provisional primary, and
Task 13.10 (rollout) was blocked pending that call. Phase 14 set out to (1) harden the
local (Ollama) path with bounded backoff, richer job telemetry, and a running
section-word-budget so a real local run could be re-measured fairly; (2) let the owner
make the actual provider decision once real evidence existed; and (3) once that
decision (drop Gemini, ship local-only) was made, close the loop with however many
more real Gate B re-runs were needed to separate genuine product gaps from
measurement/tooling defects — closing the phase on a declared schedule (Gate B-5)
rather than chasing gates indefinitely.

## Tasks (14.1–14.14, chronological)

| Task | Description | Owner | Commits |
|---|---|---|---|
| 14.1 | Bounded exponential backoff for transient provider errors | Coder | `2bd203c` (plan), `2384578` (impl); Amendment A `378bf4d`/`990a6b7` |
| 14.2 | Job telemetry: repair/fallback/provider/attempts/error codes | Coder | `73e5e6b` (plan), `cde8e79` (impl); Amendment B `c93d152`/`ba086d5` |
| 14.3 | Running section budget; hard gate only at global ±10% | Coder | `a530be3` (plan), `039bc8d` (impl) |
| 14.4a | Gate B-2 runner prep (classification, per-section stats, aggregates) | Coder | `1fb6526` (plan), `377f140` (impl); Amendment C `92baabf`/`153aa16` |
| 14.4a-c | Runner fixes from the real local Gate B-2 run (media 500, word-count scoring) | Coder | `dec4913` |
| 14.4b | **Gate B-2**: second run, both providers, declared protocol | PM | `b6a8eac`/`92ca433` (reports), `ad17925`/`86fa9b3` (state) |
| 14.5 | Correct `docs/operations/phase13-acceptance.md` | PM | (parallel, folded into `3872556`) |
| 14.1-b | Gemini backoff redesign | — | **dropped (D12)** — superseded by Amendment D, never started |
| — | **Amendment D** (owner drops Gemini, D9–D12): local-only path | Owner/PM | `94f5e7b`/`de7dbc9` |
| 14.7 | Local-only mode, config-first (ADR-001 A2) | Coder | `1661708` (plan), `518dd0a` (impl); Amendment F `ff99679`/`d623b29` |
| 14.8 | Local hardening: length-only repair pass | Coder | `824cc67` (plan), `ac61cf8` (impl); 14.8-b CR-02 fix `4542b58` |
| 14.9 | **Gate B-3**: local only, post-hardening | PM | `c6c2f35` |
| 14.6 (revised) | Resume Task 13.10: local-only rollout, rollback drill | Both | Coder `4a7383e`/`1c89b6a`/`1f723de`; PM `d5c817e`/`48695ba`/`fe9589e` |
| — | **Amendment G** (D13–D16, delegated to PM): pace calibration, D14 A/V rule, learning repair-by-removal | PM | `fd35485` |
| 14.10 | Pace calibration, measured not assumed (D13); D14 A/V fix | Coder | `0db62e9` (plan), `ec26846` (impl) |
| 14.11 | Learning repair by removal (D15) | Coder | `3f99f08` (plan), `394a794` (impl) |
| 14.12 | **Gate B-4**: local only, post-calibration | PM | `e018359` |
| — | **Amendment H** (D17–D18, delegated to PM): repetition repair, runner speed defect | PM | `d8553c9` (cards), `e018359` (decisions) |
| 14.4a-d | Runner: apply the CEFR level default speed | Coder | `9b8d0be` |
| 14.13 | Repetition repair (D17) | Coder | `256ba01` (plan), `a6169a6` (impl) |
| 14.14 | **Gate B-5**: local only, Phase 14 close-out | PM | `e9a013d` |

No Task 14.0 exists — Phase 14 began at 14.1 (unlike Phase 13, which opened with a
dedicated 14.0-style baseline/ADR task).

## The five real Gate B measurements

| Gate | Script (B1 8-min) | Samples (5/10-min + A2/C1) | Learning | Media | Verdict |
|---|---|---|---|---|---|
| Gate B (Phase 13, Task 13.9) | 1/5 complete (8/9 attempts failed the old ±15% section validator) | not reached | 1/1 (only script) | never run (no winning config) | **FAIL** |
| Gate B-2 (14.4b) | Local 3/5; Gemini FAIL-INFRA 0/5 | not fully scored (runner bug, fixed after) | — | ran end-to-end after the runner fix, but duration/A-V failed (pace ~135 wpm vs. the then-planned 100) | **FAIL** (stop condition — led to Amendment D) |
| Gate B-3 (14.9) | **5/5 PASS — first time** | — | 4/5 | FAIL as declared (surfaced the real pace-calibration gap) | **FAIL** (learning + media) |
| Gate B-4 (14.12) | 3/5 (both deaths: repeated-8-gram check only — word count now solved by 14.10) | — | 3/3 | A/V diff 0.00s (D14 confirmed real); duration FAIL — runner defect (hard-coded speed, not a product gap) | **FAIL** |
| Gate B-5 (14.14) | **5/5 complete AND 5/5 pass**, σ 18.9% (933/969/981/1002/1046 words) | **4/4 — first time** | **5/5** | A/V 0.00s, codec pass, duration FAIL (413.3s, -4.3% — script landed at the low end of tolerance + real pace ~135 wpm running modestly faster than the single-script 125 wpm calibration) | **FAIL, on media duration only** |

**Before → after, across the whole phase:** script completion 1/5 → 5/5; samples 0/4 →
4/4; learning 1/1 → 5/5. Task 14.13's repetition repair fired 3 times in the Gate B-5
matrix and all 3 of those jobs still completed — the exact failure class that killed
2/5 jobs at Gate B-4 is neutralized.

**Final decision (D11, unchanged throughout):** local-only ships regardless of Gate B
verdict — this was an explicit owner override after Gate B's original FAIL, not a
promise to keep re-running gates until one passes outright. Script/samples/learning all
pass cleanly at Gate B-5; only media duration still misses, by a small and
well-understood margin. Phase 14 closes here per the plan's own schedule (§14).

## Known residuals (not fixed in this phase, flagged for whoever picks up the next one)

- **Pace calibration was measured from a single script, and the media-duration gate's
  protocol never accounted for that.** D13's `CEFR_WORDS_PER_MINUTE`/
  `CEFR_DEFAULT_TTS_SPEED` table came from one real Edge TTS measurement run (the Gate
  B-3 winning script), declared as such at the time (not silently assumed to
  generalize). Gate B-5's media-duration miss is consistent with normal script-to-script
  pace variance around that single measurement, not a new defect — a future gate
  protocol should calibrate from multiple scripts (or accept a wider tolerance band
  reflecting real variance) rather than one sample.
- **The consecutive-lines structural check has no repair path.** Every other hard
  failure mode this phase touched (word budget, over-length, repeated 8-grams) now gets
  a bounded repair attempt before failing the job. A consecutive-lines violation still
  hard-fails immediately (Task 14.3's original design: structural errors are never
  eligible for accept-and-carry or repair). This was never revisited — a real, if
  probably rare, residual gap between this check and every other content check's
  repair-then-fail pattern.
- **`learning_pipeline._record_dropped_items` (Task 14.11) is a workaround, not the
  ideal home for its logic.** `app/services/ai_job_service.py` was outside Task 14.11's
  allowed files, so the dropped-items metrics_json write is a small local
  read-modify-write helper duplicating `record_generation_call`'s own shape, rather than
  a proper shared function in `ai_job_service.py`. Functionally correct and tested, but
  worth folding into `ai_job_service.py` as a real cleanup if that file is ever opened
  for an unrelated task.
- **`scripts/run_ai_operational_trial.py` writes every gate's evidence into a
  fixed `data/quality_reviews/phase14/gate-b2/` subdirectory**, regardless of which
  gate is actually running (confirmed directly: Gate B-3/B-4/B-5's own media artifacts
  all live under the `gate-b2/` path, found while ffprobing real Gate B-3 media during
  Task 14.10's D14 investigation). Harmless in practice (PM's own gate reports cite the
  real paths), but a confusing on-disk layout for anyone browsing the evidence
  directory tree directly — worth a one-line fix if the runner is ever touched again.

## Full history

See `PHASE-STATE.md` in this folder for the complete task-by-task execution record
(plans, commands, deviations, revert-and-confirm-failure evidence) and the individual
`tasks/task-14.*.md` cards for each task's full doc-first design record. Gate reports
live at `docs/operations/phase14-gate-b{2,3,4,5}.md`.
