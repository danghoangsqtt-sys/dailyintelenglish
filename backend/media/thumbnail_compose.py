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
from typing import Any, Callable

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

# Normalized wide layouts per variant. text: (x, y, width, height, align); group: where the characters stand -- "right" /
# "left" of the headline (rule of thirds), or "split" on both sides of a centred headline. Portrait figures use the
# separate photo-card layout below. height: the tallest a character may be; shade: where text-side darkening comes from.
#
# Walkthrough 2026-10-14, owner review + YouTube thumbnail guides (faces recognisable at 150 px wide, ~40-50 % of the
# frame; keep faces and text out of the bottom-right duration badge; ~60 px margins): the characters are big, their
# bodies may overlap a little and bleed off the outer edge, but their heads never touch (see `arrange_figures`).
LAYOUTS_16X9 = (
    {"text": (0.045, 0.21, 0.45, 0.50, "left"), "group": "right", "height": 0.86, "shade": "left"},
    {"text": (0.27, 0.17, 0.46, 0.40, "center"), "group": "split", "height": 0.86, "shade": "top"},
    {"text": (0.51, 0.21, 0.45, 0.50, "right"), "group": "left", "height": 0.86, "shade": "right"},
)
# The 720x1280 equivalent of renderer/src/safeZone.ts (1080x1920). The photo ends before the platform's right-hand
# button column begins; all lettering stays left of that column and above the bottom caption/music area.
PORTRAIT_SAFE = {"left": 48, "right": 672, "top": 155, "bottom": 880, "column_x": 576, "column_from_y": 600}
PORTRAIT_PHOTO = (48, 232, 672, 582)
PORTRAIT_HEADLINE = (48, 620, 528, 195)
PORTRAIT_FIGURE_LAYOUT = {"text": (0, 0, 1, 0, "center"), "group": "bottom", "height": 0.82}
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
    from backend.media import ai_scene  # Phase 43: the scenes Qwen drew for the "AI scene" kind

    return {"backgrounds": backgrounds, "characters": characters, "cefr": (project.get("cefr_level") or "").upper(),
            "episode": episode, "outside_image": str(outside) if outside.is_file() else None,
            "ai_scenes": ai_scene.load_scenes(project_id)}


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


def _shade(image: Image.Image, where: str, side_span: float = 0.66, strength: int = 200) -> Image.Image:
    """Darken the text side so the headline reads at thumbnail size (`side_span`: how far a left/right shade reaches;
    `strength`: the darkest alpha at the edge)."""
    width, height = image.size
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    if where in ("left", "right"):
        span = int(width * side_span)
        for offset in range(span):
            alpha = round(strength * (1 - offset / span) ** 1.3)
            x = offset if where == "left" else width - 1 - offset
            draw.line((x, 0, x, height), fill=alpha)
    elif where == "top":
        span = int(height * 0.68)
        for offset in range(span):
            draw.line((0, offset, width, offset), fill=round(190 * (1 - offset / span) ** 1.2))
    else:
        raise ValueError(f"Unknown shade direction: {where}")
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
          align: str = "left", max_width: int | None = None) -> tuple[int, int]:
    """A rounded label; with `max_width` its text shrinks until the pill fits (it must not reach a face)."""
    while True:
        font = _font(size, "ExtraBold")
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        pad_x, pad_y = round(size * 0.55), round(size * 0.32)
        width, height = right - left + 2 * pad_x, bottom - top + 2 * pad_y
        if max_width is None or width <= max_width or size <= 14:
            break
        size -= 1
    x, y = position
    if align == "right":
        x -= width
    elif align == "center":
        x -= width // 2
    draw.rounded_rectangle((x, y, x + width, y + height), radius=height // 2, fill=fill)
    draw.text((x + pad_x - left, y + pad_y - top), text, font=font, fill=ink)
    return width, height


def _logo(image: Image.Image, height: int, margin: int, top: int | None = None) -> None:
    if not LOGO_PATH.is_file():
        return
    with Image.open(LOGO_PATH) as opened:
        logo = opened.convert("RGBA")
    logo = logo.resize((max(1, round(logo.width * height / logo.height)), height), Image.Resampling.LANCZOS)
    image.alpha_composite(logo, (image.width - logo.width - margin, margin if top is None else top))


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


def grade_ai_scene(picture: Image.Image) -> Image.Image:
    """Owner review 2026-10-14: the Qwen scenes looked darker and duller than ChatGPT's. A light commercial grade:
    stretch the levels, lift the brightness, more colour and a little crispness (faces stay natural)."""
    from PIL import ImageEnhance

    graded = ImageOps.autocontrast(picture, cutoff=0.2)
    graded = ImageEnhance.Brightness(graded).enhance(1.03)
    graded = ImageEnhance.Color(graded).enhance(1.1)
    return ImageEnhance.Sharpness(graded).enhance(1.15)


def ai_scene_picture(scene: dict, size: tuple[int, int]) -> Image.Image:
    """Phase 43 (D122): the background of an "AI scene" thumbnail from Qwen's wide draw.

    The 1280x720 window `ai_scene.choose_frame` picked keeps both faces. Portrait covers place that window in the safe
    photo card instead of cutting it into another aspect ratio."""
    frame = scene["frame"]
    with Image.open(scene["image"]) as opened:
        picture = grade_ai_scene(opened.convert("RGB"))
    window = picture.crop((frame["left"], frame["top"], frame["left"] + 1280, frame["top"] + 720))
    return window.resize(size, Image.Resampling.LANCZOS) if window.size != size else window


def _portrait_picture(inputs: dict, suggestion: ThumbnailSuggestion, variant_index: int,
                      template_id: str) -> tuple[Image.Image, Image.Image]:
    """A complete landscape photo for the safe area and its unadorned scene for the full-height backdrop."""
    photo_width = PORTRAIT_PHOTO[2] - PORTRAIT_PHOTO[0]
    photo_height = PORTRAIT_PHOTO[3] - PORTRAIT_PHOTO[1]
    photo_size = (photo_width, photo_height)
    if template_id == "qwen_scene":
        scenes = inputs.get("ai_scenes") or []
        if not scenes:
            raise ValueError("no AI scene picture for this thumbnail")
        picture = ai_scene_picture(scenes[variant_index % len(scenes)], SIZES["16x9"])
    else:
        source = inputs.get("outside_image") if template_id == "outside_ai" else None
        if template_id == "composed":
            candidates = inputs.get("backgrounds") or []
            source = candidates[variant_index % len(candidates)] if candidates else None
        picture = _background(source, SIZES["16x9"], suggestion)
    photo = ImageOps.fit(picture, photo_size, method=Image.Resampling.LANCZOS).convert("RGBA")
    if template_id == "composed":
        characters = sorted(inputs.get("characters") or [], key=lambda character: character["slot"])

        def draw_at(target: int) -> list[Image.Image]:
            return [figure for figure in (_character(c, variant_index, target) for c in characters) if figure is not None]

        for figure, position in arrange_figures(draw_at, PORTRAIT_FIGURE_LAYOUT, photo_size):
            photo.alpha_composite(figure, position)
    return photo.convert("RGB"), picture


def _shorten_to_fit(text: str, fits: Callable[[str], bool]) -> str:
    """Keep a long AI suggestion inside a fixed portrait safe box, with a visible ellipsis."""
    if fits(text):
        return text
    words = text.split()
    while len(words) > 1:
        words.pop()
        candidate = " ".join(words) + "…"
        if fits(candidate):
            return candidate
    candidate = words[0] if words else text
    while candidate and not fits(candidate + "…"):
        candidate = candidate[:-1]
    return candidate + "…"


def _portrait_headline_fits(draw: ImageDraw.ImageDraw, text: str) -> bool:
    font = _font(26)
    wrapped = _wrap(draw, text, font, PORTRAIT_HEADLINE[2])
    left, top, right, bottom = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=2,
                                                       stroke_width=max(3, 26 // 14))
    return right - left <= PORTRAIT_HEADLINE[2] and bottom - top <= PORTRAIT_HEADLINE[3]


def _portrait_support_fits(draw: ImageDraw.ImageDraw, text: str) -> bool:
    font = _font(18, "ExtraBold")
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return right - left + 2 * round(18 * 0.55) <= PORTRAIT_HEADLINE[2]


def _render_portrait(inputs: dict, suggestion: ThumbnailSuggestion, variant_index: int,
                     template_id: str) -> Image.Image:
    """9:16 cover: photo, faces, branding and text occupy the owner's platform-safe shape."""
    size = SIZES["9x16"]
    photo, scene = _portrait_picture(inputs, suggestion, variant_index, template_id)
    # Keep the source scene visible across the entire 9:16 canvas. The platform may cover the lower part, but a
    # flat colour there makes the cover look unfinished in galleries and exported files. Crop the left side of the
    # landscape source for the atmospheric backdrop; the foreground photo card still holds the complete pair.
    backdrop_slice = scene.crop((0, 0, max(1, round(scene.width * 0.30)), scene.height))
    backdrop = ImageOps.fit(backdrop_slice, size, method=Image.Resampling.LANCZOS)
    backdrop = backdrop.filter(ImageFilter.GaussianBlur(5))
    backdrop = Image.blend(backdrop, Image.new("RGB", size, (8, 23, 17)), 0.34)
    image = backdrop.convert("RGBA")
    left, top, right, bottom = PORTRAIT_PHOTO
    photo_mask = Image.new("L", photo.size, 0)
    ImageDraw.Draw(photo_mask).rounded_rectangle((0, 0, photo.width - 1, photo.height - 1), radius=18, fill=255)
    image.paste(photo, (left, top), photo_mask)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((left, top, right - 1, bottom - 1), radius=18, outline="#FFFFFF", width=2)

    # A soft dark patch gives the lettering contrast without flattening the lower scene or turning it into a box.
    text_mask = Image.new("L", size, 0)
    ImageDraw.Draw(text_mask).rounded_rectangle((34, 602, 592, 888), radius=20, fill=130)
    text_mask = text_mask.filter(ImageFilter.GaussianBlur(16))
    image.paste(Image.new("RGBA", size, (5, 16, 11, 255)), (0, 0), text_mask)
    draw = ImageDraw.Draw(image)

    badge_x = PORTRAIT_SAFE["left"]
    badge_y = 164
    if inputs.get("cefr"):
        badge_width, _ = _pill(draw, f"{inputs['cefr']} ENGLISH", (badge_x, badge_y), 26, BADGE_YELLOW, BADGE_INK)
        badge_x += badge_width + 12
    if inputs.get("episode"):
        _pill(draw, f"EP. {inputs['episode']}", (badge_x, badge_y), 26, "#FFFFFF", BADGE_INK)
    _logo(image, 64, size[0] - PORTRAIT_SAFE["right"], top=158)

    fill = suggestion.palette.text if _luminance(suggestion.palette.text) >= 0.6 else "#FFFFFF"
    title = _shorten_to_fit(suggestion.headline.upper(), lambda value: _portrait_headline_fits(draw, value))
    title_bottom = _headline(draw, title, PORTRAIT_HEADLINE, "left", fill,
                             max_size=64, min_size=26)
    if suggestion.supporting_text:
        accent = suggestion.palette.accent
        support = _shorten_to_fit(suggestion.supporting_text, lambda value: _portrait_support_fits(draw, value))
        _pill(draw, support, (PORTRAIT_HEADLINE[0], title_bottom + 10), 28, accent,
              "#FFFFFF" if _luminance(accent) < 0.55 else BADGE_INK, max_width=PORTRAIT_HEADLINE[2])
    return image.convert("RGB")


def render(inputs: dict, suggestion: ThumbnailSuggestion, aspect: ThumbnailAspect, variant_index: int,
           template_id: str) -> Image.Image:
    """One thumbnail picture (RGB) at one aspect ratio."""
    if aspect == "9x16":
        return _render_portrait(inputs, suggestion, variant_index, template_id)
    size = SIZES[aspect]
    width, height = size
    layout = LAYOUTS_16X9[variant_index % len(LAYOUTS_16X9)]
    if template_id == "qwen_scene":
        scenes = inputs.get("ai_scenes") or []
        if not scenes:
            raise ValueError("no AI scene picture for this thumbnail")
        scene = scenes[variant_index % len(scenes)]
        frame = scene["frame"]
        layout = {"text": tuple(frame["text_box"]), "shade": frame["side"]}
        # a light shade, just past the title strip: the faces and the bright scene keep their light (the
        # headline's dark outline carries the contrast)
        image = _shade(ai_scene_picture(scene, size), frame["side"], min(0.66, frame["free_share"] + 0.1), 120)
        image = image.convert("RGBA")
    else:
        if template_id == "outside_ai":
            source = inputs.get("outside_image")
            layout = LAYOUTS_16X9[0]
        else:
            candidates = inputs.get("backgrounds") or []
            source = candidates[variant_index % len(candidates)] if candidates else None
        image = _shade(_background(source, size, suggestion), layout["shade"]).convert("RGBA")

    if template_id not in ("outside_ai", "qwen_scene"):
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
              round(min(size) * 0.05), accent, "#FFFFFF" if _luminance(accent) < 0.55 else BADGE_INK, align,
              max_width=text_box[2])

    badge_size = round(min(size) * 0.05)
    badge_x = margin
    if inputs.get("cefr"):
        badge_width, _ = _pill(draw, f"{inputs['cefr']} ENGLISH", (badge_x, margin), badge_size, BADGE_YELLOW, BADGE_INK)
        badge_x += badge_width + round(margin * 0.5)
    if inputs.get("episode"):
        _pill(draw, f"EP. {inputs['episode']}", (badge_x, margin), badge_size, "#FFFFFF", BADGE_INK)
    _logo(image, round(min(size) * LOGO_SHARE), margin)
    return image.convert("RGB")
