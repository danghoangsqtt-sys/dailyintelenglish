"""Task 28.2: character reference sheets (turnaround) for the woman and the man on RealVisXL V5.0.
Not shipped. Runs inside venv-image on the GPU, outside the app (stop Ollama models first).

    venv-image\\Scripts\\python scripts\\character_sheet_realvis.py --tokens-only
    venv-image\\Scripts\\python scripts\\character_sheet_realvis.py --generate --seeds 7 21
    venv-image\\Scripts\\python scripts\\character_sheet_realvis.py --compose

Six panels per character (the layout of the owner's sample sheet): full_front, full_back, face_front,
face_profile, face_three_quarter, face_smile (the sample's head-from-above view cannot be drawn: tried, failed). The face IP-Adapter carries the picked generated face to every
angle and an OpenPose ControlNet (skeletons from app/services/visuals/geometry.py) fixes each pose. No real person's photo is used as a face reference. Both characters are fully clothed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("HF_HOME", str(ROOT / "models" / "image"))
OUT = ROOT / "docs" / "operations" / "phase28-characters"
CAND = ROOT / "data" / "tmp" / "character-sheets"
REALVIS = ROOT / "models/image/hub/models--SG161222--RealVisXL_V5.0/snapshots"

STYLE = "editorial photo, {bg} studio background, soft light, crisp sharp focus, high resolution"
NEG_COMMON = ("blurry, low resolution, cartoon, anime, 3d render, ugly, deformed, extra fingers, extra person, "
              "glasses, jewelry, text, watermark, nude, bikini, swimsuit, cleavage, low cut, patterned clothes")

# face reference = a crop of the picked generated image (fractions: left, top, right, bottom)
CHARACTERS = {
    "woman": {
        "name": "Lan",
        "ref": ROOT / "data/tmp/style-realvis/presenter_E1_bright_s21.png",
        "crop": (0.26, 0.10, 0.76, 0.62),
        "bg": "white",
        "shoulder": 0.80, "hip": 0.55, "full_sh": 0.85, "full_hip": 0.40, "neck_y": 0.65, "sh_y": 0.95, "bust": 1.0, "full": (0.07, 0.11),
        "identity": "voluptuous busty young Vietnamese woman, very long straight black hair, fair skin",
        "outfit": "tight white blouse stretched across the chest, slim white trousers, white shoes",
        "negative": "black clothes, colorful clothes, short hair, tan skin, grey clothes, wide hips, flared trousers, small bust, flat chest",
        "body": "large full bust, curvy hourglass, tiny waist, narrow hips",
        "summary": ("Lan, a young Vietnamese woman. 160 cm, 50 kg, a slender hourglass figure with a narrow waist "
                    "and gently rounded hips, upright posture. Very long straight black hair with side bangs, fair "
                    "luminous skin, a soft delicate face with large dark eyes. All-white outfit."),
    },
    "man": {
        "name": "Minh",
        "ref": ROOT / "data/tmp/style-realvis-male2/N3_soft_s42.png",
        "crop": (0.10, 0.02, 0.72, 0.64),
        "bg": "white",
        "shoulder": 0.97, "hip": 0.50, "full_sh": 1.05, "full_hip": 0.42, "neck_y": 0.85, "sh_y": 1.25, "full": (0.08, 0.103),
        "identity": "handsome young Vietnamese man, fair skin, tousled black hair, long fringe",
        "outfit": "fitted short-sleeve black shirt, black trousers, black shoes",
        "negative": "white clothes, colorful clothes, shirtless, bare back, crop top, torn clothes, beard, grey clothes, rolled sleeves, hunched shoulders",
        "body": "long neck, sloped broad shoulders, slim waist, lean muscular",
        "summary": ("Minh, a young Vietnamese man. 180 cm, 80 kg, a lean muscular athletic build: broad shoulders, "
                    "defined chest and arms, a narrow waist, a V-shaped torso. Fair clear skin, a refined slim "
                    "face with straight eyebrows and almond eyes, tousled black hair with a long side-swept "
                    "fringe. All-black outfit."),
    },
}

# panel -> (size, ip_scale, view words, detailed description of the view); POSE gives the ControlNet scale
POSE_SCALE = {"full_front": 0.85, "full_back": 0.85, "face_front": 0.6, "face_profile": 1.0,
              "face_three_quarter": 1.0, "face_smile": 0.6}
PANELS = {
    "full_front": ((832, 1216), 0.55, "full body, standing straight facing camera, arms at sides",
                   "Full-body front view, standing upright, feet together, arms relaxed at the sides, facing the "
                   "camera with a calm neutral expression; the whole body from head to shoes is visible."),
    "full_back": ((832, 1216), 0.0, "full body from behind, back view, standing straight",
                  "Full-body back view, standing upright with the back to the camera; the hair, the back of the "
                  "garments and the shoes are visible."),
    "face_front": ((1024, 1024), 0.65, "close-up face portrait, facing the camera, calm neutral expression",
                   "Close-up of the face and shoulders from the front, calm neutral expression, eyes looking "
                   "straight at the camera, hair framing the face."),
    "face_profile": ((1024, 1024), 0.2, "close-up side profile portrait, face turned 90 degrees to the right",
                     "Close-up of the head in a strict side profile facing right: forehead, nose bridge, lips, "
                     "chin line and jaw, and the ear are visible."),
    "face_three_quarter": ((1024, 1024), 0.2, "close-up three-quarter view portrait, face turned 45 degrees",
                           "Close-up of the face turned about 45 degrees, both eyes visible, the far cheek "
                           "partly hidden by the nose line, a soft natural expression."),
    "face_smile": ((1024, 1024), 0.5, "close-up face portrait, facing the camera, big happy smile, teeth visible",
                   "Close-up of the face and shoulders from the front with a warm natural smile, teeth slightly "
                   "visible, eyes engaged, hair framing the face; the talking-video expression."),
}
FULL = ("full_front", "full_back")


def prompt_for(char: dict, panel: str) -> tuple[str, str]:
    _, _, view, _ = PANELS[panel]
    style = STYLE.format(bg=char["bg"])
    if panel in FULL:  # the outfit leads (right after the person) so its colour wins over the background
        return (f"{style}, {char['identity']}, {char['outfit']}, {view}, {char['body']}",
                f"{NEG_COMMON}, {char['negative']}")
    return f"{style}, {char['identity']}, {char['outfit'].split(',')[0]}, {view}", f"{NEG_COMMON}, {char['negative']}"


def _geometry():
    import importlib.util
    spec = importlib.util.spec_from_file_location("geometry", ROOT / "app/services/visuals/geometry.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_FACE = ("nose", "r_eye", "l_eye", "r_ear", "l_ear")
_LOWER = ("r_elbow", "r_wrist", "l_elbow", "l_wrist", "r_hip", "l_hip", "r_knee", "l_knee", "r_ankle", "l_ankle")


def pose_map(char: dict, panel: str):
    """The OpenPose skeleton image of a panel (black canvas = no pose control)."""
    from PIL import Image
    geo = _geometry()
    size = PANELS[panel][0]
    sh, hip = char["shoulder"], char["hip"]
    body = {"r_shoulder": (-sh, 0.72), "l_shoulder": (sh, 0.72), "r_hip": (-hip, 3.0), "l_hip": (hip, 3.0)}
    keys = geo._KEYS
    if panel in ("full_front", "full_back"):
        fs, fh = char["full_sh"], char["full_hip"]  # shoulders sit ~0.95 below the nose (not a shrug)
        ny, sy = char["neck_y"], char["sh_y"]
        drop = sy - 0.95  # every joint below the shoulders moves down with them
        arms = {"neck": (0.0, ny), "r_shoulder": (-fs, sy), "l_shoulder": (fs, sy),
                "r_hip": (-fh, 3.3 + drop), "l_hip": (fh, 3.3 + drop),
                "r_elbow": (-fs - 0.15, 2.2 + drop), "r_wrist": (-fs - 0.25, 3.4 + drop),
                "l_elbow": (fs + 0.15, 2.2 + drop), "l_wrist": (fs + 0.25, 3.4 + drop)}
        legs = {"r_knee": (-fh, 4.9 + drop), "l_knee": (fh, 4.9 + drop),
                "r_ankle": (-fh - 0.05, 6.5 + drop), "l_ankle": (fh + 0.05, 6.5 + drop)}
        points = geo.person_pose(size, 0.5, char["full"][0], char["full"][1], "front", arms, legs)
        if panel == "full_back":
            points = [None if key in _FACE else pt for key, pt in zip(keys, points, strict=True)]
        return geo.draw_pose_pixels(points, size)
    head_h = 0.6  # close-ups: the head is about a third of the frame width
    points = geo.person_pose(size, 0.5, 0.40, head_h, "front", body)
    unit = head_h * size[1]
    cx, ny = 0.5 * size[0], 0.40 * size[1]
    face = {  # panel -> face points as (x, y) offsets in head units, None = hidden (a true side view)
        "face_profile": {"nose": (0.5, 0), "l_eye": (0.28, -0.12), "r_eye": None,
                         "l_ear": (-0.1, -0.05), "r_ear": None},
        "face_three_quarter": {"nose": (0.25, 0), "r_eye": (0.02, -0.12), "l_eye": (0.34, -0.12),
                               "l_ear": (-0.12, -0.05), "r_ear": None},
    }.get(panel)
    out = []
    for key, pt in zip(keys, points, strict=True):
        if key in _LOWER:
            out.append(None)
        elif face and key in face:
            out.append(None if face[key] is None else (cx + face[key][0] * unit, ny + face[key][1] * unit))
        else:
            out.append(pt)
    return geo.draw_pose_pixels(out, size)


DEPTH_SCALE = {"full_front": 0.9}  # panels that get the torso depth control (the others use a black map, scale 0)


def depth_map(char: dict, panel: str):
    """A smooth grey-scale depth map of a clothed torso (white = near): chest with two raised bust forms, a
    narrow waist, narrow hips. Only characters with a "bust" size get one; the others get black (no control)."""
    from PIL import Image, ImageDraw, ImageFilter
    size = PANELS[panel][0]
    canvas = Image.new("L", size, 0)
    if "bust" not in char or panel not in DEPTH_SCALE:
        return canvas
    width, height = size
    nose_y, head_h = char["full"]
    u = head_h * height
    cx, ny = width / 2, nose_y * height
    sy = ny + char["sh_y"] * u
    hip_y = ny + (3.3 + char["sh_y"] - 0.95) * u
    bust_y = sy + 0.9 * u
    waist_y = hip_y - 0.8 * u
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((cx - 0.38 * u, ny - 0.55 * u, cx + 0.38 * u, ny + 0.45 * u), fill=175)          # head
    draw.rectangle((cx - 0.2 * u, ny + 0.3 * u, cx + 0.2 * u, sy), fill=150)                       # neck
    torso = [(cx - 1.0 * u, sy), (cx - 0.92 * u, bust_y), (cx - 0.52 * u, waist_y),
             (cx - 0.78 * u, hip_y + 0.2 * u), (cx + 0.78 * u, hip_y + 0.2 * u), (cx + 0.52 * u, waist_y),
             (cx + 0.92 * u, bust_y), (cx + 1.0 * u, sy)]
    draw.polygon(torso, fill=160)
    for side in (-1, 1):                                                                            # arms, legs
        draw.line([(cx + side * 1.0 * u, sy), (cx + side * 1.15 * u, sy + 1.25 * u),
                   (cx + side * 1.25 * u, sy + 2.45 * u)], fill=140, width=round(0.33 * u), joint="curve")
        draw.line([(cx + side * 0.4 * u, hip_y), (cx + side * 0.4 * u, ny + 4.9 * u),
                   (cx + side * 0.45 * u, ny + 6.5 * u)], fill=150, width=round(0.42 * u), joint="curve")
    r = 0.42 * u * char["bust"]
    for side in (-1, 1):                                                                            # the bust forms
        x = cx + side * 0.42 * u
        draw.ellipse((x - r, bust_y - r, x + r, bust_y + r), fill=215)
    return canvas.filter(ImageFilter.GaussianBlur(0.07 * u))


def tokens_only() -> int:
    from transformers import CLIPTokenizer
    tok = CLIPTokenizer.from_pretrained(next(REALVIS.iterdir()), subfolder="tokenizer")
    worst = 0
    for key, char in CHARACTERS.items():
        for panel in PANELS:
            prompt, negative = prompt_for(char, panel)
            counts = (len(tok(prompt, truncation=False).input_ids), len(tok(negative, truncation=False).input_ids))
            worst = max(worst, *counts)
            flag = "  <-- TOO LONG" if max(counts) > 77 else ""
            print(f"{key:6s} {panel:19s} prompt {counts[0]:3d} negative {counts[1]:3d}{flag}")
    return 1 if worst > 77 else 0


def build(control: str = "pose"):
    """One ControlNet at a time ("pose" or "depth"): two together overflowed the 12 GB card (19 minutes an image)."""
    import torch
    from diffusers import (AutoencoderKL, ControlNetModel, EulerAncestralDiscreteScheduler,
                           StableDiffusionXLControlNetPipeline)
    from huggingface_hub import snapshot_download

    vae = AutoencoderKL.from_pretrained(snapshot_download("madebyollin/sdxl-vae-fp16-fix",
                                        allow_patterns=["config.json", "diffusion_pytorch_model.safetensors"]),
                                        torch_dtype=torch.float16)
    repo = {"pose": "xinsir/controlnet-openpose-sdxl-1.0", "depth": "xinsir/controlnet-depth-sdxl-1.0"}[control]
    controlnet = ControlNetModel.from_pretrained(repo, torch_dtype=torch.float16)
    pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
        next(REALVIS.iterdir()), vae=vae, controlnet=controlnet, torch_dtype=torch.float16, variant="fp16",
        use_safetensors=True, add_watermarker=False)
    pipe.load_ip_adapter("h94/IP-Adapter", subfolder="sdxl_models",
                         weight_name="ip-adapter-plus-face_sdxl_vit-h.safetensors",
                         image_encoder_folder="models/image_encoder")
    pipe.enable_model_cpu_offload()  # UNet + ControlNet + IP encoder do not fit the 12 GB card together
    pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
    pipe.vae.enable_tiling()
    pipe.set_progress_bar_config(disable=True)
    return pipe


def face_crop(char: dict, key: str):
    from PIL import Image
    image = Image.open(char["ref"]).convert("RGB")
    w, h = image.size
    left, top, right, bottom = char["crop"]
    crop = image.crop((round(left * w), round(top * h), round(right * w), round(bottom * h)))
    OUT.mkdir(parents=True, exist_ok=True)
    crop.save(OUT / f"ref_face_{key}.png")
    return crop


def generate(seeds: list[int], only: list[str], panels: list[str]) -> int:
    import torch
    CAND.mkdir(parents=True, exist_ok=True)
    pipes: dict = {}

    def pipe_for(mode: str):
        import gc
        if mode not in pipes:
            pipes.clear()
            gc.collect()
            torch.cuda.empty_cache()
            pipes[mode] = build(mode)
        return pipes[mode]

    log = []
    for key, char in CHARACTERS.items():
        if only and key not in only:
            continue
        ref = face_crop(char, key)
        for panel, ((width, height), scale, _, _) in PANELS.items():
            if panels and panel not in panels:
                continue
            prompt, negative = prompt_for(char, panel)
            depth = depth_map(char, panel)
            use_depth = bool(depth.getbbox())  # the depth map holds the silhouette (and the bust), so it replaces the skeleton
            pipe = pipe_for("depth" if use_depth else "pose")
            pipe.set_ip_adapter_scale(scale)
            for seed in seeds:
                started = time.monotonic()
                if use_depth:
                    control, control_scale = depth.convert("RGB"), DEPTH_SCALE[panel]
                    control.save(CAND / f"depth_{key}_{panel}.png")
                else:
                    control, control_scale = pose_map(char, panel), POSE_SCALE[panel]
                    control.save(CAND / f"pose_{key}_{panel}.png")
                image = pipe(prompt=prompt, negative_prompt=negative, ip_adapter_image=ref, image=control,
                             controlnet_conditioning_scale=control_scale, width=width,
                             height=height, num_inference_steps=35, guidance_scale=6.5,
                             generator=torch.Generator("cpu").manual_seed(seed)).images[0]
                image.save(CAND / f"{key}_{panel}_s{seed}.png")
                log.append({"character": key, "panel": panel, "seed": seed, "ip_scale": scale,
                            "sec": round(time.monotonic() - started, 1)})
                print(json.dumps(log[-1]), flush=True)
    print("done", flush=True)
    return 0


def contact(seeds: list[int]) -> None:
    from PIL import Image, ImageDraw
    for key in CHARACTERS:
        for panel, ((width, height), *_rest) in PANELS.items():
            files = [CAND / f"{key}_{panel}_s{s}.png" for s in seeds if (CAND / f"{key}_{panel}_s{s}.png").exists()]
            if not files:
                continue
            tile_h = 420
            tiles = [Image.open(f).resize((round(tile_h * width / height), tile_h)) for f in files]
            sheet = Image.new("RGB", (sum(t.width for t in tiles), tile_h + 22), "white")
            x = 0
            for tile, seed in zip(tiles, seeds):
                sheet.paste(tile, (x, 22))
                ImageDraw.Draw(sheet).text((x + 6, 5), f"{key} {panel} seed {seed}", fill="black")
                x += tile.width
            sheet.save(CAND / f"cand_{key}_{panel}.png")


def compose(picks: dict) -> None:
    """The sample layout: two tall panels on the left, a 2 x 2 block of squares on the right."""
    from PIL import Image, ImageDraw
    OUT.mkdir(parents=True, exist_ok=True)
    lines = ["# Phase 28 character reference sheets: detailed prompts per view\n",
             "Generated with RealVisXL V5.0 (35 steps, CFG 6.5, Euler-a) and the face IP-Adapter "
             "(`ip-adapter-plus-face_sdxl_vit-h`). The face reference is the generated face the owner picked, "
             "never a photo of a real person. Both characters are fully clothed.\n"]
    for key, char in CHARACTERS.items():
        seed = lambda panel: picks.get(key, {}).get(panel, 7)  # noqa: E731
        tall = [Image.open(CAND / f"{key}_{p}_s{seed(p)}.png") for p in FULL]
        squares = [Image.open(CAND / f"{key}_{p}_s{seed(p)}.png").resize((608, 608))
                   for p in ("face_front", "face_profile", "face_three_quarter", "face_smile")]
        sheet = Image.new("RGB", (832 * 2 + 608 * 2, 1216), "white")
        sheet.paste(tall[0], (0, 0))
        sheet.paste(tall[1], (832, 0))
        for i, tile in enumerate(squares):
            sheet.paste(tile, (832 * 2 + (i % 2) * 608, (i // 2) * 608))
        draw = ImageDraw.Draw(sheet)
        for text, xy in (("front", (8, 6)), ("back", (840, 6)), ("face front", (1672, 6)),
                         ("profile", (2280, 6)), ("three-quarter", (1672, 614)), ("smile", (2280, 614))):
            draw.text(xy, text, fill="black")
        sheet.save(OUT / f"{key}_sheet.png")
        sheet.resize((2000, round(2000 * 1216 / sheet.width))).save(OUT / f"{key}_sheet_2000.png")
        for panel in PANELS:
            Image.open(CAND / f"{key}_{panel}_s{seed(panel)}.png").save(OUT / f"{key}_{panel}.png")
        lines += [f"\n## {char['name']} ({key})\n", f"{char['summary']}\n"]
        for panel, (_, scale, _, detail) in PANELS.items():
            prompt, negative = prompt_for(char, panel)
            lines += [f"\n### {panel} (seed {seed(panel)}, face reference strength {scale})\n",
                      f"**Detailed description:** {detail} {char['summary']}\n",
                      f"**Generation prompt:** `{prompt}`\n", f"**Negative prompt:** `{negative}`\n"]
    (OUT / "prompts.md").write_text("\n".join(lines), encoding="utf-8")
    print("composed", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tokens-only", action="store_true")
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--compose", action="store_true")
    parser.add_argument("--contact", action="store_true")
    parser.add_argument("--seeds", type=int, nargs="+", default=[7, 21])
    parser.add_argument("--only", nargs="*", default=[])
    parser.add_argument("--panels", nargs="*", default=[])
    parser.add_argument("--picks", default=str(OUT / "picks.json"), help="JSON {character: {panel: seed}}")
    args = parser.parse_args()
    if args.tokens_only:
        return tokens_only()
    if args.generate:
        return generate(args.seeds, args.only, args.panels)
    if args.contact:
        contact(args.seeds)
        return 0
    if args.compose:
        picks_path = Path(args.picks)
        compose(json.loads(picks_path.read_text(encoding="utf-8")) if picks_path.exists() else {})
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
