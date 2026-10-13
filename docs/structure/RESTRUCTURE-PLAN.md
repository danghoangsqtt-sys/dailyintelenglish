# Restructure plan — Phase 38 (D115, owner-approved 2026-10-13)

Made with the `vp-struct` process: audit numbers → target tree → mapping → approval → plan committed → moves.

## Why (structure scan, 2026-10-13)

- `app/services/` is one flat folder of 29 modules plus `ai/` and `visuals/` (22 modules) — scripts, audio, video,
  YouTube, channel, GPU and settings side by side.
- AI is spread over **six** places: `app/services/ai/` (LLM providers), `app/services/ai_*.py`, `app/core/prompt_loader.py`,
  `app/services/visuals/` (image engine and pipelines), `app/services/gpu_model_manager.py`, `app/services/tts_service.py`,
  plus runtime code in `scripts/image_worker.py`, prompts in `prompts/`, weights in `models/` and `requirements-image.txt` at the root.
- `app/models/` holds Pydantic schemas, easily confused with AI model weights.
- 1,154 references to `app.` in 230 files (73 in `app/`, 106 in `tests/`, 10 in `scripts/`).

## Target tree

```
Daily_Intel_English/
├── backend/                 # was app/ — the FastAPI package (main.py, desktop_launcher.py)
│   ├── api/  core/  db/     # unchanged inside (settings_service.py joins core/)
│   ├── schemas/             # was app/models/ (Pydantic request/response models)
│   ├── ai/
│   │   ├── llm/             # gateway, router, providers, AI jobs + worker, prompt_loader
│   │   ├── image/           # engine, runner, jobs, pipelines, recipes, checks, GPU arbiter, image_worker.py, requirements.txt
│   │   ├── tts/             # tts_service
│   │   ├── prompts/         # was prompts/
│   │   └── models/          # was models/ — weights (gitignored)
│   ├── content/             # script, learning, youtube, shorts, project
│   ├── media/               # audio, music, video + Remotion bridge, thumbnail, brand
│   ├── library/             # characters, scenes, shots, sprites, activity library, storyboard
│   └── channel/             # channel plan, dashboard
├── frontend/                # unchanged
├── renderer/                # was video-renderer/ (Remotion)
├── scripts/                 # maintenance CLIs only (nothing the app imports or spawns)
├── tests/  docs/  data/
└── .venv/  .venv-image/     # recreated from pip freeze (were venv/, venv-image/)
```

Module file names do not change (only packages), so code that uses `audio_service.x` keeps its identifiers.

## Module mapping (old → new)

| Old | New |
|---|---|
| `app.services.visuals.colour_check` | `backend.ai.image.colour_check` |
| `app.services.visuals.engine` | `backend.ai.image.engine` |
| `app.services.visuals.geometry` | `backend.ai.image.geometry` |
| `app.services.gpu_model_manager` | `backend.ai.image.gpu_model_manager` |
| `app.services.visuals.jobs` | `backend.ai.image.jobs` |
| `app.services.visuals.pipelines` | `backend.ai.image.pipelines` |
| `app.services.visuals.recipes` | `backend.ai.image.recipes` |
| `app.services.visuals.runner` | `backend.ai.image.runner` |
| `app.services.visuals.shot_checks` | `backend.ai.image.shot_checks` |
| `app.services.ai_job_service` | `backend.ai.llm.ai_job_service` |
| `app.services.ai_worker` | `backend.ai.llm.ai_worker` |
| `app.services.ai.contracts` | `backend.ai.llm.contracts` |
| `app.services.ai.fake_provider` | `backend.ai.llm.fake_provider` |
| `app.services.ai.ollama_provider` | `backend.ai.llm.ollama_provider` |
| `app.services.ai.openai_compat_provider` | `backend.ai.llm.openai_compat_provider` |
| `app.core.prompt_loader` | `backend.ai.llm.prompt_loader` |
| `app.services.ai.router` | `backend.ai.llm.router` |
| `app.services.ai.validation` | `backend.ai.llm.validation` |
| `app.services.tts_service` | `backend.ai.tts.tts_service` |
| `app.services.channel_service` | `backend.channel.channel_service` |
| `app.services.dashboard_service` | `backend.channel.dashboard_service` |
| `app.services.learning_pipeline` | `backend.content.learning_pipeline` |
| `app.services.learning_service` | `backend.content.learning_service` |
| `app.services.project_service` | `backend.content.project_service` |
| `app.services.script_pipeline` | `backend.content.script_pipeline` |
| `app.services.script_service` | `backend.content.script_service` |
| `app.services.shorts_service` | `backend.content.shorts_service` |
| `app.services.youtube_service` | `backend.content.youtube_service` |
| `app.services.settings_service` | `backend.core.settings_service` |
| `app.services.visuals.activity_illustrations` | `backend.library.activity_illustrations` |
| `app.services.visuals.activity_library_service` | `backend.library.activity_library_service` |
| `app.services.visuals.activity_matcher` | `backend.library.activity_matcher` |
| `app.services.visuals.character_asset_service` | `backend.library.character_asset_service` |
| `app.services.visuals.character_profile_service` | `backend.library.character_profile_service` |
| `app.services.visuals.library_service` | `backend.library.library_service` |
| `app.services.visuals.project_visuals_service` | `backend.library.project_visuals_service` |
| `app.services.visuals.shot_library_service` | `backend.library.shot_library_service` |
| `app.services.visuals.sprite_plan` | `backend.library.sprite_plan` |
| `app.services.visuals.sprite_service` | `backend.library.sprite_service` |
| `app.services.visuals.sprite_upload` | `backend.library.sprite_upload` |
| `app.services.visuals.storyboard_service` | `backend.library.storyboard_service` |
| `app.services.audio_service` | `backend.media.audio_service` |
| `app.services.brand_service` | `backend.media.brand_service` |
| `app.services.music_analysis` | `backend.media.music_analysis` |
| `app.services.music_bed` | `backend.media.music_bed` |
| `app.services.music_library_service` | `backend.media.music_library_service` |
| `app.services.music_select_service` | `backend.media.music_select_service` |
| `app.services.thumbnail_compose` | `backend.media.thumbnail_compose` |
| `app.services.thumbnail_service` | `backend.media.thumbnail_service` |
| `app.services.video_renderer_remotion` | `backend.media.video_renderer_remotion` |
| `app.services.video_service` | `backend.media.video_service` |
| `app.models.*` | `backend.schemas.*` |
| `app.api.*`, `app.core.*`, `app.db.*`, `app.main`, `app.desktop_launcher` | `backend.…` (same names) |

## Folder and file moves

| Old | New | How |
|---|---|---|
| `app/` | `backend/` | `git mv` |
| `app/models/` | `backend/schemas/` | `git mv` |
| `scripts/image_worker.py` | `backend/ai/image/image_worker.py` | `git mv` |
| `prompts/` | `backend/ai/prompts/` | `git mv` |
| `requirements-image.txt` | `backend/ai/image/requirements.txt` | `git mv` |
| `video-renderer/` | `renderer/` | same-drive rename (keeps `node_modules/`) |
| `models/` | `backend/ai/models/` | same-drive rename, **after** the Phase 39 downloads finish |
| `venv/`, `venv-image/` | `.venv/`, `.venv-image/` | recreated from `pip freeze` (same versions); old ones removed only after tests pass and with owner OK |

## References to rewrite

- Python imports and string targets (`monkeypatch.setattr("app.services.x.f")`) — by codemod over this mapping
  (AST-located `from … import …` statements, split when one statement imports modules that now live in different
  packages).
- `backend/core/paths.py` stays 3 levels deep (`backend/core/paths.py` → root); path constants for prompts
  (`backend/ai/prompts`), renderer (`renderer/`), image worker, image venv (`.venv-image`), model cache
  (`backend/ai/models/image`).
- Entry points: `uvicorn backend.main:app`; `.claude/launch.json`; `scripts/build_exe.ps1` (`.venv`);
  `daily_intel_english_studio.spec` (datas: `backend/ai/prompts`, `backend/db/migrations`; entry script); `.gitignore`
  (`.venv*/`, `backend/ai/models/`, `renderer/` ignores); `pytest.ini`; Ruff config; `scripts/*.py`.
- Docs: README (install, run, structure), `.viepilot/ARCHITECTURE.md`, `AI-GUIDE.md`, `docs/structure/STRUCTURE.md`
  (new "where does X live" map), CHANGELOG. Historical phase docs keep the old paths.
- Packaged app: data folder and exe names unchanged (`DailyIntelEnglishStudio`).

## Steps (one commit each, full verification after each)

1. Code moves + codemod + path constants + entry points (`backend/`, `schemas/`, domains, worker, prompts).
2. `video-renderer/` → `renderer/` and its references.
3. Recreate `.venv` and `.venv-image` from freeze; switch launch/build scripts; tests on the new venvs.
4. After the Phase 39 downloads: `models/` → `backend/ai/models/`.
5. Docs: README, ARCHITECTURE, AI-GUIDE, STRUCTURE.md, CHANGELOG.
6. Restart the real app (owner OK) with `uvicorn backend.main:app`; smoke test.

Verification: `compileall`, import of every module, Ruff, full pytest (baseline **1,686 passed**), Vitest (70),
`tsc`, app smoke on a spare port, `git grep` for every old path (only history docs may keep them).

Rollback: `git revert` the step's commit; the old venvs and folders stay until the end.
