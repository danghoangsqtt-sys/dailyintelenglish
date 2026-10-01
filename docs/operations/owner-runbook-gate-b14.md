# Gate B-14 — AI Visuals owner runbook

Phase 20 implementation is on `feature/phase20-ai-visuals`. PM review and owner visual sign-off remain separate from the implementer smoke. Run this on the owner's NVIDIA machine after reviewing the Task 20.3–20.8 handovers.

## Preconditions

- Use the Phase 20 branch and a clean tracked worktree. Leave the six existing Gate B-12 MP4s alone.
- `venv\`, `venv-image\`, Node and `video-renderer\node_modules\` already exist. Do not install packages during this gate.
- Close any app listening on port 8000 before the real smoke. The script starts an isolated in-process app and creates a temporary `DIE_DATA_DIR`; it never writes to the owner's production DB.
- The real worker needs an NVIDIA GPU. The image engine leases GPU memory and may unload a resident Ollama model to meet the 8192 MiB threshold.

## Smoke

From the repository root in PowerShell:

```powershell
.\venv\Scripts\python.exe scripts\smoke_ai_visuals.py --fake
.\venv\Scripts\python.exe scripts\smoke_ai_visuals.py --output-dir data\tmp\gate-b14-smoke
```

The first command is the deterministic CI-style check. The second drives the real worker. Both commands create two invented characters, generate candidates and four approved sheet assets each, lock them, assign them to two project speakers and two built-in scenes, generate eight shots, build Remotion props and render one 1280×720 still for each shot kind (`single`, `duo_close`, `duo_wide`). An exit code of zero and a JSON summary with `shot_count: 8` and three still paths is the smoke pass condition. The real stills are kept under `data\tmp\gate-b14-smoke\<run>\`; generated files are ignored by Git. The temporary DB and images are removed when the command exits.

If either command fails, retain its terminal output and record the failing stage and error in the gate evidence; do not call the gate passed. The script prints `shot_generation_seconds` and `three_stills_seconds` for timing evidence.

### Implementer smoke evidence (2026-10-01)

- Fake engine: pass — two locked characters, eight completed shots, and three Remotion stills.
- Real worker on RTX 3060: pass — project `50b87215-e72e-43c2-a61a-a3704edc99c1`, eight completed shots; shot generation **598.32 s**, three Remotion stills **10.42 s**.
- Real stills: `data\tmp\gate-b14-smoke\20261001T061647Z-50b87215\{single,duo_close,duo_wide}.png`.
- Implementer visual observation: the `duo_close` still includes an unintended third person, and outfit colors drift from the references. The owner should evaluate this in the refine comparison and three-episode review. This smoke establishes execution, not visual acceptance.

## Owner visual checks

1. Open all three real stills. Check recognizable faces and outfits, hands, scene continuity, framing, captions and unobstructed vocabulary cards. Record any shot IDs that need regeneration.
2. Compare duo scenes with `DIE_VISUALS_DUO_REFINE=true` and `false` on the same two-character project. Record which version keeps both identities and outfit colors more consistently. Keep seeds and scene choice in the evidence so the comparison is reviewable.
3. In the app, generate shots for three real episodes with different dialog and scene choices. Record project IDs, selected scenes, shot counts, failures and representative final images. Do not commit the image output.
4. Record shot generation time and Enhanced (Remotion) render time per project. Confirm Standard (ffmpeg) remains usable and existing thumbnail templates remain available on projects without shots.

## Gate record

The owner records **PASS**, **PARTIAL** or **FAIL** with the still paths, three-project notes, refine comparison and timing table. The PM reviews the evidence under AR-06. This runbook and implementer smoke do not themselves grant owner visual acceptance.
