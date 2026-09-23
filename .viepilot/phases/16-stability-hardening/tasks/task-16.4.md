# Task 16.4 — Repetition: Evidence-Driven Avoid List (ENH-009 step A)

- **Status:** in_progress
- **Owner:** Coder
- **Priority:** P0 (the core pipeline's remaining variable failure)
- **Dependency:** 16.3 accepted
- **Controlling detail:** plan §4 "16.4", invariants 24 and 27, owner decision D18;
  `.viepilot/requests/ENH-009.md`; `docs/operations/phase15-gate-b6.md`

## Measured problem (do not re-derive)

Gate B-6: script 3/5. Both deaths were `repeated 8-gram ratio` (1.00%, 1.42%) after the one
bounded repetition repair (Task 14.13). The same code scored 5/5 at B-5. Today's
`avoid_phrases` (`frequent_repeated_phrases`, top `SCRIPT_SECTION_AVOID_PHRASES_MAX = 8`)
lists only 8-grams that have **already** repeated. The second occurrence, the one that
creates the repeat, is never prevented.

## Allowed files

`prompts/script/section.txt`, `prompts/script/repair.txt`,
`app/services/script_pipeline.py` (avoid-phrase selection only),
`app/core/constants.py`, `tests/test_script_pipeline.py`, `tests/test_prompt_loader.py`,
`tests/fixtures/ai/*`, `CHANGELOG.md`.

## Required behaviour

1. **Evidence (the design section, reviewed by the PM before code):** from
   `data/quality_reviews/phase15/gate-b6/` (JSON + `trial-data/app.db`, **read-only**),
   extract the repeated 8-grams of every B-6 script run (failures, runs 2 and 5, first),
   with section attribution. Classify each as *framing* (openers, closers, transitions,
   topic restatements) or *content* (the topic's own key terms). Put the table here.
2. **Proposal:** close the "second occurrence" gap with a bounded mechanism. Candidates:
   - pass prior sections' opening and closing lines as "don't reuse this framing";
   - a static rule block in `section.txt` against the observed framing *patterns*.

   Recommend one, state the prompt-size bound, and trace every added rule or phrase to a
   row of the evidence table (invariant 27).
3. No threshold change, and no new repair pass (that is 16.6, conditional).

## Explicitly forbidden

Changing `SCRIPT_MAX_REPEATED_8GRAM_RATIO` or any other pinned threshold. Adding the topic's
content words to an avoid list. Writing to any gate evidence DB.

## Design decisions (Coder, doc-first — commit before code, PM approves)

**Method.** `data/quality_reviews/phase15/gate-b6/trial-data/app.db`, opened
read-only (`file:...?mode=ro`), plus the gate JSON, never written to. Each
run's 5 section checkpoints (`stage='section'`, the final/latest row per
`section_index`) were loaded and fed through the pipeline's own
`find_repeated_8grams_by_section` / `repeated_8gram_ratio`
(`app/services/script_pipeline.py`) — the exact functions the gate itself
used, imported read-only, not reimplemented. The computed ratios matched the
gate's own recorded verdicts exactly (run2: 1.0000% vs. reported "1.00%";
run5: 1.4156% vs. reported "1.42%"), confirming the reconstruction is faithful
before drawing any conclusions from it.

## Evidence table

All 5 B-6 script runs, failures (run2, run5) first. "Sections" is where each
repeat *starts* (`find_repeated_8grams_by_section`'s attribution). Text is
shown casefolded, matching how the pipeline itself detects repeats
(`normalize_text`). Overlapping rows are sliding-8-word-window views of the
same underlying repeated sentence.

| Run | Ratio | Sections | Repeated 8-gram | Class |
|---|---|---|---|---|
| **run2** (FAIL, 1.00%) | | 4, 4 | "just start again the next morning without feeling" | Framing — restart/reset narrative beat, repeated **within the same section** (not a later section reusing an earlier one) |
| run2 | | 4, 4 | "consistency matters more than perfection if you want" | Framing — thesis/takeaway restatement, **within-section** self-repeat |
| run2 | | 4, 4 | "matters more than perfection if you want to" | (same sentence, next sliding window) |
| run2 | | 4, 4 | "more than perfection if you want to keep" | (same sentence, next sliding window) |
| run2 | | 4, 4 | "than perfection if you want to keep healthy" | (same sentence, next sliding window) |
| **run5** (FAIL, 1.42%) | | 2, 3 | "exactly right, alex. i truly believe that drinking" | Framing — agreement-opener template |
| run5 | | 2, 3 | "right, alex. i truly believe that drinking plenty" | (same sentence, next sliding window) |
| run5 | | 2, 3 | "alex. i truly believe that drinking plenty of" | (same sentence, next sliding window) |
| run5 | | 2, 3 | "i truly believe that drinking plenty of water" | (same sentence, next sliding window) |
| run5 | | 2, 3, **5** | "that is exactly right, alex. i truly believe" | Framing — agreement-opener template, reused a **3rd** time in section 5 |
| run5 | | 2, 3, **5** | "is exactly right, alex. i truly believe that" | (same sentence, next sliding window) |
| run3 (PASS, 0.75%) | | 2, 3 | "that healthy habits are the absolute key to" | Framing — thesis/"key to X" closing-claim template |
| run3 | | 2, 3 | "healthy habits are the absolute key to a" | (same sentence, next sliding window) |
| run3 | | 2, 3 | "habits are the absolute key to a happy" | (same sentence, next sliding window) |
| run3 | | 2, 3 | "are the absolute key to a happy life." | (same sentence, next sliding window) |
| run1 (PASS, 0.00%) | | — | none | — |
| run4 (PASS, 0.00%) | | — | none | — |

**Reading the table.** Every distinct repeated *sentence* (collapsing the
sliding-window duplicates) falls into exactly two generic templates, both
generic self-help/podcast rhetorical devices, not this episode's specific
topic vocabulary:
1. **Agreement-opener**: "That's/That is exactly right, `<name>`, I truly
   believe that `<continues into content>`" — run5, reused 3 times (sections
   2, 3, 5).
2. **Thesis/"key to X" restatement**: a short claim-sentence summarizing the
   episode's overall point — "consistency matters more than perfection..."
   (run2, section 4, twice), "`<X>` are the absolute key to a happy life"
   (run3, sections 2 and 3).

run2 is the one case that **isn't** a later section reusing an earlier one —
both occurrences are inside section 4 itself, already the section the
existing one-repair mechanism (Task 14.13) had picked as "worst" and
regenerated (its checkpoint carries `"repetition_repaired": true`), and the
*repaired* output still self-repeats. That's a real finding, but it's a
repair-effectiveness problem, not a "second occurrence across sections"
problem — the avoid-list mechanism this task is scoped to only ever informs
*later* sections about *earlier* ones, so it has nothing to say about a
section repeating itself in one generation. Flagging it here for the record
(and because rule 3 below happens to also cover it) but not counting it
toward the "gap" this task closes; a genuinely second repair pass is 16.6's
territory if Gate B-7 needs it.

run3 and run5 *are* exactly the "second occurrence" gap: `frequent_repeated_
phrases()` only ever includes an 8-gram once it has `count > 1` — i.e. only
after it has *already* repeated. Section 2 uses a phrase once; at that count
(1) it's not yet "frequent," so section 3's prompt never sees it in
`avoid_phrases`, and section 3 reuses it — creating the actual second
occurrence that then, only from section 4/5 onward, would finally show up as
"frequent." The current mechanism can only ever catch a *third* reuse, never
the second.

## Recommendation

**A static, topic-agnostic rule block (candidate 2)** in `prompts/script/
section.txt`, naming the two generic pattern categories the table shows, not
today's specific topic wording. Rejected candidate 1 (echo prior sections'
opening/closing lines): it only helps the cross-section case (run3, run5) and
does nothing for run2's within-section self-repeat, since there's no "prior
line" to echo against when the model duplicates itself inside one generation
pass. Also considered and **rejected**: loosening `frequent_repeated_
phrases()`'s `count > 1` filter to `count >= 1`, which would literally close
the "only catches the third reuse" gap using the *existing*, already-allowed
avoid-phrase-selection code path — but at `count >= 1` almost every 8-word
window from prior sections qualifies, most of them ordinary, legitimate reuse
of the topic's own vocabulary (a wellness episode saying "healthy habits"
more than once is fine), not a repetition problem. That would routinely add
the topic's content words to the avoid list — the task's explicit
prohibition — so it's rejected despite being a tempting one-line fix.

Every added rule traces to the evidence table above (invariant 27):

1. *(traces to run5's 3 occurrences, table rows 6-11)* — "Vary how speakers
   agree with or react to each other. Do not open a turn with the same fixed
   agreement phrase (for example, always saying something like "That's
   exactly right, I truly believe that...") more than once across the whole
   episode."
2. *(traces to run3's 2 occurrences and run2's 2 occurrences, table rows 2
   and 12-15)* — "State the episode's main point or takeaway freshly in your
   own words each time it comes up. Never repeat the same summary or "the key
   to X" claim sentence, word-for-word or nearly so, in more than one
   section."
3. *(traces to run2's within-section self-repeat, table rows 1-5)* — "Do not
   restate the same sentence or claim twice within this section itself, even
   reworded in a way that reuses most of the same wording."

**Prompt-size bound.** 3 fixed rule lines added to `section.txt`'s existing
numbered `## Rules` list (rules 4-6), ~70 words total — a small, **constant**
addition, independent of episode length, section count, or topic, unlike the
existing dynamic `avoid_phrases` block (already present, unchanged by this
task) which scales up to `SCRIPT_SECTION_AVOID_PHRASES_MAX` (8) phrases. One
short mirrored line is added to `prompts/script/repair.txt` too (~20 words),
since run2's own evidence shows the *repaired* output still self-repeating —
the repair prompt already lists the specific phrases already flagged as
errors, but not the general pattern to avoid reintroducing a fresh variant of
the same thing.

**No code change.** Both additions are static prompt text — no new Jinja
variables, no change to `frequent_repeated_phrases()` or the existing
`avoid_phrases` selection/rendering, which is already correct and stays
exactly as-is. `app/services/script_pipeline.py` is therefore not touched by
this task, despite being in the allowed-files list.

**Test plan**
- `tests/test_script_pipeline.py` (not `test_prompt_loader.py` — `section.txt`
  and `repair.txt` render through `script_pipeline.py`'s own private Jinja
  `_env`, a deliberate separation from `app/core/prompt_loader.py` already
  noted in the module's own comments at line 525-526, since `prompt_loader.py`
  isn't in this task's allowed files either): following this file's own
  established pattern (see `test_pipeline_section_prompt_word_range_matches_
  the_tolerance_constant` — run the real handler via `make_handler` against a
  fake router, then inspect the captured `gemini.calls[N].prompt` text, rather
  than reaching for the private `_render_sync` directly), new tests confirm:
  the 3 new static rules are present in the real section prompt sent to the
  model, unconditionally (a case with `avoid_phrases` empty — no prior
  sections — and a case with a repetition repair triggered, both still carry
  the 3 rules); and `repair.txt`'s one new line appears in a real repair
  prompt (piggybacking on the existing `test_pipeline_repairs_an_invalid_
  section_once_then_completes`-style setup).
- `tests/test_script_pipeline.py`: since there's no selection-logic code
  change, no new unit tests for "bound / empty case / dedupe" apply here (the
  existing `frequent_repeated_phrases` tests, if any, are untouched and stay
  passing) — the prompt-contract tests are what carry this task's test
  weight, per the card's own verification list ("a render test of
  `section.txt`... prompt-contract tests pass").
- Revert-and-confirm-failure target: the render test asserting the 3 new
  rule lines are present in `section.txt` — remove the block, confirm the
  test fails, restore.
- Full suite, `ruff`. Real-model effect (does Gate B-7 actually reach 5/5) is
  the PM's to measure in 16.5, not here (card's own instruction).

## Verification (required)

Unit tests for the selection logic (bound, empty case, dedupe). A render test of
`section.txt` with the new block. Prompt-contract tests pass. Revert-and-confirm-failure on
the selection test. Full suite. `ruff`. Real-model effect is measured by the PM in 16.5
(Gate B-7), not here.

## Evidence

_pending_
