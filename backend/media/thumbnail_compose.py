"""Task 36.3/36.4 (D90-D92): the episode thumbnail composed from what the episode already has.

`composed`: a topic illustration as the background (the topic picture drawn on the local GPU, Phase 39, else an approved
Activity Library picture the storyboard uses, else a scene plate, else the brand gradient), the two cast characters cut from their approved talking sprites (man left / woman right and
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

from backend.core.config import settings
from backend.core.exceptions import NotFoundError
from backend.core.paths import get_project_root
from backend.schemas.thumbnail import ThumbnailAspect, ThumbnailSuggestion

PROJECT_ROOT = get_project_root()
FONT_PATH = PROJECT_ROOT / "frontend" / "static" / "fonts" / "Montserrat-Variable.ttf"
LOGO_PATH = PROJECT_ROOT / "renderer" / "public" / "brand" / "logo.png"
SIZES: dict[str, tuple[int, int]] = {"16x9": (1280, 720), "9x16": (720, 1280)}
BADGE_YELLOW = "#FFD23F"
BADGE_INK = "#14301F"
# One expression per variant (the first one the character's pack has).
EXPRESSIONS = (("smile__open", "smile__closed"), ("surprised__open", "surprised__closed"), ("laugh__open", "laugh__closed"))
FALLBACK_EXPRESSIONS = ("smile__open", "smile__closed", "calm__open", "calm__closed")
CROP_SHARE = 0.52  # head to chest: big faces read at thumbnail size (the sprite canvas is knee-up)

# Normalized layouts per variant. text: (x, y, width, height, align); group: where the characters stand -- "right" /
# "left" of the headline (rule of thirds), "split" on both sides of a centred headline, "bottom" under it (9:16);
# height: the tallest a character may be, as a share of the canvas; shade: where the text-side darkening comes from.
#
# Walkthrough 2026-10-14, owner review + YouTube thumbnail guides (faces recognisable at 150 px wide, ~40-50 % of the
# frame; keep faces and text out of the bottom-right duration badge; ~60 px margins): the characters are big, their
# bodies may overlap a little and bleed off the outer edge, but their heads never touch (see `arrange_figures`).
LAYOUTS_16X9 = (
    {"text": (0.045, 0.21, 0.45, 0.50, "left"), "group": "right", "height": 0.86, "shade": "left"},
    {"text": (0.27, 0.17, 0.46, 0.40, "center"), "group": "split", "height": 0.86, "shade": "top"},
    {"text": (0.51, 0.21, 0.45, 0.50, "right"), "group": "left", "height": 0.86, "shade": "right"},
)
LAYOUT_9X16 = {"text": (0.07, 0.15, 0.86, 0.20, "center"), "group": "bottom", "height": 0.50, "shade": "middle"}
LOGO_SHARE = 0.14  # the channel logo's height, as a share of the short side
MARGIN_SHARE = 0.04
SAFE_MARGIN = 60 / 1280  # heads stay this far (of the width) from the frame's edges
HEAD_SHARE = 0.40  # the top share of a head-to-chest figure that holds the head (hair, face, neck)
HEAD_GAP = 0.025  # at least this much (of the width) between the two heads
MAX_BLEED = 0.35  # a body may run off the outer edge by at most this share of its width


# ---------------------------------------------------------------- inputs (async, read once)

async def composition_inputs(db: aiosqlite.Connection, project: dict, episode: int | None = None) -> dict[str, Any]:
    """Everything a render needs, as plain JSON: background candidates, the two characters, the CEFR level, the episode."""
    from backend.media.video_renderer_remotion import sprite_mirrored, sprite_placement  # lazy: a heavy module
    from backend.library import activity_illustrations, sprite_service, storyboard_service
    from backend.library import activity_library_service as activity_library
    from backend.library import project_visuals_service as project_visuals

    project_id = project["id"]
    backgrounds: list[str] = []

    def add(path: str | Path | None) -> None:
        if path and Path(path).is_file() and str(path) not in backgrounds:
            backgrounds.append(str(path))

    add(settings.DATA_DIR / "thumbnails" / project_id / "topic_qwen.png")  # Phase 39: the local-AI topic picture first
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
        from backend.channel import channel_service

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


def head_box(figure: Image.Image) -> tuple[int, int, int, int]:
    """(left, top, right, bottom) of the figure's head -- the opaque part of its top `HEAD_SHARE` rows."""
    alpha = figure.getchannel("A")
    bottom = max(1, round(figure.height * HEAD_SHARE))
    box = alpha.crop((0, 0, figure.width, bottom)).getbbox() or (0, 0, figure.width, bottom)
    return box[0], box[1], box[2], bottom


def _covers(front: Image.Image, front_at: tuple[int, int], rect: tuple[int, int, int, int]) -> bool:
    """True when any opaque pixel of `front` (drawn at `front_at`) falls inside the canvas rectangle `rect`."""
    left, top = max(rect[0], front_at[0]), max(rect[1], front_at[1])
    right, bottom = min(rect[2], front_at[0] + front.width), min(rect[3], front_at[1] + front.height)
    if left >= right or top >= bottom:
        return False
    patch = front.getchannel("A").crop((left - front_at[0], top - front_at[1], right - front_at[0], bottom - front_at[1]))
    return patch.getextrema()[1] > 24


def _place(figures: list[Image.Image], layout: dict, size: tuple[int, int]) -> list[tuple[int, int]] | None:
    """Positions (left, top) for figures already drawn at one height, or None when they do not fit the layout."""
    width, height = size
    margin, gap = round(width * SAFE_MARGIN), round(width * HEAD_GAP)
    x, _, box_width, _, _ = layout["text"]
    text_left, text_right = round(x * width), round((x + box_width) * width)
    group = layout["group"]
    tops = [height - figure.height for figure in figures]
    heads = [head_box(figure) for figure in figures]

    def bleed_ok(index: int, left: int) -> bool:
        over = max(0, -left) + max(0, left + figures[index].width - width)
        return over <= figures[index].width * MAX_BLEED

    if len(figures) == 1:
        head = heads[0]
        if group in ("right", "split"):
            left = width - margin - head[2]
            ok = left >= text_right
        elif group == "left":
            left = margin - head[0]
            ok = left + figures[0].width <= text_left
        else:
            left, ok = (width - figures[0].width) // 2, True
        return [(left, tops[0])] if ok and bleed_ok(0, left) else None
    if group == "split":
        lefts = [margin - heads[0][0], width - margin - heads[1][2]]
        if lefts[0] + figures[0].width > text_left or lefts[1] < text_right:
            return None
        return list(zip(lefts, tops)) if all(bleed_ok(i, left) for i, left in enumerate(lefts)) else None
    # two figures in one group: the outer one at the edge, the inner (front) one beside it, heads apart
    left_fig, right_fig = figures
    left_head, right_head = heads
    for extra in range(0, round(width * 0.12), max(1, round(width * 0.01))):
        if group in ("right", "bottom"):
            right_left = width - margin - right_head[2]
            left_left = right_left + right_head[0] - gap - extra - left_head[2]
        else:
            left_left = margin - left_head[0]
            right_left = left_left + left_head[2] + gap + extra - right_head[0]
        if group == "bottom":  # centre the pair of heads
            shift = (width - (left_left + left_head[0]) - (right_left + right_head[2])) // 2
            left_left, right_left = left_left + shift, right_left + shift
            if left_left + left_head[0] < margin:
                return None
        elif group == "right" and left_left < text_right:
            return None
        elif group == "left" and right_left + right_fig.width > text_left:
            return None
        if not (bleed_ok(0, left_left) and bleed_ok(1, right_left)):
            return None
        # the inner figure is drawn in front: it must not cover the other's head
        if group in ("right", "bottom"):
            back_head = (right_left + right_head[0], tops[1] + right_head[1],
                         right_left + right_head[2], tops[1] + right_head[3])
            clear = not _covers(left_fig, (left_left, tops[0]), back_head)
        else:
            back_head = (left_left + left_head[0], tops[0] + left_head[1],
                         left_left + left_head[2], tops[0] + left_head[3])
            clear = not _covers(right_fig, (right_left, tops[1]), back_head)
        if clear:
            return [(left_left, tops[0]), (right_left, tops[1])]
    return None


def arrange_figures(draw_at, layout: dict, size: tuple[int, int]) -> list[tuple[Image.Image, tuple[int, int]]]:
    """The biggest figures that fit: `draw_at(height)` returns the figures (left to right) drawn at that height. Tries
    from the layout's height down, never into the logo row; returns (figure, position) in drawing order (back first)."""
    width, height = size
    top_reserved = round(min(size) * (MARGIN_SHARE + LOGO_SHARE + 0.02))
    tallest = min(round(height * layout["height"]), height - top_reserved)
    step = max(4, round(height * 0.02))
    for target in range(tallest, round(height * 0.3), -step):
        figures = draw_at(target)
        if not figures:
            return []
        positions = _place(figures, layout, size)
        if positions is not None:
            pairs = list(zip(figures, positions))
            # the inner figure goes in front of the outer one
            return pairs[::-1] if layout["group"] in ("right", "bottom") and len(pairs) == 2 else pairs
    return []


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
        characters = sorted(inputs.get("characters") or [], key=lambda character: character["slot"])

        def draw_at(target: int) -> list[Image.Image]:
            return [figure for figure in (_character(c, variant_index, target) for c in characters) if figure is not None]

        for figure, position in arrange_figures(draw_at, layout, size):
            image.alpha_composite(figure, position)

    draw = ImageDraw.Draw(image)
    margin = round(min(size) * MARGIN_SHARE)
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
    _logo(image, round(min(size) * LOGO_SHARE), margin)
    return image.convert("RGB")
