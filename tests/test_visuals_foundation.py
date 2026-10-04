"""Phase 20.3 migration, prompt, geometry, image engine and job guarantees."""

import asyncio

import aiosqlite
import pytest
from PIL import Image, ImageChops

from app.core.config import settings
from app.core.exceptions import GpuUnavailableError
from app.db.database import Database, MIGRATIONS_DIR, init_db
from app.db.transactions import write_transaction
from app.services.visuals import geometry, jobs, recipes
from app.services.visuals.engine import FakeImageEngine, WorkerImageEngine
from app.services.visuals.runner import ImageJobRunner

CHARACTER = {
    "age_group": "middle-aged", "ethnicity": "Vietnamese", "gender": "female",
    "role": "English teacher", "hair": "long wavy black hair", "eyes": "brown eyes",
    "top_color": "light blue", "top_item": "slim-fit shirt",
    "bottom_color": "navy blue", "bottom_item": "slim trousers",
}
SCENE = {"place": "a cozy Vietnamese street cafe", "staging": "seated"}


@pytest.fixture(autouse=True)
def fake_image_engine(monkeypatch):
    monkeypatch.setattr(settings, "IMAGE_ENGINE", "fake")


@pytest.mark.asyncio
@pytest.mark.parametrize("preexisting", [False, True])
async def test_migration_008_and_builtin_seed_once(tmp_path, monkeypatch, preexisting):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    if preexisting:
        connection = await aiosqlite.connect(tmp_path / "app.db")
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if migration.name.startswith("008"):
                break
            await connection.executescript(migration.read_text(encoding="utf-8"))
        await connection.close()
    old = Database._instance
    Database._instance = None
    try:
        await init_db()
        await init_db()
        db = Database.instance().connection
        cursor = await db.execute("SELECT count(*) FROM scenes WHERE is_builtin = 1")
        assert (await cursor.fetchone())[0] == 6
        cursor = await db.execute("SELECT count(*) FROM schema_migrations WHERE filename = '008_ai_visuals.sql'")
        assert (await cursor.fetchone())[0] == 1
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'image_jobs'")
        assert (await cursor.fetchone())[0] == "image_jobs"
    finally:
        await Database.instance().close()
        Database._instance = old


def test_recipe_strings_and_worst_case_budget():
    phrase = (
        "middle-aged Vietnamese woman English teacher, long wavy black hair, brown eyes, "
        "plain light blue slim-fit shirt, plain navy blue slim trousers"
    )
    assert recipes.character_phrase(CHARACTER) == phrase
    assert recipes.candidate_prompt(CHARACTER) == (
        recipes.STYLE_CEL_ANIME + ", " + phrase
        + ", portrait, facing the viewer, arms down, plain light background"
    )
    assert recipes.single_prompt(CHARACTER, SCENE) == (
        recipes.STYLE_CEL_ANIME + ", " + phrase
        + ", close-up, talking with a hand gesture, in a cozy Vietnamese street cafe"
    )
    prompts = [
        recipes.candidate_prompt(CHARACTER), recipes.scene_preview_prompt(SCENE),
        recipes.single_prompt(CHARACTER, SCENE), recipes.refine_prompt(CHARACTER, SCENE),
        recipes.hand_prompt(),
        *(recipes.sheet_prompt(CHARACTER, kind) for kind in recipes.SHEET_KINDS),
        *(recipes.duo_prompt(CHARACTER, CHARACTER, {**SCENE, "staging": staging}, kind)
          for staging in ("standing", "seated") for kind in ("duo_close", "duo_wide")),
    ]
    assert all(recipes.token_count(prompt) <= 75 for prompt in prompts)
    assert recipes.token_count(recipes.single_prompt(CHARACTER, SCENE)) == 74


def test_geometry_heads_halves_ears_hands_and_refine_mask():
    size = (1344, 768)
    single = geometry.shot_people("single", "standing", size)[0]
    assert single["points"][0][1] - 0.78 * 0.30 * size[1] > 0.11 * size[1]
    people = geometry.shot_people("duo_close", "seated", size)
    assert people[0]["points"][17] is None  # far left-person ear
    assert people[1]["points"][16] is None  # far right-person ear
    left, right = geometry.half_masks(size)
    assert left.getpixel((0, 0)) == 255 and left.getpixel((size[0] - 1, 0)) == 0
    assert right.getpixel((0, 0)) == 0 and right.getpixel((size[0] - 1, 0)) == 255
    for person, half in zip(people, (left, right), strict=True):
        mask = geometry.refine_mask(person, size, half)
        assert ImageChops.subtract(mask, half).getbbox() is None
    boxes = geometry.hand_boxes(single["points"], size, single["head_h"])
    assert boxes
    for hand in boxes:
        x0, y0, x1, y1 = hand["box"]
        assert 0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1]
        assert hand["center"][1] >= 0
    base = Image.new("RGB", size, "black")
    hand = boxes[0]
    fixed = Image.new("RGB", (768, 768), "white")
    pasted = geometry.paste_hand(base, fixed, hand["box"], geometry.hand_mask(
        hand["box"][2] - hand["box"][0], hand["center"], hand["radius"]
    ))
    assert ImageChops.difference(base, pasted).getbbox() is not None
    assert ImageChops.difference(base, pasted).getbbox()[0] >= hand["box"][0]


@pytest.mark.asyncio
async def test_fake_engine_and_worker_token_response(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "IMAGE_ENGINE", "fake")
    fake = FakeImageEngine()
    embeds = tmp_path / "embeds.pt"
    async with fake.session(ip="with_encoder") as session:
        encoded = await session.request({
            "command": "encode", "output_path": str(embeds),
            "items": [{"prompt": "small"}, {"prompt": "word " * 80}],
        })
    assert encoded["items"] == 2
    assert encoded["item_tokens"][1]["prompt_truncated"] is True
    async with fake.session(pipeline="controlnet", encoders=False, ip="layers_only") as session:
        rendered = await session.request({
            "command": "generate", "embeds_path": str(embeds), "embeds_index": 1,
            "seed": 7, "width": 32, "height": 24, "output_path": str(tmp_path / "shot.png"),
        })
    assert rendered["prompt_truncated"] is True
    assert Image.open(tmp_path / "shot.png").size == (32, 24)

    class StubWorker:
        def request(self, payload):
            if payload["command"] == "encode":
                return {"status": "ok", "items": 2, "item_tokens": encoded["item_tokens"]}
            return {"status": "ok", "output_path": str(tmp_path / "shot.png")}

    worker = WorkerImageEngine()
    worker._worker = StubWorker()
    await worker.request({"command": "encode", "output_path": str(embeds), "items": [{}, {}]})
    result = await worker.request({"command": "generate", "embeds_path": str(embeds), "embeds_index": 1})
    assert result["prompt_truncated"] is True


@pytest.mark.asyncio
async def test_jobs_fifo_duplicate_cancel_recovery(db):
    async with write_transaction(db):
        first = await jobs.create_job(db, "character_candidates", "one")
        duplicate = await jobs.create_job(db, "character_candidates", "one")
        second = await jobs.create_job(db, "scene_preview", "two")
        claimed = await jobs.claim_next(db)
    assert duplicate["id"] == first["id"]
    assert claimed["id"] == first["id"]
    async with write_transaction(db):
        await jobs.request_cancel(db, second["id"])
        assert (await jobs.get_job(db, second["id"]))["status"] == "cancelled"
        assert await jobs.recover_running(db) == 1
    assert (await jobs.get_job(db, first["id"]))["error"] == "interrupted by app restart"


@pytest.mark.asyncio
async def test_runner_cancels_at_boundary_and_gpu_error(db):
    def monkey_db():
        return db
    runner = ImageJobRunner(monkey_db, poll_seconds=0.01)
    events = []

    async def handler(job, active_runner):
        events.append(job["id"])
        if job["target_id"] == "gpu":
            raise GpuUnavailableError("image", "no_nvidia_gpu")
        async with write_transaction(db):
            await jobs.request_cancel(db, job["id"])
        await active_runner.boundary(job["id"], "next image", 50)

    runner.register_handler("project_shots", handler)
    async with write_transaction(db):
        cancel_job = await jobs.create_job(db, "project_shots", "cancel")
        gpu_job = await jobs.create_job(db, "project_shots", "gpu")
    await runner.start()
    try:
        for _ in range(100):
            await asyncio.sleep(0.01)
            if (await jobs.get_job(db, gpu_job["id"]))["status"] == "error":
                break
        assert (await jobs.get_job(db, cancel_job["id"]))["status"] == "cancelled"
        assert "no_nvidia_gpu" in (await jobs.get_job(db, gpu_job["id"]))["error"]
        assert len(events) == 2
    finally:
        await runner.stop()
