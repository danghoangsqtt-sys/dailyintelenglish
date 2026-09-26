"""Offline-only tests for scripts/live_provider_contract_check.py (Task 18.9,
D30, Amendment G point 5).

This script is opt-in and PM-run-only against real endpoints -- this file
covers only its one pure, no-I/O helper (`_build_probe_request`). Everything
else in the script (building real provider instances, making a real HTTP
call) is exercised, offline, by `tests/test_openai_compat_provider.py`'s
per-vendor payload contract tests and `tests/test_ai_router.py`'s chain-
building tests -- this script itself just calls that already-tested code, it
doesn't reimplement any of it.
"""

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "live_provider_contract_check.py"


def _load_script():
    """Same importlib pattern as tests/test_run_ai_operational_trial.py's
    `runner_module` fixture -- this script has no argv/env side effects at
    import time (unlike that runner), so no snapshot/restore is needed, only
    a fresh module identity."""
    module_name = "live_provider_contract_check_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        return module
    finally:
        sys.modules.pop(module_name, None)


def test_build_probe_request_is_a_tiny_fixed_prompt():
    module = _load_script()
    request = module._build_probe_request()
    assert request.prompt == "Reply with the single word: ok."
    assert request.purpose == "live_provider_contract_check"
    assert request.deadline_seconds == 15.0


def test_module_has_a_main_guard_and_does_nothing_on_import():
    """Importing the module must never make a real call -- `main()` only runs
    under `if __name__ == "__main__":`, never at import time."""
    module = _load_script()
    assert hasattr(module, "main")
    assert callable(module.main)
