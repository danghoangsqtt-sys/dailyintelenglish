"""Guard tests for tests/conftest.py's `_neutralize_cloud_config()` (Task
18.3, PM review N1).

`app.core.config` loads the real `.env` at import time, so without that
neutralization, `settings.OPENAI_COMPAT_*` would hold the owner's real
OpenRouter key and base URL for this whole pytest process -- a test whose
mock slips could spend the owner's free-tier quota or send real project data
to a third party (invariant 31/33). This file has no fixtures of its own,
deliberately, so nothing else in a test's own setup could have reset the
values these tests check.
"""

from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent

# Any of these appearing in a test file's source would bypass conftest.py's
# neutralization and reintroduce the owner's real key/URL into a test.
# Legitimate tests always go through `config.settings.OPENAI_COMPAT_*`
# (optionally overridden with `monkeypatch`), never straight `os.environ`/a
# raw `.env` read.
_FORBIDDEN_PATTERNS = (
    'os.environ["DIE_OPENAI_COMPAT_API_KEY"]',
    "os.environ['DIE_OPENAI_COMPAT_API_KEY']",
    'os.environ.get("DIE_OPENAI_COMPAT_API_KEY"',
    "os.environ.get('DIE_OPENAI_COMPAT_API_KEY'",
    'os.getenv("DIE_OPENAI_COMPAT_API_KEY"',
    "os.getenv('DIE_OPENAI_COMPAT_API_KEY'",
    'open(".env"',
    "open('.env'",
    '.env").read',
    ".env').read",
)


def test_cloud_settings_are_neutralized_for_the_whole_session():
    """A fresh test with no fixtures at all -- confirms conftest.py's
    `_neutralize_cloud_config()` (called once at import time, before any
    test or fixture runs) actually holds, not just that some earlier
    fixture happened to leave it looking that way."""
    from app.core import config

    assert config.settings.OPENAI_COMPAT_API_KEY == ""
    assert config.ENV_OPENAI_COMPAT_API_KEY == ""
    assert config.settings.OPENAI_COMPAT_BASE_URL == "https://openrouter.invalid/api/v1"
    assert config.settings.AI_ALLOW_CLOUD is False
    assert config.settings.GEMINI_API_KEY == ""


def test_no_test_file_reads_the_env_cloud_key_directly():
    """Statically scans every tests/*.py file's source for the forbidden
    patterns above. conftest.py itself is exempt (it's what sets these
    fields to empty strings in the first place -- an assignment, not a read
    of a real value; none of the forbidden patterns match that code anyway,
    but it's excluded explicitly for clarity)."""
    offenders = []
    for path in TESTS_DIR.glob("*.py"):
        if path.name in ("conftest.py", "test_cloud_config_isolation.py"):
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in _FORBIDDEN_PATTERNS:
            if pattern in text:
                offenders.append(f"{path.name}: {pattern!r}")
    assert offenders == []
