"""Phase 90 (D128–D130): edit a word-roots or grammar Short on its video -- the beats, their cards and the preview."""

import aiosqlite
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.content import beats_service, export_service
from backend.core.responses import ok
from backend.db.database import get_db
from backend.db.transactions import read_transaction, write_transaction

router = APIRouter(prefix="/api/projects/{project_id}/beats", tags=["beats"])


class CardEdit(BaseModel):
    line_id: str = Field(min_length=1)
    card: dict


class CardsUpdate(BaseModel):
    lines: list[CardEdit] = Field(min_length=1, max_length=80)


class TextUpdate(BaseModel):
    text: str = Field(min_length=1, max_length=600)


class PictureRequest(BaseModel):
    word: str = Field(min_length=1, max_length=40)
    picture: str = Field(min_length=3, max_length=300)


@router.get("")
async def get_beats(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        return ok(await beats_service.load(db, project_id))


@router.get("/lines")
async def get_lines(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Phase 91.3: the spoken lines of any kind of video, with whether each voice still matches."""
    async with read_transaction():
        return ok(await beats_service.spoken_lines(db, project_id))


@router.put("")
async def save_cards(project_id: str, payload: CardsUpdate, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        saved = await beats_service.save_cards(db, project_id, [edit.model_dump() for edit in payload.lines])
    await export_service.sync_quietly(db, project_id)
    return ok({"saved": saved})


@router.put("/{line_id}/text")
async def save_text(project_id: str, line_id: str, payload: TextUpdate, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        line = await beats_service.save_text(db, project_id, line_id, payload.text)
    await export_service.sync_quietly(db, project_id)
    return ok(line)


@router.post("/picture")
async def redraw_picture(project_id: str, payload: PictureRequest, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Draw one word's line-art picture again from its (edited) description."""
    from backend.content import project_service
    from backend.media import roots_pictures, short_pictures

    style = (await project_service.get_project(db, project_id)).get("explainer_style")
    path = (await short_pictures.redraw(project_id, style, payload.word, payload.picture) if style in short_pictures.CARD_STYLES
            else await roots_pictures.redraw(db, project_id, payload.word, payload.picture))
    return ok({"word": payload.word, "url": beats_service.picture_url(project_id, path.name) if path else None})


@router.post("/picture/upload")
async def upload_picture(project_id: str, word: str = Form(min_length=1, max_length=40), file: UploadFile = File(...),
                         db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Phase 96 (D153): a picture made elsewhere takes this word's place."""
    from backend.content import project_service
    from backend.core.exceptions import ValidationError
    from backend.media import short_pictures

    style = (await project_service.get_project(db, project_id)).get("explainer_style")
    if style not in short_pictures.CARD_STYLES:
        raise ValidationError("This kind of video has no pictures to upload")
    path = await short_pictures.upload(project_id, word, await file.read(), style=style)
    return ok({"word": word, "url": beats_service.picture_url(project_id, path.name)})


@router.get("/pictures/{name}")
async def get_picture(project_id: str, name: str) -> FileResponse:
    return FileResponse(beats_service.picture_path(project_id, name), media_type="image/png",
                        headers={"Cache-Control": "no-store"})
