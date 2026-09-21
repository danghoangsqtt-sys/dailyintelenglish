# Task 14.4 — Gate B Second Run, Both Providers

- **Status:** pending
- **Owner:** 14.4a Coder (runner preparation); 14.4b PM (execution and report)
- **Priority:** P1
- **Dependency:** 14.1, 14.2, 14.3 merged and PM-reviewed; 14.4a before 14.4b
- **Controlling detail:** plan §4.4, §6 Task 14.4

## Objective

Measure, under a protocol declared before any run, whether each provider can now
complete real eight-minute script jobs, separating infrastructure failures (503/429/
timeout/quota) from content failures (word count), and quantifying repair, backoff, and
per-section behaviour. The result selects the rollout mode for Task 13.10 (14.6).

## 14.4a — Runner preparation (Coder)

**Allowed files:** `scripts/run_ai_operational_trial.py` only.

**Required changes:**

1. Failure class per run from `error_code`: `infra` if it starts with `provider_`;
   `content` for `section_validation_failed`/`global_validation_failed`; `other`
   (including `handler_exception`) otherwise. Keep the existing word-count breakdown.
2. Read `metrics.calls[]` from the job API per run and report: total attempts, total
   backoff seconds, max attempts on one call, absorbed transient errors
   (`sum(attempts − 1)` over calls that ended `ok`), `repair_count`, `fallback_count`,
   `actual_provider`, `model`.
3. Per-section table from the trial DB `ai_generation_checkpoints.metrics_json`
   (`stage='section'`): nominal, effective, actual words, deviation %, repaired,
   words before repair.
4. Aggregates per matrix: completion rate; content pass rate; infra failure count;
   per-section within-±15%-of-nominal rate; repair success rate (repairs that ended
   inside ±15% of effective); mean/σ section deviation; totals vs 720–880; total
   backoff seconds; max attempts observed.
5. `--matrix local|gemini` (replaces ad-hoc `--mode` use for gates; keep `--mode` for
   raw diagnostics): local matrix = Phase 13 13.9 protocol verbatim; Gemini matrix =
   5 × B1 eight-minute + learning per completed script, samples optional
   (`--with-samples`), media pipeline optional (`--with-media`), `AI_MODE=gemini`.
6. Decision output per plan §4.4: local → PASS/FAIL (13.9 rule); Gemini → PASS-cloud /
   FAIL-CONTENT / FAIL-INFRA; any `handler_exception` flagged as a defect. Partial
   matrix stays `DIAGNOSTIC_ONLY`. A two-day split of the Gemini matrix is supported by
   `--resume-evidence <json>` so five runs across two files aggregate as one matrix.
7. `has_outro` false negative (disclosed in the Phase 13 report): treat the final line
   as an outro when it matches the widened marker list **or** the outline's last
   section objective mentions closing/outro/farewell; document the rule in the docstring.
8. Evidence under `data/quality_reviews/phase14/gate-b2/` (gitignored). Never port 8000.
9. `--reaggregate <evidence.json>`: recompute aggregates/decision from an existing
   evidence file without running anything (used to verify the new code against the
   Phase 13 files).

**Verification (Coder — no live trial):** `ruff` clean; `py_compile`; `--reaggregate`
against `data/quality_reviews/phase13/gate-b/gate-b-20260921T000903Z.json` and
`…T010451Z.json` reproduces the known counts (local 1/5 complete; Gemini 0/2, both
`infra` once 14.2's codes exist — for the old files they classify as `other` with
message `ProviderUnavailableError…`; both outcomes must be printed and pasted here).
**The Coder never runs a live trial** (`OLLAMA_NUM_PARALLEL=1`).

## 14.4b — Execution and report (PM)

**Allowed files:** `docs/operations/phase14-gate-b2.md`,
`data/quality_reviews/phase14/gate-b2/*` (gitignored), runtime-created rows/media.

**Preflight (all recorded in the report):**

- User confirms the Coder is idle; `git rev-parse HEAD`; worktree clean; full suite
  green at that HEAD.
- Ollama env set (`OLLAMA_HOST=127.0.0.1:11434`, `OLLAMA_MODELS=D:\DataAdmin\OllamaModels`,
  `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_QUEUE=4`,
  `OLLAMA_NO_CLOUD=1`); `curl http://127.0.0.1:11434/api/tags` shows digest
  `6488c96fa5fa…`.
- Three direct Gemini `generateContent` probes, status codes logged.
- Live RPM/RPD for `gemini-3.8-flash` from the AI Studio dashboard. If RPD < ~35, the
  Gemini matrix is split 3 + 2 across two calendar days, declared here before run 1.
- `nvidia-smi` baseline; port 8000 untouched.

**Sequence:** local matrix (full 13.9 protocol) → Gemini matrix. Never concurrent.
Between matrices, verify no job is active on the trial DB.

**Measured per run / per section / aggregate:** exactly plan §4.4.

**Decision rules (declared, immutable):**

- Local: Phase 13 Gate B rule verbatim → PASS promotes local in development.
- Gemini: PASS-cloud = 5/5 complete ∧ ≥ 4/5 content pass ∧ ≤ 1 infra job death.
  Absorbed transient errors (retries that ended `ok`) are the 14.1 success signal, not
  failures. ≥ 2 infra deaths → FAIL-INFRA (reopens 14.1, blocks 14.6). Content failures
  alone → FAIL-CONTENT.
- Any `handler_exception` → defect triage before quoting the matrix.
- Thresholds never weakened after seeing results.

**Report (`docs/operations/phase14-gate-b2.md`):** preflight; per-run tables; per-
section tables; aggregates; both decisions with reasons; comparison against the Phase 13
run (per-section pass rate, repair effectiveness now measurable, backoff absorption);
open questions answered or carried (−9% compensation; 3 vs 4 attempts); evidence file
names and SHA-256.

## Execution record

- 14.4a (Coder):
- 14.4b (PM):
