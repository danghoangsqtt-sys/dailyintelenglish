# Task 34.2: Completion checkpoint tags (BUG-024)

## Plan

Create an annotated tag at the commit that closed each phase. Confirm the evidence first:

| Tag | Candidate commit | Evidence |
|---|---|---|
| `die-vp-p21-complete` | `849f65c` | D38: Phase 21 closed wontfix, Edge TTS stays (tag message says "closed wontfix") |
| `die-vp-p26-complete` | `bdedace` | Task 26.4 done, Phase 26 interim polish complete |
| `die-vp-p30-complete` | `eca4765` | Task 30.4, PHASE-STATE complete (confirm no later Phase 30 commit) |
| `die-vp-p31-complete` | `7da7369` (last Phase 31 commit; the 31.2 card landed in `f52ebb3`) | PHASE-STATE done 2026-10-07 |

Push the tags to `origin` only after the owner OKs the push (outward-facing). Phases 20, 22, 23, 24, 27, 28, 29 and 32 get no
tag: they wait for owner gates.

## Paths

- (git tags only, no files)

## Verification

`git tag -l "die-vp-p*-complete"` lists 21, 26, 30 and 31; `git ls-remote --tags origin` shows them after the push.
