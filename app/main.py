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
from app.core.constants import GEMINI_MODEL
from app.core.exceptions import AppError
from app.core.paths import get_project_root
from app.core.responses import ok
from app.core.system_checks import check_ffmpeg, get_gpu_info
from app.db.database import Database, close_db, init_db
from app.services import learning_pipeline, script_pipeline, settings_service
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.ollama_provider import OllamaProvider
from app.services.ai.router import AIRouter
from app.services.ai.contracts import AIMode
from app.services.ai_worker import AIWorker

PROJECT_ROOT = get_project_root()
FRONTEND_DIR = PROJECT_ROOT / "frontend"

app_state: dict = {"ffmpeg_ok": False, "gpu_info": None}
ai_worker = AIWorker(db_getter=lambda: Database.instance().connection)


def _build_ai_router() -> AIRouter:
    """One shared AIRouter for the app's durable job worker (Phase 13, Task 13.6).

    Reads `settings.AI_MODE` live at call time (called once at startup, after
    `settings_service.load_ai_mode_from_db()` has applied any DB override) --
    mirrors `script_service._build_ai_router()`'s construction exactly.
    """
    local = OllamaProvider(
        base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL, num_ctx=settings.OLLAMA_NUM_CTX
    )
    gemini = GeminiProvider(api_key=settings.GEMINI_API_KEY, model=GEMINI_MODEL)
    return AIRouter(local=local, gemini=gemini, mode=AIMode(settings.AI_MODE))


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
    await settings_service.load_gemini_api_key_from_db(Database.instance().connection)
    await settings_service.load_ai_mode_from_db(Database.instance().connection)
    app_state["ffmpeg_ok"] = await check_ffmpeg()
    app_state["gpu_info"] = await get_gpu_info()

    ai_router = _build_ai_router()
    ai_worker.register_handler("script", script_pipeline.make_handler(ai_router))
    ai_worker.register_handler("learning", learning_pipeline.make_handler(ai_router))
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
