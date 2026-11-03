# Task 88.1 — `grammar` template: data and script

See [PLAN.md](../PLAN.md); D125 (VieNeu for Vietnamese narration), D126 (≤ 3 min), D127 (brand colours).

## Objective

A Short with `explainer_style = "grammar"` gets a script built from one schema-checked **grammar lesson** (sample B:
break the rote formulas, one rule that explains them, 3–6 scenes of stacking cards, a summary table, the one core rule).
Each script line is one beat and keeps its card data in its language notes (`grammar`), so the renderer (88.2) draws the
beat from its own line and Step 2 can still edit the spoken text.

## Design (written before code)

- **Style registration** (`backend/schemas/project.py`): `grammar` joins `SOLO_SHORT_STYLES`, the explainer-style
  literal, `LINE_DRAWN_STYLES` and `ACADEMIC_STYLES` (2 min default, 3 min max like `roots`).
- **Lesson model** (`backend/content/grammar_lesson.py`, new):
  `GrammarLesson {point, kind: essence|vietnamese_error, hook {pain, formulas[2–6], promise}, scenes[3–6] {label, title,
  subtitle, steps[1–4] {say, card}}, summary {title, columns[2–3], rows[2–5] {cells, say}}, core_rule, quiz? {question,
  options[2–3], answer}}`. One flat `GrammarCard {kind: formula|compare|table|rule|example|sticker|stamp|lego, text,
  chips[{text, role}], left_en/left_vi/right_en/right_vi, columns, rows, en, vi, marks[{text, role}], result}` (a flat
  object is easier for the local model's structured output than a union); a card without the fields its kind needs is
  dropped, and its step keeps its spoken line on the cards already shown. Chip roles are the fixed colour code:
  `s, v, o, be, ing, v3, modal, have, adj, plain`.
- **Beats** (`build_beats(lesson, lang)` → `(spoken text, card)` per line): hook scene 0 (pain line with the formula
  card, the fixed "Quên hết đi!" / "Forget them all!" stamp line, the promise line); each scene's steps; the summary
  (a fixed intro line, then one line per row with the table filled up to that row); the core rule; the quiz (if any)
  and the follow line. Each line's card is `{beat, scene, label, title, subtitle, cards: [...]}` with the cards shown so
  far in that scene (cumulative), so the renderer only reads the current line.
- **Fact check**: a second AI pass reviews the lesson (rules correct, English examples natural and grammatical, chips
  spell the formula, Vietnamese only in Vietnamese fields) and returns it corrected with a list of issues; when the
  review call fails the first lesson is kept (logged). Server checks: CJK characters stripped, Vietnamese letters never
  kept in English fields, at least 3 usable scenes.
- **Narration language** follows the audience like `roots`: Việt Nam / Cả hai → Vietnamese explanation, English
  examples; Quốc tế → English. The narrator switches to VieNeu / Edge in the save transaction (`_set_narrator_engine`).
- The topic names the grammar point.
- Step 2 edits the line text; the cards stay with their lines (`SKIPPED_STYLES` gets `grammar`).

## Paths

`backend/schemas/project.py`, `backend/schemas/script.py`, `backend/content/script_service.py` (`LanguageNotes*.grammar`),
`backend/content/grammar_lesson.py` (new), `backend/content/script_pipeline.py` (`_run_grammar_job`),
`backend/content/script_editor.py`, `backend/channel/batch_service.py`, `backend/automation/automation_service.py`,
tests `tests/test_grammar_script.py` (new).

## Verification

`pytest tests/test_grammar_script.py tests/test_roots_script.py tests/test_projects_api.py -q`; ruff.
