# Task 46.3 — BUG-039: Remotion navigation recovery

## Objective
The observed no-response navigation failure gets one fresh render attempt within the existing timeout budget, with diagnostics retained and old successful media preserved.

## Paths
- backend/media/video_renderer_remotion.py
- tests/test_video_service_remotion.py
- .viepilot/debug/CURRENT.json
- .viepilot/debug/session-debug-20261014T091435Z.json
- .viepilot/requests/BUG-039.md
- docs/operations/phase46-render-reliability.md
- .viepilot/phases/46-audit-bugfixes/
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md

## File-Level Plan
- Renderer bridge: detect only the recorded temporary localhost navigation/no-response error; retry once with a fresh process and remaining total timeout. Persist per-attempt stdout/stderr and outcome. Arbitrary errors/timeouts still fail honestly; publication remains atomic.
- Tests: transient failure then success; repeated transient failure; ordinary failure not retried; shared timeout budget; prior output preserved.
- Real verification: use read-only production snapshots or saved props/assets; render a full episode into disposable output, verify duration/resolution/audio with ffprobe. No production DB writes or app restart.
- Debug and operation report: distinguish mitigated failure from unconfirmed underlying cause and record measured evidence.

## Risk and conventions
A retry can increase elapsed time but may not exceed the existing overall render budget. Do not retry arbitrary failures or conceal failure diagnostics. No automatic acceptance of owner visual gates.

## Verification
- python -m pytest -q tests/test_video_service_remotion.py tests/test_video_service.py
- Real full episode render and ffprobe; Ruff, renderer typecheck/Vitest; full pytest.

## Verification result
Fault-injection regression failed before implementation. After implementation: 47 focused tests passed; full real episode rendered successfully in 194.886 s, 240.917333 s output duration, 1280x720 H.264/AAC, A/V difference <0.1 s. Source DB connection was read-only/query_only with zero changes. Original null-response cause remains unconfirmed; the fix is bounded recovery with retained diagnostics. Report: docs/operations/phase46-render-reliability.md. Full regression gate is running.

## Final regression gate
2026-10-15: 1,621 pytest passed in 871.13 s; 72 Vitest passed; Ruff, TypeScript, JS syntax and diff checks clean. Technical implementation/verification complete; formal acceptance and persistence await the owner/PM under AR-06.
