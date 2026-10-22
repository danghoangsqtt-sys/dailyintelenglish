"""Deterministic Solo layout proof from immutable front pixels and shared frame rules.

Rules v2 (Phase 55, ENH-037): the presenter stands waist-up on a stage in front of the segment's scene, so the figure
is taller than the frame and its legs run below it. The proof protects cards from the presenter's head and torso (the
calm poses); gesturing hands may pass in front of a card because the presenter is drawn above it.
"""
from __future__ import annotations

import asyncio
import copy
import json
import math
from pathlib import Path

from PIL import Image

from backend.core.exceptions import ValidationError
from backend.core.paths import get_project_root
from backend.library import presenter_asset_plan
from backend.schemas.explainer import ExplainerPlan, SegmentLayout

RULES = json.loads((get_project_root() / "frontend/static/explainer-layout-rules.json").read_text(encoding="utf-8"))
EPSILON = 1e-8


def intersects(a: dict, b: dict) -> bool:
    """Strict overlap; touching edges are permitted before the explicit motion margin."""
    return a["x"] < b["x"] + b["width"] - EPSILON and b["x"] < a["x"] + a["width"] - EPSILON and a["y"] < b["y"] + b["height"] - EPSILON and b["y"] < a["y"] + a["height"] - EPSILON


def contains(outer: dict, inner: dict) -> bool:
    """Contain finite positive rectangles, including their full edges."""
    return (all(math.isfinite(float(v)) for v in inner.values()) and inner["width"] > 0 and inner["height"] > 0
            and inner["x"] >= outer["x"] - EPSILON and inner["y"] >= outer["y"] - EPSILON
            and inner["x"] + inner["width"] <= outer["x"] + outer["width"] + EPSILON
            and inner["y"] + inner["height"] <= outer["y"] + outer["height"] + EPSILON)


def inside_safe(rect: dict, aspect: str) -> bool:
    """Use the existing vertical platform polygon, not the geometric frame centre."""
    spec = RULES["aspects"][aspect]
    column = spec.get("column")
    return contains(spec["safe"], rect) and not (column and rect["y"] + rect["height"] > column["fromY"] + EPSILON and rect["x"] + rect["width"] > column["x"] + EPSILON)


def envelope(a: dict, b: dict, margin: float = 0) -> dict:
    """AABB contains every intermediate point of monotonic easing and idle margin."""
    x, y = min(a["x"], b["x"]) - margin, min(a["y"], b["y"]) - margin
    return {"x": x, "y": y, "width": max(a["x"] + a["width"], b["x"] + b["width"]) + margin - x,
            "height": max(a["y"] + a["height"], b["y"] + b["height"]) + margin - y}


def presenter_boxes(placement: dict, metrics: dict, aspect: str) -> tuple[dict, dict]:
    """Place the union alpha centre/feet and derive an undistorted full PNG canvas."""
    spec, alpha = RULES["aspects"][aspect], metrics["alpha"]
    ch = placement["height"] / alpha["height"]
    cw = ch * spec["height"] / spec["width"] * metrics["canvasWidth"] / metrics["canvasHeight"]
    canvas = {"x": placement["x"] - (alpha["x"] + alpha["width"] / 2) * cw,
              "y": placement["y"] - (alpha["y"] + alpha["height"]) * ch, "width": cw, "height": ch}
    return ({"x": canvas["x"] + alpha["x"] * cw, "y": canvas["y"] + alpha["y"] * ch,
             "width": alpha["width"] * cw, "height": placement["height"]}, canvas)


CORE_POSES = ("calm__closed", "calm__open", "blink")
FULL_FRAME = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}


def shown_edges(visual: dict) -> list[dict]:
    """Edges worth a text line: steps/cause-effect already show consecutive order with numbers or arrows."""
    order = [node["id"] for node in visual.get("nodes", [])]
    implied = visual.get("template") in ("steps", "cause_effect")
    return [edge for edge in visual.get("edges", [])
            if edge.get("label") or not implied or edge["source"] not in order or edge["target"] not in order
            or order.index(edge["target"]) != order.index(edge["source"]) + 1]


def core_box(placement: dict, metrics: dict, aspect: str) -> dict:
    """Head and torso (the calm poses' alpha) on the same canvas as the full figure."""
    _, canvas = presenter_boxes(placement, metrics, aspect)
    core = metrics.get("core") or metrics["alpha"]
    return {"x": canvas["x"] + core["x"] * canvas["width"], "y": canvas["y"] + core["y"] * canvas["height"],
            "width": core["width"] * canvas["width"], "height": core["height"] * canvas["height"]}


def head_box(placement: dict, metrics: dict, aspect: str) -> dict:
    """The top of the core box: the face and hair that must stay inside the platform-safe area."""
    core = core_box(placement, metrics, aspect)
    return {**core, "height": min(core["height"], RULES["headFraction"] * placement["height"])}


def visible(rect: dict) -> dict:
    """Clip to the frame; the stage figure's legs lie below it."""
    x, y = max(0.0, rect["x"]), max(0.0, rect["y"])
    right, bottom = min(1.0, rect["x"] + rect["width"]), min(1.0, rect["y"] + rect["height"])
    return {"x": x, "y": y, "width": max(0.0, right - x), "height": max(0.0, bottom - y)}


def text_metrics(visual: dict, panel: dict, aspect: str) -> dict:
    """Conservative character wrapping bounds shared with the actual card/grid renderer."""
    spec = RULES["aspects"][aspect]
    width, height = panel["width"] * spec["width"], panel["height"] * spec["height"]
    padding, gap, font, title_font = (spec[k] for k in ("padding", "gap", "font", "titleFont"))
    def lines(text: str, available: float, size: int) -> int:
        # 1.1em per character bounds ordinary English including wide Latin glyphs.
        capacity = max(1, math.floor(available / (size * 1.1)))
        return sum(max(1, math.ceil(len(part) / capacity)) for part in text.split("\n")) if text else 0
    title_height = lines(visual.get("title", ""), width - 2 * padding, title_font) * title_font * 1.25
    available_height = height - 2 * padding - title_height - gap
    if visual["kind"] in ("photo", "activity", "quote", "chart", "timeline", "map"):
        # bounded short texts; the VOX kinds (Phase 59) size themselves to their board in the renderer
        return {"font": font, "titleFont": title_font, "padding": padding, "gap": gap, "columns": 1}
    columns = min(2 if visual.get("template") == "comparison" else spec["columns"], len(visual.get("nodes", [1])))
    if visual["kind"] == "text_card":
        needed = sum(lines(text, width - 2 * padding - font, font) * font * 1.3 + gap for text in visual.get("bullets", []))
        needed += lines(visual.get("emphasis", ""), width - 2 * padding, font) * font * 1.3
    else:
        node_width = (width - 2 * padding - gap * (columns - 1)) / columns
        row_heights = []
        for index in range(0, len(visual["nodes"]), columns):
            row_heights.append(max((lines(node["label"], node_width - 2 * gap, font) * font * 1.3
                                    + lines(node.get("detail", ""), node_width - 2 * gap, font) * font * 1.3 + 2 * gap)
                                   for node in visual["nodes"][index:index + columns]))
        needed = sum(row_heights) + gap * max(0, len(row_heights) - 1)
        nodes = {node["id"]: node["label"] for node in visual["nodes"]}
        for edge in shown_edges(visual):
            label = f"{nodes[edge['source']]} → {nodes[edge['target']]}" + (f": {edge['label']}" if edge.get("label") else "")
            needed += gap + lines(label, width - 2 * padding, font) * font * 1.3
    if width < 2 * padding + 4 * font or available_height < needed:
        raise ValidationError("The card/diagram text cannot fit readably; shorten its title/details or reduce nodes")
    return {"font": font, "titleFont": title_font, "padding": padding, "gap": gap, "columns": columns}


def protected_regions(visual: dict, panel: dict, aspect: str, illustrations: dict) -> list[dict]:
    """Map owner photo annotations through contain/cover and refuse important cropping."""
    if visual["kind"] == "activity":
        return []  # a full-frame picture behind the presenter, like the conversation video's inserts
    if visual["kind"] != "photo" or not visual.get("important_regions"):
        if visual["kind"] == "photo" and visual.get("fit") == "cover":
            raise ValidationError("Use contain for an unannotated photo, or mark all important regions before cropping")
        return [panel]
    ref = visual.get("asset")
    image = illustrations.get((ref["asset_id"], ref["version"])) if ref else None
    if not image:
        raise ValidationError("Import/select the photo before validating its protected regions")
    spec = RULES["aspects"][aspect]
    pw, ph = panel["width"] * spec["width"], panel["height"] * spec["height"]
    scale = (max if visual.get("fit") == "cover" else min)(pw / image["width"], ph / image["height"])
    iw, ih = image["width"] * scale / spec["width"], image["height"] * scale / spec["height"]
    origin = {"x": panel["x"] + (panel["width"] - iw) / 2, "y": panel["y"] + (panel["height"] - ih) / 2}
    protected = [{"x": origin["x"] + r["x"] * iw, "y": origin["y"] + r["y"] * ih, "width": r["width"] * iw, "height": r["height"] * ih} for r in visual["important_regions"]]
    if not all(contains(panel, box) for box in protected):
        raise ValidationError("This crop removes an important photo region; choose contain or reframe it")
    return protected


def validate_segment(segment: dict, aspect: str, metrics: dict, illustrations: dict, previous: dict | None = None) -> dict:
    """Prove endpoints and the entire motion envelope against cards and reserved UI (rules v2 stage)."""
    layout = segment["layouts"].get(aspect)
    if not layout or layout.get("rules_version") != RULES["version"]:
        raise ValidationError("Resolve the missing or outdated layout before approval")
    spec = RULES["aspects"][aspect]
    stage, activity = spec["stage"], segment["visual"]["kind"] == "activity"
    panel, placement = layout["illustration"], layout["presenter"]
    if not activity and (not inside_safe(panel, aspect) or any(intersects(panel, spec[key]) for key in ("caption", "header"))):
        raise ValidationError("The card/illustration must stay inside the safe zone and outside captions/brand")

    def sized(value: dict) -> None:
        if not stage["minHeight"] <= value["height"] <= stage["maxHeight"]:
            raise ValidationError(f"Presenter size must stay within {stage['minHeight']}–{stage['maxHeight']} of the frame height")

    sized(placement)
    bounds, canvas = presenter_boxes(placement, metrics, aspect)
    core, head = core_box(placement, metrics, aspect), head_box(placement, metrics, aspect)
    start_core, start_head = core, head
    protected = protected_regions(segment["visual"], panel, aspect, illustrations)
    obstacles = list(protected)
    if layout["transition"] != "cut":
        origin = layout.get("motion_from") or (previous or {}).get("presenter")
        if previous and layout.get("motion_from") and layout["motion_from"] != previous["presenter"]:
            raise ValidationError("The motion start no longer matches the previous segment")
        if origin:
            sized(origin)
            start_core, start_head = core_box(origin, metrics, aspect), head_box(origin, metrics, aspect)
        if previous:
            obstacles.extend(previous.get("protected", []))
    swept_head = envelope(start_head, head, RULES["margin"])
    if not inside_safe(swept_head, aspect) or intersects(swept_head, spec["header"]):
        raise ValidationError("The presenter's head must stay inside the safe zone and below the brand line")
    swept = visible(envelope(start_core, core, RULES["margin"]))
    if swept["x"] <= 0 or swept["x"] + swept["width"] >= 1:
        raise ValidationError("The presenter's body must stay inside the frame horizontally")
    if any(intersects(swept, item) for item in obstacles):
        raise ValidationError("Presenter or its movement crosses the card; move it to the other side, shrink it, or use a boundary cut")
    return {"id": segment["id"], "presenter": placement, "bounds": bounds, "canvas": canvas, "core": core,
            "motion_bounds": swept, "protected": protected, "text": text_metrics(segment["visual"], panel, aspect),
            "transition": layout["transition"]}


def measure_front(manifest: dict) -> dict:
    """Measure every pose alpha, including hands, on one verified aligned canvas."""
    union, core, dimensions = None, None, None
    for key, asset in manifest["pictures"].items():
        with Image.open(Path(asset["path"])) as source:
            if dimensions and source.size != dimensions:
                raise ValidationError("Front pictures must share one aligned canvas")
            dimensions = source.size
            alpha = source.convert("RGBA").getchannel("A")
            bounds = alpha.point(lambda value: 255 if value > 4 else 0).getbbox()
            if not bounds:
                raise ValidationError("A front pose has no visible figure")
            union = bounds if union is None else (min(union[0], bounds[0]), min(union[1], bounds[1]), max(union[2], bounds[2]), max(union[3], bounds[3]))
            if key in CORE_POSES:
                core = bounds if core is None else (min(core[0], bounds[0]), min(core[1], bounds[1]), max(core[2], bounds[2]), max(core[3], bounds[3]))
    if not union or not dimensions:
        raise ValidationError("Approve the full front21 pack before solving layouts")
    w, h = dimensions
    core = core or union

    def fraction(box: tuple) -> dict:
        return {"x": box[0] / w, "y": box[1] / h, "width": (box[2] - box[0]) / w, "height": (box[3] - box[1]) / h}

    return {"canvasWidth": w, "canvasHeight": h, "alpha": fraction(union), "core": fraction(core)}


async def front_metrics(snapshot: dict) -> dict:
    """Verify pinned pack bytes then measure outside the shared database lock."""
    ref = snapshot.get("presenter")
    if not ref or not ref.get("front_pack_revision"):
        raise ValidationError("Approve the full front21 pack before solving layouts")
    manifest = await presenter_asset_plan.resolve_manifest(ref["profile_id"], ref["identity_version"], ref["front_pack_revision"])
    return await asyncio.to_thread(measure_front, manifest)


def prove(snapshot: dict, plan: ExplainerPlan, metrics: dict) -> dict:
    """Build a deterministic proof; no AI, filesystem or mutable runtime measurements."""
    illustrations = {(item["id"], item["version"]): item for item in snapshot["source"]["illustrations"] if not item.get("missing")}
    aspects = {}
    for aspect in plan.aspects:
        previous, records = None, []
        for segment in plan.segments:
            try:
                record = validate_segment(segment.model_dump(), aspect, metrics, illustrations, previous)
            except ValidationError as exc:
                raise ValidationError(f"Segment {segment.id} ({aspect}): {exc}") from exc
            records.append(record)
            previous = record
        spec = RULES["aspects"][aspect]
        aspects[aspect] = {"safe": spec["safe"], "caption": spec["caption"], "header": spec["header"], "segments": records,
                           "anchor_options": spec["anchors"]}
    return {"rules_version": RULES["version"], "presenter_metrics": metrics, "aspects": aspects}


VOX_GAP = 0.015


def vox_caption(aspect: str) -> dict:
    """The VOX caption band: the Solo one in 16:9; in 9:16 (no presenter below it) it moves to the bottom of the safe area
    so the graphics get the tall upper board."""
    spec = RULES["aspects"][aspect]
    if aspect != "9:16":
        return spec["caption"]
    safe, caption = spec["safe"], spec["caption"]
    height = caption["height"]
    return {**caption, "y": safe["y"] + safe["height"] - height - VOX_GAP}


def vox_board(aspect: str) -> dict:
    """Phase 59 (ENH-041): the VOX board -- the safe area between the brand line and the captions (no presenter)."""
    spec = RULES["aspects"][aspect]
    header, caption, safe = spec["header"], vox_caption(aspect), spec["safe"]
    top = header["y"] + header["height"] + VOX_GAP
    return {"x": safe["x"], "y": top, "width": safe["width"], "height": caption["y"] - VOX_GAP - top}


def vox_proof(plan: ExplainerPlan) -> dict:
    """The VOX geometry proof: one board per aspect and each segment's text metrics on it (no front pictures)."""
    aspects = {}
    for aspect in plan.aspects:
        spec, board = RULES["aspects"][aspect], vox_board(aspect)
        records = []
        for segment in plan.segments:
            try:
                text = text_metrics(segment.visual.model_dump(), board, aspect)
            except ValidationError as exc:
                raise ValidationError(f"Segment {segment.id} ({aspect}): {exc}") from exc
            records.append({"id": segment.id, "board": board, "text": text})
        aspects[aspect] = {"safe": spec["safe"], "caption": vox_caption(aspect), "header": spec["header"], "board": board,
                           "segments": records}
    return {"rules_version": RULES["version"], "style": "vox", "aspects": aspects}


def _vox(snapshot: dict) -> bool:
    # Phase 63: the news and blur Shorts use the VOX board and caption proof too
    return snapshot["source"]["project"].get("explainer_style") in ("vox", "news", "blur")


async def validate_plan(snapshot: dict, plan: ExplainerPlan) -> dict:
    """Production approval gate: actual front pixels, complete layouts and safe paths."""
    if plan is not None and _vox(snapshot):
        return vox_proof(plan)
    if plan is None or any(aspect not in segment.layouts for segment in plan.segments for aspect in plan.aspects):
        raise ValidationError("Resolve the missing layouts for all selected aspects before approval")
    return prove(snapshot, plan, await front_metrics(snapshot))


async def arrange(snapshot: dict, plan: ExplainerPlan) -> tuple[list, dict]:
    """Suggest valid unlocked stage layouts; preserve owner locks and use cuts for unsafe paths.

    The presenter keeps one stage side for the whole video (like the conversation video's characters); cards float on
    the other side and activity pictures fill the frame behind her.
    """
    if _vox(snapshot):  # no presenter to place: the VOX board is fixed
        return copy.deepcopy(plan.segments), vox_proof(plan)
    metrics = await front_metrics(snapshot)
    illustrations = {(item["id"], item["version"]): item for item in snapshot["source"]["illustrations"] if not item.get("missing")}
    segments = copy.deepcopy(plan.segments)
    for aspect in plan.aspects:
        previous = None
        spec = RULES["aspects"][aspect]
        stage = spec["stage"]
        for segment in segments:
            lock = segment.locks.layout_16_9 if aspect == "16:9" else segment.locks.layout_9_16
            if lock:
                previous = validate_segment(segment.model_dump(), aspect, metrics, illustrations, previous)
                continue
            anchor = previous["presenter"]["anchor"] if previous else stage["anchor"]
            anchors = [anchor, *[item for item in ("right", "left", "center") if item != anchor]]
            heights = [value for value in (round(stage["defaultHeight"] - step * 0.05, 4) for step in range(40))
                       if value >= stage["minHeight"]]
            error = first_error = None
            for choice in anchors:
                for height in heights:
                    illustration = FULL_FRAME if segment.visual.kind == "activity" else spec["panels"][choice]
                    proposal = {"presenter": {"anchor": choice, "x": spec["anchors"][choice], "y": stage["headTop"] + height,
                                              "height": height},
                                "illustration": illustration, "transition": "ease", "transition_seconds": 0.4,
                                "rules_version": RULES["version"]}
                    if previous:
                        proposal["motion_from"] = previous["presenter"]
                    for transition in ("ease", "cut"):
                        proposal["transition"] = transition
                        if transition == "cut":
                            proposal.pop("motion_from", None)
                        segment.layouts[aspect] = SegmentLayout.model_validate(proposal)
                        try:
                            record = validate_segment(segment.model_dump(), aspect, metrics, illustrations, previous)
                        except ValidationError as exc:
                            error = exc
                        else:
                            previous, error = record, None
                            break
                    if error is None:
                        break
                if error is None:
                    break
                first_error = first_error or error  # the preferred stage side explains the refusal best
            if error:
                raise ValidationError(f"Segment {segment.id} ({aspect}): {first_error}") from first_error
    candidate = plan.model_copy(update={"segments": segments})
    return segments, prove(snapshot, candidate, metrics)
