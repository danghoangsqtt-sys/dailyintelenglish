# Task 19.5 — Vocabulary/idiom pop-up cards (timed to the containing line)

- **Status:** not started (doc-first card, awaiting Coder pickup after 19.4)
- **Owner:** Coder
- **Priority:** P0 (third and final composition feature for the T6 report; 19.6 dropped
  from scope)
- **Dependency:** Task 19.4 accepted (in flight); learning content already present on the
  demo project (`learning_contents` row for `b330d37f...`, 5 vocab + 4 idioms verified
  read-only)
- **Controlling detail:** `docs/implementation/phase-19-remotion.md` §3 "19.5" ("timed to
  the line that contains the item, from the existing Learning pack — no new learning
  content is generated"); Phase 19 invariants 36–40; ENH-013 scope item 3

## Goal

While a line plays whose text contains a vocab word or an idiom phrase from the project's
`learning_contents`, show a small pop-up card overlaying part of the frame with: the
word/phrase, IPA (vocab only), part-of-speech (vocab only), English + Vietnamese definition/
meaning, and the example sentence. When the line ends, the card fades or hides. A project
with no learning content still renders (no cards, no error).

**Timing/anchor decision must be made in design (D19.5-c below), because there is no
`line_id` field on vocab/idiom items.** The card must derive which line to attach to from
the item text alone.

No `VideoService` wire-up here (that's 19.7 partial). No new user-visible behaviour on the
app itself yet — still opt-in via the spike runner.

## Real data preflight (already verified read-only from PM side)

- Demo project (`b330d37f...`) has `learning_contents` with **5 vocab** + **4 idioms**.
- **Vocab item shape:** `word`, `part_of_speech`, `ipa`, `definition_en`, `definition_vi`,
  `example_sentence`.
- **Idiom item shape:** `phrase`, `meaning_en`, `meaning_vi`, `example_sentence`.
- **Neither shape carries a `line_id` or timing anchor.** The card must derive line
  attachment from the item text vs. line text — see D19.5-c.
- Learning content is optional: `learning_contents` row may be absent for a project.
  Handle it. (`b330d37f...` happens to have one; a future report-render episode may not.)

## Allowed files

- **Modify** `video-renderer/src/types.ts` — extend props schema (zod) with an optional
  top-level `learning: {vocab: Array<VocabItem>, idioms: Array<IdiomItem>}`. Both arrays may
  be empty. If `learning` is absent entirely, no card path is exercised.
- **Modify** `video-renderer/src/Episode.tsx` — add a `<VocabCard>` overlay component
  rendered when an active card is present. Position: **top-right corner** (opposite the
  speaker chip at top-left from 19.4, opposite the caption band at bottom). One card at a
  time; if multiple items match the same line, cycle through them in the item's own array
  order (each shows for the line's duration divided by the number of items in that line —
  Remotion time-slicing math, not a queue).
- **New** `video-renderer/src/vocab.ts` — pure helper
  `attachItemsToLines(vocab, idioms, lines) -> Array<{line_id, items: (VocabItem|IdiomItem)[]}>`
  and `activeItemForFrame(currentTimeSec, attached) -> VocabItem | IdiomItem | null`. Both
  pure functions, unit-testable.
- **New** `video-renderer/src/vocab.test.ts` — vitest for the two helpers. Coverage: word
  found in one line (attached correctly), word found in multiple lines (attached to the
  first matching line — deterministic, spec the tie-breaking rule), word not found in any
  line (item silently dropped — real Learning Content may reference concepts more abstract
  than verbatim script words), multi-item same-line time-slicing math, empty inputs, no
  learning content at all. Revert-and-confirm-failure required.
- **Modify** `scripts/run_remotion_spike.py` — read `learning_contents` for the selected
  project (`mode=ro` connection, same pattern), parse the JSON arrays, pass as
  `props.learning`. If the row is absent, pass `learning: undefined` (or omit — same
  effect).
- **New** `docs/operations/phase19-t5-vocab.md` — task-scoped report. Covers: matching
  strategy chosen (D19.5-c) + real numbers from the demo (how many of the 5 vocab / 4 idioms
  actually matched a line), wall time vs. 19.4's baseline, ≥2 frame-level spot checks of a
  card during its owning line, one frame that captures **all three** Phase 19 features
  simultaneously (karaoke band + speaker chip + vocab card) to prove nothing regressed.
- `CHANGELOG.md` — one `[Unreleased]` bullet.
- `.viepilot/phases/19-remotion/PHASE-STATE.md` — flip 19.5 row to done, append evidence
  entry.

**Not allowed:** any file under `app/`, `frontend/`, `tests/`, `docs/implementation/`; the
19.1 spike report, 19.3 t3 report, 19.4 t4 report (all immutable). `data/app.db` and
`data/learning*/` are `mode=ro` from Coder side, always.

## Design decisions (Coder, doc-first — commit these under `docs(review)` before code)

### D19.5-a: Matching strategy for vocab words

- Vocab items carry a `word` (single token, e.g. "punctual"). Options for finding which
  line "contains" it:
  - (i) **Case-insensitive substring match** on the raw line text (`line.text.toLowerCase()`
    contains `word.toLowerCase()`). Simplest. False positives possible (e.g. "run" matches
    "running" — arguably a feature). Deterministic.
  - (ii) **Word-boundary regex** (`\bword\b`, case-insensitive). Stricter; misses inflected
    forms ("run" won't match "running"). Deterministic.
  - (iii) **Lemma/stem match** (needs an NLP dep — adds significant weight to
    `video-renderer/node_modules`, out of proportion for a 4-day report scope).
- Recommend (i) — the false-positive risk is small in practice (vocab items are usually
  content words specific to the topic; a 5-item pack rarely has ambiguous common words),
  and matching inflected forms is arguably an educational feature (learner sees the card
  when they hear the word in any form). If a specific vocab word matches zero lines,
  silently drop it (real Learning Content sometimes references abstract concepts not
  literally in the script) — record this count in the report.
- **Justify with a real number from the demo:** run your matching strategy against the real
  5-vocab pack + 30-line script for `b330d37f...` before writing the composition code, and
  say how many of the 5 items actually matched a line (report §1). If the number is 0 or 1,
  the whole card system is a demo-time no-op and we need a different strategy — flag as a
  design finding, not as "shipped anyway."

### D19.5-b: Matching strategy for idiom phrases

- Idiom items carry a `phrase` (multi-word, e.g. "hit the books"). Options:
  - (i) **Case-insensitive substring match** on the raw line text.
  - (ii) **Normalized substring match** — lowercase both sides and collapse whitespace, so
    "  Hit  the books" matches "hit the books".
- Recommend (ii). Justify with a real matching test on the 4-idiom pack for `b330d37f...`.

### D19.5-c: Time-slicing when multiple items match the same line

- If a line contains 2 vocab words (or 1 vocab + 1 idiom), the card overlay shows one at a
  time. Options:
  - (i) **Divide the line's duration into N equal slots**, one card per slot in the order
    the items appear in their source arrays. Simple, deterministic.
  - (ii) **Anchor each card to the word's own spoken timestamp** (from 19.2/19.3's
    per-word data — use `activeTokenIndex` from 19.3's `karaoke.ts`). More accurate but
    depends on word-level timing being present (fallback needed if a line has no `words`).
- Recommend (i) for this task (simpler, robust to missing word timings). (ii) is a nicer
  future enhancement, out of scope for 4-day report.

### D19.5-d: Card visual + position + duration hint

- Position: top-right corner (opposite speaker chip at top-left, opposite caption band at
  bottom). Justify against not colliding with 19.4's chip's right edge in the demo's
  2-speaker case + at 5–6 speakers where chips wrap to a second top row.
- Card contents:
  - **Vocab:** `word` (bold, large) + `part_of_speech` (small italic) + `ipa` (small, in
    `/…/`), then `definition_en`, then `definition_vi` on a smaller row, then the
    `example_sentence` in italic.
  - **Idiom:** `phrase` (bold, large), then `meaning_en`, then `meaning_vi`, then
    `example_sentence` in italic.
- Fade in/out (~200 ms) rather than pop cut. Card background: semi-transparent dark panel
  (`rgba(14, 15, 21, 0.85)`, matching the composition's own background at ~85% opacity).
- Font: same family as the caption band (already in `CAPTION_TEXT_STYLE` from 19.1/19.3);
  smaller size (~18–20 px for body, ~24 px for the word/phrase header).

### D19.5-e: Verification, real numbers

- Real match count on demo (D19.5-a/-b real numbers).
- Wall time re-render vs. 19.4's baseline (expect near-flat: card is a text overlay, cheap).
- ≥2 frame spot checks of a card during its owning line + 1 frame with all three Phase 19
  features simultaneously.
- vitest passes; revert-and-confirm-failure on the matching helper.

### D19.5-f: Re-verify 19.1/19.3/19.4 invariants

- `app/services/video_service.py` still untouched (this is the last task before 19.7 partial
  touches it).
- Python full suite 1178/1178 unchanged.
- 19.3 karaoke + 19.4 speaker chip still render correctly — the combined-features frame
  proves both.

## Verification

- Real re-render of `b330d37f...` succeeds; ≥2 frame spot checks of a vocab/idiom card
  during its owning line; 1 combined-features frame.
- vitest passes; revert-and-confirm-failure on the matching helper.
- `tsc --noEmit` clean; Python full suite 1178/1178; ruff clean.
- `git log fe06405..HEAD -- app/services/video_service.py` still empty.
- Report on disk with real match count + wall time comparison.

## Evidence (Coder handover)

- Two shas (design + implementation).
- Full-suite + ruff + tsc + vitest lines.
- Re-render wall time vs. 19.4 baseline.
- Real match count: X of 5 vocab matched (which specific words did/didn't), Y of 4 idioms
  matched (which phrases). This is a real-data honesty item — if 0 or 1 match, flag as a
  design finding rather than shipping silently.
- ≥2 frame filenames + expected-vs-observed cards + 1 all-three-features frame.
- Carry-overs still open (8-min episode; Chrome 270 MB).

## Definition of done

- Two commits, design before implementation.
- Composition renders vocab/idiom cards timed to owning lines; falls back cleanly on
  no-match items and no-learning-content episodes.
- Report on disk (`docs/operations/phase19-t5-vocab.md`).
- All checks green, `app/services/video_service.py` genuinely untouched.
- Handover per Evidence checklist.
