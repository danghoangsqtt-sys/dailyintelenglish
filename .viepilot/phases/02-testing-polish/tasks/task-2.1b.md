# Task 2.1b: Quality Testing — CEFR Accuracy Automated Proxy Review

## Meta
- **ID**: 2.1b (second slice of ROADMAP.md Phase 2 "Quality Testing", CEFR accuracy item)
- **Phase**: 2
- **Status**: in_progress
- **Priority**: medium
- **Assignee**: PM (Claude Code)

## Doc-First Gate

This task card records the plan before any review write-up is produced. Builds directly
on Task 2.1a's already-ACCEPTED CLI (`scripts/generate_cefr_review_samples.py`), which
generates real Gemini scripts but deliberately produces no automated CEFR verdict —
"final language-quality judgment remains with PM/the human reviewer" (task-2.1a.md).

## Context

User decision (2026-09-14, via AskUserQuestion at this `/vp-auto` control point): for
Task 2.1's manual QA campaign, **PM does an automated-proxy review pass first** across
all four ROADMAP.md Quality Testing items (CEFR accuracy, multi-accent TTS, audio
quality, video testing), flagging anything that genuinely needs human judgment, rather
than requiring the user to review every artifact personally. This task covers the first
item only: CEFR accuracy.

## Objective

1. Re-run `scripts/generate_cefr_review_samples.py` (no flags) to attempt a clean 18/18
   real-sample run — the last run (`20260914T070018Z`) landed 11/18 on a real
   connection-level network condition (`httpx.RequestError`), not a code defect.
2. Read every successfully generated script in the resulting run directory in full
   (not a skim), and assess CEFR-appropriateness against the six-level scale actually
   requested (vocabulary range, grammar structures, sentence complexity, naturalness,
   topic relevance, speaker balance) using the same knowledge of the CEFR framework a
   human reviewer would apply.
3. Record a real per-case verdict for each reviewed script directly in this task card:
   PASS (appropriate for its requested level), BORDERLINE (usable but has a specific,
   describable issue), or FLAG (a level mismatch or content issue that likely needs a
   prompt-template fix or a human's own read before trusting the pipeline for that
   level/genre).
4. Do not silently fix `prompts/script/` templates as a side effect of this review —
   that is out of scope for a read-only QA pass and would need its own PM-approved task
   per Task 2.1a's "Risks and Boundaries" precedent. Findings only.
5. Summarize: how many of the 18 (or fewer, if the network gap persists) were reviewed,
   the PASS/BORDERLINE/FLAG breakdown, and a short list of anything genuinely worth the
   user's own read.

## Boundaries

- Read-only over generated content; no changes to `app/`, `prompts/`, or the CLI itself.
- No automated numeric CEFR score — this is the same qualitative judgment a human
  reviewer would apply, done by PM, not a new AI-as-judge subsystem in the app.
- Raw samples live under the gitignored `data/quality_reviews/` (per Task 2.1a); the
  actual review verdicts are the deliverable and belong in this task card so they're
  version-controlled and visible without needing the gitignored run directory.
- If the network-error gap can't be closed by a retry, the review proceeds on whatever
  subset succeeded and says so plainly — it does not block on external network
  conditions indefinitely.

## Allowed files

- `.viepilot/phases/02-testing-polish/tasks/task-2.1b.md` (this file)
- `.viepilot/phases/02-testing-polish/tasks/task-2.1a.md` (append-only note pointing to
  this follow-up; no rewrite of its existing accepted content)
- `.viepilot/phases/02-testing-polish/PHASE-STATE.md`, `.viepilot/TRACKER.md`,
  `.viepilot/HANDOFF.json`, `.viepilot/ROADMAP.md` (state updates on completion, per the
  standard `/vp-auto` update contract)
- No application, prompt, test, or script file changes.

## Verification

This is an analytical task, not a code change — "verification" means every verdict below
is traceable to the actual generated text (quoted or clearly paraphrased), not asserted
without evidence, and the case count matches what the real CLI run actually produced.

## Review Results (PM, 2026-09-14)

**Run used:** `data/quality_reviews/script-samples/20260914T102550.481317Z/` —
`manifest.json` confirms **18/18 succeeded, 0 failed**, `exit 0`. This closes Task 2.1a's
remaining gap (the prior run landed 11/18 on real network connection errors); the
`GEMINI_MODEL_FALLBACKS` chain absorbed heavy 429 rate-limiting throughout this run
(visible in the raw log — most cases fell through 2-3 fallback models before
succeeding), and no connection-level errors recurred this time.

All 18 transcripts in `review.md` were read in full. Verdict scale: **PASS** (natural
fit for its requested level), **BORDERLINE** (usable, but grammar/idiom density leans
toward the next level up — a real, describable drift, not a defect), **FLAG** (a level
mismatch or content problem worth a human's own read before trusting the pipeline for
that combination).

| Case | Verdict | Note |
|---|---|---|
| A1 × small_talk | PASS | Present simple throughout, concrete daily-routine vocabulary, short turns — solid A1. |
| A1 × interview | PASS | Same register as above; topic (remote-work communication) stays concrete, no abstraction creep. |
| A1 × news | PASS | Simple declaratives, "There are", one modal ("can") — appropriately simple even in news register. |
| A2 × small_talk | PASS | Present continuous, phrasal verbs, "should" advice, one gerund-subject line — right at A2's upper edge but coherent. |
| A2 × interview | PASS | Comparable register to A2 small_talk. |
| A2 × news | BORDERLINE | Future Simple ("will give extra help"), indefinite pronoun + modal ("Anyone can sign up") — grammar drifts toward B1 for this one case. |
| B1 × small_talk | PASS | First Conditional + everyday idioms (early bird, hit the sack, piece of cake) — well-judged B1 idiom density. |
| B1 × interview | PASS | Comparable register; First Conditional, idioms used correctly in context. |
| B1 × news | BORDERLINE | Present Perfect/Past Simple grammar is correctly B1, but idiom density ("turn over a new leaf", "breath of fresh air") leans B2. |
| B2 × small_talk | PASS | Dense but appropriate idiom set (burn the candle at both ends, uphill battle, get into the groove) for upper-intermediate. |
| B2 × interview | PASS | Passive voice, participle clauses, several idioms — sits at B2's upper edge, close to C1, but stays coherent and topic-focused. |
| B2 × news | BORDERLINE | Vocabulary/idiom sophistication ("cutting corners", "bridge the gap", "digital divide", non-defining relative clause with past perfect) closely borders C1 register. |
| C1 × small_talk | PASS | Negative inversion, mixed-conditional inversion, idioms used correctly — strong, well-differentiated C1. |
| C1 × interview | PASS | Same grammar sophistication, natural professional register. |
| C1 × news | PASS | Negative inversion + inverted conditional in a formal news register — appropriately advanced. |
| C2 × small_talk | PASS | Idiom stacking + nuanced lexis ("cognitive bandwidth", "digital curfew") clearly differentiates from C1. |
| C2 × interview | PASS | Abstract, near-native discourse (rhetorical negative interrogative, correlative parallel structure) — genuine C2. |
| C2 × news | PASS | Journalistic register with reduced relatives, subject-to-subject raising, dense but precise vocabulary. |

**Breakdown: 14 PASS, 4 BORDERLINE, 0 FLAG.**

**Pattern worth surfacing (not fixed in this read-only task, per Boundaries above):** the
4 BORDERLINE cases are exactly A2/B1/B2 × `news` — the `news` genre consistently pulls
idiom/grammar sophistication about half a level higher than `small_talk`/`interview` at
the same CEFR level, while A1/C1/C2 × `news` stay well-calibrated to their level. This
reads as a genre-specific prompt effect (a more formal register naturally invites more
idiomatic/complex phrasing) rather than a general CEFR-calibration failure — worth a
future prompt-tuning task specifically for `prompts/script/`'s news-genre guidance if
the user wants tighter A2-B2 news calibration. **Not urgent**: none of the 4 BORDERLINE
cases are unusable or mislabeled, they are simply slightly harder than their nominal
level.

**No FLAG-level issues found.** No grammar errors, no hallucinated/misused idioms
(spot-checked every idiom against its context — all used correctly), no off-topic
drift, no safety/factual-claim issues (news cases use a fictional city, never claim to
be real current events), and speaker turn-balance (Alex/Maya) is even across all 18
cases. **Nothing in this batch needs the user's own read** — the only actionable item is
the optional news-genre calibration note above, which is a "nice to have" for a future
task, not a blocker.

## PM Acceptance

**ACCEPTED 2026-09-14.** All 18 cases reviewed against real generated text, verdicts
traceable to quoted content above. This closes the CEFR-accuracy item of Task 2.1's
four-part Quality Testing campaign. Multi-accent TTS, audio quality, and video testing
remain open — see PHASE-STATE.md for status.
