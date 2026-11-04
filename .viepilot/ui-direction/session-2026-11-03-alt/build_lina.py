"""Prototype only: cut Lina's talking-sprite pictures (front set and three-quarter set, same outfit) down to a half-body
frame for the corner mascot. Both views are scaled by the eye-to-chin distance so the head keeps its size when she turns.

Run from the repo root:  .venv\\Scripts\\python .viepilot\\ui-direction\\session-2026-11-03-alt\build_lina.py
Writes lina/{front,side}/<slot>.webp (not committed: they come from the library).
"""
import sqlite3
from pathlib import Path

from PIL import Image

LINA = "e961d07c-da89-4395-beec-7741df69142d"
OUT = Path(__file__).parent / "lina"
SIZE = (680, 760)  # 8.5 x 9.5 eye-to-chin units
# eye midpoint and eye-to-chin distance measured on calm__closed of each set (2026-11-03)
VIEWS = {
    "front": {"eye": (635, 265), "unit": 85, "eye_at": (0.50, 0.32)},
    "side": {"eye": (503, 425), "unit": 140, "eye_at": (0.44, 0.32)},
}
FRONT = ["calm__closed", "calm__open", "blink"] + [f"gesture-{g}{m}" for g in
         ("wave", "point-left", "talk", "think", "emphasize", "count-1", "count-2", "count-3") for m in ("", "__open")]
SIDE = ["blink"] + [f"{e}__{m}" for e in ("calm", "smile", "laugh", "surprised", "thinking", "worried", "serious")
                    for m in ("closed", "open")] + [f"gesture-{g}{m}" for g in
         ("wave", "point", "talk", "think", "open", "heart", "listen") for m in ("", "__open")]


def frame(src: Path, view: dict) -> Image.Image:
    im = Image.open(src).convert("RGBA")
    unit = view["unit"]
    w, h = 8.5 * unit, 9.5 * unit
    left = view["eye"][0] - view["eye_at"][0] * w
    top = view["eye"][1] - view["eye_at"][1] * h
    canvas = Image.new("RGBA", (round(w), round(h)), (0, 0, 0, 0))
    canvas.alpha_composite(im, (round(-left), round(-top)))  # pads with transparency where the crop leaves the picture
    return canvas.resize(SIZE, Image.LANCZOS)


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    db = sqlite3.connect(root / "data" / "app.db")
    front = {k.removeprefix("sprite/"): p for k, p in db.execute(
        "SELECT slot_key, path FROM character_assets WHERE character_id = ? AND is_current = 1 AND facing = 'front'", (LINA,))}
    for view, names, where in (("front", FRONT, lambda n: Path(front[n])),
                               ("side", SIDE, lambda n: root / "data" / "library" / "sprites" / LINA / f"{n}.png")):
        (OUT / view).mkdir(parents=True, exist_ok=True)
        for name in names:
            frame(where(name), VIEWS[view]).save(OUT / view / f"{name}.webp", quality=88, method=6)
        print(view, len(names))


if __name__ == "__main__":
    main()
