import json
import sqlite3

from PIL import Image

from app.core.config import settings
from app.services import video_service
from app.services.visuals.activity_matcher import beat_speaker_index, match_activity, suggest
from tests.test_visuals_project_api import client, data, setup_project  # noqa: F401


def _asset(asset_id, character_id, activity, aliases=(), contexts=(), uses=0, last=None):
    return {"id": asset_id, "character_id": character_id, "activity": activity, "aliases": list(aliases),
            "context_tags": list(contexts), "use_count": uses, "last_used_at": last}


def test_character_asset_wins_then_generic_and_never_other_character():
    alex, lina = "alex", "lina"
    candidates = [_asset("wrong", lina, "cooking"), _asset("generic", None, "cooking"), _asset("alex", alex, "cooking")]
    match = match_activity(candidates, alex, "cooking dinner", "I cook dinner every night")
    assert match["activity_id"] == "alex" and match["match_type"] == "character"
    generic = match_activity(candidates[:2], alex, "cooking dinner", "I cook dinner every night")
    assert generic["activity_id"] == "generic" and generic["match_type"] == "generic"
    assert match_activity([candidates[0]], alex, "cooking dinner", "I cook dinner every night") is None


def test_character_scope_beats_a_higher_scoring_generic_candidate():
    candidates = [
        _asset("character", "alex", "exercise", aliases=("work out",)),
        _asset("generic", None, "work out", contexts=("gym",)),
    ]
    match = match_activity(candidates, "alex", "", "I work out at the gym", ["gym"])
    assert match["activity_id"] == "character"
    assert match["score"] == 70 and match["match_type"] == "character"


def test_alias_context_and_least_used_tie_breaking_are_explainable():
    candidates = [_asset("newer", None, "exercise", aliases=("work out",), contexts=("morning",), uses=2),
                  _asset("older", None, "exercise", aliases=("work out",), contexts=("morning",), uses=0)]
    match = match_activity(candidates, None, "", "I work out every morning", ["morning"])
    assert match["activity_id"] == "older" and match["score"] == 75 and "alias" in match["reason"]


def test_equal_usage_rotates_by_oldest_last_use_then_stable_id():
    candidates = [
        _asset("z", None, "reading", uses=1, last="2026-10-09T10:00:00Z"),
        _asset("b", None, "reading", uses=1, last="2026-10-08T10:00:00Z"),
        _asset("a", None, "reading", uses=1, last="2026-10-08T10:00:00Z"),
    ]
    assert match_activity(candidates, None, "reading", "")["activity_id"] == "a"


def test_weak_or_unrelated_activity_is_missing():
    assert match_activity([_asset("cook", None, "cooking")], None, "", "I read a book") is None


def test_direction_image_matches_the_instruction_without_crossing_directions():
    straight = _asset(
        "straight", None, "go straight",
        aliases=("continue straight", "walk straight ahead", "keep going straight"),
        contexts=("directions", "navigation", "city street"),
    )
    match = match_activity([straight], None, "", "Keep going straight for two blocks", ["directions"])
    assert match["activity_id"] == "straight" and match["score"] == 75
    assert "alias 'keep going straight'" in match["reason"]
    assert match_activity([straight], None, "turn right", "Turn right at the corner", ["directions"]) is None


def _beat(line_from, line_to, speakers=(), action=""):
    return {"line_from": line_from, "line_to": line_to, "speakers": list(speakers), "action": action}


def test_beat_speaker_comes_from_the_beat_then_from_its_lines():
    """Task 32.8a (BUG-029, D76): an insert with ``speakers: []`` still belongs to whoever says its line."""
    line_speakers = [0, 1, 0, 1, None]
    texts = ["I stretch for ten minutes.", "Nice.", "Then I cook breakfast.", "I cook too!", "(music)"]
    assert beat_speaker_index(_beat(0, 0, speakers=[1]), line_speakers, texts) == 1  # explicit speaker wins
    assert beat_speaker_index(_beat(0, 0, action="exercise"), line_speakers, texts) == 0  # one line, one speaker
    assert beat_speaker_index(_beat(1, 2, action="cook"), line_speakers, texts) == 0  # only line 2 names the action
    assert beat_speaker_index(_beat(2, 3, action="cook"), line_speakers, texts) == 0  # both name it: first line
    assert beat_speaker_index(_beat(0, 1, action="dance"), line_speakers, texts) == 0  # nobody names it: first line
    assert beat_speaker_index(_beat(4, 4), line_speakers, texts) is None  # unknown speaker
    assert beat_speaker_index(_beat(7, 9), line_speakers, texts) is None  # out of range


def test_speakerless_insert_prefers_the_speaking_characters_picture():
    candidates = [_asset("generic", None, "exercise"), _asset("alex", "alex", "exercise"), _asset("lina", "lina", "exercise")]
    cast = {0: "alex", 1: "lina"}
    beat = _beat(0, 0, action="exercise")
    speaker = beat_speaker_index(beat, [0, 1], ["I stretch for ten minutes.", "Good idea."])
    assert match_activity(candidates, cast[speaker], beat["action"], "I stretch for ten minutes.")["activity_id"] == "alex"
    beat = _beat(1, 1, action="exercise")
    speaker = beat_speaker_index(beat, [0, 1], ["Hi.", "I exercise every day."])
    assert match_activity(candidates, cast[speaker], beat["action"], "I exercise every day.")["activity_id"] == "lina"


def test_activity_coverage_uses_the_speaker_of_a_speakerless_insert(client):  # noqa: F811
    project, character_ids, _ = setup_project(client, 2, 1)
    picture = settings.DATA_DIR / "library" / "activities" / "character-exercise.png"
    picture.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1280, 720), (20, 30, 40)).save(picture)
    speaker_ids = [speaker["id"] for speaker in project["speakers"]]
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute(
            "INSERT INTO script_lines (id, project_id, line_index, speaker_id, text) VALUES (?, ?, 0, ?, ?)",
            ("speakerless-line", project["id"], speaker_ids[0], "I stretch for ten minutes every morning."),
        )
        connection.execute(
            "INSERT INTO project_storyboards (project_id, status, source, updated_at) VALUES (?, 'approved', 'owner', 'now')",
            (project["id"],),
        )
        connection.execute(
            "INSERT INTO project_beats (id, project_id, position, line_from, line_to, kind, speakers_json, action, "
            "expression, created_at, updated_at) VALUES ('speakerless-beat', ?, 0, 0, 0, 'insert', '[]', 'exercise', "
            "'calm', 'now', 'now')",
            (project["id"],),
        )
        connection.execute(
            "INSERT INTO activity_library (id, activity, path, content_sha, review_state, created_at, updated_at) "
            "VALUES ('generic-exercise', 'exercise', ?, 'sha-generic-exercise', 'approved', 'now', 'now')",
            (str(picture),),
        )
        connection.execute(
            "INSERT INTO activity_library (id, character_id, activity, path, content_sha, review_state, created_at, updated_at) "
            "VALUES ('character-exercise', ?, 'exercise', ?, 'sha-character-exercise', 'approved', 'now', 'now')",
            (character_ids[0], str(picture)),
        )

    coverage = data(client.get(f"/api/projects/{project['id']}/visuals/activity-coverage"))

    assert coverage["items"][0]["status"] == "character"
    assert coverage["items"][0]["match"]["activity_id"] == "character-exercise"


def test_activity_coverage_api_reports_character_generic_and_sprite_fallback(client):  # noqa: F811
    project, character_ids, _ = setup_project(client, 2, 1)
    activity_folder = settings.DATA_DIR / "library" / "activities"
    activity_folder.mkdir(parents=True, exist_ok=True)
    character_picture = activity_folder / "character-left.png"
    generic_picture = activity_folder / "generic-straight.png"
    Image.new("RGB", (1280, 720), (20, 30, 40)).save(character_picture)
    Image.new("RGB", (1280, 720), (50, 60, 70)).save(generic_picture)
    speaker_ids = [speaker["id"] for speaker in project["speakers"]]
    with sqlite3.connect(settings.db_path) as connection:
        for index, (speaker_id, text) in enumerate(zip(
            speaker_ids + speaker_ids[:1],
            ("Turn left at the corner.", "Go straight for two blocks.", "Cross the street carefully."),
            strict=True,
        )):
            connection.execute(
                "INSERT INTO script_lines (id, project_id, line_index, speaker_id, text) VALUES (?, ?, ?, ?, ?)",
                (f"coverage-line-{index}", project["id"], index, speaker_id, text),
            )
        connection.execute(
            "INSERT INTO project_storyboards (project_id, status, source, updated_at) VALUES (?, 'approved', 'owner', 'now')",
            (project["id"],),
        )
        actions = ("turn left", "go straight", "cross the street")
        for index, action in enumerate(actions):
            connection.execute(
                "INSERT INTO project_beats (id, project_id, position, line_from, line_to, kind, speakers_json, action, "
                "expression, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'insert', ?, ?, 'calm', 'now', 'now')",
                (f"coverage-beat-{index}", project["id"], index, index, index, json.dumps([index % 2]), action),
            )
        connection.execute(
            "INSERT INTO activity_library (id, character_id, activity, path, content_sha, review_state, created_at, updated_at) "
            "VALUES ('character-left', ?, 'turn left', ?, 'sha-character-left', 'approved', 'now', 'now')",
            (character_ids[0], str(character_picture)),
        )
        connection.execute(
            "INSERT INTO activity_library (id, activity, aliases_json, path, content_sha, review_state, created_at, updated_at) "
            "VALUES ('generic-straight', 'directions', '[\"go straight\"]', ?, 'sha-generic-straight', 'approved', 'now', 'now')",
            (str(generic_picture),),
        )

    coverage = data(client.get(f"/api/projects/{project['id']}/visuals/activity-coverage"))

    assert (coverage["character"], coverage["generic"], coverage["missing"], coverage["matched"]) == (1, 1, 1, 2)
    assert [item["status"] for item in coverage["items"]] == ["character", "generic", "missing"]
    assert coverage["items"][2]["fallback"] == "sprites"


def test_successful_video_records_the_selected_activity_in_the_same_job(client, monkeypatch):  # noqa: F811
    project, _, _ = setup_project(client, 1, 1)
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute(
            "INSERT INTO audio_jobs (id, project_id, status, mp3_path, wav_path, timestamps_json, "
            "word_timestamps_json, duration_seconds) VALUES "
            "('audio-coverage', ?, 'complete', 'audio.mp3', 'audio.wav', '[]', '[]', 1.0)",
            (project["id"],),
        )
        connection.execute(
            "INSERT INTO activity_library (id, activity, path, content_sha, review_state, created_at, updated_at) "
            "VALUES ('used-activity', 'go straight', 'unused.png', 'sha-used-activity', 'approved', 'now', 'now')",
        )

    async def fake_render(*_args, **_kwargs):
        return {
            "mp4_path": "video.mp4", "srt_path": None, "background_image": None, "mode": "remotion",
            "activity_uses": [{"activity_id": "used-activity", "beat_id": "beat-straight"}],
        }

    monkeypatch.setattr(video_service, "generate_video", fake_render)
    generated = data(client.post(
        f"/api/projects/{project['id']}/video/generate",
        json={"template_id": "midnight", "renderer": "remotion", "visual_mode": "podcast_sprites"},
    ))
    history = data(client.get("/api/visuals/library/activities/used-activity/history"))
    item = data(client.get("/api/visuals/library/activities"))[0]

    assert item["use_count"] == 1 and item["last_used_at"]
    assert history[0]["beat_id"] == "beat-straight"
    assert history[0]["render_id"] == generated["id"]


def test_an_unmatched_insert_gets_the_closest_library_activities():
    """Gate B-23: "searching for travel accommodation" over lines about a cabin and a hotel matched nothing."""
    candidates = [_asset("h", None, "find hotel"), _asset("c", None, "check in hotel"), _asset("p", None, "packing"),
                  _asset("p2", "alex", "packing"), _asset("w", None, "working out")]
    text = "searching for travel accommodation finding a cabin is cheaper than a fancy hotel"
    assert suggest(candidates, text) == ["find hotel", "check in hotel"]
    assert suggest(candidates, "we should pack warm clothes") == []
    assert suggest(candidates, "start packing tonight", limit=1) == ["packing"]
