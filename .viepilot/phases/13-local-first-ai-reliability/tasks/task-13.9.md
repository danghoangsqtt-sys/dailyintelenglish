# Task 13.9 — Real No-Mock Bake-Off and Operational Trial (Gate B)

- **Status:** pending
- **Dependency:** 13.1–13.8
- **Controlling detail:** implementation plan §8, Task 13.9

## Objective

Use live uvicorn HTTP and real providers to decide local-primary versus experimental,
then complete a real eight-minute script → every-line Edge TTS → MP3 → midnight 16:9
MP4 run. Never use TestClient, pytest, mocks, or assumed completion.

## Allowed files/runtime effects

Operational runner, acceptance report, ignored JSON/CSV/log/media evidence, and created
project/media/database rows. Do not delete the test project; keep review server running.

## Gate B

Use every fixed threshold in the controlling plan: five local-only B1 eight-minute
runs, 4/5 content/performance pass, 5/5 deterministic learning checks plus human review,
and ffprobe-readable 432–528s audio/video with ≤1.0s A/V difference and no server
ERROR/traceback. Record IDs, digest/settings, timings, repairs/fallbacks, resource peaks,
bytes, hashes, durations, codecs, and all warnings. Do not weaken thresholds post hoc.
