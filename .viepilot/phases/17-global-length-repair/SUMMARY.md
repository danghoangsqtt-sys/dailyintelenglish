# Phase 17 Summary — Budget-Aware Global Validation (ENH-010)

- **Status:** complete. Opened and closed 2026-09-23.
- **Plan:** `docs/implementation/phase-17-global-length-repair.md` (Amendments A–C)

| Task | Result | Commits |
|---|---|---|
| 17.1 Budget-aware global stage | Nominal-deviation targeting; the full per-section rerun (`_run_section_pipeline`); an ordered 2-slot loop (budget then repetition); a length-aware repetition repair; the shared error prefix | `caab2e2`, `b265221`, `5930aaf` |
| 17.2 Final-section sign-off | Sign-off instruction and the rule-5 exemption, both last-section only; `has_outro_last3` diagnostic | `4950f25`, `80f04b6` |
| 17.3 Gate B-8 | Runner PASS (B1 5/5, samples 4/4); owner config 1/2 exposed the "under" plain-repair overshoot | `09b8f1e` |
| 17.4 "Under" via the full path | The plain-repair branch was removed | `5008792` |
| 17.5 Re-gate | **B1 5/5, owner config 4/4**; every global repair recovered its job | report `phase17-gate-b8r.md` |

Suite 956 → **964**. Every task was PM-reviewed with independent revert checks.

## Lessons

- The PM's own guidance caused one defect: C4's "under keeps a plain repair", which the PM's
  own evidence already contradicted. The owner-config sample in the gate caught it. **Keep the
  owner's own configuration in every gate.**
- A gate report claim ("no global repair exists") was wrong and had to be corrected in an
  erratum. Read the checkpoints before writing a report's causal section.

## Residuals

- The A2 small_talk sign-off is sometimes missing (2 occurrences). Re-check under the Phase 18
  cloud primary.
- Rerun continuity with the following section was not observed as a problem; keep watching.
