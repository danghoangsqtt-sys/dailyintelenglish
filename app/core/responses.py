"""Standard API response envelope shared by every route."""

import time
from typing import Any


def ok(data: Any, started_at: float | None = None, **meta: Any) -> dict:
    """Build a success envelope: {success, data, error: null, meta}.

    Args:
        data: Payload to return to the client.
        started_at: `time.perf_counter()` value captured at request start,
            used to compute `processing_time_ms` when provided.
        **meta: Extra metadata fields (e.g. model_used).

    Returns:
        Response dict matching the project-wide API contract.
    """
    if started_at is not None:
        meta["processing_time_ms"] = round((time.perf_counter() - started_at) * 1000, 2)
    return {"success": True, "data": data, "error": None, "meta": meta}
