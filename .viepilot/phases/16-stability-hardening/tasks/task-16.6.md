# Task 16.6 — Second Bounded Repetition Repair (ENH-009 step B) — CONDITIONAL

- **Status:** conditional — runs only if Gate B-7 (16.5) script gate < 5/5 on repetition
- **Owner:** Coder
- **Controlling detail:** plan §4 "16.6", invariant 24, owner decision D18

Description only until the PM opens it with Gate B-7 evidence. Outline:
`SCRIPT_PIPELINE_MAX_REPETITION_REPAIRS` 1 → 2. The second pass targets the **next-worst**
section by `find_repeated_8grams_by_section`, never the same section twice. It stays
bounded and separate from other repair budgets. Allowed files as for 16.4. Then Gate B-8
(16.7, PM).
