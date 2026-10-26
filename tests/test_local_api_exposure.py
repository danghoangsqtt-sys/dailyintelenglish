"""ENH-056: the studio answers only to its own local names and origins (CORS and DNS rebinding); BUG-055: the harmless
Windows connection-reset traceback is not logged."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.core.config import settings


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.mark.parametrize("host", ["localhost:8000", "127.0.0.1:8030", "[::1]:8000", "localhost", "testserver"])
def test_local_host_names_are_served(client, host):
    assert client.get("/api/settings", headers={"host": host}).status_code == 200


@pytest.mark.parametrize("host", ["evil.example.com", "evil.example.com:8000", "192.168.1.20:8000", "automation"])
def test_other_host_names_are_refused(client, host):
    response = client.get("/api/settings", headers={"host": host})
    assert response.status_code == 400 and response.json()["success"] is False


def test_a_network_app_host_turns_the_check_off(client, monkeypatch):
    monkeypatch.setattr(settings, "APP_HOST", "0.0.0.0")
    assert client.get("/api/settings", headers={"host": "192.168.1.20:8000"}).status_code == 200


def test_only_the_studios_own_origin_gets_cors(client):
    own = f"http://localhost:{settings.APP_PORT}"
    allowed = client.get("/api/settings", headers={"origin": own})
    assert allowed.headers.get("access-control-allow-origin") == own
    other = client.get("/api/settings", headers={"origin": "http://localhost:3000"})
    assert "access-control-allow-origin" not in other.headers


def test_host_name_parsing():
    assert main._host_name("localhost:8000") == "localhost"
    assert main._host_name("[::1]:8000") == "::1"
    assert main._host_name("::1") == "::1"
    assert main._host_name("Example.COM") == "example.com"


def test_the_harmless_connection_reset_is_not_logged(monkeypatch):
    seen = []

    async def scenario():
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(lambda _loop, context: seen.append(context["message"]))
        main._quiet_connection_resets()

        class Handle:
            def __repr__(self):
                return "<Handle _ProactorBasePipeTransport._call_connection_lost()>"

        loop.call_exception_handler({"message": "Exception in callback", "exception": ConnectionResetError(10054),
                                     "handle": Handle()})
        loop.call_exception_handler({"message": "something else", "exception": ValueError("real")})

    asyncio.run(scenario())
    assert seen == ["something else"]


def test_the_automation_client_uses_a_local_host_name():
    from backend.automation.runner import StepClient

    assert StepClient(main.app)._client.base_url.host == "localhost"
