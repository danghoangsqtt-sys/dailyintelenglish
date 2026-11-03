# Task 87.2 — `roots` template: data and script

See [PLAN.md](../PLAN.md), D125–D127.

## Objective

A Short with `explainer_style = "roots"` gets a script built from one schema-checked **word family** (a root, a prefix
or a suffix and 5–7 words made with it). Each script line is one beat and carries a structured card in its language
notes, so the renderer (87.3) draws the beat from its own line and Step 2 can still edit the spoken text.

## Design (written before code)

- **Style registration** (`backend/schemas/project.py`): `roots` joins `SOLO_SHORT_STYLES`, `VOICE_ONLY_STYLES` (through
  the solo list) and `LINE_DRAWN_STYLES` (no visual plan to approve). New `ACADEMIC_STYLES = ("roots",)` (88 adds
  `grammar`). D126: `ACADEMIC_SHORT_MAX_MINUTES = 3.0`, `short_minutes("roots") = 2.0`; the ≤ 1 minute checks use a
  per-style maximum.
- **Card data** (`backend/content/word_family.py`, new): `WordFamily {kind: root|prefix|suffix, head, origin_lang,
  origin_form, head_meaning, head_logic, head_example_en, head_example_vi, words: [FamilyWord], quiz: FamilyWord}`,
  `FamilyWord {word, parts: [{text, role: prefix|root|suffix, meaning}], meaning, logic, example_en, example_vi,
  picture}`; 4–7 words. `LanguageNotesOut.roots: dict | None` holds one beat's card:
  `{beat, word?, parts?, meaning?, breakdown?, example_en?, example_vi?, picture?, words?, origin?}`.
- **Narration language** follows the audience (Phase 72): Việt Nam / Cả hai → Vietnamese explanation with the English
  words and examples (meanings `*_vi`); Quốc tế → all English. The AI writes the meaning/logic fields in that language;
  the server builds the beats from fixed templates so every video keeps the formula of sample A:
  hook ("Bạn có biết X là …," / "nhưng X và Y cùng một gốc?") → promise (N words, one root) → origin → bare head +
  example → per word: whole ("Express, bày tỏ."), split (the AI's one-sentence logic), example (English sentence read
  aloud, Vietnamese gloss on screen) → quiz ("Đoán từ cuối nhé!" + clue) → follow line.
- **Voice** (D125): the roots job sets the narrator to VieNeu (default preset for the gender) when the narration is
  Vietnamese, and back to Edge when it is English, in the same transaction that saves the script.
- **Curated seed** (`backend/content/data/word_roots.json`): checked heads (root / prefix / suffix) with origin and
  meaning and common family words. When the topic names a listed head, its origin and meaning are given to the AI as
  facts to copy; an unlisted head is allowed, but the AI must return `origin_form` only when sure (else empty, and the
  origin beat is skipped). A word whose parts do not spell the word is dropped (server check), and the family needs at
  least 4 words left.
- **Pasted list**: `source_words` (owner's list) become the family's words, in order.
- Step 2 edits the line text; the cards stay with their lines.

## Paths

`backend/schemas/project.py`, `backend/content/script_service.py` (`LanguageNotesOut.roots`),
`backend/content/word_family.py` (new), `backend/content/data/word_roots.json` (new),
`backend/content/script_pipeline.py` (`_run_roots_job`), `backend/content/project_service.py` (if the length check lives
there), tests `tests/test_roots_script.py` (new).

## Verification

`pytest tests/test_roots_script.py tests/test_slowpod_flashcards.py tests/test_projects_api.py -q`.
