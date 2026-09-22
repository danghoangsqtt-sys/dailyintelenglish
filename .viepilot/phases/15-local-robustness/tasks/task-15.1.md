# Task 15.1 — Speaker Aliases in the Section Contract

- **Status:** in progress
- **Owner:** Coder
- **Priority:** P0
- **Dependency:** none (first task of Phase 15)
- **Controlling detail:** plan §3 "15.1 — Speaker aliases in the section contract";
  invariants 20/21; the owner's real run failure and the Gate B-3/B-4 sample failures
  it matches

## Objective

Stop the model from having to echo a 36-character UUID verbatim per line — the exact
mechanical failure that killed the owner's own first real run (`section 3,
unknown speaker_id(s): ['ff5f20e0-417b-8d9f-752e844d46f0']` against the real id
`ff5f20e0-4082-417b-8d9f-752e844d46f0`, Alex — one UUID group dropped) and matches the
same failure class at Gate B-4's B1 5-minute sample. Give the section/repair contract a
short, easy-to-echo alias instead, and resolve it back to the real UUID
deterministically on the server before validation runs.

## Measured problem (do not re-derive)

Three independent real hits of the unknown-speaker-id structural check, all mechanical
(a copy/transcription error, not a content problem): the owner's own run (dropped UUID
group), Gate B-4's B1 5-minute sample (truncated UUID), and — a related but distinct
structural check — Gate B-3's B1 10-minute sample died on the consecutive-lines rule
(Task 15.2's problem, not this one). Every other content check this project has (word
budget, length, repetition, learning grounding) already has a bounded repair path;
these two structural checks are still fatal after the one semantic repair.

## Allowed files

`app/services/script_pipeline.py`, `app/core/constants.py`, `prompts/script/section.txt`,
`prompts/script/repair.txt`, `tests/test_script_pipeline.py`, `tests/fixtures/ai/*`.

Anything else → stop and ask the PM to amend the plan.

## Required behaviour

1. The section and repair prompts present speakers as short aliases — `S1`, `S2`, … in
   `speaker_index` order — alongside each speaker's display name. The JSON contract asks
   for `"speaker": "S1"` (the alias), never the UUID. `SectionLineOut` (or its wire-level
   counterpart) gains an alias-shaped field; the pipeline resolves alias → real speaker
   UUID **server-side, before validation runs**. The persisted line shape
   (`speaker_id` UUID, via `script_service.save_script`) is unchanged — the API and UI
   see no difference.
2. **Resolution rules, deterministic and logged** (a log line per resolution, e.g.
   `script_speaker_resolved kind=...`), tried in this order:
   - exact alias match (`S1`);
   - alias match ignoring case/whitespace;
   - the speaker's display name, only when names are unique within the project;
   - a value that exactly equals a known speaker UUID;
   - **safety net** (older checkpoints, or a model that still echoes an id-shaped
     value): a UUID-shaped value that matches **exactly one** known id at
     ≥ `SCRIPT_SPEAKER_ID_MATCH_MIN_RATIO = 0.85` similarity
     (`difflib.SequenceMatcher` ratio, new constant).
   - Anything else (including a value equidistant between two known ids, or matching
     none above the threshold) stays an unknown speaker → the existing repair → the
     existing `section_validation_failed` path, unchanged.
3. **Resume compatibility:** a checkpoint written before this task holds raw
   `speaker_id` UUIDs (not aliases) — the loader must accept both shapes.
4. **Explicitly out of scope:** legacy single-line `regenerate_line`
   (`app/services/script_service.py`) still echoes ids and is not touched by this task
   — noted here, not silently left inconsistent.

## Explicitly forbidden

- Ever publishing a line with a speaker id that does not belong to the project
  (invariant 20) — resolution may only *map* to a real, known speaker, never invent or
  guess one absent a matching signal.
- Editing a line's `text` during resolution (invariant 21) — this task touches only
  which speaker a line is attributed to, never its words.
- Loosening any existing threshold (`SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER`, either
  word tolerance, `SCRIPT_MAX_REPEATED_8GRAM_RATIO`) to make this task easier.

## Verification (all must be in the diff)

1. Pure-function tests for every resolution rule, including the real, literal examples
   from this phase's trigger: `"ff5f20e0-417b-8d9f-752e844d46f0"` resolves to Alex
   (`ff5f20e0-4082-417b-8d9f-752e844d46f0`) via the safety net; a UUID-shaped value
   equidistant between two known ids resolves to unknown (not an arbitrary pick).
2. FakeProvider e2e test: the model returns aliases → job completes normally.
3. FakeProvider e2e test: the model returns a truncated/near-miss UUID → resolved via
   the safety net, job completes, the resolution is logged.
4. FakeProvider e2e test: a genuinely unresolvable speaker value → fails exactly as
   today (`section_validation_failed`, after the one repair).
5. A checkpoint written in the old `speaker_id`-UUID shape still resumes correctly.
6. Constants pin extended with `SCRIPT_SPEAKER_ID_MATCH_MIN_RATIO`; revert-and-confirm-
   failure on the safety net (e.g. temporarily require exact match only, confirm the
   truncated-UUID e2e test now fails, restore).
7. Full suite green; `ruff check app tests scripts` clean.

## Rollback

`SCRIPT_SPEAKER_ID_MATCH_MIN_RATIO = 1.0` restores exact-match-only behavior for the
safety net without a code revert; the alias contract itself (prompt wording, JSON
shape) is reverted by git only, same as any other prompt/pipeline change.

## Execution record

- Plan/decisions before code:
  1. **New wire model, existing model unchanged.** `SectionLineOut` (`speaker_id: str`)
     stays exactly as-is -- it is the *resolved*, persisted shape every downstream
     consumer (`validate_section_structure`, checkpoints, `script_service.save_script`)
     already expects, and none of them change. A new `SectionLineWire` model
     (`speaker: str`, same `text`/`language_notes`) is what the AI actually returns and
     is parsed into; a new `_SECTION_LINES_WIRE_ADAPTER = TypeAdapter(list[SectionLineWire])`
     replaces `_SECTION_LINES_ADAPTER` only at the two call sites that talk to the model
     (`json_schema=...` and `parse_and_validate(...)` in `_generate_section`/
     `_repair_section`) -- `_SECTION_LINES_ADAPTER` itself is untouched and keeps
     serializing/deserializing checkpoints in the resolved `SectionLineOut` shape, which
     is also why **"resume compatibility" needs no special-casing**: a checkpoint has
     always stored the resolved shape and still does -- the alias contract is a
     wire-format concern between the model and the server, never a persisted-data
     concern, so an old checkpoint and a new one are byte-identically shaped.
  2. **Resolution function**, pure and unit-testable:
     `resolve_speaker(raw: str, speakers: list[dict]) -> tuple[str, str | None]`
     (returns `(resolved_id_or_original_value, kind)`; `kind is None` means
     unresolved). Tried in this exact order:
     - exact alias (`S{i}`, 1-indexed in `speakers` order -- the same order the
       section/repair prompt's own `{% for speaker in speakers %}` loop assigns
       aliases in, via Jinja's `loop.index`, so the two are consistent by
       construction with no separate alias list threaded through the render call);
     - alias case/whitespace-insensitive;
     - the speaker's display name, `.strip().casefold()` compared, **only when the
       name is unique across the project** (PM's note 1) -- computed via a
       `Counter` of casefolded names; two same-named speakers means this rule
       contributes nothing for either of them, not a guess;
     - an exact match against a known speaker UUID;
     - **safety net**: gated first by a loose "UUID-shaped" regex
       (`^[0-9a-f-]{8,}$`, case-insensitive -- deliberately loose, not the strict
       8-4-4-4-12 UUID grammar, since the whole point is to catch a near-miss like
       the real trigger case's *missing dash group*, which a strict pattern would
       reject outright); among UUID-shaped values, every known id is scored via
       `difflib.SequenceMatcher(None, raw, known_id).ratio()`, and the value
       resolves **only if exactly one** id scores ≥ `SCRIPT_SPEAKER_ID_MATCH_MIN_RATIO
       = 0.85` (PM's note 2 -- two-or-more ties above the threshold is unknown, not
       a guess between them, mirrored directly by `len(matches) == 1`).
     - Anything else: `(raw, None)` -- the original, unresolved value passes through
       unchanged into the existing `SectionLineOut`, so `validate_section_structure`'s
       existing "unknown speaker_id(s)" check catches it with **zero changes to that
       function** -- the exact same error shape as today.
  3. **`resolve_section_lines(wire_lines, speakers) -> list[SectionLineOut]`** applies
     `resolve_speaker` to every wire line and logs each one:
     `logger.info("script_speaker_resolved kind=%s original=%r resolved=%s", kind,
     raw, resolved)` -- only when `kind is not None` (an unresolved value is about to
     hit the existing unknown-speaker error path, which already reports it; no need
     to double-log a non-resolution). Called once, right after `parse_and_validate`,
     in both `_generate_section` and `_repair_section`, before either function's
     existing `validate_section_structure`/`validate_section_word_budget` calls --
     both of those stay byte-for-byte unchanged, operating on the now-resolved lines
     exactly as they operate on today's lines.
  4. **Repair prompt's "previous answer" echo must speak the same alias contract.**
     `_repair_section` currently serializes `previous_lines` (already-resolved
     `SectionLineOut`, UUID-shaped) straight into the repair prompt via
     `_SECTION_LINES_ADAPTER.dump_json(...)`. Under the new alias contract this would
     show the model a self-contradictory example (asked for `"speaker": "S1"`, shown
     its own previous answer in the old `"speaker_id": "<uuid>"` shape). New helper
     `_lines_to_wire_json(lines, speakers)` reverse-maps each line's `speaker_id` back
     to its alias for display; a line whose `speaker_id` was never resolved (exactly
     the case that triggered this repair) falls back to showing the *literal original
     value* the model produced -- more useful for a repair prompt than either hiding
     it or showing a fabricated alias for something that was never resolved.
  5. **Prompt changes**: `section.txt`'s Speakers section changes `id: {{ speaker.id }}`
     to `alias: S{{ loop.index }}` (Jinja's built-in loop counter, no new render
     parameter); its Output Format's `"speaker_id": "the exact id (UUID)..."` becomes
     `"speaker": "the exact alias (e.g. S1)..."`; rule 2 ("use only the id values")
     becomes "use only the alias values". `repair.txt` gets the identical alias
     treatment for its own Speakers list and Output Format line.
  6. **New constant**: `SCRIPT_SPEAKER_ID_MATCH_MIN_RATIO = 0.85` in
     `app/core/constants.py`, alongside the other `SCRIPT_PIPELINE_*`/`SCRIPT_*`
     governance constants, with a comment explaining the difflib safety net and
     citing the real trigger case.
  7. **New tests** in `tests/test_script_pipeline.py`: pure tests for every
     `resolve_speaker` branch, including the two literal real-world values
     (`"ff5f20e0-417b-8d9f-752e844d46f0"` -> the real
     `"ff5f20e0-4082-417b-8d9f-752e844d46f0"` (Alex) via the safety net; a
     constructed value equidistant between two known ids -> unresolved); e2e tests
     for alias-returned/near-miss-returned/unresolvable/old-checkpoint-resume per
     the card's verification list; constants pin extension +
     revert-and-confirm-failure on the safety net.
- Commands and results:
- Deviations:
- Revert-and-confirm-failure evidence:
- Commit(s):
