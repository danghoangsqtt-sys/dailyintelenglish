"""Task 36.3/36.4 (D90-D92): the episode thumbnail composed from what the episode already has.

`composed`: a topic illustration as the background (an approved Activity Library picture the storyboard uses, else a scene
plate, else the brand gradient), the two cast characters cut from their approved talking sprites (man left / woman right and
facing each other, exactly as in the video, D81/D82), a big headline, the CEFR badge, the episode number and the channel logo.
`outside_ai`: the owner's own picture made with an outside AI is the whole background; only the text, badges and logo are added.

`composition_inputs` reads the database once (async); `render` only draws (sync, Pillow) from those inputs, which are stored in
the thumbnail's `render.json` so an edit re-renders exactly the same picture.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import aiosqlite
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont, ImageOps

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.paths import get_project_root
from app.models.thumbnail import ThumbnailAspect, ThumbnailSuggestion

PROJECT_ROOT = get_project_root()
FONT_PATH = PROJECT_ROOT / "frontend" / "static" / "fonts" / "Montserrat-Variable.ttf"
LOGO_PATH = PROJECT_ROOT / "video-renderer" / "public" / "brand" / "logo.png"
SIZES: dict[str, tuple[int, int]] = {"16x9": (1280, 720), "9x16": (720, 1280)}
BADGE_YELLOW = "#FFD23F"
BADGE_INK = "#14301F"
# One expression per variant (the first one the character's pack has).
EXPRESSIONS = (("smile__open", "smile__closed"), ("surprised__open", "surprised__closed"), ("laugh__open", "laugh__closed"))
FALLBACK_EXPRESSIONS = ("smile__open", "smile__closed", "calm__open", "calm__closed")
CROP_SHARE = 0.52  # head to chest: big faces read at thumbnail size (the sprite canvas is knee-up)

# Normalized layouts per variant (16x9). text: (x, y, width, height, align); centers: x of the left/right character;
# height: the character's height as a share of the canvas; shade: where the text-side darkening comes from.
LAYOUTS_16X9 = (
    {"text": (0.045, 0.21, 0.50, 0.50, "left"), "centers": (0.64, 0.86), "height": 0.90, "shade": "left"},
    {"text": (0.26, 0.17, 0.48, 0.40, "center"), "centers": (0.14, 0.86), "height": 0.86, "shade": "top"},
    {"text": (0.47, 0.21, 0.49, 0.50, "right"), "centers": (0.15, 0.37), "height": 0.90, "shade": "right"},
)
LAYOUT_9X16 = {"text": (0.07, 0.22, 0.86, 0.20, "center"), "centers": (0.27, 0.73), "height": 0.44, "shade": "middle"}


# ---------------------------------------------------------------- inputs (async, read once)

async def composition_inputs(db: aiosqlite.Connection, project: dict, episode: int | None = None) -> dict[str, Any]:
    """Everything a render needs, as plain JSON: background candidates, the two characters, the CEFR level, the episode."""
    from app.services.video_renderer_remotion import sprite_mirrored, sprite_placement  # lazy: a heavy module
    from app.services.visuals import activity_illustrations, sprite_service, storyboard_service
    from app.services.visuals import activity_library_service as activity_library
    from app.services.visuals import project_visuals_service as project_visuals

    project_id = project["id"]
    backgrounds: list[str] = []

    def add(path: str | Path | None) -> None:
        if path and Path(path).is_file() and str(path) not in backgrounds:
            backgrounds.append(str(path))

    coverage = await activity_illustrations.coverage(db, project_id)
    for item in coverage["items"]:
        if item.get("match"):
            try:
                add(await activity_library.content_path(db, item["match"]["activity_id"]))
            except NotFoundError:
                pass
    beats = await storyboard_service.approved_beats(db, project_id) or []
    scene_ids = [beat["scene_id"] for beat in beats if beat.get("scene_id")]
    cursor = await db.execute("SELECT scene_id FROM project_scenes WHERE project_id = ? ORDER BY position", (project_id,))
    scene_ids += [row[0] for row in await cursor.fetchall()]
    for scene_id in dict.fromkeys(scene_ids):
        cursor = await db.execute("SELECT preview_path FROM scenes WHERE id = ?", (scene_id,))
        row = await cursor.fetchone()
        add(row[0] if row else None)

    cast = await project_visuals.cast_rows(db, project_id)
    cursor = await db.execute(
        "SELECT sp.speaker_index, COUNT(*) FROM script_lines sl JOIN speakers sp ON sp.id = sl.speaker_id "
        "WHERE sl.project_id = ? GROUP BY sp.speaker_index", (project_id,))
    talk = {row[0]: row[1] for row in await cursor.fetchall()}
    ready = []
    for member in sorted(cast, key=lambda row: (-talk.get(row["speaker_index"], 0), row["speaker_index"])):
        sprite_set = sprite_service.load_set(member["character_id"])
        if sprite_service.usable(sprite_set):
            ready.append({**member, "names": sprite_set["names"], "folder": sprite_set["folder"]})
        if len(ready) == 2:
            break
    ready.sort(key=lambda row: row["speaker_index"])
    slots = sprite_placement([(row["speaker_index"], row.get("gender") or "male") for row in ready])
    characters = [{
        "character_id": row["character_id"], "name": row.get("name") or "", "gender": row.get("gender") or "",
        "folder": row["folder"], "names": row["names"],
        "slot": slots[row["speaker_index"]],
        "mirror": sprite_mirrored(slots[row["speaker_index"]], row.get("sprite_facing") or "", row.get("gender") or "male"),
    } for row in ready]
    if episode is None:  # Task 36.5: the episode number of a project in the channel plan
        from app.services import channel_service

        context = await channel_service.episode_context(db, project_id)
        episode = context["number"] if context else None
    outside = settings.DATA_DIR / "thumbnails" / project_id / "outside_source.png"
    return {"backgrounds": backgrounds, "characters": characters, "cefr": (project.get("cefr_level") or "").upper(),
            "episode": episode, "outside_image": str(outside) if outside.is_file() else None}


# ---------------------------------------------------------------- drawing (sync)

def _font(size: int, weight: str = "Black") -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(FONT_PATH), size)
    font.set_variation_by_name(weight)
    return font


def _luminance(color: str) -> float:
    red, green, blue = ImageColor.getrgb(color)[:3]
    return (0.299 * red + 0.587 * green + 0.114 * blue) / 255


def _gradient(size: tuple[int, int], first: str, second: str) -> Image.Image:
    """The brand fallback background: a diagonal blend of the palette's two main colours."""
    width, height = size
    ramp = Image.linear_gradient("L").rotate(-35, expand=True).resize(size)
    return Image.composite(Image.new("RGB", size, second), Image.new("RGB", size, first), ramp).resize((width, height))


def _background(path: str | None, size: tuple[int, int], suggestion: ThumbnailSuggestion) -> Image.Image:
    if path and Path(path).is_file():
        with Image.open(path) as opened:
            return ImageOps.fit(opened.convert("RGB"), size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.4))
    return _gradient(size, suggestion.palette.primary, suggestion.palette.secondary)


def _shade(image: Image.Image, where: str) -> Image.Image:
    """Darken the text side so the headline reads at thumbnail size."""
    width, height = image.size
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    if where in ("left", "right"):
        span = int(width * 0.66)
        for offset in range(span):
            alpha = round(200 * (1 - offset / span) ** 1.3)
            x = offset if where == "left" else width - 1 - offset
            draw.line((x, 0, x, height), fill=alpha)
    elif where == "top":
        span = int(height * 0.68)
        for offset in range(span):
            draw.line((0, offset, width, offset), fill=round(190 * (1 - offset / span) ** 1.2))
    else:  # middle band (9x16)
        top, bottom = int(height * 0.22), int(height * 0.60)
        for y in range(top, bottom):
            middle = (top + bottom) / 2
            draw.line((0, y, width, y), fill=round(170 * (1 - abs(y - middle) / ((bottom - top) / 2)) ** 0.6))
    return Image.composite(Image.new("RGB", image.size, (8, 14, 10)), image, mask)


def _character(character: dict, variant_index: int, target_height: int) -> Image.Image | None:
    names = set(character["names"])
    wanted = next((name for name in EXPRESSIONS[variant_index % len(EXPRESSIONS)] if name in names), None) \
        or next((name for name in FALLBACK_EXPRESSIONS if name in names), None)
    path = Path(character["folder"]) / f"{wanted}.png" if wanted else None
    if path is None or not path.is_file():
        return None
    with Image.open(path) as opened:
        sprite = opened.convert("RGBA")
    sprite = sprite.crop((0, 0, sprite.width, int(sprite.height * CROP_SHARE)))
    box = sprite.getchannel("A").getbbox()
    if box is None:
        return None
    sprite = sprite.crop((box[0], box[1], box[2], sprite.height))
    if character.get("mirror"):
        sprite = ImageOps.mirror(sprite)
    scale = target_height / sprite.height
    sprite = sprite.resize((max(1, round(sprite.width * scale)), target_height), Image.Resampling.LANCZOS)
    # a white sticker outline, the usual YouTube look, so the figure stands out from any background
    alpha = sprite.getchannel("A")
    outline = alpha.filter(ImageFilter.MaxFilter(9))
    sticker = Image.new("RGBA", sprite.size, (255, 255, 255, 0))
    sticker.putalpha(outline)
    sticker.alpha_composite(sprite)
    return sticker


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> str:
    words = text.split()
    lines = [words[0]] if words else []
    for word in words[1:]:
        candidate = f"{lines[-1]} {word}"
        if draw.textbbox((0, 0), candidate, font=font, stroke_width=4)[2] <= width:
            lines[-1] = candidate
        else:
            lines.append(word)
    return "\n".join(lines)


def _headline(draw: ImageDraw.ImageDraw, text: str, box: tuple[int, int, int, int], align: str, fill: str,
              max_size: int, min_size: int) -> int:
    """The biggest size at which the headline fits the box; returns the y just below it."""
    x, y, width, height = box
    for size in range(max_size, min_size - 1, -2):
        font = _font(size)
        stroke = max(3, size // 14)
        wrapped = _wrap(draw, text, font, width)
        spacing = round(size * 0.08)
        left, top, right, bottom = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing, align=align,
                                                           stroke_width=stroke)
        if right - left <= width and bottom - top <= height:
            draw_x = x if align == "left" else x + width - (right - left) if align == "right" else x + (width - (right - left)) / 2
            draw.multiline_text((draw_x - left, y - top), wrapped, font=font, fill=fill, spacing=spacing, align=align,
                                stroke_width=stroke, stroke_fill="#0B1A10")
            return y + (bottom - top)
    font = _font(min_size)
    draw.multiline_text((x, y), _wrap(draw, text, font, width), font=font, fill=fill, stroke_width=3, stroke_fill="#0B1A10")
    return y + height


def _pill(draw: ImageDraw.ImageDraw, text: str, position: tuple[int, int], size: int, fill: str, ink: str,
          align: str = "left") -> tuple[int, int]:
    font = _font(size, "ExtraBold")
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    pad_x, pad_y = round(size * 0.55), round(size * 0.32)
    width, height = right - left + 2 * pad_x, bottom - top + 2 * pad_y
    x, y = position
    if align == "right":
        x -= width
    elif align == "center":
        x -= width // 2
    draw.rounded_rectangle((x, y, x + width, y + height), radius=height // 2, fill=fill)
    draw.text((x + pad_x - left, y + pad_y - top), text, font=font, fill=ink)
    return width, height


def _logo(image: Image.Image, height: int, margin: int) -> None:
    if not LOGO_PATH.is_file():
        return
    with Image.open(LOGO_PATH) as opened:
        logo = opened.convert("RGBA")
    logo = logo.resize((max(1, round(logo.width * height / logo.height)), height), Image.Resampling.LANCZOS)
    image.alpha_composite(logo, (image.width - logo.width - margin, margin))


def render(inputs: dict, suggestion: ThumbnailSuggestion, aspect: ThumbnailAspect, variant_index: int,
           template_id: str) -> Image.Image:
    """One thumbnail picture (RGB) at one aspect ratio."""
    size = SIZES[aspect]
    width, height = size
    layout = LAYOUT_9X16 if aspect == "9x16" else LAYOUTS_16X9[variant_index % len(LAYOUTS_16X9)]
    if template_id == "outside_ai":
        source = inputs.get("outside_image")
        layout = LAYOUT_9X16 if aspect == "9x16" else LAYOUTS_16X9[0]
    else:
        candidates = inputs.get("backgrounds") or []
        source = candidates[variant_index % len(candidates)] if candidates else None
    image = _shade(_background(source, size, suggestion), layout["shade"]).convert("RGBA")

    if template_id != "outside_ai":
        for character in inputs.get("characters") or []:
            figure = _character(character, variant_index, round(height * layout["height"]))
            if figure is None:
                continue
            center = layout["centers"][character["slot"] if len(inputs["characters"]) > 1 else 1]
            image.alpha_composite(figure, (round(width * center - figure.width / 2), height - figure.height))

    draw = ImageDraw.Draw(image)
    margin = round(min(size) * 0.04)
    x, y, box_width, box_height, align = layout["text"]
    text_box = (round(x * width), round(y * height), round(box_width * width), round(box_height * height))
    fill = suggestion.palette.text if _luminance(suggestion.palette.text) >= 0.6 else "#FFFFFF"
    bottom = _headline(draw, suggestion.headline.upper(), text_box, align, fill,
                       max_size=round(height * (0.075 if aspect == "9x16" else 0.16)), min_size=28)
    if suggestion.supporting_text:
        accent = suggestion.palette.accent
        anchor_x = text_box[0] if align == "left" else text_box[0] + text_box[2] if align == "right" else \
            text_box[0] + text_box[2] // 2
        _pill(draw, suggestion.supporting_text, (anchor_x, bottom + round(height * 0.03)),
              round(min(size) * 0.05), accent, "#FFFFFF" if _luminance(accent) < 0.55 else BADGE_INK, align)

    badge_size = round(min(size) * 0.05)
    badge_x = margin
    if inputs.get("cefr"):
        badge_width, _ = _pill(draw, f"{inputs['cefr']} ENGLISH", (badge_x, margin), badge_size, BADGE_YELLOW, BADGE_INK)
        badge_x += badge_width + round(margin * 0.5)
    if inputs.get("episode"):
        _pill(draw, f"EP. {inputs['episode']}", (badge_x, margin), badge_size, "#FFFFFF", BADGE_INK)
    _logo(image, round(min(size) * 0.14), margin)
    return image.convert("RGB")
