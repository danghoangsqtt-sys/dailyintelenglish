# Changelog — Daily Intel English Studio

All notable changes to this project will be documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [SemVer](https://semver.org/)

---

## [Unreleased]

### Added
- Initial project crystallization from brainstorm session 2026-09-10
- Architecture design: FastAPI + OmniVoice + Gemini + ffmpeg stack
- 7-step production pipeline design
- SQLite database schema
- FastAPI skeleton (CORS, lifespan, routers), SQLite init via aiosqlite, dark-mode dashboard UI
- `ProjectService` full CRUD (create/get/list/update/delete) with validated Pydantic models (`ScriptConfig`, `SpeakerConfig`, `ProjectUpdate`) and `POST/GET/PUT/DELETE /api/projects[/{id}]`
- Forward-only project state machine: `draft → script_generated → audio_generated → video_generated → complete` — no skipping or reverting
- Atomic `num_speakers`/`speakers` updates — the two can only change together, keeping the `speakers` table and the `num_speakers` column consistent
- `config_json` is recomputed from the merged project state on every update, not only at creation
- Global `RequestValidationError` handler so Pydantic 422s use the same `{success, data, error, meta}` envelope as every other response
- All settings namespaced under a `DIE_` env-var prefix, so generic system env vars (e.g. bare `DEBUG`) can no longer crash startup or leak into config
- `scripts/check_dependencies.py` now checks the configured ffmpeg path and Gemini API key the same way the app itself resolves them (`settings.FFMPEG_PATH`, `settings.GEMINI_API_KEY`), plus a new OmniVoice model directory check
- `ruff` added as the lint gate; 30 automated tests (`pytest`) covering project CRUD, validation, and dependency-check logic

---

## [0.1.0] — 2026-09-10

### Added
- Project initialized
- `.viepilot/` architecture artifacts created
- Brainstorm session completed

[Unreleased]: https://github.com/danghoangsqtt-sys/dailyintelenglish/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/danghoangsqtt-sys/dailyintelenglish/releases/tag/v0.1.0
