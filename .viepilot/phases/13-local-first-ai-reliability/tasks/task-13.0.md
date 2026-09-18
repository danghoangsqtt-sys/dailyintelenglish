# Task 13.0 — Baseline, ADR, Backup, and Rollback Contract

- **Status:** done (2026-09-18)
- **Dependency:** doc-first gate
- **Controlling detail:** implementation plan §8, Task 13.0

## Objective

Freeze reproducible API/content baselines, record the architecture decision, make a
verified online SQLite backup before migration, and prove the Gemini rollback path is
specified before product code changes.

## Allowed files

`docs/implementation/phase-13-local-first-ai-reliability.md`, Phase 13 state/task files,
`docs/architecture/adr-001-local-first-ai.md`, `tests/fixtures/ai/**`,
`scripts/verify_ai_baseline.py`, `.env.example`.

## Risks and controls

- Live DB copy can be inconsistent: use SQLite Online Backup API/`.backup`, then
  integrity and foreign-key checks. Never use `Copy-Item` on a live DB.
- Backup contains the stored API key: keep it under ignored `data/backups/`, do not
  print values, stage it, or upload it.
- Fixtures can leak content/secrets: sanitize them and check staged diff before commit.

## Verification and exit

Baseline verifier exits 0; backup hash/size/schema/project count recorded;
`integrity_check=ok`; `foreign_key_check` empty; no application code changed; rollback
contract is unambiguous. Record exact commands/results in this task before marking done.

## Evidence

- Controlling plan: 595 lines; 11 task contracts; two independent read-only plan
  reviews integrated; no placeholder markers; `git diff --check` clean after formatting.
- `venv\Scripts\python.exe scripts\verify_ai_baseline.py`:
  `AI baseline OK: 3 golden projects, 4 endpoint contracts`.
- `venv\Scripts\python.exe -m ruff check scripts\verify_ai_baseline.py`:
  `All checks passed!`.
- Online backup path (local and gitignored):
  `data/backups/app-before-phase13-20260918T164151Z.db`.
- Backup size: `1,290,240` bytes.
- Backup SHA-256:
  `ba0359aad4bdcd0222781ce9ffb61278f2c94c6efc893432f687b082538fd033`.
- Source and backup both: `integrity=ok`, zero foreign-key violations, 6 migration
  records, 293 projects, 573 script lines, 157 learning-content rows.
- Port 8000 remained owned by the existing process 33604 throughout; it was not stopped.
- The first direct verifier run exposed a real import-path defect in the new script;
  fixed using the repository's established `sys.path` bootstrap and re-run successfully.
- The first metadata query used the historical singular table name `learning_content`;
  the migration intentionally replaced it with `learning_contents`. The backup itself
  was valid; the corrected query passed against both source and backup with equal counts.

**Acceptance:** complete. No product runtime code or migration was changed in Task 13.0.
