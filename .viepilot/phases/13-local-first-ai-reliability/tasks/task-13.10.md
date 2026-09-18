# Task 13.10 — Rollout, Documentation, and Rollback Drill

- **Status:** pending
- **Dependency:** Gate B decision (pass or fail), not necessarily a local-primary pass
- **Controlling detail:** implementation plan §8, Task 13.10

## Objective

Ship the evidence-selected mode, document the external runtime safely, prove packaging,
and drill `hybrid → gemini with Ollama stopped → hybrid` without DB repair/data loss.

## Allowed files

Exactly the documentation/state/config/dependency/packaging paths listed for 13.10 in
the controlling plan.

## Release branches

- Gate B pass: local-first in development; packaged default changes only if onboarding
  and fresh-install diagnostics pass.
- Gate B fail: durable jobs ship Gemini-primary; local is explicitly experimental.

## Verification and exit

Install/pull/digest/update/uninstall/privacy guidance is actionable; missing Ollama/model/
VRAM/key states are nonfatal and clear; rollback produces script and learning with no
migration reversal; full suite/build remains green; state/docs match measured behavior;
only explicit files are committed/pushed under the authorized workflow.
