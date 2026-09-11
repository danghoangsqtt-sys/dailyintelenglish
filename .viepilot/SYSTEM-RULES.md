# SYSTEM-RULES.md — Daily Intel English Studio

## Architecture Rules

### AR-01: Separation of Concerns
- Backend services MUST NOT contain any HTML/CSS/JS
- Frontend MUST NOT contain any business logic — only UI state and API calls
- Each service class handles ONE domain (script, tts, audio, video, thumbnail, youtube, project)

### AR-02: Async First
- All FastAPI routes MUST be `async def`
- All I/O operations (file read/write, API calls, subprocess) MUST use `await` or run in threadpool
- Use `asyncio.create_task()` for background jobs (TTS generation)

### AR-03: Service Layer Pattern
```python
# CORRECT: Route delegates to service
@router.post("/projects/{id}/script/generate")
async def generate_script(id: str, config: ScriptConfig):
    return await script_service.generate(id, config)

# WRONG: Business logic in route
@router.post("/projects/{id}/script/generate")
async def generate_script(id: str, config: ScriptConfig):
    prompt = f"Generate a {config.genre} script..."  # ❌ Business logic in route
    response = await gemini.generate(prompt)
    return response
```

### AR-04: Error Propagation
- Services raise typed exceptions (`ScriptGenerationError`, `TTSError`, `AudioMixError`)
- Global exception handler in FastAPI converts to JSON `{"success": false, "error": "..."}`
- Never return `None` from service — raise exception instead

### AR-05: No Blocking Calls in Event Loop
- TTS generation, ffmpeg, Pillow → run in `asyncio.get_event_loop().run_in_executor()`
- Never call `subprocess.run(block=True)` from async context

### AR-06: PM-GEMINI Delivery Contract (No Self-Approval)
- Product Manager (PM) is the sole authority on scope, prioritization, acceptance, marking tasks done, commits, and releases.
- GEMINI / AI Developer is an implementation-only agent with strictly NO self-approval privileges.
- Before coding, implementer MUST produce: plan, bounded `allowed_files` list, risk evaluation, and tests to run, then WAIT for PM confirmation.
- Only modify files within `allowed_files`; no out-of-scope refactoring or unassigned bugfixes.
- Never use `git add .`, never push directly without PM sign-off.
- AI output requires two-layer validation: JSON Schema validation at API layer and Pydantic semantic validation.
- UI async operations must enforce double-submit lock, serialization, trailing autosave, and dirty navigation guards.

---

## Coding Rules

### CR-01: Python Style
- PEP 8 compliant (use `ruff` or `black` for formatting)
- Type hints MANDATORY for all function signatures
- Docstrings MANDATORY for all public service methods

```python
# CORRECT
async def generate_script(
    project_id: str,
    config: ScriptConfig,
    db: Database,
) -> ScriptResult:
    """
    Generate podcast script via Gemini API.
    
    Args:
        project_id: UUID of the project
        config: Script generation configuration
        db: Database connection
        
    Returns:
        ScriptResult with lines, language_notes, metadata
        
    Raises:
        ScriptGenerationError: If Gemini API fails or content violates rules
    """
    ...

# WRONG
async def gen(pid, cfg, d):  # ❌ No type hints, no docstring, bad names
    ...
```

### CR-02: Configuration Management
- ALL magic numbers → named constants in `app/core/constants.py`
- ALL API keys → environment variables via `python-dotenv`
- NEVER hardcode paths — use `pathlib.Path` and `settings.DATA_DIR`

```python
# CORRECT
from app.core.constants import DEFAULT_SILENCE_BETWEEN_SPEAKERS_MS
gap = DEFAULT_SILENCE_BETWEEN_SPEAKERS_MS  # 500

# WRONG
gap = 500  # ❌ Magic number
```

### CR-03: Prompt Template Management
- ALL Gemini prompts → files in `prompts/` directory (NOT hardcoded strings)
- Prompts use Jinja2 template syntax for variable injection
- Prompt files named: `{domain}_{variant}.txt` (e.g., `script_debate_b2.txt`)

### CR-04: File Path Safety
```python
# CORRECT — always use pathlib
from pathlib import Path
audio_dir = Path(settings.DATA_DIR) / "audio" / project_id
audio_dir.mkdir(parents=True, exist_ok=True)

# WRONG
audio_dir = f"data/audio/{project_id}"  # ❌ String paths
```

### CR-05: Frontend API Calls
- ALL API calls → centralized in `frontend/static/js/api.js`
- Use `async/await` with `fetch()`
- Show loading state during ALL async operations
- Display user-friendly error messages (not raw API errors)

---

## Comment Standards

### Good Comments (explain WHY, not WHAT)
```python
# OmniVoice has 12GB VRAM limit on RTX 3060 — semaphore prevents concurrent overflow
tts_semaphore = asyncio.Semaphore(2)

# CEFR B1 allows simple present perfect but NOT past perfect
# Reference: Cambridge CEFR Can-Do statements, B1 grammar inventory
grammar_rules = load_b1_grammar_rules()
```

### Bad Comments (state the obvious)
```python
# This is a for loop  ❌
for line in script_lines:
    pass
    
# Generate the audio  ❌
await generate_audio()
```

---

## Versioning

- **SemVer**: `MAJOR.MINOR.PATCH`
  - MAJOR: Breaking changes to project data format or API
  - MINOR: New features (new genre, new TTS engine, new language)
  - PATCH: Bug fixes, prompt improvements

---

## Git Conventions (Conventional Commits)

```
feat(script): add B2 collocation validation in prompt
fix(tts): handle OmniVoice VRAM overflow gracefully  
fix(audio): correct silence gap between speakers
feat(video): integrate LivePortrait lips-sync
perf(tts): cache OmniVoice model between requests
docs(api): update TTS endpoint documentation
refactor(audio): extract AudioMixer to separate class
test(script): add CEFR level vocabulary tests
```

### Branch Strategy
- `main` — stable, tested code
- `feature/{name}` — new features
- `fix/{name}` — bug fixes

---

## Quality Gates

### Before Each Commit & Handoff
- [ ] `ruff check .` — 0 linting errors
- [ ] `python -m pytest tests/ -x` — all tests pass 100%
- [ ] `node --check` — clean validation on all modified frontend JS files
- [ ] UI tasks: Browser E2E verification (happy path, error path, reload, and race conditions)
- [ ] Explicit staging only: `git add <file>` (NEVER `git add .`)
- [ ] No hardcoded API keys or secrets
- [ ] All new service methods have docstrings

### Before Phase Completion
- [ ] All Phase tasks marked complete in TRACKER.md
- [ ] End-to-end test: create project → generate script → audio → video → YouTube package
- [ ] Manual review of 3 sample scripts at different CEFR levels

---

## Stack-Specific Rules

### FastAPI Rules
- Use `APIRouter` for each domain (not one giant `main.py`)
- Use `Depends()` for dependency injection (DB, settings)
- Enable CORS for `localhost:*` only
- Use Pydantic models for ALL request/response validation

### Gemini API Rules
- Implement exponential backoff: 1s → 2s → 4s → 8s (max 4 retries)
- Log every API call with: model, tokens_used, latency_ms, prompt_hash
- NEVER log full prompt content in production (may contain sensitive topic)
- Use `response_schema` (JSON mode) for structured outputs

### OmniVoice Rules
- Load model ONCE at startup (not per-request) — 15-30s startup time
- Use semaphore(2) for concurrent request limit
- Catch `torch.cuda.OutOfMemoryError` → fallback to Edge TTS automatically
- Clear GPU cache after each batch: `torch.cuda.empty_cache()`

### SQLite Rules
- Use `aiosqlite` for async access (NOT sqlite3 blocking)
- Run migrations with simple SQL files in `app/db/migrations/`
- Always close connections in `finally` blocks

### ffmpeg Rules
- Always specify `-loglevel error` to suppress verbose output
- Use `-y` flag to overwrite without prompt
- Test ffmpeg availability at startup; fail fast with clear error message
