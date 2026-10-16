"""Solo plan review and immutable project illustration routes."""
import aiosqlite
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from backend.core.constants import EXPLAINER_IMAGE_MAX_BYTES
from backend.core.exceptions import ValidationError
from backend.core.responses import ok
from backend.db.database import get_db
from backend.library import explainer_service
from backend.schemas.ai_job import AIJobOut
from backend.schemas.explainer import ExplainerApproval, ExplainerPlanPatch, ExplainerProposalRequest

router = APIRouter(prefix="/api/projects/{project_id}/explainer-plan", tags=["explainer"])
asset_router = APIRouter(prefix="/api/projects/{project_id}/explainer/assets", tags=["explainer"])


@router.get("")
async def get_plan(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Read a draft or approved version together with live source issues."""
    return ok(await explainer_service.get_plan(db, project_id))


@router.get("/history")
async def plan_history(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Read immutable project revisions in order."""
    return ok(await explainer_service.history(db, project_id))


@router.get("/preview")
async def preview_plan(project_id: str, aspect: str = "16:9", db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Resolve verified draft preview props without approving factual content."""
    from backend.library.explainer_media import preview
    return ok(await preview(db, project_id, aspect))


@router.patch("")
async def save_plan(project_id: str, body: ExplainerPlanPatch, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Save an owner edit against both the expected revision and current source."""
    return ok(await explainer_service.save_plan(db, project_id, body))


@router.post("/propose")
async def propose_plan(project_id: str, body: ExplainerProposalRequest, db: aiosqlite.Connection = Depends(get_db)) -> JSONResponse:
    """Create or return the existing durable proposal job."""
    job, created = await explainer_service.enqueue_proposal(db, project_id, body)
    return JSONResponse(status_code=202 if created else 200, content=ok(AIJobOut.model_validate(job).model_dump()))


@router.post("/approve")
async def approve_plan(project_id: str, body: ExplainerApproval, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Validate source/assets/audio/layouts before pinning the reviewed revision."""
    return ok(await explainer_service.approve_plan(db, project_id, body))


@router.post("/layout")
async def arrange_plan(project_id: str, body: ExplainerApproval, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Suggest collision-checked layouts without implicitly saving or approving a plan."""
    return ok(await explainer_service.arrange_plan(db, project_id, body))


@asset_router.get("")
async def list_assets(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """List the project's available illustration versions."""
    return ok(await explainer_service.list_illustrations(db, project_id))


@asset_router.post("")
async def upload_asset(project_id: str, file: UploadFile = File(...), db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Read a bounded multipart image; service owns decoding and guarded publication."""
    content = await file.read(EXPLAINER_IMAGE_MAX_BYTES + 1)
    if len(content) > EXPLAINER_IMAGE_MAX_BYTES:
        raise ValidationError("Choose an illustration up to 20 MB")
    return ok(await explainer_service.import_illustration(db, project_id, content, file.filename or "illustration.png"))


@asset_router.get("/{asset_id}/{version}/content")
async def asset_content(project_id: str, asset_id: str, version: int, db: aiosqlite.Connection = Depends(get_db)) -> FileResponse:
    """Serve only a scoped, verified immutable PNG version."""
    path = await explainer_service.illustration_content(db, project_id, asset_id, version)
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "private, no-cache"})
