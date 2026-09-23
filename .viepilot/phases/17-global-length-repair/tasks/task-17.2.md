# Task 17.2 — Final-Section Sign-Off + `has_outro_last3` Diagnostic

- **Status:** done
- **Owner:** Coder
- **Priority:** P2
- **Dependency:** 17.1 accepted
- **Controlling detail:** plan §3 "17.2"; the ENH-010 watch item

## Measured problem (do not re-derive)

Gate B-7 had 2 `has_outro: false` results (0 at B-6):
- **B1 run 4 is a runner false negative.** The sign-off ("It was a genuine pleasure talking to
  you both … we will be back very soon next episode") sits two lines before the last line.
- **Owner run 1 genuinely ends on a call to action with no goodbye.** A possible cause is 16.4's
  rule 5 (no repeated takeaway sentence) discouraging a closing recap.

## Allowed files

`prompts/script/section.txt`, `scripts/run_ai_operational_trial.py` (diagnostic field only),
`tests/test_script_pipeline.py`, and a runner test file named in the design section,
`CHANGELOG.md`.

## Required behaviour

1. `section.txt`'s `is_last_section` block states that the last section **ends with a short
   spoken sign-off/goodbye**, and that a one-sentence recap of the takeaway inside it is allowed.
   This exempts the final wrap-up from rule 5. Describe it abstractly, with no quoted example
   sign-off (N6 principle).
2. The runner records `has_outro_last3` (sign-off markers in any of the last 3 lines) next to
   `has_outro`. **The gate decision keeps using `has_outro`.**

## Design decisions (Coder, doc-first — commit before code, PM approves)

**PM review (`2ea5467`) — C1 and C2 folded in during implementation, no re-approval
required per PM's explicit instruction:**
- **C1:** the rule-5 exemption clause is wrapped in `{% if is_last_section %}…{% endif +%}`
  (inline on rule 5, as designed), not rendered unconditionally for every section. The
  `+%}` on `endif` disables Jinja2's `trim_blocks` for that one tag — without it, the
  newline after `{% endif %}` was being stripped from the template source regardless of
  which branch actually rendered, merging rule 5 and rule 6 onto one line whenever
  `is_last_section=False`. Verified with a manual render of both branches before writing
  the automated test. This *replaces* the test-plan text below saying the exemption
  clause is unconditional/present in every section — it is not; see the corrected test
  plan and Evidence.
- **C2:** `tests/test_run_ai_operational_trial.py` loads the script via `importlib`
  inside a `runner_module` fixture (same pattern as `tests/test_check_dependencies.py`
  already uses for `scripts/check_dependencies.py`), snapshotting and restoring
  `os.environ`, `sys.argv`, and the loaded module's `sys.modules` entry around the
  import/exec — not a bare top-level `import scripts.run_ai_operational_trial`, and not
  relying on this file's alphabetical position in test collection.

**Runner test file: `tests/test_run_ai_operational_trial.py`** (new — none exists today for
this script). One thing worth flagging before writing it: `scripts/run_ai_operational_trial.py`
does real work at *module import time* — it reads `sys.argv` for `--gate`/`--matrix`/`--mode`,
unconditionally sets `os.environ["DIE_AI_MODE"]`/`os.environ["DIE_DATA_DIR"]`, then imports
`app.main` (constructing the real FastAPI `app` and `AIWorker` singletons, though not starting
a server). None of that is new — it's how the script has always worked, driven by its own
docstring ("`DIE_AI_MODE` ... set before any `app.*` import"). In a pytest session,
`app.core.config.Settings()` is a module-level singleton read from the environment once, at
whichever test file's import first triggers `app.core.config` — since this new test file sorts
alphabetically after the vast majority of the suite's other `test_*.py` files (nearly all start
`a`-`q`), that happens well before this file is ever collected, so `os.environ["DIE_DATA_DIR"]`
being set here has no practical effect on `settings.DATA_DIR` (already fixed by the time this
runs). Confirmed by running the full suite (see Evidence) with no change in outcome or in the
real DB's project count. Not a new risk introduced by this task, and out of this task's allowed
files to restructure (`scripts/run_ai_operational_trial.py`'s "diagnostic field only" scope) —
noting it here so it's a documented, deliberate observation, not a silent assumption.

**1. `has_outro_last3` (required behaviour #2).** A new function,
`_has_outro_in_last_n(texts_lower: list[str], n: int, outline_last_objective: str | None) ->
bool`, generalizing the existing `_has_outro(last_text_lower, outline_last_objective)`: checks
the same `_OUTRO_LINE_MARKERS` against each of the last `n` lines (not only the very last one),
falling back to the same `_OUTRO_OBJECTIVE_MARKERS`-against-the-outline-objective check `_has_outro`
already has. `_has_outro` itself is **not** refactored to call it (its own single-string
signature has no other caller/test depending on it today, but changing it isn't necessary for
this task and keeping it as-is minimizes the diff in a file where "diagnostic field only" is
the allowed scope). `analyze_script` computes `has_outro_last3 =
_has_outro_in_last_n([t.lower() for t in texts], 3, outline_last_objective)` and adds it to the
returned dict, alongside (not replacing) the existing `has_outro` key. **The `checks`/
`all_checks_pass` dict is unchanged** — `outro_present` still reads from `has_outro` only, so
the gate decision is unaffected (required behaviour #2's explicit instruction).

Verified directly against the real Gate B-7 run 4 ending (read-only, `trial-data/app.db`,
project `976be88b-eb93-444f-b2f8-664d9e7a0383`), the exact case this task exists to fix — the
episode's last 3 lines:
1. (3rd-to-last) "Thank you so much for joining us on this final last section of our show about
   healthy living and daily wellness tips."
2. (2nd-to-last) "It was a genuine pleasure talking to you both. Please remember always to
   **take care** of yourself today and throughout the rest of your week."
3. (last) "Until then, try adopting one small new habit. Your future health and happiness
   depends entirely on the choices you make right now."

Line 3 (the true last line) matches none of `_OUTRO_LINE_MARKERS` — `has_outro` is correctly
`False`, matching the real gate's own recorded value. Line 2 contains "take care" — one of the
existing markers — so `has_outro_last3` over the last 3 lines is `True`: the exact false
negative the task names, reproduced and fixed with real data, not a synthetic approximation.

**2. `section.txt`'s sign-off instruction (required behaviour #1), N6-compliant.** The
`is_last_section` block (in the `## This Section` area, unconditional prose, not a numbered
rule) gains one line stating the last section must end with a short spoken sign-off to the
audience — described abstractly, no quoted example goodbye, matching the exact N6 principle
already applied in Task 16.4. The *exemption from rule 5* (16.4's "never repeat the same
takeaway sentence in more than one section") is phrased as a clause added to rule 5 itself, in
the `## Rules` list — not a forward-reference from the earlier `is_last_section` block, since
in the rendered template `## Rules` comes *after* `## This Section`, so a forward reference
from there would point at content not yet read. Exact wording:
- `is_last_section` block: "This is the LAST section of the episode — end it with a short
  spoken sign-off to the audience, not just a final piece of advice or a call to action alone."
- Rule 5, amended: "...Never repeat the same summary or takeaway sentence, word-for-word or
  nearly so, in more than one section — except once, briefly, as part of the final section's
  sign-off."

No topic-specific content, no quoted phrase, no change to any other rule or to the
already-existing `is_last_section` framing sentence structure elsewhere in the file.

**Test plan**
- `tests/test_script_pipeline.py`: a render test (following this file's established
  `make_handler` + captured-prompt pattern) over a 2-section outline confirms the sign-off
  instruction is present in the LAST section's prompt and absent from the first section's
  prompt — proving it's conditional on `is_last_section`, not unconditional prose. A second
  assertion (C1) confirms rule 5's exemption clause is likewise present ONLY in the LAST
  section's prompt and absent from the first section's — rule 5 itself is unconditional and
  renders in every section, but the exemption clause appended to it is not.
- `tests/test_run_ai_operational_trial.py` (new): a unit test calling
  `_has_outro_in_last_n` (and, for contrast, the existing `_has_outro`) directly against the
  real Gate B-7 run 4 lines above (hardcoded as literal strings in the test, not read from the
  trial DB at test time — the DB read above was investigation only, per invariant 26 read-only)
  confirms `has_outro is False` and `has_outro_last3 is True` — the exact false-negative/fix
  pair. A second test confirms `analyze_script`'s returned `checks`/`all_checks_pass` and
  `outro_present` are computed from `has_outro` only, unaffected by `has_outro_last3`'s value
  (required behaviour #2's explicit "gate decision keeps using `has_outro`").
- Revert-and-confirm-failure target: the render test asserting the sign-off instruction is
  present in the last section's prompt — remove the line from `section.txt`, confirm it fails,
  restore.
- Full suite, `ruff`.

## Verification (required)

The render test checks that the sign-off instruction appears only for the last section. A
`has_outro_last3` unit test uses the B-7 run 4 ending. Full suite, `ruff`.

## Evidence

**Code:** `prompts/script/section.txt` (sign-off line in the `is_last_section` block;
rule 5's exemption clause wrapped in `{% if is_last_section %}…{% endif +%}`),
`scripts/run_ai_operational_trial.py` (`_has_outro_in_last_n`, `has_outro_last3` added
to `analyze_script`'s returned dict, `checks`/`all_checks_pass`/`outro_present`
untouched).

**Tests added:**
- `tests/test_script_pipeline.py::test_pipeline_last_section_sign_off_instruction_is_conditional_on_is_last_section`
  — 2-section clean run (no repair calls); asserts both the sign-off instruction and
  rule 5's exemption clause are present in section 2's (last) prompt and absent from
  section 1's.
- `tests/test_run_ai_operational_trial.py` (new file, C2 isolation fixture):
  - `test_has_outro_in_last_n_catches_the_gate_b7_run4_false_negative` — real Gate B-7
    run 4 last-3-lines text (project `976be88b-eb93-444f-b2f8-664d9e7a0383`); confirms
    `_has_outro` is `False` (matches the real recorded gate value) and
    `_has_outro_in_last_n(..., 3, ...)` is `True`.
  - `test_analyze_script_gate_decision_still_uses_has_outro_only` — same lines through
    `analyze_script`; confirms `has_outro_last3` is `True` while `has_outro`,
    `checks["outro_present"]`, and `all_checks_pass` stay driven by `has_outro` (`False`)
    alone.

**Isolation check (C2):** ran `tests/test_run_ai_operational_trial.py` immediately
before `tests/test_ai_health_api.py` (a file whose tests read `app.core.config`
settings) in the same pytest invocation — all 9 tests passed, confirming the runner
script's import-time `os.environ["DIE_AI_MODE"]`/`["DIE_DATA_DIR"]` writes don't leak
past the fixture's teardown.

**Revert-and-confirm-failure:** removed the sign-off sentence from `section.txt`'s
`is_last_section` block, reran the new render test — failed with the expected
`AssertionError: sign-off instruction must appear for the last section`. Restored the
line, reran — passed.

**Full suite:** 962 passed, 1 failed (`test_dashboard_browser.py::test_dashboard_filter_and_search_reset_pagination_to_first_page`,
a Playwright `wait_for_selector` timeout) — confirmed pre-existing/flaky, not caused by
this task's changes: re-ran that single test in isolation immediately afterward and it
passed. 963 total = the 960 baseline from Task 17.1 + 3 new tests (1 render test + 2 in
the new runner test file). `ruff check` clean on all touched Python files.
