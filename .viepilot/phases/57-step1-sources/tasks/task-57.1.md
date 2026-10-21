# Task 57.1 — Project source material

Status: planned 2026-10-21.

## Paths
- backend/db/migrations/030_project_source.sql (new)
- backend/schemas/project.py (`ScriptConfig.source_kind|source_text|source_use`)
- backend/content/project_service.py (insert, detail columns), backend/content/script_service.py (`parse_dialogue`, import at creation)
- backend/api/projects.py (create: word-for-word script saved in the same transaction)
- tests/test_project_source.py (new)

## File-Level Plan
Columns: `source_kind TEXT NOT NULL DEFAULT ''` ('' | 'dialogue' | 'vocabulary'), `source_text TEXT NOT NULL DEFAULT ''` (≤ 12 000 chars), `source_use TEXT NOT NULL DEFAULT 'rewrite'` ('rewrite' | 'verbatim'). Validation: text required when a kind is set; 'verbatim' only for a dialogue in a conversation project. `parse_dialogue(text, speakers)`: lines "Label: text" (label ≤ 30 chars); labels map to Speaker 1/2 in order of first appearance (a label equal to a speaker's name maps to that speaker); unlabelled lines continue the previous line; blank lines skipped; more labels than speakers or no line → validation error. Verbatim: the parsed lines are saved as the script when the project is created (language notes empty; Step 2 can still regenerate lines).

## Tests
Parser cases (A/B labels, names, continuation, too many labels); create with a vocabulary list stores it; verbatim dialogue gives a script immediately; verbatim refused for Solo and for vocabulary.
