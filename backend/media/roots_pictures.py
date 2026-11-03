"""Phase 87.4: the line-art pictures of a word-roots Short, drawn by the local Qwen model when the video is made.

One picture per word (the hook, split, example and quiz beats of a word share it), from the word's `picture`
description. Pictures are cached in the project's visuals folder and reused on the next render; each new one is also
kept in the Activity Library as an approved generic picture tagged "lineart". Without Qwen the video is still made: the
renderer then draws the word's line icons.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from pathlib import Path

import aiosqlite

from backend.ai.image import recipes
from backend.core.config import settings

logger = logging.getLogger(__name__)
PICTURE_SIZE = (1344, 768)  # the Activity Library keeps 16:9 cutaways only


def picture_key(word: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", word.lower()).strip("-") or "word"


def roots_folder(project_id: str) -> Path:
    return settings.DATA_DIR / "visuals" / project_id / "roots"


def wanted_pictures(cards: list[dict]) -> dict[str, str]:
    """word key -> picture description, first description per word, for the beats that show a word's picture."""
    wanted: dict[str, str] = {}
    for card in cards:
        if card and card.get("word") and card.get("picture"):
            wanted.setdefault(picture_key(card["word"]), card["picture"])
    return wanted


async def _keep_in_library(db: aiosqlite.Connection, path: Path, label: str) -> None:
    from backend.core.exceptions import ConflictError, ValidationError
    from backend.db.transactions import write_transaction
    from backend.library import activity_library_service as activity_library

    content = await asyncio.to_thread(path.read_bytes)
    try:
        async with write_transaction(db):
            row = await activity_library.upload_activity_bytes(db, path.name, content,
                                                               {"activity": label, "context_tags": ["lineart"]})
            await activity_library.set_review(db, row["id"], "approved")
    except (ConflictError, ValidationError) as exc:  # the library copy is a convenience; the video has its picture
        logger.info("roots_picture_library_skipped picture=%s reason=%s", path.name, exc)


async def ensure_pictures(db: aiosqlite.Connection, project_id: str, cards: list[dict]) -> dict[str, Path]:
    """The pictures that exist for these cards after drawing the missing ones (when Qwen is available)."""
    from backend.ai.image.engine import QwenUnavailable, generation_available, get_image_engine

    wanted = wanted_pictures(cards)
    folder = roots_folder(project_id)
    paths = {key: folder / f"{key}.png" for key in wanted}
    missing = [key for key, path in paths.items() if not path.is_file()]
    if missing and generation_available():
        await asyncio.to_thread(folder.mkdir, parents=True, exist_ok=True)
        items = [{"prompt": recipes.qwen_lineart_prompt(wanted[key]), "seed": random.randint(1, 2**31 - 1),
                  "width": PICTURE_SIZE[0], "height": PICTURE_SIZE[1], "output_path": str(paths[key])} for key in missing]
        try:
            await get_image_engine().qwen_batch("qwen21", items, "roots_pictures")
        except QwenUnavailable as exc:
            logger.warning("roots_pictures_qwen_unavailable project_id=%s reason=%s", project_id, exc)
        except Exception as exc:  # a picture is a nice-to-have: the icons stand in, the video is still made
            logger.warning("roots_pictures_failed project_id=%s reason=%s", project_id, exc)
        for key in missing:
            if paths[key].is_file():
                await _keep_in_library(db, paths[key], f"{key.replace('-', ' ')}: {wanted[key][:60]}")
    elif missing:
        logger.info("roots_pictures_skipped project_id=%s missing=%d (no image engine)", project_id, len(missing))
    return {key: path for key, path in paths.items() if path.is_file()}


async def line_cards(db: aiosqlite.Connection, project_id: str) -> list[dict]:
    cursor = await db.execute("SELECT language_notes FROM script_lines WHERE project_id = ? ORDER BY line_index", (project_id,))
    return [(json.loads(row[0] or "{}") or {}).get("roots") or {} for row in await cursor.fetchall()]
