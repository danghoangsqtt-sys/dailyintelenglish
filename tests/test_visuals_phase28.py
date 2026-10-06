"""Phase 28 (Task 28.3): the semi-realistic look in the app -- single-colour outfits, the editorial recipes,
RealVisXL in the worker request and the photographic white/black colour rules."""

from __future__ import annotations

import importlib.util
from contextlib import asynccontextmanager
from pathlib import Path

import pytest

from app.core.config import settings
from app.models.visuals import CharacterInput
from app.services.visuals import colour_check, engine, recipes

ROOT = Path(__file__).resolve().parent.parent

LAN = {
    "gender": "female", "age_group": "young", "ethnicity": "Vietnamese", "role": "English teacher",
    "hair": "long straight black hair", "eyes": "dark eyes",  # the form allows 4 hair words at most
    "top_color": "white", "top_item": "blouse", "bottom_color": "white", "bottom_item": "trousers",
}
MINH = {
    "gender": "male", "age_group": "young", "ethnicity": "Vietnamese", "role": "English teacher",
    "hair": "tousled black hair", "eyes": "dark eyes",
    "top_color": "black", "top_item": "slim-fit shirt", "bottom_color": "black", "bottom_item": "slim trousers",
}
TWO_COLOURS = {**LAN, "top_color": "light blue", "bottom_color": "navy blue", "top_item": "slim-fit shirt",
               "bottom_item": "slim trousers"}


def test_outfit_phrase_names_a_single_colour_once():
    assert recipes.outfit_phrase(LAN) == "plain white blouse and trousers"
    assert recipes.outfit_phrase(MINH) == "plain black slim-fit shirt and slim trousers"
    assert recipes.outfit_phrase(TWO_COLOURS) == "plain light blue slim-fit shirt, plain navy blue slim trousers"
    for character in (LAN, MINH, TWO_COLOURS):
        phrase = recipes.outfit_phrase(character)
        assert phrase in recipes.character_phrase(character)
        assert phrase in recipes.compact_phrase(character)
        assert recipes.garment_refine_prompt(character, {"place": "a cafe"}).startswith(
            recipes.STYLE_EDITORIAL + ", " + phrase)


def test_character_with_one_colour_is_accepted_and_a_bad_colour_is_not():
    fields = {"name": "Lan", **LAN}
    assert CharacterInput(**fields).top_color == CharacterInput(**fields).bottom_color == "white"
    with pytest.raises(ValueError, match="solid colours"):
        CharacterInput(**{**fields, "bottom_color": "plaid"})


def test_style_is_editorial_and_the_negatives_guard_a_photograph():
    assert "photograph" in recipes.STYLE_EDITORIAL and "sharp focus" in recipes.STYLE_EDITORIAL
    for word in ("cel", "anime", "ink", "watercolor", "pastel"):
        assert word not in recipes.STYLE_EDITORIAL
    for word in ("blurry", "bokeh", "cartoon", "3d render"):
        assert word in recipes.NEGATIVE and word in recipes.PLATE_NEGATIVE
    assert "watercolor" not in recipes.NEGATIVE and "pastel" not in recipes.NEGATIVE
    assert "person" in recipes.PLATE_NEGATIVE  # the plate must stay empty


def _real_tokenizer():
    from huggingface_hub import snapshot_download  # noqa: F401  (import check only)
    folders = list((ROOT / "models/image/hub/models--SG161222--RealVisXL_V5.0/snapshots").glob("*/tokenizer"))
    if not folders:
        pytest.skip("the RealVisXL tokenizer is not cached")
    from transformers import CLIPTokenizer
    return CLIPTokenizer.from_pretrained(folders[0].parent, subfolder="tokenizer")


def test_new_characters_fit_the_real_clip_budget():
    """The spike counted 77 real tokens as the limit; the app's estimator under-counts by 5-9."""
    tok = _real_tokenizer()
    scene = {"place": "a cozy Vietnamese street cafe", "staging": "seated", "time_of_day": "day"}
    for character in (LAN, MINH):
        prompts = [
            recipes.single_prompt(character, scene), recipes.refine_prompt(character, scene),
            recipes.garment_refine_prompt(character, scene), recipes.candidate_prompt(character),
            *(recipes.sheet_prompt(character, kind) for kind in recipes.SHEET_KINDS),
            *(recipes.duo_prompt(LAN, MINH, scene, kind) for kind in ("duo_close", "duo_wide")),
        ]
        for prompt in prompts:
            assert len(tok(prompt, truncation=False).input_ids) <= 77, prompt
    for negative in (recipes.NEGATIVE, recipes.PLATE_NEGATIVE):
        assert len(tok(negative, truncation=False).input_ids) <= 77


def test_white_and_black_rules_hold_on_measured_photographs():
    """Medians measured (Task 28.3 calibration) on the owner-approved Lan and Minh sheets: no rule change
    was needed, so these values pin the rules."""
    whites = [(3.2, 0.051, 0.859), (16.1, 0.012, 0.906), (18.0, 0.071, 0.816), (5.3, 0.067, 0.855),
              (218.8, 0.027, 0.961)]
    blacks = [(16.4, 0.145, 0.239), (225.1, 0.125, 0.369), (232.9, 0.149, 0.251), (215.3, 0.204, 0.243)]
    for h, s, v in whites:
        hsv = {"h": h, "s": s, "v": v}
        assert colour_check.matches("white", hsv) and not colour_check.matches("black", hsv)
    for h, s, v in blacks:
        hsv = {"h": h, "s": s, "v": v}
        assert colour_check.matches("black", hsv) and not colour_check.matches("white", hsv)


class _StubWorker:
    sent: list[dict] = []

    def __init__(self) -> None:
        pass

    def request(self, payload):
        _StubWorker.sent.append(payload)
        return {"status": "ok"}

    def close(self, kill: bool = False) -> None:
        pass


class _StubGpu:
    @asynccontextmanager
    async def lease(self, *args, **kwargs):
        yield


@pytest.mark.asyncio
@pytest.mark.parametrize("repo, scheduler, expected", [
    ("SG161222/RealVisXL_V5.0", "euler_a", {"base_repo": "SG161222/RealVisXL_V5.0", "scheduler": "euler_a"}),
    ("", "euler_a", {}),
])
async def test_worker_load_request_carries_the_picture_model(monkeypatch, repo, scheduler, expected):
    monkeypatch.setattr(settings, "IMAGE_BASE_REPO", repo)
    monkeypatch.setattr(settings, "IMAGE_SCHEDULER", scheduler)
    monkeypatch.setattr(engine, "require_generation", lambda: None)
    monkeypatch.setattr(engine, "get_gpu_manager", lambda: _StubGpu())
    monkeypatch.setattr(engine, "_WorkerProcess", _StubWorker)
    _StubWorker.sent = []
    async with engine.WorkerImageEngine().session(pipeline="controlnet"):
        pass
    load = _StubWorker.sent[0]
    assert load["command"] == "load" and load["mode"] == "base" and load["pipeline"] == "controlnet"
    for key in ("base_repo", "scheduler"):
        assert (key in load) is (key in expected)
    assert {key: load[key] for key in expected} == expected


def test_settings_default_to_realvisxl_with_euler_a():
    assert settings.IMAGE_BASE_REPO == "SG161222/RealVisXL_V5.0" and settings.IMAGE_SCHEDULER == "euler_a"


def _worker_module():
    spec = importlib.util.spec_from_file_location("image_worker_under_test", ROOT / "scripts" / "image_worker.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_finetune_download_prefers_fp16_and_falls_back(tmp_path, monkeypatch):
    """RealVisXL keeps 10 GB of fp32 shards next to its fp16 files; the app must fetch fp16 only. A fine-tune
    without an fp16 UNet (Animagine style) gets the full patterns."""
    worker = _worker_module()
    import huggingface_hub

    calls: list[list[str]] = []
    made = [0]

    def fake_download(repo, allow_patterns=None, **_):
        calls.append(list(allow_patterns))
        made[0] += 1
        folder = tmp_path / f"snap{made[0]}"
        (folder / "unet").mkdir(parents=True, exist_ok=True)
        if allow_patterns == worker.FINETUNE_FP16_PATTERNS and has_fp16[0]:
            (folder / "unet" / "diffusion_pytorch_model.fp16.safetensors").write_bytes(b"x")
        return str(folder)

    monkeypatch.setattr(huggingface_hub, "snapshot_download", fake_download)
    has_fp16 = [True]
    folder = worker.ImageWorker._resolve_base("base", None, "SG161222/RealVisXL_V5.0")
    assert calls == [worker.FINETUNE_FP16_PATTERNS] and (folder / "unet" / "diffusion_pytorch_model.fp16.safetensors").is_file()
    assert "unet/*" not in worker.FINETUNE_FP16_PATTERNS  # never the fp32 shards

    calls.clear()
    has_fp16[0] = False
    worker.ImageWorker._resolve_base("base", None, "cagliostrolab/animagine-xl-4.0")
    assert calls == [worker.FINETUNE_FP16_PATTERNS, worker.FINETUNE_PATTERNS]
    with pytest.raises(ValueError, match="base"):
        worker.ImageWorker._resolve_base("lightning", None, "SG161222/RealVisXL_V5.0")
