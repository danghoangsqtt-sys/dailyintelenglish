"""Generate docs/api.md from the app's real FastAPI OpenAPI schema.

Loads the actual app object (no live server needed) and renders one Markdown
section per route, grouped by tag, from `app.openapi()` — the same schema
FastAPI serves at `/openapi.json` and renders at `/docs`. Re-run this script
after changing any route instead of hand-editing docs/api.md, so the
reference can never drift from the real API the way ARCHITECTURE.md once did
(see TRACKER.md Task 2.6a).

Usage:
    venv\\Scripts\\python scripts\\generate_api_docs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402

OUTPUT_PATH = ROOT / "docs" / "api.md"

METHOD_ORDER = ["GET", "POST", "PUT", "PATCH", "DELETE"]


def _resolve_schema_name(schema_ref: dict) -> str | None:
    ref = schema_ref.get("$ref") or schema_ref.get("items", {}).get("$ref")
    if not ref:
        return None
    return ref.rsplit("/", 1)[-1]


def _describe_request_body(operation: dict) -> str | None:
    body = operation.get("requestBody")
    if not body:
        return None
    content = body.get("content", {})
    json_body = content.get("application/json")
    if not json_body:
        return None
    name = _resolve_schema_name(json_body.get("schema", {}))
    return name or "object"


def _describe_response(operation: dict) -> str | None:
    responses = operation.get("responses", {})
    ok = responses.get("200") or responses.get("201")
    if not ok:
        return None
    content = ok.get("content", {})
    json_body = content.get("application/json")
    if not json_body:
        return None
    name = _resolve_schema_name(json_body.get("schema", {}))
    return name or "object"


def generate() -> str:
    schema = app.openapi()
    paths: dict = schema.get("paths", {})

    by_tag: dict[str, list[tuple[str, str, dict]]] = {}
    for path, methods in paths.items():
        for method, operation in methods.items():
            if method.upper() not in METHOD_ORDER:
                continue
            tags = operation.get("tags") or ["untagged"]
            for tag in tags:
                by_tag.setdefault(tag, []).append((method.upper(), path, operation))

    lines: list[str] = []
    lines.append("# API Reference")
    lines.append("")
    lines.append(
        f"Auto-generated from `{schema.get('info', {}).get('title', 'app')}`'s real "
        "FastAPI OpenAPI schema by `scripts/generate_api_docs.py` — do not hand-edit; "
        "re-run the script after changing any route. The live, always-current version of "
        "this same schema is also served at `/docs` (Swagger UI) and `/openapi.json` "
        "whenever the app is running."
    )
    lines.append("")
    lines.append(f"OpenAPI version: `{schema.get('openapi', 'unknown')}`")
    lines.append("")

    for tag in sorted(by_tag):
        lines.append(f"## {tag}")
        lines.append("")
        routes = sorted(
            by_tag[tag],
            key=lambda item: (item[1], METHOD_ORDER.index(item[0])),
        )
        for method, path, operation in routes:
            summary = operation.get("summary") or operation.get("operationId", "")
            lines.append(f"### `{method} {path}`")
            if summary:
                lines.append("")
                lines.append(summary)
            description = operation.get("description")
            if description and description.strip() != summary.strip():
                lines.append("")
                lines.append(description.strip())
            request_model = _describe_request_body(operation)
            response_model = _describe_response(operation)
            lines.append("")
            if request_model:
                lines.append(f"- **Request body:** `{request_model}`")
            if response_model:
                lines.append(f"- **Response body:** `{response_model}`")
            params = operation.get("parameters", [])
            if params:
                param_bits = ", ".join(
                    f"`{p['name']}`" + ("" if p.get("required") else " (optional)")
                    for p in params
                )
                lines.append(f"- **Parameters:** {param_bits}")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    content = generate()
    OUTPUT_PATH.write_text(content, encoding="utf-8")
    route_count = sum(
        1
        for methods in app.openapi().get("paths", {}).values()
        for method in methods
        if method.upper() in METHOD_ORDER
    )
    print(f"Wrote {OUTPUT_PATH} ({route_count} routes documented)")


if __name__ == "__main__":
    main()
