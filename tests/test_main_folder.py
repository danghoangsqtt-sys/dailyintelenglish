"""Phase 80 (owner 2026-10-26): one main save folder; every new project gets <main>/<Topic>/<Series>/Ep NN - <title>/."""

from pathlib import Path

from tests.test_visuals_project_api import client, data  # noqa: F401

PROJECT = {"name": "Coffee talk", "topic": "Ordering coffee", "cefr_level": "B1", "duration_minutes": 5, "num_speakers": 2,
           "genre": "interview", "accent": "american",
           "speakers": [{"name": "Lan", "gender": "female", "accent": "american"},
                        {"name": "Minh", "gender": "male", "accent": "american"}]}


def test_without_a_main_folder_nothing_is_assigned(client):  # noqa: F811
    view = data(client.get("/api/settings/main-folder"))
    assert view["output_dir"] is None
    project = data(client.post("/api/projects", json=PROJECT))
    assert data(client.get(f"/api/projects/{project['id']}/export"))["settings"] is None
    assert client.post("/api/settings/main-folder/apply").status_code == 422


def test_new_projects_get_a_topic_folder_under_the_main_folder(client, tmp_path):  # noqa: F811
    before = data(client.post("/api/projects", json=PROJECT))  # made before the main folder was chosen
    main = tmp_path / "Videos"
    view = data(client.put("/api/settings/main-folder", json={"output_dir": str(main)}))
    assert view["output_dir"] == str(main) and main.is_dir() and view["projects_without_folder"] >= 1

    project = data(client.post("/api/projects", json={**PROJECT, "name": "Second coffee talk"}))
    export = data(client.get(f"/api/projects/{project['id']}/export"))
    assert export["settings"]["output_dir"] == str(main) and export["settings"]["layout_mode"] == "topic_hierarchy"
    assert Path(export["folder"]).is_relative_to(main) and "Second coffee talk" in export["folder"]
    assert data(client.get(f"/api/projects/{before['id']}/export"))["settings"] is None  # not touched until asked

    applied = data(client.post("/api/settings/main-folder/apply"))
    assert applied["given"] >= 1 and applied["projects_without_folder"] == 0
    assert data(client.get(f"/api/projects/{before['id']}/export"))["settings"]["output_dir"] == str(main)


def test_a_project_with_its_own_folder_keeps_it(client, tmp_path):  # noqa: F811
    project = data(client.post("/api/projects", json=PROJECT))
    own = tmp_path / "Own"
    data(client.put(f"/api/projects/{project['id']}/export", json={"output_dir": str(own), "layout_mode": "legacy"}))
    data(client.put("/api/settings/main-folder", json={"output_dir": str(tmp_path / "Main")}))
    data(client.post("/api/settings/main-folder/apply"))
    assert data(client.get(f"/api/projects/{project['id']}/export"))["settings"]["output_dir"] == str(own)


def test_without_a_choice_new_projects_go_to_the_default_folder(client, tmp_path, monkeypatch):  # noqa: F811
    """Phase 83 (owner 2026-10-28): automatic videos stayed inside the app's data folder when no main folder was chosen."""
    from backend.core.config import settings

    default = tmp_path / "Videos"
    monkeypatch.setattr(settings, "DEFAULT_OUTPUT_DIR", str(default))
    view = data(client.get("/api/settings/main-folder"))
    assert (view["output_dir"], view["is_default"], view["default_dir"]) == (str(default), True, str(default))
    project = data(client.post("/api/projects", json=PROJECT))
    export = data(client.get(f"/api/projects/{project['id']}/export"))
    assert export["settings"]["output_dir"] == str(default) and default.is_dir()  # made on first use
    assert "shorts" in export["settings"]["items"]  # clips cut from the episode go to its folder too
    chosen = tmp_path / "Mine"
    assert data(client.put("/api/settings/main-folder", json={"output_dir": str(chosen)}))["is_default"] is False
    back = data(client.put("/api/settings/main-folder", json={"output_dir": None}))  # "Use the default folder"
    assert (back["output_dir"], back["is_default"]) == (str(default), True)
    assert data(client.get(f"/api/projects/{project['id']}/export"))["settings"]["output_dir"] == str(default)  # kept


def test_the_default_folder_setting(monkeypatch):
    from pathlib import Path as P

    from backend.core.config import settings

    monkeypatch.setattr(settings, "DEFAULT_OUTPUT_DIR", "off")
    assert settings.default_output_dir is None
    monkeypatch.setattr(settings, "DEFAULT_OUTPUT_DIR", "auto")
    expected = P("D:/Videos") if P("D:/").exists() else P.home() / "Videos" / "Daily Beyond English"
    assert settings.default_output_dir == expected


def test_relative_paths_are_refused_and_the_folder_can_be_cleared(client, tmp_path):  # noqa: F811
    assert client.put("/api/settings/main-folder", json={"output_dir": "Videos"}).status_code == 422
    data(client.put("/api/settings/main-folder", json={"output_dir": str(tmp_path / "M")}))
    assert data(client.put("/api/settings/main-folder", json={"output_dir": None}))["output_dir"] is None
