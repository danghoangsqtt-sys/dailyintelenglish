"""Stable local build and data-instance identity, without exposing filesystem paths."""

from __future__ import annotations

import hashlib
import json
import sys
from functools import lru_cache
from pathlib import Path

PRODUCT_ID = "daily-beyond-english-studio"


@lru_cache(maxsize=1)
def get_build_info() -> dict:
    """Fingerprint the running code once; same-version trial builds remain distinct."""
    packaged = bool(getattr(sys, "frozen", False))
    digest = hashlib.sha256()
    metadata = {}
    if packaged:
        executable = Path(sys.executable).resolve()
        with executable.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        info = executable.parent / "build-info.json"
        if info.is_file():
            raw = info.read_bytes()
            digest.update(raw)
            metadata = json.loads(raw)
    else:
        root = Path(__file__).resolve().parents[2]
        for folder in ("backend", "frontend"):
            for path in sorted((root / folder).rglob("*")):
                if path.is_file() and path.suffix in {".py", ".html", ".js", ".css"}:
                    digest.update(path.relative_to(root).as_posix().encode())
                    digest.update(path.read_bytes())
    return {
        "product": PRODUCT_ID,
        "build_id": digest.hexdigest(),
        "version": str(metadata.get("version", "source")),
        "built_at_utc": str(metadata.get("built_at_utc", "")),
        "source_commit": str(metadata.get("source_commit", "")),
        "source_dirty": bool(metadata.get("source_dirty", False)),
        "packaged": packaged,
    }


def get_instance_info(data_dir: Path) -> dict:
    """Distinguish matching code using a different profile/project database."""
    data_identity = hashlib.sha256(str(data_dir.resolve()).casefold().encode()).hexdigest()
    return {**get_build_info(), "instance_id": data_identity}
