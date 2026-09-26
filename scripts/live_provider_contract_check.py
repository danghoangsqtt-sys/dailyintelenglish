"""Task 18.9 (D30, Amendment G point 5): opt-in live contract check for every
CONFIGURED cloud provider entry.

**Opt-in, PM-run only. Never collected by pytest** (this filename matches
neither pytest's default `test_*.py` nor `*_test.py` collection patterns, and
`pytest.ini` carries no `python_files`/`testpaths` override that would sweep
`scripts/` -- already safe from accidental collection by construction; this
docstring states the rule anyway, belt-and-suspenders). **The Coder never runs
this against a real endpoint** -- only its offline, MockTransport-testable
parts (none currently extracted; the request-building itself lives in
`OpenAICompatProvider.generate()`, already covered by
`tests/test_openai_compat_provider.py`'s per-vendor payload contract tests).

Sends the app's EXACT request (built by the real `OpenAICompatProvider` class,
via `app.services.ai.router`'s own chain-building helpers -- the same code
`build_ai_router_from_settings` uses, so this checks precisely what a real job
would send) with one tiny fixed prompt to each currently-configured vendor.
Calls each provider's `generate()` directly -- bypassing `AIRouter` and every
circuit entirely, since this is a raw one-shot probe, not a routed call.

Prints ONLY the vendor name, HTTP status (or "-" when there was none, e.g. a
timeout), and pass/fail -- never the exception message text (some upstreams
echo request data in it; `OpenAICompatProvider._redact` already scrubs the key
from it, but this script prints strictly less than that as a second layer),
never the request/response body, never the key.

Usage:
    venv\\Scripts\\python scripts\\live_provider_contract_check.py

Costs exactly one real request per currently-configured provider entry.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.exceptions import ProviderError  # noqa: E402
from app.services.ai.contracts import GenerationRequest  # noqa: E402
from app.services.ai.router import _build_chain_entries, _configured_cloud_provider_names  # noqa: E402

_PROBE_PROMPT = "Reply with the single word: ok."
_PROBE_DEADLINE_SECONDS = 15.0


def _build_probe_request() -> GenerationRequest:
    """The one thing here worth unit-testing offline -- a plain, pure
    constructor call, no I/O. Covered by `tests/test_live_provider_contract_check.py`."""
    return GenerationRequest(
        prompt=_PROBE_PROMPT, deadline_seconds=_PROBE_DEADLINE_SECONDS, purpose="live_provider_contract_check"
    )


async def _check_one(name: str, provider) -> None:
    request = _build_probe_request()
    try:
        await provider.generate(request)
    except ProviderError as exc:
        status = getattr(exc, "upstream_status", None)
        print(f"{name}: FAIL (HTTP {status if status is not None else '-'}, {type(exc).__name__})", flush=True)
        return
    print(f"{name}: OK", flush=True)


async def main() -> int:
    configured_names = _configured_cloud_provider_names(settings)
    if not configured_names:
        print("no cloud provider configured -- nothing to check", flush=True)
        return 0

    entries = []
    for name in configured_names:
        try:
            entries.extend(_build_chain_entries(name, settings, circuits=None))
        except ValueError as exc:
            print(f"{name}: FAIL (could not build provider: {type(exc).__name__})", flush=True)

    for entry in entries:
        await _check_one(entry.name, entry.provider)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
