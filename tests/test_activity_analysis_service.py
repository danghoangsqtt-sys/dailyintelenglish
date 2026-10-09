"""Provider and worker-boundary tests for local-first Activity Vision."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path

import pytest
import httpx
from PIL import Image

from app.core.config import settings
from app.services.visuals import activity_analysis_service as analysis


def picture_bytes(color: tuple[int, int, int] = (30, 60, 90)) -> bytes:
    output = BytesIO()
    Image.new("RGB", (1280, 720), color).save(output, format="PNG")
    return output.getvalue()


@pytest.mark.asyncio
async def test_local_batch_is_validated_normalized_and_keeps_order(monkeypatch):
    monkeypatch.setattr(settings, "ACTIVITY_VISION_PROVIDER", "local")
    monkeypatch.setattr(settings, "ACTIVITY_VISION_CLOUD_FALLBACK", False)

    async def fake_local(images):
        assert [filename for _content, filename in images] == ["one.png", "two.png"]
        return [
            '{"activity":"Go Straight","context_tags":["Directions","City Street"],'
            '"aliases":["Continue Straight","Walk Straight Ahead"],"confidence":0.94}',
            '{"activity":"Turn Right","context_tags":["Navigation"],'
            '"aliases":["Make a Right Turn"],"confidence":0.88}',
        ]

    monkeypatch.setattr(analysis, "_local_responses", fake_local)
    results = await analysis.analyze_activity_images([(b"one", "one.png"), (b"two", "two.png")])

    assert [item["activity"] for item in results] == ["go straight", "turn right"]
    assert results[0]["context_tags"] == ["directions", "city street"]
    assert all(item["source"] == "local_ai" for item in results)


@pytest.mark.asyncio
async def test_invalid_local_result_uses_filename_without_cloud_by_default(monkeypatch):
    monkeypatch.setattr(settings, "ACTIVITY_VISION_PROVIDER", "local")
    monkeypatch.setattr(settings, "ACTIVITY_VISION_CLOUD_FALLBACK", False)

    async def fake_local(_images):
        return ["not json"]

    async def forbidden_cloud(_content):
        raise AssertionError("cloud must be opt-in")

    monkeypatch.setattr(analysis, "_local_responses", fake_local)
    monkeypatch.setattr(analysis, "_cloud_suggestion", forbidden_cloud)
    result = (await analysis.analyze_activity_images([(b"image", "cross-the-street.png")]))[0]

    assert result["activity"] == "cross the street"
    assert result["source"] == "filename"


@pytest.mark.asyncio
async def test_opt_in_cloud_only_fills_failed_local_items(monkeypatch):
    monkeypatch.setattr(settings, "ACTIVITY_VISION_PROVIDER", "local")
    monkeypatch.setattr(settings, "ACTIVITY_VISION_CLOUD_FALLBACK", True)

    async def fake_local(_images):
        return [
            '{"activity":"go straight","context_tags":[],"aliases":[],"confidence":0.9}',
            "malformed",
        ]

    cloud_calls: list[bytes] = []

    async def fake_cloud(content):
        cloud_calls.append(content)
        return {
            "activity": "turn left", "context_tags": ["directions"],
            "aliases": ["make a left turn"], "confidence": 0.8, "source": "cloud_ai",
        }

    monkeypatch.setattr(analysis, "_local_responses", fake_local)
    monkeypatch.setattr(analysis, "_cloud_suggestion", fake_cloud)
    results = await analysis.analyze_activity_images([(b"first", "1.png"), (b"second", "2.png")])

    assert [item["source"] for item in results] == ["local_ai", "cloud_ai"]
    assert cloud_calls == [b"second"]


@pytest.mark.asyncio
async def test_local_worker_uses_one_process_for_batch_and_removes_staging(tmp_path, monkeypatch):
    fake_python = tmp_path / "python.exe"
    fake_python.touch()
    monkeypatch.setattr(settings, "ACTIVITY_VISION_PYTHON", fake_python)
    monkeypatch.setattr(settings, "ACTIVITY_VISION_CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(settings, "ACTIVITY_VISION_TIMEOUT_SECONDS", 10.0)
    monkeypatch.setattr(settings, "ACTIVITY_VISION_RUNTIME", "huggingface")

    leases: list[tuple[str, int]] = []

    class FakeManager:
        @asynccontextmanager
        async def lease(self, consumer, min_free_mb):
            leases.append((consumer, min_free_mb))
            yield object()

    class FakeProcess:
        returncode = 0

        def __init__(self, output_path: Path):
            self.output_path = output_path

        async def communicate(self):
            self.output_path.write_text(json.dumps({"items": [
                {"id": "0", "text": "first"}, {"id": "1", "text": "second"},
            ]}), encoding="utf-8")
            return b"loaded once", b""

        def kill(self):
            raise AssertionError("worker should not time out")

    calls: list[tuple[str, ...]] = []

    async def fake_subprocess(*args, **_kwargs):
        calls.append(tuple(str(arg) for arg in args))
        output_path = Path(args[args.index("--output") + 1])
        return FakeProcess(output_path)

    monkeypatch.setattr(analysis, "get_gpu_manager", lambda: FakeManager())
    monkeypatch.setattr(analysis.asyncio, "create_subprocess_exec", fake_subprocess)

    responses = await analysis._local_responses([
        (picture_bytes(), "one.png"), (picture_bytes((10, 20, 30)), "two.png"),
    ])

    assert responses == ["first", "second"]
    assert len(calls) == 1
    assert leases == [("activity_vision", settings.ACTIVITY_VISION_MIN_FREE_MB)]
    work_root = settings.DATA_DIR / "tmp" / "activity_vision"
    assert work_root.is_dir() and list(work_root.iterdir()) == []


@pytest.mark.asyncio
async def test_ollama_runtime_keeps_model_for_batch_then_unloads(monkeypatch):
    payloads: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        payloads.append(payload)
        activity = "go straight" if len(payloads) == 1 else "turn left"
        return httpx.Response(200, json={"message": {"content": json.dumps({
            "activity": activity, "context_tags": ["directions"],
            "aliases": [], "confidence": 0.9,
        })}})

    class FakeManager:
        @asynccontextmanager
        async def lease(self, consumer, min_free_mb):
            assert (consumer, min_free_mb) == ("activity_vision_ollama", 0)
            yield object()

    original_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(analysis, "get_gpu_manager", lambda: FakeManager())
    monkeypatch.setattr(
        analysis.httpx, "AsyncClient",
        lambda **kwargs: original_client(transport=transport, **kwargs),
    )

    responses = await analysis._ollama_responses([
        (picture_bytes(), "straight.png"), (picture_bytes(), "left.png"),
    ])

    assert len(responses) == 2
    assert [payload["keep_alive"] for payload in payloads] == ["5m", 0]
    assert all(payload["model"] == settings.ACTIVITY_VISION_MODEL for payload in payloads)
    assert all(payload["format"] == analysis._OLLAMA_JSON_SCHEMA for payload in payloads)
