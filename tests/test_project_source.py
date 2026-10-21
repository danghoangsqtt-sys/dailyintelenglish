"""Phase 57 (ENH-039): a project made from the owner's material, AI topic ideas and reading a photographed text."""

from __future__ import annotations

import asyncio
import io
import json

import httpx
import pytest
from PIL import Image

from backend.ai.llm.contracts import GenerationRequest, GenerationResult
from backend.ai.llm.ollama_provider import OllamaProvider
from backend.ai.llm.openai_compat_provider import OpenAICompatProvider
from backend.content import script_pipeline, source_service
from backend.core.exceptions import ProviderRequestRejectedError, ValidationError
from tests.test_channel_api import failed
from tests.test_visuals_project_api import PROJECT, client, data  # noqa: F401

SPEAKERS = [{"id": "s1", "name": "Lina"}, {"id": "s2", "name": "Alex"}]


class ScriptedRouter:
    """Answers every request with the given text and remembers the requests."""

    def __init__(self, text: str | Exception):
        self.text = text
        self.requests: list[GenerationRequest] = []

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        self.requests.append(request)
        if isinstance(self.text, Exception):
            raise self.text
        return GenerationResult(text=self.text, provider="fake", model="fake", latency_ms=1, prompt_hash="x", attempt=1)


# ---------------------------------------------------------------------------- parsing


def test_a_dialogue_is_split_into_turns_for_the_two_characters():
    lines = source_service.parse_dialogue("A: Hi there!\nB: Hello.\n  How are you?\n\nA: Fine, thanks.", SPEAKERS)
    assert lines == [{"speaker_id": "s1", "text": "Hi there!"}, {"speaker_id": "s2", "text": "Hello. How are you?"},
                     {"speaker_id": "s1", "text": "Fine, thanks."}]
    named = source_service.parse_dialogue("Alex: Ready?\nLina: Yes!", SPEAKERS)
    assert [line["speaker_id"] for line in named] == ["s2", "s1"]  # a character's own name keeps that character


@pytest.mark.parametrize("text,message", [
    ("A: one\nB: two\nC: three", "more speakers"),
    ("no label here\nA: hi", "speaker label"),
    ("   \n ", "empty"),
])
def test_an_unusable_dialogue_says_why(text, message):
    with pytest.raises(ValidationError, match=message):
        source_service.parse_dialogue(text, SPEAKERS)


def test_a_vocabulary_list_keeps_only_the_words():
    words = source_service.parse_vocabulary("1. invoice - hoá đơn\nbalance sheet: bảng cân đối\n• audit, Invoice; cash flow")
    assert words == ["invoice", "balance sheet", "audit", "cash flow"]
    with pytest.raises(ValidationError):
        source_service.parse_vocabulary(", ,\n")


def test_missing_vocabulary_is_found_as_whole_words():
    texts = ["We checked the invoice.", "Cash-flow matters? Yes, the cash flow does."]
    assert script_pipeline.missing_vocabulary(["invoice", "cash flow", "audit", "voice"], texts) == ["audit", "voice"]
    _errors, warnings = script_pipeline.validate_global([], 10, set(), 2, "topic", ["audit"])
    assert warnings == []  # no lines: the early return


# ---------------------------------------------------------------------------- projects


def _project(**extra) -> dict:
    return {**PROJECT, **extra}


def test_a_word_for_word_dialogue_is_the_script_at_once(client):  # noqa: F811
    created = data(client.post("/api/projects", json=_project(
        source_kind="dialogue", source_use="verbatim", source_text="A: Shall we order?\nB: Yes, two coffees please.")))
    assert (created["source_kind"], created["source_use"], created["status"]) == ("dialogue", "verbatim", "script_generated")
    script = data(client.get(f"/api/projects/{created['id']}/script"))
    speakers = [speaker["id"] for speaker in created["speakers"]]
    assert [(line["speaker_id"], line["text"]) for line in script] == [
        (speakers[0], "Shall we order?"), (speakers[1], "Yes, two coffees please.")]
    progress = data(client.get(f"/api/projects/{created['id']}/progress"))
    assert progress["steps"][1]["done"] and progress["missing_vocabulary"] == []


def test_material_is_validated_and_stored(client):  # noqa: F811
    assert "more speakers" in failed(client.post("/api/projects", json=_project(
        source_kind="dialogue", source_use="verbatim", source_text="A: x\nB: y\nC: z")))
    assert "word for word" in failed(client.post("/api/projects", json=_project(
        source_kind="vocabulary", source_use="verbatim", source_text="invoice")))
    assert "paste the dialogue" in failed(client.post("/api/projects", json=_project(source_kind="dialogue", source_text=" ")))
    stored = data(client.post("/api/projects", json=_project(source_kind="vocabulary", source_text="invoice\naudit")))
    assert (stored["source_kind"], stored["source_text"], stored["status"]) == ("vocabulary", "invoice\naudit", "draft")
    plain = data(client.post("/api/projects", json=_project(source_text="ignored without a kind")))
    assert (plain["source_kind"], plain["source_text"], plain["source_use"]) == ("", "", "rewrite")


def test_the_step_bar_lists_vocabulary_the_script_does_not_use(client):  # noqa: F811
    created = data(client.post("/api/projects", json=_project(source_kind="vocabulary", source_text="invoice\naudit")))
    speaker = created["speakers"][0]["id"]
    data(client.put(f"/api/projects/{created['id']}/script", json={"lines": [{"speaker_id": speaker, "text": "Send the invoice."}]}))
    assert data(client.get(f"/api/projects/{created['id']}/progress"))["missing_vocabulary"] == ["audit"]


# ---------------------------------------------------------------------------- prompts


def _render(template: str, project: dict) -> str:
    context = dict(topic="Cafe talk", genre="small_talk", cefr_level="B1", duration_minutes=5, num_speakers=2,
                   accent="american", speakers=[{**s, "gender": "female", "accent": "american"} for s in SPEAKERS],
                   target_words=500, num_sections=3, genre_instructions="", cefr_constraints="",
                   presentation_mode="classic", outline_title="T", section_index=1, section_count=3, objective="o",
                   min_words=1, max_words=2, prior_summary="", is_last_section=False, avoid_phrases=[],
                   max_consecutive_lines=3, solo_instructions="", language_features={})
    return asyncio.run(script_pipeline._render(template, **context, **script_pipeline._source_context(project)))


@pytest.mark.parametrize("template", ["outline.txt", "section.txt"])
def test_the_script_prompts_carry_the_material_only_when_there_is_some(template):
    assert "Source Material" not in _render(template, {})
    dialogue = _render(template, {"source_kind": "dialogue", "source_text": "A: Two coffees, please."})
    assert "the Owner's Dialogue" in dialogue and "A: Two coffees, please." in dialogue
    vocabulary = _render(template, {"source_kind": "vocabulary", "source_text": "invoice\naudit"})
    assert "Vocabulary to Teach" in vocabulary and "- invoice" in vocabulary and "- audit" in vocabulary


# ---------------------------------------------------------------------------- AI help


def test_topic_ideas_come_back_as_six_cards(client, monkeypatch):  # noqa: F811
    ideas = [{"name": f"Idea {n}", "topic": f"Topic {n}", "description": "d"} for n in range(8)]
    router = ScriptedRouter(json.dumps({"ideas": ideas}))
    monkeypatch.setattr(source_service, "build_ai_router_from_settings", lambda: router)
    result = data(client.post("/api/projects/topic-ideas", json={
        "presentation_mode": "solo_explainer", "cefr_level": "A2", "hint": "coffee machines"}))
    assert [idea["name"] for idea in result["ideas"]] == [f"Idea {n}" for n in range(6)]
    prompt = router.requests[0].prompt
    assert "coffee machines" in prompt and "Solo presentation" in prompt and "CEFR A2" in prompt and '"ideas"' in prompt
    router.text = "not json"
    assert "not usable" in failed(client.post("/api/projects/topic-ideas", json={}))


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (2400, 1200), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_a_photo_is_read_by_the_ai_and_returned_for_editing(client, monkeypatch):  # noqa: F811
    from backend.core.config import settings

    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", True)  # the tests run with cloud AI off
    router = ScriptedRouter(json.dumps({"text": "A: Hello\nB: Hi"}))
    monkeypatch.setattr(source_service, "build_ai_router_from_settings", lambda: router)
    result = data(client.post("/api/projects/read-image", data={"kind": "dialogue"},
                              files={"file": ("page.png", _png(), "image/png")}))
    assert result["text"] == "A: Hello\nB: Hi"
    image = router.requests[0].images[0]
    assert image.startswith("data:image/jpeg;base64,")
    assert "Name: words" in router.requests[0].prompt
    assert "not a picture" in failed(client.post("/api/projects/read-image", files={"file": ("a.txt", b"hello", "text/plain")}))
    router.text = ProviderRequestRejectedError("no vision")
    assert "cloud AI that can see images" in failed(client.post(
        "/api/projects/read-image", data={"kind": "vocabulary"}, files={"file": ("page.png", _png(), "image/png")}))


def test_the_cloud_provider_sends_the_picture_and_the_local_one_refuses(monkeypatch):
    sent = {}

    async def fake_post(self, url, json=None, headers=None):  # noqa: A002
        sent.update(json)
        return httpx.Response(200, json={"choices": [{"message": {"content": "{\"text\": \"x\"}"}}]},
                              request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = OpenAICompatProvider(base_url="https://generativelanguage.googleapis.com/v1beta/openai", api_key="k",
                                    model="gemini-x", vendor="gemini")
    request = GenerationRequest(prompt="read", images=["data:image/jpeg;base64,AAAA"], deadline_seconds=5, purpose="t")
    asyncio.run(provider.generate(request))
    content = sent["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "read"}
    assert content[1] == {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,AAAA"}}
    plain = GenerationRequest(prompt="plain", deadline_seconds=5, purpose="t")
    asyncio.run(provider.generate(plain))
    assert sent["messages"][0]["content"] == "plain"  # text requests are unchanged
    with pytest.raises(ProviderRequestRejectedError):
        asyncio.run(OllamaProvider(base_url="http://127.0.0.1:11434", model="m", num_ctx=2048).generate(request))


# ---------------------------------------------------------------------------- Amendment A (owner spec)


def test_word_for_word_is_checked_and_at_most_four_speakers():
    assert source_service.verify_verbatim("A: Hi, there!\nB: Fine.", [{"text": "Hi there"}, {"text": "fine"}]) == 1.0
    with pytest.raises(ValidationError, match="word for word"):
        source_service.verify_verbatim("A: Hi there, how are you today?", [{"text": "Hello, how are you?"}])
    six = [{"id": f"s{n}", "name": f"P{n}"} for n in range(6)]
    with pytest.raises(ValidationError, match="at most 4"):
        source_service.parse_dialogue("A: 1\nB: 2\nC: 3\nD: 4\nE: 5", six)


def test_vocabulary_items_are_limited_and_matched_with_simple_inflections():
    assert len(source_service.parse_vocabulary("\n".join(f"word{n}" for n in range(80)))) == 80
    with pytest.raises(ValidationError, match="at most 80"):
        source_service.parse_vocabulary("\n".join(f"word{n}" for n in range(81)))
    with pytest.raises(ValidationError, match="too long"):
        source_service.parse_vocabulary("x" * 121)
    texts = ["She delivered two invoices, then studied and stopped. We are following up."]
    assert script_pipeline.missing_vocabulary(
        ["deliver", "invoice", "study", "stop", "follow up", "audit", "voice"], texts) == ["audit", "voice"]


def test_a_solo_project_stores_its_subject_and_its_default_structure(client):  # noqa: F811
    solo = {**PROJECT, "num_speakers": 1, "speakers": PROJECT["speakers"][:1], "presentation_mode": "solo_explainer"}
    howto = data(client.post("/api/projects", json={**solo, "explainer_subject": "howto"}))
    assert (howto["explainer_subject"], howto["explainer_structure"]) == ("howto", "how")
    field = data(client.post("/api/projects", json={**solo, "explainer_subject": "field", "explainer_structure": "why"}))
    assert (field["explainer_subject"], field["explainer_structure"]) == ("field", "why")  # the owner's choice wins
    assert data(client.post("/api/projects", json=solo))["explainer_subject"] == "topic"
    classic = data(client.post("/api/projects", json={**PROJECT, "explainer_subject": "product"}))
    assert classic["explainer_subject"] is None
    copied = data(client.post(f"/api/projects/{howto['id']}/copy-settings"))
    assert copied["explainer_subject"] == "howto"


@pytest.mark.parametrize("subject,marker", [
    ("field", "A FIELD OR JOB"), ("product", "A PRODUCT"), ("howto", "A HOW-TO"), ("topic", None)])
def test_the_solo_prompt_has_a_block_per_subject(subject, marker):
    from backend.ai.llm import prompt_loader

    block = asyncio.run(prompt_loader.load_presentation_block("solo_explainer", "why", 1, subject))
    for other in ("A FIELD OR JOB", "A PRODUCT", "A HOW-TO"):
        assert (f"SUBJECT — {other}" in block) == (other == marker)
    if subject == "product":
        assert "Never invent technical specifications, prices" in block


def test_topic_ideas_avoid_recent_topics_and_drop_repeats(client, monkeypatch):  # noqa: F811
    data(client.post("/api/projects", json={**PROJECT, "topic": "How an espresso machine works"}))
    ideas = [{"name": "Espresso!", "topic": "How an Espresso Machine works.", "description": "d"},
             {"name": "Grinders", "topic": "Choosing a coffee grinder", "description": "d"}]
    router = ScriptedRouter(json.dumps({"ideas": ideas}))
    monkeypatch.setattr(source_service, "build_ai_router_from_settings", lambda: router)
    result = data(client.post("/api/projects/topic-ideas", json={
        "presentation_mode": "solo_explainer", "explainer_subject": "product"}))
    assert [idea["name"] for idea in result["ideas"]] == ["Grinders"]
    prompt = router.requests[0].prompt
    assert "- How an espresso machine works" in prompt and "presents a kind of product" in prompt
    router.text = json.dumps({"ideas": ideas[:1]})
    assert "only repeated" in failed(client.post("/api/projects/topic-ideas", json={}))


def test_photos_keep_only_the_text_and_its_hash_and_obey_the_cloud_switch(client, monkeypatch):  # noqa: F811
    import hashlib

    from backend.core.config import settings

    router = ScriptedRouter(json.dumps({"text": "invoice\naudit"}))
    monkeypatch.setattr(source_service, "build_ai_router_from_settings", lambda: router)
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", True)
    picture = _png()
    read = data(client.post("/api/projects/read-image", data={"kind": "vocabulary"},
                            files={"file": ("list.png", picture, "image/png")}))
    assert read["image_sha"] == hashlib.sha256(picture).hexdigest()
    created = data(client.post("/api/projects", json={**PROJECT, "source_kind": "vocabulary", "source_text": read["text"],
                                                      "source_image_sha": read["image_sha"]}))
    assert created["source_image_sha"] == read["image_sha"]
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD", False)
    assert "DIE_AI_ALLOW_CLOUD=false" in failed(client.post(
        "/api/projects/read-image", data={"kind": "vocabulary"}, files={"file": ("list.png", picture, "image/png")}))


def test_the_learning_pack_lists_the_owners_words_the_script_uses():
    from backend.ai.llm.prompt_loader import render_learning_prompt
    from backend.content import learning_pipeline

    project = {"source_kind": "vocabulary", "source_text": "invoice\naudit\nrefund"}
    assert learning_pipeline._required_vocabulary(project, "We sent the invoices. A refund came.") == ["invoice", "refund"]
    assert learning_pipeline._required_vocabulary({}, "text") == []
    prompt = asyncio.run(render_learning_prompt(topic="t", cefr_level="B1", genre="small_talk", transcript_text="x",
                                                required_vocabulary=["invoice"]))
    assert "vocabulary list comes first" in prompt and "- invoice" in prompt
    plain = asyncio.run(render_learning_prompt(topic="t", cefr_level="B1", genre="small_talk", transcript_text="x"))
    assert "vocabulary list comes first" not in plain


def test_one_vocabulary_repair_round_is_kept_only_when_it_helps(monkeypatch):
    from contextlib import asynccontextmanager

    Line, Spec = script_pipeline.SectionLineOut, script_pipeline.OutlineSectionSpec
    outline = script_pipeline.ScriptOutline(title="t", sections=[
        Spec(index=1, objective="Open the talk about the payment", target_words=10),
        Spec(index=2, objective="Explain the audit and the refund", target_words=10)])
    first = [Line(speaker_id="a", text="We sent the invoice on Monday morning to the client.")]
    second = [Line(speaker_id="b", text="Then we waited for the money from the client team.")]
    dump = script_pipeline._SECTION_LINES_ADAPTER.dump_json
    checkpoints = {1: {"result_json": dump(first).decode(), "metrics_json": "{}"},
                   2: {"result_json": dump(second).decode(), "metrics_json": "{}"}}
    calls, saved = [], []

    async def load(db, job_id):
        return checkpoints

    async def repair(router, project, spec, lines, errors, known, db, job_id, *, purpose):
        calls.append((spec.index, errors[0]))
        return [Line(speaker_id="b", text="Then the audit showed a refund was due to the client team.")], [], []

    async def save(*args, **kwargs):
        saved.append(args[2])

    @asynccontextmanager
    async def transaction(db):
        yield

    monkeypatch.setattr(script_pipeline, "_load_section_checkpoints", load)
    monkeypatch.setattr(script_pipeline, "_repair_section", repair)
    monkeypatch.setattr(script_pipeline.ai_job_service, "save_checkpoint", save)
    monkeypatch.setattr(script_pipeline, "write_transaction", transaction)
    monkeypatch.setattr(script_pipeline, "validate_global", lambda *args, **kwargs: ([], []))
    project = {"source_kind": "vocabulary", "source_text": "invoice\naudit\nrefund", "topic": "t"}
    run = lambda: asyncio.run(script_pipeline._vocabulary_repair(  # noqa: E731
        None, project, outline, first + second, 20, {"a", "b"}, 2, None, "j"))
    lines = run()
    assert [index for index, _error in calls] == [2] and "audit, refund" in calls[0][1]  # the section naming them
    assert saved == [2] and "audit" in lines[1].text
    calls.clear()
    saved.clear()
    monkeypatch.setattr(script_pipeline, "validate_global", lambda *args, **kwargs: (["too long"], []))
    assert run() == first + second and saved == []  # a repair that breaks the script is thrown away
