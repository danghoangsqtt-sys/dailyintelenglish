# Phase 18 State — Cloud-First AI with Local Fallback (ENH-011)

## Metadata

- **Phase:** 18
- **Slug:** `18-cloud-first-ai`
- **Status:** open (2026-09-23; handover to the Coder in the Phase 17 close-out commit, `0197cbd`)
- **Planned:** 2026-09-23 (`/vp-evolve ENH-011`)
- **Controlling plan:** `docs/implementation/phase-18-cloud-first-ai.md`
- **Authorization:** owner decisions D21–D24 (brainstorm `docs/brainstorm/session-2026-09-23.md`).
- **Ownership of this folder:** PM until the handover commit, Coder after it.

## Preflight (to be completed when the phase starts)

- Phase 17 closed 2026-09-23. The local baseline for Gate B-9's comparison is the Phase 17 re-gate `docs/operations/phase17-gate-b8r.md` (B1 5/5, owner 4/4) plus Gate B-8 for the samples.
- Full suite **964/964**, `ruff` clean (start of Phase 18).
- The owner's OpenRouter key is present in `.env` as `DIE_OPENAI_COMPAT_API_KEY`, on the free
  tier (checked 2026-09-23, never printed).

## Task status

| Task | Description | Owner | Status |
|---|---|---|---|
| 18.1 | `OpenAICompatProvider` | Coder | done (ACCEPTED, `2a6a77c`) |
| 18.2 | Router roles/modes, per-provider budgets, circuit breaker; Gemini provider removed | Coder | done (ACCEPTED, `16209c6` + N1 `28196a4`) |
| 18.3 | Settings (key/URL/model, test connection), health fields, privacy note | Coder | done (ACCEPTED, `3e7c09f` + N1 `5301536` + N2 `4342bf3`) |
| 18.4 | Fallback-rate readout + runner `--matrix cloud_first` | Coder | done (ACCEPTED, `4e21554`) |
| 18.5 | Gate B-9 A/B, cloud_first vs local | PM | done (`docs/operations/phase18-gate-b9.md`, `4828f10`) -- PASS on the runner criterion, regression on samples/speed; `AI_MODE` default stays `local` (Amendment C) |
| 18.6 | Cloud model chain + speed tuning (D27, plan Amendment D) | Coder | done (pending PM ACCEPTED) |
| 18.7 | Gate B-10 | PM | not started -- moves after 18.8 (Amendment E) |
| 18.8 | Multi-provider cloud chain (D28, plan Amendment E) | Coder | not started |

## Evidence log

(Coder and PM append per task.)
