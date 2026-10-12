# Task 34.4: ARCHITECTURE, PROJECT-META and API reference (ENH-025)

## Plan

- `.viepilot/PROJECT-META.md`: product name, version `1.2.0-beta`, current stack (cloud-first AI gateway, Remotion + ffmpeg, visuals).
- `.viepilot/ARCHITECTURE.md`: describe the AI gateway (`app/services/ai/`), the visual libraries and pipelines
  (`app/services/visuals/`: scene, shot, activity and sprite libraries, storyboard, matcher), and the Remotion renderer with its
  fallback. Update the Mermaid sources `system-overview.mermaid`, `data-flow.mermaid` and `module-dependencies.mermaid` and keep
  the "Diagram source" lines in step (ENH-022 sidecar rule).
- `docs/api.md`: regenerate with `scripts/generate_api_docs.py` from the current FastAPI schema; check that the Activity Library,
  sprite and activity-coverage routes in `app/api/visuals.py` are present.

## Paths

- `.viepilot/PROJECT-META.md`
- `.viepilot/ARCHITECTURE.md`
- `.viepilot/architecture/system-overview.mermaid`
- `.viepilot/architecture/data-flow.mermaid`
- `.viepilot/architecture/module-dependencies.mermaid`
- `docs/api.md`

## Verification

The route count in `docs/api.md` equals the count in the live OpenAPI schema; grep finds the activity and sprite routes; every
`required` diagram has Mermaid content and a matching sidecar file.
