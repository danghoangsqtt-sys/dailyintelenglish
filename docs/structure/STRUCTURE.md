# Where is what — project structure map

Current layout, refreshed 2026-10-15 (Phase 46). Module rows are generated from the current Python files and their docstrings; historical Phase 38 plan: `docs/structure/RESTRUCTURE-PLAN.md`.

| Folder | What lives there |
|---|---|
| `backend/` | FastAPI package: `main.py` (app, routers, startup), `desktop_launcher.py` (packaged exe entry) |
| `backend/ai/prompts/` | Jinja2 prompt templates (script, learning, thumbnail, YouTube, storyboard, channel, shorts) |
| `backend/ai/models/` | Local model weights, Hugging Face cache (gitignored) |
| `backend/db/migrations/` | Numbered SQL migrations, applied at startup |
| `frontend/` | `pages/` (one HTML page per screen) and `static/` (css, js, fonts, brand) |
| `renderer/` | Remotion (React/TypeScript) video compositions, `public/` assets, Vitest tests |
| `scripts/` | Maintenance CLIs and `benchmarks/`; nothing the app imports at runtime |
| `tests/` | pytest suite (unit, API, Playwright browser tests) |
| `docs/` | `user/` guides, `operations/` runbooks and gate reports, `implementation/` phase plans, `report/`, `structure/`, `brainstorm/` |
| `.venv/`, `.venv-image/` | Python for the app; separate Python with torch + diffusers for the image worker |

## AI — text — `backend/ai/llm/`

| Module | Purpose |
|---|---|
| `ai_job_service.py` | Durable AI generation job state machine (Phase 13, Task 13.3) |
| `ai_worker.py` | In-process worker for durable AI generation jobs (Phase 13, Task 13.3) |
| `contracts.py` | Typed request/result contracts and the provider interface for the AI gateway. |
| `fake_provider.py` | Deterministic, network-free provider double for tests. |
| `ollama_provider.py` | Ollama adapter: one HTTP call to a loopback-only /api/generate, no internal retry |
| `openai_compat_provider.py` | OpenAI-compatible adapter (OpenRouter, or any /chat/completions-shaped endpoint): one HTTP call per `generate()`, no internal retry |
| `prompt_loader.py` | Loads and renders script-generation prompt templates (Jinja2) |
| `router.py` | Central AI router: AI_MODE selection, bounded per-provider retry with exponential backoff for transient errors, one visible cloud-to-local fallback, and an in-process circuit breaker over the primary provider (Phase 13/14, ADR-001; Phase 18/D21 made cloud the default primary, local the fallback) |
| `validation.py` | Shared JSON-parse + Pydantic-schema validation primitive for AI provider output. |

## AI — local GPU images — `backend/ai/image/`

| Module | Purpose |
|---|---|
| `engine.py` | Image worker protocol (Qwen batches) and the deterministic, GPU-free test engine. |
| `gpu_model_manager.py` | Task 20.1 -- one process-wide arbiter for the single RTX 3060 (D20.1-a..g) |
| `image_worker.py` | The local image worker process (runs INSIDE `.venv-image/`) |
| `jobs.py` | Persistent FIFO image jobs |
| `pipelines.py` | Background image jobs |
| `qwen_runner.py` | Phase 39 (D118): Qwen image models inside the image worker (runs in `.venv-image`; the app never imports it) |
| `recipes.py` | The image prompts |
| `runner.py` | One-at-a-time image job loop with durable restart and cancellation semantics. |

## AI — speech — `backend/ai/tts/`

| Module | Purpose |
|---|---|
| `tts_service.py` | Converts script lines to speech per speaker (Task 1.6, Sub-task 1.6a) |

## Episode content and exports — `backend/content/`

| Module | Purpose |
|---|---|
| `export_service.py` | Phase 41 (D120): the project's own output folder |
| `learning_pipeline.py` | Grounded learning-content pipeline (Phase 13, Task 13.5) |
| `learning_service.py` | Generates and persists Learning Content packs via the AI provider gateway (Task 1.5) |
| `project_service.py` | Project CRUD and state-machine logic. |
| `script_pipeline.py` | Checkpointed script generation pipeline (Phase 13, Task 13.4) |
| `script_service.py` | Generates podcast scripts via the AI provider gateway, with schema validation. |
| `shorts_service.py` | Phase 37 (D98-D101): highlight clips for YouTube Shorts and TikTok |
| `youtube_service.py` | Generates and persists YouTube Package metadata via the AI provider gateway (Task 1.9) |

## Media production — `backend/media/`

| Module | Purpose |
|---|---|
| `ai_scene.py` | Phase 43 (D122): framing the "AI scene" thumbnail |
| `audio_service.py` | Mixes per-line TTS audio into one podcast track (Task 1.6, Sub-task 1.6b) |
| `brand_service.py` | Phase 25 (D52-D55): the branded intro/outro voice lines |
| `music_analysis.py` | Task 22.9: automatic classification of a library track (blocking; run in a thread) |
| `music_bed.py` | Task 22.4 (D51): the background-music bed under an episode's voice |
| `music_library_service.py` | Task 22.7: Music Library track details (rows in `music_tracks`) for hand-downloaded free music |
| `music_select_service.py` | Task 22.8 (D51): pick a library track for an episode by topic and length |
| `thumbnail_compose.py` | Task 36.3/36.4 (D90-D92): the episode thumbnail composed from what the episode already has |
| `thumbnail_service.py` | Generate, render, persist, and safely resolve thumbnail variants. |
| `video_renderer_remotion.py` | Remotion rendering: props, subprocess diagnostics, bounded navigation recovery and atomic media publication |
| `video_service.py` | Renders a project's mixed audio into the episode MP4 with Remotion (the only video renderer since Phase 35, Task 35.5, D89: the Standard ffmpeg background+subtitle renderer, its templates and the silent fallback were removed) and writes the SRT subtitles beside it |

## Picture library and storyboard — `backend/library/`

| Module | Purpose |
|---|---|
| `activity_illustrations.py` | Task 33.10 (Gate B-23, D102): which storyboard inserts have an Activity Library picture, and the pictures still missing |
| `activity_library_service.py` | Review-gated reusable activity illustrations and their safe local storage. |
| `activity_matcher.py` | Pure, explainable selection of reviewed activity images for storyboard insert beats. |
| `character_asset_service.py` | Phase 33 (Task 33.3, D84/D86): the picture slots of a character profile, their prompts, uploads and review |
| `character_profile_service.py` | Phase 33 (Task 33.2): reusable character profiles -- Quick create, autosave, readiness, duplicate, archive and safe delete |
| `library_service.py` | Global character and scene library lifecycle and safe content paths. |
| `project_visuals_service.py` | Project cast and ordered scenes |
| `scene_backgrounds.py` | Scene plates imported from `assets_background/` (named by scene key: cafe.png, city-street.png...) |
| `sprite_plan.py` | Phase 32 (Task 32.2): what each talking sprite does on each line -- its face, its gesture and when its mouth is open |
| `sprite_service.py` | Phase 32 (Task 32.1): the talking-sprite sets of the library characters |
| `sprite_upload.py` | Phase 33 (Task 33.3, D84/D86): turn a picture made with an outside AI into a talking-sprite slot picture |
| `storyboard_service.py` | Task 24.1: storyboard storage, validation against the project, and the image estimate. |

## Channel — `backend/channel/`

| Module | Purpose |
|---|---|
| `channel_service.py` | Task 36.5 (D103-D105): the channel plan |
| `dashboard_service.py` | Task 36.7 (D106-D108): the channel dashboard -- what the channel has, what to do today, where it stands on the channel-building roadmap, which step every episode is at, and the next two weeks |

## HTTP routes — `backend/api/`

| Module | Purpose |
|---|---|
| `ai_jobs.py` | Durable AI generation job routes, and the AI runtime health check (Phase 13, Task 13.3). |
| `audio.py` | Audio mixing routes (Task 1.6, Sub-task 1.6b) |
| `channel.py` | Task 36.5 (D103-D105): the channel plan -- topics, series, episodes, the AI map and the publishing calendar. |
| `export.py` | Phase 41 (D120): the project's output folder and the components exported there. |
| `learning.py` | Learning Content routes (Task 1.5 — Sprint 1.5B). |
| `music.py` | Music library routes for listing, uploading, previewing, editing details and deleting tracks. |
| `profiles.py` | Phase 33 (Task 33.2): character profile API |
| `projects.py` | Project management routes. |
| `settings.py` | App-level settings routes (Task 12.1; Task 18.3 cloud provider settings). |
| `shorts.py` | Phase 37 (D98-D101): highlight clips for YouTube Shorts and TikTok, and their covers and texts. |
| `storyboard.py` | Task 24.1: a project's storyboard (beats that tile the script lines). |
| `thumbnail.py` | Thumbnail generation, listing, template discovery, and content routes. |
| `tts.py` | TTS engine discovery + per-line preview routes (Task 1.6). |
| `video.py` | Video generation routes (Task 1.7, Sub-task 1.7a) |
| `visuals.py` | Character, scene, and project visuals API. |
| `youtube.py` | YouTube Package routes (Task 1.9). |

## Core — `backend/core/`

| Module | Purpose |
|---|---|
| `config.py` | Application settings loaded from environment variables / .env file. |
| `constants.py` | Named constants shared across services |
| `exceptions.py` | Typed exceptions raised by services |
| `paths.py` | Centralized project-root resolution (Task 12.2) |
| `responses.py` | Standard API response envelope shared by every route. |
| `settings_service.py` | App-level settings (Task 12.1; Task 18.3 cloud provider settings) |
| `system_checks.py` | Non-blocking checks for external tooling (ffmpeg, GPU) used at startup and /health. |

## Database — `backend/db/`

| Module | Purpose |
|---|---|
| `database.py` | Async SQLite connection management (aiosqlite). |
| `transactions.py` | Shared write-lock/transaction helpers over the single app-wide aiosqlite connection |

## Pydantic schemas — `backend/schemas/`

| Module | Purpose |
|---|---|
| `ai_job.py` | Pydantic models for the durable AI generation job API (Phase 13, Task 13.3). |
| `audio.py` | Pydantic models for audio mixing requests/responses (Task 1.6, Sub-task 1.6b). |
| `channel.py` | Task 36.5 (D103-D105): the channel plan -- topics (playlists) -> series -> episodes, and the AI channel map. |
| `learning.py` | Pydantic models for Learning Content (Task 1.5) generation and persistence. |
| `music.py` | Task 22.7 (D50/D51): Music Library track details -- mood and tags for auto-select, licence and credit for the YouTube description |
| `project.py` | Pydantic models for project creation and update requests. |
| `script.py` | Pydantic models for script generation/regeneration/save requests. |
| `settings.py` | Pydantic models for app-level settings requests (Task 12.1, 13.6, 18.3). |
| `storyboard.py` | Task 24.1: storyboard beats -- story moments that tile a project's script lines. |
| `thumbnail.py` | Pydantic contracts for thumbnail templates, Gemini suggestions, and API requests. |
| `tts.py` | Pydantic models for TTS preview requests. |
| `video.py` | Pydantic models for video generation requests/responses (Task 1.7, Sub-task 1.7a). |
| `visuals.py` | Validated library inputs and fixed options for AI visuals. |
| `youtube.py` | Pydantic contracts for YouTube Package generation (Task 1.9, Sub-task 1.9a). |
