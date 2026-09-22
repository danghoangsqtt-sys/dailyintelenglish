# Task 15.1 — Speaker Aliases in the Section Contract

- **Status:** pending
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
- Commands and results:
- Deviations:
- Revert-and-confirm-failure evidence:
- Commit(s):
