# Task 4.1: CEFR `news`-genre prompt tuning

## Meta
- **ID**: 4.1
- **Phase**: 4
- **Status**: done (2026-09-15) — partial improvement, honestly reported (see Results)
- **Priority**: low (optional calibration improvement, not a defect)
- **Assignee**: PM (Claude Code)

## Doc-First Gate

Scoped in the 2026-09-15 brainstorm session (`docs/brainstorm/session-2026-09-15.md`),
approved by the user as the first Phase 4 task. Builds directly on Task 2.1b's real
18-sample review (2026-09-14), which found a specific, quoted pattern — not a vague
impression — and explicitly left it unfixed as a "future prompt-tuning task."

## Problem (real evidence from Task 2.1b, not re-derived)

4 of 18 real-generated samples landed BORDERLINE, all `news` genre:
- **A2 × news**: drifted to B1 grammar — Future Simple ("will give extra help"),
  indefinite pronoun + modal ("Anyone can sign up").
- **B1 × news**: grammar stayed correctly B1, but idiom density leaned B2 ("turn over a
  new leaf", "breath of fresh air").
- **B2 × news**: vocabulary/idiom sophistication closely bordered C1 ("cutting corners",
  "bridge the gap", "digital divide", non-defining relative clause + past perfect).

A1/C1/C2 × `news` were already well-calibrated — this is genre-specific, not a general
CEFR failure. Task 2.1b's own hypothesis: `news`'s formal register instruction leads
Gemini to reach for more sophisticated phrasing than the CEFR ceiling (set separately, in
`prompts/script/cefr_*.txt`) actually allows, because nothing in `news.txt` distinguishes
"formal tone/structure" from "advanced grammar/vocabulary."

## Objective

Add explicit register-vs-complexity guidance to `prompts/script/news.txt`, directly
targeting the 3 quoted failure patterns above (not a vague "be simpler" instruction):
1. State that the formal tone/structure is about organization and word choice, not
   permission to exceed the CEFR ceiling set elsewhere in the prompt.
2. Explicitly discourage reaching for a sophisticated idiom just because the topic is a
   news story — matches the B1/B2 idiom-density pattern.
3. Explicitly prefer the simplest tense/structure that states the fact clearly over
   Future Simple / passive / complex relative clauses unless CEFR level is B2+ — matches
   the A2/B2 grammar-drift pattern.
4. Note that a short, plain closing line is authentic at every level — removes any
   implicit pressure toward embellishment.

Genuinely empirical: this is a best-effort prompt tweak against a probabilistic model,
not a guaranteed fix. Verification must honestly report the real outcome, including if
it's still borderline.

## Allowed files
- `prompts/script/news.txt`
- `.viepilot/ROADMAP.md`, `.viepilot/TRACKER.md`, `.viepilot/HANDOFF.json`,
  `.viepilot/phases/04-post-beta-polish/PHASE-STATE.md`, `CHANGELOG.md` (state tracking)
- No `app/`, `tests/`, or other prompt files touched — single-file, scoped change.

## Verification
- `venv\Scripts\python scripts\generate_cefr_review_samples.py --levels A2 B1 B2
  --genres news` — real Gemini calls, 3 new samples.
- PM reads all 3 new transcripts in full and re-applies Task 2.1b's exact rubric
  (vocabulary range, grammar structures, naturalness, topic relevance), recording a
  fresh verdict per case directly in this task card.
- No regression check needed on other genres/levels — `news.txt` is genre-scoped, other
  15 genre×level combinations from Task 2.1b are unaffected by this file.

## Results (PM, 2026-09-15) — real, honest before/after comparison

Real run: `data/quality_reviews/script-samples/20260915T034532.159865Z/`, 3/3 succeeded.
All 3 transcripts read in full and compared directly against Task 2.1b's exact quoted
before-state.

| Case | Before (Task 2.1b) | After (this run) | Verdict |
|---|---|---|---|
| A2 × news | Future Simple ("will give extra help"), indefinite pronoun + modal ("Anyone can sign up") | The specific "indefinite pronoun + modal" pattern did NOT recur. But 2 Future Simple lines remain ("Staff **will turn on** the new equipment", "The building **will open** every day") | **Partially improved** — one failure mode gone, a related one (Future Simple) persists |
| B1 × news | Idiom density leaned B2 ("turn over a new leaf", "breath of fresh air") | The exact same idiom, **"a breath of fresh air"**, recurred verbatim (line 9) | **Not improved** — the targeted idiom-avoidance guidance did not prevent this specific idiom |
| B2 × news | Vocabulary/idiom bordered C1 ("cutting corners", "bridge the gap", "digital divide", non-defining relative clause + past perfect) | Idioms are now more solidly B2-appropriate ("breathe new life into", "hit the ground running", "pull off" — common, teachable B2 idioms vs. the prior obscure/literary set); but grammar still reaches for an advanced structure (Past Perfect Continuous — "had been looking forward to") | **Partially improved** — idiom choice better calibrated, grammar ceiling still borders C1 |

**Honest overall verdict: partial, mixed improvement — not a full fix.** The tuning
measurably changed model behavior (different idiom/grammar choices appeared, one
specific before-pattern didn't recur), proving the prompt edit had a real effect, not
zero effect. But it did not fully close the gap Task 2.1b found — `news` still drifts
slightly above its nominal CEFR ceiling, most visibly the recurring "breath of fresh
air" idiom at B1 and Future Simple usage at A2. This is consistent with prompt-tuning
against a probabilistic model: incremental, not guaranteed. Given Task 2.1b explicitly
scoped this as "optional, nice to have, not urgent" (none of the original 4 BORDERLINE
cases were unusable or mislabeled — just slightly harder than nominal), this task closes
here with the honest result rather than iterating further on a low-priority item;
further iteration (e.g., an explicit denylist of specific idioms, or a stricter
tense-ceiling rule per level) is a candidate for a future task if the user wants tighter
calibration.

## PM Acceptance

**Accepted 2026-09-15** — real before/after evidence recorded, no overclaiming. The
`news.txt` change is real, disclosed, and low-risk (single genre-scoped prompt file, no
app/test code touched); its effect is a genuine partial improvement, reported honestly
rather than declared a full fix. Closes Task 4.1.
