"""Full HTTP tests for the Task 1.8a thumbnail generation vertical slice."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services import thumbnail_service

PROJECT_PAYLOAD = {
    "name": "Thumbnail API Episode",
    "topic": "How AI changes careers",
    "cefr_level": "B2",
    "duration_minutes": 5,
    "num_speakers": 1,
    "genre": "debate",
    "accent": "american",
    "speakers": [{"name": "Alex", "gender": "neutral", "accent": "american"}],
}


def suggestion_json(prefix: str = "Concept") -> str:
    """Build a valid three-variant mocked Gemini response."""
    colors = [
        ("#111827", "#60A5FA", "#F59E0B"),
        ("#3B0764", "#C084FC", "#22D3EE"),
        ("#052E16", "#4ADE80", "#FDE047"),
    ]
    variants = []
    for index, (primary, secondary, accent) in enumerate(colors):
        variants.append(
            {
                "headline": f"{prefix} {index + 1}",
                "supporting_text": "Practical English for tomorrow",
                "topic_keywords": ["AI", f"career-{index + 1}"],
                "palette": {
                    "primary": primary,
                    "secondary": secondary,
                    "accent": accent,
                    "text": "#FFFFFF",
                },
            }
        )
    return json.dumps({"variants": variants})


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Run the full app with isolated storage and mocked Gemini text generation."""
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")

    async def fake_generate(prompt: str, schema: dict) -> str:
        return suggestion_json()

    monkeypatch.setattr(thumbnail_service, "_generate_with_retry", fake_generate)
    with TestClient(app) as test_client:
        yield test_client


def create_project(client: TestClient) -> dict:
    """Create one valid project through the real project API."""
    response = client.post("/api/projects", json=PROJECT_PAYLOAD)
    assert response.status_code == 200
    return response.json()["data"]


def test_templates_endpoint_lists_five_valid_preview_assets(client: TestClient) -> None:
    response = client.get("/api/thumbnails/templates")

    assert response.status_code == 200
    templates = response.json()["data"]
    assert len(templates) == 5
    assert all(template["preview_url"].endswith(".png") for template in templates)


def test_generate_creates_exactly_n_rows_for_one_selected_template(client: TestClient) -> None:
    project = create_project(client)

    response = client.post(
        f"/api/projects/{project['id']}/thumbnails/generate",
        json={"template_name": "modern_split", "variant_count": 3},
    )

    assert response.status_code == 200
    variants = response.json()["data"]
    assert len(variants) == 3
    assert [variant["variant_index"] for variant in variants] == [0, 1, 2]
    assert {variant["template_name"] for variant in variants} == {"modern_split"}
    assert len({variant["id"] for variant in variants}) == 3
    assert all("image_path_16x9" not in variant for variant in variants)
    assert all("image_path_9x16" not in variant for variant in variants)


def test_generated_derivatives_are_streamed_with_correct_media_types(client: TestClient) -> None:
    project = create_project(client)
    variants = client.post(
        f"/api/projects/{project['id']}/thumbnails/generate",
        json={"template_name": "minimal_clean", "variant_count": 3},
    ).json()["data"]

    for aspect in ("16x9", "9x16"):
        for image_format, media_type in (("png", "image/png"), ("jpg", "image/jpeg")):
            response = client.get(variants[0]["assets"][aspect][image_format])
            assert response.status_code == 200
            assert response.headers["content-type"].startswith(media_type)
            assert response.content


def test_list_endpoint_restores_render_metadata_and_urls(client: TestClient) -> None:
    project = create_project(client)
    generated = client.post(
        f"/api/projects/{project['id']}/thumbnails/generate",
        json={"template_name": "dynamic_wave", "variant_count": 3},
    ).json()["data"]

    response = client.get(f"/api/projects/{project['id']}/thumbnails")

    assert response.status_code == 200
    restored = response.json()["data"]
    assert [item["suggestion"] for item in restored] == [item["suggestion"] for item in generated]
    assert restored[0]["assets"]["16x9"]["png"].endswith("/16x9.png")


def test_regeneration_replaces_rows_and_removes_superseded_files(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = create_project(client)
    endpoint = f"/api/projects/{project['id']}/thumbnails/generate"
    first = client.post(
        endpoint,
        json={"template_name": "minimal_clean", "variant_count": 3},
    ).json()["data"]
    first_dirs = [
        settings.DATA_DIR / "thumbnails" / project["id"] / variant["id"] for variant in first
    ]

    async def second_generate(prompt: str, schema: dict) -> str:
        return suggestion_json("Replacement")

    monkeypatch.setattr(thumbnail_service, "_generate_with_retry", second_generate)
    second_response = client.post(
        endpoint,
        json={"template_name": "podcast_classic", "variant_count": 3},
    )

    assert second_response.status_code == 200
    second = second_response.json()["data"]
    assert {variant["template_name"] for variant in second} == {"podcast_classic"}
    assert not any(path.exists() for path in first_dirs)
    assert len(client.get(f"/api/projects/{project['id']}/thumbnails").json()["data"]) == 3


@pytest.mark.parametrize(
    "payload",
    [
        {"template_name": "../escape", "variant_count": 3},
        {"template_name": "modern_split", "variant_count": 2},
        {"template_name": "modern_split", "variant_count": 6},
    ],
)
def test_generate_rejects_invalid_template_or_variant_count(
    client: TestClient,
    payload: dict,
) -> None:
    project = create_project(client)

    response = client.post(
        f"/api/projects/{project['id']}/thumbnails/generate",
        json=payload,
    )

    assert response.status_code == 422


def test_unknown_project_thumbnail_routes_return_404(client: TestClient) -> None:
    generate = client.post(
        "/api/projects/missing/thumbnails/generate",
        json={"template_name": "modern_split", "variant_count": 3},
    )
    listing = client.get("/api/projects/missing/thumbnails")
    content = client.get("/api/projects/missing/thumbnails/id/16x9.png")

    assert generate.status_code == 404
    assert listing.status_code == 404
    assert content.status_code == 404


def test_content_route_rejects_unknown_id_aspect_and_format(client: TestClient) -> None:
    project = create_project(client)

    missing = client.get(f"/api/projects/{project['id']}/thumbnails/missing/16x9.png")
    bad_aspect = client.get(f"/api/projects/{project['id']}/thumbnails/missing/square.png")
    bad_format = client.get(f"/api/projects/{project['id']}/thumbnails/missing/16x9.gif")

    assert missing.status_code == 404
    assert bad_aspect.status_code == 422
    assert bad_format.status_code == 422
