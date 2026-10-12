# Task 34.3: README refresh (ENH-024)

## Plan

- Product name: Daily Beyond English (brand, Phase 27), keeping the repo/app name where it is technical.
- Stack: the separate `video-renderer/` React/Remotion workspace (default Enhanced renderer) with the ffmpeg fallback;
  the cloud-first AI chain with the local Ollama fallback; Edge TTS; the smart music bed.
- Shipped features through Phase 32 in a short table, with links to the plans in `docs/implementation/` and the operation guides
  (storyboard, scene/shot/activity libraries, intro/outro, podcast modes, talking sprites). Fix the Phase 19 row ("in progress").
- Mark work that is built but waiting for owner gates as such. The released version stays `1.2.0-beta`.
- Base every claim on CHANGELOG, TRACKER and the code. Do not describe a feature the code does not have.

## Paths

- `README.md`

## Verification

Every link in README resolves to an existing file; the version line matches TRACKER and HANDOFF; no mention of the removed
vision auto-naming.
