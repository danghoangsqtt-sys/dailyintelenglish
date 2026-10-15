# Task 47.1: Fix subtitle phrase continuity

## Objective / authorization

Implement BUG-041 after the owner's explicit 2026-10-15 instruction to plan with vp-evolve and execute with vp-auto. The preceding audit and the owner's clarification identify subtitle text pagination as the scope. Complete bounded implementation and checks autonomously; preserve production media and data.

## Paths

- renderer/src/karaoke.ts
- renderer/src/captionPaging.ts (new)
- renderer/src/Episode.tsx
- renderer/src/captionPaging.test.ts
- .viepilot/phases/47-caption-continuity/SPEC.md
- .viepilot/phases/47-caption-continuity/PHASE-STATE.md
- .viepilot/phases/47-caption-continuity/tasks/task-47.1.md
- .viepilot/requests/BUG-041.md
- .viepilot/audit/caption-continuity-20261015.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- docs/operations/caption-continuity-20261015.md (new)
- data/tmp/caption-fix-20261015/ (disposable probes, input props, logs and preview outputs)

## File-Level Plan / allowed_files

- `captionPaging.ts`: focused pure segmentation helper with typed token imports. Score fitting boundary choices using sentence/clause punctuation, function-word boundaries, protected learning phrases and page balance. Split at sentence boundaries; preserve short-line identity and single-word over-capacity fallback. Use bounded dynamic programming/lookahead, deterministic stable tie-breaking, no NLP/provider dependency.
- `karaoke.ts`: retain public captionPage compatibility, delegate pagination and expose helpers to precompute/select pages. Fix punctuation recognition within the replaced pagination logic, not unrelated token matching.
- `Episode.tsx`: memoize protected idiom/multiword vocab phrases from existing learning data, pass to CaptionBand and memoize segmentation by tokens/layout/phrases. Keep existing font geometry and word highlight/timing/motion.
- `captionPaging.test.ts`: regressions for actual Episode 3 full utterances and both layout capacities, phrase preservation, punctuation/short clauses, balanced tails, all-token/timing identity, seek order, absent/overlong/overlapping phrases and numeric mismatch. Tests must fail against the original behavior before the fix where practical.
- Phase/request/audit/state/changelog files above: record plan before code, progress and accurate final verification; no claimed owner gate acceptance or release tag bump.
- `docs/operations/caption-continuity-20261015.md`: implementation explanation and reproducible verification/preview references.
- Temporary probes can read the real DB in `mode=ro, query_only`; generated Remotion assets may be staged only through the existing ignored renderer public asset/cache paths. Outputs stay in `data/tmp/caption-fix-20261015/`, never overwrite existing project MP4/SRT/audio.

## Risks / guardrails

- Heuristics cannot parse arbitrary English perfectly: prioritize known learning phrases and grammatical cues, keep hard layout bounds, degrade deterministically when a phrase/token cannot fit. Avoid screenshot-specific phrase dictionaries.
- Global page scoring can over-fragment or create tiny remainders: test both natural boundaries and balanced pages. Do not hide issues by globally shrinking fonts or raising word/character caps.
- Extra per-frame work could increase render time: memoize segmentation, leave only page selection and active-word selection frame-dependent.
- Preserve every token object and timestamp, audio, transcript, speaker and word ordering. No TTS calls or DB writes. Preview with actual production composition and actual word timings.
- New modules must not introduce runtime circular dependencies; type-only imports and one pure helper module.

## Best practices / context

Apply `.viepilot/audit/caption-continuity-20261015.md` guardrails and official Netflix English line-treatment guidance already researched during audit (as a readability design reference, not a YouTube delivery standard). React useMemo caches pure computations but must not be required for correctness. Existing Remotion/React/TypeScript dependencies and runtime docs are the implementation reference.

## Verification

1. Run targeted caption tests before/after; show screenshot regressions fail before the product fix.
2. `npm.cmd test` and `npm.cmd run typecheck` in renderer; all pass.
3. Reproduce page boundaries from actual Episode 3 word timings; validate all original words in sequence and bounded pages for both layouts.
4. Render real production boundary PNGs and short clips for both layouts; inspect visible phrase continuity, fit/safe area and highlight alignment. No full-episode render required to verify this local change.
5. `git diff --check`, explicit staged-file review, commit/push to existing owner branch under continuing authorization; verify clean working tree and no unpushed commits before reporting durable completion. No main application merge or new release asset.

## Progress

- Planning/preflight complete; 47.1 is in_progress before source edits.
- Plan checkpoint: 8d9a019, annotated task checkpoint die-vp-p47-t47.1. Owner explicitly authorized plan + execute; no extra scope approval was needed.
- Initial four new screenshot regressions failed while the four original paging tests passed, confirming meaningful regression coverage.
- Implemented deterministic sentence-aware dynamic programming, grammatical cue costs, balanced tails, fitting learning-phrase protection and capacity fallback. Memoized pages and protected phrase lists in the actual composition.
- Final renderer suite: **104 passed / 14 files**, TypeScript clean. No backend changes or dependency additions; full Python suite not rerun.
- Actual Episode 3: **22 lines / 44 layout partitions**, original token objects/times retained and every page within existing limits. General modifier cues were refined after inspecting the narrow-layout output, adding regression coverage for the intact `notoriously difficult recipe` unit.
- Final real production previews: 8 PNGs and 4 H.264/AAC clips, both resolutions, inspected representative frames, all clips fully decoded. 150/186 video frames (5.0/6.2 s), container AAC padding ~0.05 s. Source MP3/WAV hashes unchanged; DB read-only, zero changes; full production videos/SRT untouched.
- Evidence and limits: `docs/operations/caption-continuity-20261015.md`; local files under `data/tmp/caption-fix-20261015/`.
- Technical implementation verified; formal owner visual acceptance pending. Published rc.1 assets unchanged; installed linked-runtime app uses this renderer for future renders.
