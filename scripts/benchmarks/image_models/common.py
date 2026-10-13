"""Phase 39 benchmark: shared prompt building and result records (stdlib only, used from `.venv` and `.venv-qwen`)."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.ai.image import recipes  # noqa: E402  (pure module: re + Mapping only)

HERE = Path(__file__).resolve().parent
OUT = ROOT / "data" / "tmp" / "phase39-bench"
THUMB_NEGATIVE = "blurry, low resolution, cartoon, anime, 3d render, watermark, deformed, bad anatomy, misspelled text"


def bench_set() -> dict:
    return json.loads((HERE / "bench_set.json").read_text(encoding="utf-8"))


def sdxl_prompt(item: dict, character: dict | None = None) -> tuple[str, str]:
    """The app's own RealVisXL recipes (D110: a few ordinary people for activity pictures)."""
    task = item["task"]
    if task == "activity":
        prompt = recipes._styled(item["people"], item["action"], f"in {item['place']}", "wide view, the action clearly visible")
        return prompt, recipes.ACTIVITY_NEGATIVE
    if task == "plate":
        return recipes.scene_preview_prompt(item), recipes.PLATE_NEGATIVE
    if task == "thumbnail":
        return recipes._styled(item["subject"], f'the sign says "{item["text"]}"', "centered, vivid colours"), THUMB_NEGATIVE
    if task == "character":
        return recipes.insert_person_prompt(character, item["action"]), recipes.negative_for(character)
    raise ValueError(task)


def qwen_prompt(item: dict, character: dict | None = None) -> str:
    """Natural-language prompts, the form the Qwen models are trained on (same subjects as `sdxl_prompt`)."""
    task = item["task"]
    if task == "activity":
        return (f"A photorealistic editorial photograph of {item['people']} {item['action']} in {item['place']}. "
                "A natural candid everyday moment, the action clearly visible in the middle of the frame, realistic faces "
                "and hands, ordinary casual clothes, soft natural light, crisp sharp focus. No text, no logo.")
    if task == "plate":
        light = recipes.TIME_OF_DAY_LIGHT.get(item.get("time_of_day", "day"), "")
        return (f"A photorealistic wide photograph of {item['place']}{', ' + light if light else ''}. The place is completely "
                "empty, with no people at all. Realistic details, soft natural light, crisp sharp focus. No text.")
    if task == "thumbnail":
        return (f"A photorealistic editorial photograph of {item['subject']}. The sign clearly reads \"{item['text']}\" in "
                "bold clean letters, spelled exactly. Vivid colours, centered composition, soft natural light, crisp focus.")
    if task == "character":
        noun = "woman" if character["gender"] == "female" else "man"
        return (f"Photorealistic editorial photograph, medium shot: the same {noun} as in the reference picture, with the same "
                f"face and hair, wearing {recipes.outfit_phrase(character)}, {item['action']}. Natural pose, soft natural "
                "light, crisp sharp focus, realistic hands.")
    raise ValueError(task)


class VramPeak:
    """Peak GPU memory used (MiB) while a block runs, sampled from nvidia-smi every 0.5 s (any process)."""

    def __enter__(self) -> "VramPeak":
        self.peak, self._stop = 0, threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                                     capture_output=True, text=True, timeout=5).stdout
                self.peak = max(self.peak, int(out.split()[0]))
            except Exception:  # noqa: BLE001 -- sampling is best-effort
                pass
            self._stop.wait(0.5)

    def __exit__(self, *exc) -> None:
        self._stop.set()
        self._thread.join(timeout=2)


def record(engine: str, row: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "results.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"engine": engine, "at": time.strftime("%Y-%m-%d %H:%M:%S"), **row}) + "\n")
    print(json.dumps({"engine": engine, **row}), flush=True)
