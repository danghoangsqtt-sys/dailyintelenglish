"""FastAPI application entrypoint for Daily Intel English Studio."""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import ai_jobs, audio, learning, music, projects, settings as settings_api, thumbnail, tts, video, youtube
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.paths import get_project_root
from app.core.responses import ok
from app.core.system_checks import check_ffmpeg, get_gpu_info
from app.db.database import Database, close_db, init_db
from app.services import learning_pipeline, script_pipeline, settings_service
from app.services.ai.router import AIRouter, CircuitBreaker, build_ai_router_from_settings
from app.services.ai_worker import AIWorker

PROJECT_ROOT = get_project_root()
FRONTEND_DIR = PROJECT_ROOT / "frontend"

app_state: dict = {"ffmpeg_ok": False, "gpu_info": None}
ai_worker = AIWorker(db_getter=lambda: Database.instance().connection)

# Phase 18/Task 18.8: one circuit breaker PER cloud provider name, for the app's
# whole lifetime, threaded through every freshly-built per-job router below -- so
# breaker state survives across jobs even though the router itself is rebuilt per
# job dispatch (to pick up a Settings-page change without a restart; see
# _build_ai_router's docstring). Starts empty and grows on demand (a breaker is
# created the first time a given provider name is actually dispatched to,
# app/services/ai/router.py's `_chain_entry`) -- never hardcodes which provider
# names exist, so adding/removing/reordering providers in Settings needs no
# change here.
_ai_circuits: dict[str, CircuitBreaker] = {}


def _build_ai_router() -> AIRouter:
    """One fresh `AIRouter` per call, reading `settings.*` live (Phase 18),
    sharing this module's one app-lifetime `_ai_circuits` dict.

    Called once per job dispatch (not once at startup, and not once per
    `generate()` call within a job) by the two handler wrappers below --
    `AIWorker`'s registered handlers used to close over a single router built
    once in `lifespan`, so a Settings-page change (Task 18.3) would never
    reach a running job's actual provider calls (both `OllamaProvider` and the
    old `GeminiProvider` froze their config at construction). Rebuilding here
    fixes that; `_ai_circuits` keeps each breaker itself from also resetting on
    every rebuild.
    """
    return build_ai_router_from_settings(circuits=_ai_circuits)


async def _script_job_handler(job: dict, worker: AIWorker) -> None:
    await script_pipeline.make_handler(_build_ai_router())(job, worker)


async def _learning_job_handler(job: dict, worker: AIWorker) -> None:
    await learning_pipeline.make_handler(_build_ai_router())(job, worker)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database and verify external tooling on startup.

    OmniVoice's model is loaded lazily on first TTS request (Task 1.6),
    not here — startup should stay fast.
    """
    for subdir in (
        "audio",
        "music_library",
        "projects",
        "thumbnails",
        "tts_cache",
        "video",
    ):
        (settings.DATA_DIR / subdir).mkdir(parents=True, exist_ok=True)

    await init_db()
    await settings_service.load_cloud_settings_from_db(Database.instance().connection)
    await settings_service.load_provider_chain_from_db(Database.instance().connection)
    await settings_service.load_ai_mode_from_db(Database.instance().connection)
    app_state["ffmpeg_ok"] = await check_ffmpeg()
    app_state["gpu_info"] = await get_gpu_info()

    ai_worker.register_handler("script", _script_job_handler)
    ai_worker.register_handler("learning", _learning_job_handler)
    await ai_worker.start()

    yield

    await ai_worker.stop()
    await close_db()


app = FastAPI(title="Daily Intel English Studio", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://localhost(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Convert typed service exceptions into the standard error envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "data": None, "error": exc.message, "meta": {}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convert Pydantic request-validation failures into the standard error envelope."""
    details = [
        f"{'.'.join(str(part) for part in error['loc'] if part != 'body')}: {error['msg']}"
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"success": False, "data": None, "error": "; ".join(details), "meta": {}},
    )


app.include_router(projects.router)
app.include_router(learning.router)
app.include_router(tts.router)
app.include_router(tts.preview_router)
app.include_router(audio.router)
app.include_router(video.router)
app.include_router(video.templates_router)
app.include_router(music.router)
app.include_router(thumbnail.router)
app.include_router(youtube.router)
app.include_router(settings_api.router)
app.include_router(ai_jobs.router)
app.include_router(ai_jobs.health_router)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")


@app.get("/")
async def root() -> FileResponse:
    """Serve the dashboard as the app's landing page."""
    return FileResponse(FRONTEND_DIR / "pages" / "dashboard.html")


@app.get("/step1")
async def step1_config() -> FileResponse:
    """Serve the Step 1 — Script Config wizard."""
    return FileResponse(FRONTEND_DIR / "pages" / "step1_config.html")


@app.get("/step2")
async def step2_script() -> FileResponse:
    """Serve the Step 2 — AI Script Generation page."""
    return FileResponse(FRONTEND_DIR / "pages" / "step2_script.html")


@app.get("/step3")
async def step3_learning() -> FileResponse:
    """Serve the Step 3 — Learning Content page."""
    return FileResponse(FRONTEND_DIR / "pages" / "step3_learning.html")


@app.get("/step4")
async def step4_tts() -> FileResponse:
    """Serve the Step 4 — TTS Audio Studio."""
    return FileResponse(FRONTEND_DIR / "pages" / "step4_tts.html")


@app.get("/step5")
async def step5_video() -> FileResponse:
    """Serve the Step 5 — Video Studio page."""
    return FileResponse(FRONTEND_DIR / "pages" / "step5_video.html")


@app.get("/step6")
async def step6_thumbnail() -> FileResponse:
    """Serve the Step 6 — interactive Thumbnail Generator page."""
    return FileResponse(FRONTEND_DIR / "pages" / "step6_thumbnail.html")


@app.get("/step7")
async def step7_youtube() -> FileResponse:
    """Serve the Step 7 — YouTube Package page."""
    return FileResponse(FRONTEND_DIR / "pages" / "step7_youtube.html")


@app.get("/music")
async def music_library() -> FileResponse:
    """Serve the background Music Library management page."""
    return FileResponse(FRONTEND_DIR / "pages" / "music_library.html")


@app.get("/settings")
async def settings_page() -> FileResponse:
    """Serve the app-level Settings page (Task 12.1 — Gemini API key)."""
    return FileResponse(FRONTEND_DIR / "pages" / "settings.html")



@app.get("/health")
async def health() -> dict:
    """Report readiness of the database, ffmpeg, and GPU for the check_dependencies script and UI."""
    started_at = time.perf_counter()
    db_ok = True
    try:
        await Database.instance().connection.execute("SELECT 1")
    except Exception:
        db_ok = False
    return ok(
        {
            "status": "ok",
            "database": db_ok,
            "ffmpeg": app_state["ffmpeg_ok"],
            "gpu": app_state["gpu_info"],
        },
        started_at=started_at,
    )
