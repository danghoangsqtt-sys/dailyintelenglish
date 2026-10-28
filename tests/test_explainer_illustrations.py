"""Phase 85 (owner 2026-10-28): the local Qwen model draws a Solo / VOX plan's photo slots that have no picture."""

from pathlib import Path

from backend.ai.image import pipelines, recipes
from backend.library import activity_library_service, explainer_service


def test_only_empty_unlocked_photo_slots_are_drawn_and_the_prompt_is_face_free():
    plan = {"segments": [
        {"id": "a", "visual": {"kind": "photo", "asset": None, "prompt": "colleagues chatting by a coffee machine"}},
        {"id": "b", "visual": {"kind": "photo", "asset": {"asset_id": "x", "version": 1}}},
        {"id": "c", "visual": {"kind": "photo", "asset": None}, "locks": {"visual": True}},
        {"id": "d", "visual": {"kind": "text_card", "title": "Tips"}},
    ]}
    assert [segment["id"] for segment in pipelines.explainer_photo_slots(plan)] == ["a"]
    prompt = recipes.qwen_illustration_prompt("colleagues chatting by a coffee machine.")
    assert "colleagues chatting by a coffee machine. Ordinary" in prompt and "no famous person" in prompt


async def test_the_job_draws_imports_sets_and_keeps_each_picture(monkeypatch, tmp_path):
    def span(line):
        return {"line_ids": [line], "start": {"line_id": line, "token_index": 0}, "end": {"line_id": line, "token_index": 3}}

    plan = {"revision": 3, "aspects": ["16:9"], "segments": [
        {"id": "idea-1", "intent": "Show small talk", **span("l1"),
         "visual": {"kind": "photo", "asset": None, "prompt": "two colleagues chatting"}},
        {"id": "idea-2", "intent": "Rules", **span("l2"), "visual": {"kind": "text_card", "title": "Rules", "bullets": []}},
    ]}
    saved, kept, approved = {}, [], []

    async def get_plan(db, project_id):
        return {"plan": plan, "current_source_fingerprint": "f" * 64}

    async def import_illustration(db, project_id, content, filename):
        assert content == b"png"
        return {"asset": {"asset_id": "asset-1", "version": 1, "content_hash": "a" * 64}}

    async def save_plan(db, project_id, body):
        saved["body"] = body

    async def upload(db, filename, content, metadata):
        kept.append(metadata)
        return {"id": "lib-1"}

    async def set_review(db, activity_id, state):
        approved.append((activity_id, state))

    class Engine:
        async def qwen_batch(self, model, items, consumer):
            for item in items:
                Path(item["output_path"]).write_bytes(b"png")

    class Runner:
        def get_db(self):
            return object()

        async def boundary(self, *args):
            return None

    monkeypatch.setattr(explainer_service, "get_plan", get_plan)
    monkeypatch.setattr(explainer_service, "import_illustration", import_illustration)
    monkeypatch.setattr(explainer_service, "save_plan", save_plan)
    monkeypatch.setattr(activity_library_service, "upload_activity_bytes", upload)
    monkeypatch.setattr(activity_library_service, "set_review", set_review)
    monkeypatch.setattr(pipelines, "get_image_engine", lambda: Engine())
    monkeypatch.setattr(pipelines.settings, "DATA_DIR", tmp_path)

    class NoLock:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(pipelines, "write_transaction", lambda db: NoLock())
    result = await pipelines.explainer_illustrations({"id": "j", "target_id": "p1"}, Runner())
    assert result == {"drawn": ["idea-1"]}
    body = saved["body"]
    assert body.expected_revision == 3 and body.segments[0].visual.asset.asset_id == "asset-1"
    assert body.segments[1].visual.kind == "text_card"
    assert kept == [{"activity": "two colleagues chatting", "context_tags": ["qwen"]}] and approved == [("lib-1", "approved")]
    assert not any((tmp_path / "visuals" / "p1" / "explainer_drafts").iterdir())  # drafts removed
