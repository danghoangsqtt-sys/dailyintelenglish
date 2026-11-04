"""Phase 96 (D151/D153): the 9:16 pictures of the picture-led Shorts (Word of the day, What is this called?, a picture for
each sentence, Basic vs Advanced).

Each line carries a card in `language_notes.<style>`; a card's `word` names its picture and `picture` describes it. The
pictures are drawn by the local Qwen model when the video is made, or uploaded, and kept in the project's visuals folder.
Without one the closest approved generic picture of the Activity Library stands in; without that the renderer keeps its
plain background. The video is always made.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import random
from pathlib import Path

import aiosqlite
from PIL import Image, ImageOps, UnidentifiedImageError

from backend.ai.image import recipes
from backend.core.exceptions import ValidationError
from backend.library import activity_library_service as activity_library
from backend.library import activity_matcher
from backend.media.roots_pictures import picture_key, roots_folder

logger = logging.getLogger(__name__)
PICTURE_SIZE = (768, 1344)  # 9:16 for the full frame
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
# The look of each kind of Short; one seed per video keeps a video's pictures alike
PROMPTS = {"wordday": recipes.qwen_word_prompt, "whatis": recipes.qwen_object_prompt, "levelup": recipes.qwen_moment_prompt, "picstory": recipes.qwen_firstperson_prompt}
CARD_STYLES = tuple(PROMPTS)


def picture_file(project_id: str, word: str) -> Path:
    return roots_folder(project_id) / f"{picture_key(word)}.png"


async def line_cards(db: aiosqlite.Connection, project_id: str, style: str) -> list[dict]:
    cursor = await db.execute("SELECT language_notes FROM script_lines WHERE project_id = ? ORDER BY line_index", (project_id,))
    return [(json.loads(row[0] or "{}") or {}).get(style) or {} for row in await cursor.fetchall()]


async def _draw(project_id: str, style: str, wanted: dict[str, str]) -> None:
    """Draw word -> description in one batch; a failure leaves the video to its stand-ins."""
    from backend.ai.image.engine import QwenUnavailable, generation_available, get_image_engine

    if not wanted:
        return
    if not generation_available():
        logger.info("short_pictures_skipped project_id=%s missing=%d (no image engine)", project_id, len(wanted))
        return
    seed = random.randint(1, 2**31 - 1)
    items = [{"prompt": PROMPTS[style](description), "seed": seed, "width": PICTURE_SIZE[0], "height": PICTURE_SIZE[1],
              "output_path": str(picture_file(project_id, word))} for word, description in wanted.items()]
    await asyncio.to_thread(roots_folder(project_id).mkdir, parents=True, exist_ok=True)
    try:
        await get_image_engine().qwen_batch("qwen21", items, "short_pictures")
    except QwenUnavailable as exc:
        logger.warning("short_pictures_qwen_unavailable project_id=%s reason=%s", project_id, exc)
    except Exception as exc:  # the video is still made, over a library picture or its plain background
        logger.warning("short_pictures_failed project_id=%s reason=%s", project_id, exc)


async def ensure_pictures(db: aiosqlite.Connection, project_id: str, style: str, cards: list[dict]) -> dict[str, Path]:
    """word -> its picture: its own (drawn when missing), else the closest library picture; a word with neither is left out."""
    wanted: dict[str, str] = {}
    for card in cards:
        if card.get("word") and card.get("picture"):
            wanted.setdefault(card["word"], card["picture"])
    await _draw(project_id, style, {word: text for word, text in wanted.items() if not picture_file(project_id, word).is_file()})
    candidates = [row for row in await activity_library.approved_candidates(db) if not row.get("character_id")]
    found: dict[str, Path] = {}
    for word, description in wanted.items():
        own = picture_file(project_id, word)
        if own.is_file():
            found[word] = own
            continue
        closest = activity_matcher.suggest(candidates, f"{word} {description}", limit=1)
        row = next((row for row in candidates if closest and row["activity"] == closest[0] and Path(row["path"]).is_file()), None)
        if row:
            found[word] = Path(row["path"])
    return found


async def redraw(project_id: str, style: str, word: str, description: str) -> Path:
    """The word's picture drawn again from its edited description; the previous one stays when it cannot be drawn."""
    path = picture_file(project_id, word)
    old = path.with_suffix(".old.png")
    if path.is_file():
        await asyncio.to_thread(path.replace, old)
    await _draw(project_id, style, {word: description})
    if path.is_file():
        await asyncio.to_thread(old.unlink, missing_ok=True)
        return path
    if old.is_file():
        await asyncio.to_thread(old.replace, path)
    raise ValidationError("The picture could not be drawn now (the local image model is not available or out of memory)")


def _fitted_png(content: bytes, path: Path) -> None:
    try:
        with Image.open(io.BytesIO(content)) as image:
            picture = ImageOps.fit(ImageOps.exif_transpose(image).convert("RGB"), PICTURE_SIZE, Image.Resampling.LANCZOS)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError("This file is not a picture that can be read") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_suffix(".new.png")
    picture.save(staged, "PNG")
    staged.replace(path)


async def upload(project_id: str, word: str, content: bytes) -> Path:
    """D153: a picture made elsewhere takes this word's place (a Lite computer, or an outside AI); cropped to 9:16."""
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise ValidationError("The picture must be a file of at most 20 MB")
    path = picture_file(project_id, word)
    await asyncio.to_thread(_fitted_png, content, path)
    return path
