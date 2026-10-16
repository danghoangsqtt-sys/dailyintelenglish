"""Voice-aware cache reuse and stale publication across synthesis, mix and render."""

import asyncio
import copy
import json
from pathlib import Path

import pytest

from backend.ai.tts import tts_service
from backend.api import audio as audio_api, shorts as shorts_api, tts as tts_api, video as video_api
from backend.content import project_service, script_service, shorts_service
from backend.core.config import settings
from backend.core.exceptions import AudioMixError, ConflictError, TTSError, ValidationError
from backend.core.voice import line_fingerprint
from backend.db.transactions import write_transaction
from backend.media import audio_service, video_service, video_renderer_remotion
from backend.schemas.audio import GenerateAudioRequest
from backend.schemas.project import ScriptConfig, SpeakerUpdate
from backend.schemas.tts import PreviewLineRequest
from backend.schemas.video import GenerateVideoRequest
from tests.test_character_voice_selection import config

REAL_SYNTHESIZE = tts_service._synthesize_edge_tts


@pytest.fixture(autouse=True)
def isolated_media(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)

    async def fake_speech(text, speaker):
        return speaker["voice_id"].encode(), [tts_service.WordBoundary(text.split()[0], 0.0, 0.2)]

    monkeypatch.setattr(tts_service, "_synthesize_edge_tts", fake_speech)


async def project_with_cache(db):
    project = await project_service.create_project(db, ScriptConfig(**config()))
    lines = await script_service.save_script(db, project["id"], [
        {"speaker_id": speaker["id"], "text": f"Example number {index}."}
        for index, speaker in enumerate(project["speakers"])
    ])
    for line in lines:
        result = await tts_service.synthesize_line(db, project, line)
        line["audio_cache_path"] = result["audio_path"]
    return await project_service.get_project(db, project["id"]), lines


async def change_voice(db, project, index=0):
    speaker = project["speakers"][index]
    async with write_transaction(db):
        await project_service.mark_speaker_voice_changed(db, project["id"], commit=False, speaker_id=speaker["id"])
        await project_service.update_speaker(
            db, project["id"], speaker["id"], SpeakerUpdate(voice_id="en-GB-RyanNeural"), commit=False,
        )


async def existing_jobs(db, project):
    folder = settings.DATA_DIR / "previous"
    folder.mkdir(exist_ok=True)
    for name in ("mix.mp3", "mix.wav", "video.mp4", "video_vertical.mp4", "subtitles.srt"):
        (folder / name).write_bytes(f"last-good-{name}".encode())
    audio = await audio_service.save_audio_job(
        db, project["id"], status="complete", mp3_path=str(folder / "mix.mp3"), wav_path=str(folder / "mix.wav"),
        timestamps=[{"start_sec": 0, "end_sec": 1, "text": "Example", "speaker_id": project["speakers"][0]["id"]}],
    )
    video = await video_service.save_video_job(
        db, project["id"], status="complete", mp4_path=str(folder / "video.mp4"),
        mp4_path_vertical=str(folder / "video_vertical.mp4"), srt_path=str(folder / "subtitles.srt"),
    )
    return audio, video, {path: path.read_bytes() for path in folder.iterdir()}


@pytest.mark.parametrize("field,value", [
    ("voice_id", "en-GB-RyanNeural"), ("speed", 1.2), ("pitch", 0.3), ("volume", 0.8),
    ("tts_engine", "unsupported"),
])
async def test_fingerprint_checks_every_effective_synthesis_input(db, field, value):
    project, lines = await project_with_cache(db)
    line = lines[0]
    assert tts_service.cache_matches(project, line)
    stored = Path(line["audio_cache_path"])
    metadata = json.loads(stored.with_suffix(".tts.json").read_text(encoding="utf-8"))
    assert metadata == line_fingerprint(project, line)
    changed = copy.deepcopy(project)
    changed["speakers"][0][field] = value
    assert not tts_service.cache_matches(changed, line)
    assert not tts_service.cache_matches(project, {**line, "text": "A changed sentence."})
    assert stored.read_bytes() == project["speakers"][0]["voice_id"].encode()


async def test_legacy_cache_is_read_only_and_reuse_requires_no_network(db, monkeypatch):
    project, lines = await project_with_cache(db)
    path = Path(lines[0]["audio_cache_path"])
    path.with_suffix(".tts.json").unlink()
    before = path.stat().st_mtime_ns
    assert tts_service.cache_matches(project, lines[0])
    assert not tts_service.cache_matches(project, lines[0], allow_legacy=False)

    async def forbidden(*args):
        raise AssertionError("An unchanged cached line must not be synthesized again")

    monkeypatch.setattr(tts_service, "_synthesize_edge_tts", forbidden)
    result = await tts_api.preview_line(project["id"], PreviewLineRequest(line_id=lines[0]["id"], reuse_cached=True), db)
    assert result["data"]["reused"] and result["data"]["audio_path"] == str(path)
    assert path.stat().st_mtime_ns == before
    assert not path.with_suffix(".tts.json").exists()


async def test_voice_change_invalidates_only_one_speaker_and_keeps_media(db):
    project, lines = await project_with_cache(db)
    audio, video, previous = await existing_jobs(db, project)
    old_line_files = {Path(line["audio_cache_path"]): Path(line["audio_cache_path"]).read_bytes() for line in lines}
    await change_voice(db, project)
    current = await audio_service.get_lines_for_mixing(db, project["id"])
    assert current[0]["audio_cache_path"] is None
    assert current[1]["audio_cache_path"] == lines[1]["audio_cache_path"]
    stale_audio = await audio_service.get_audio_job(db, project["id"])
    stale_video = await video_service.get_video_job(db, project["id"])
    assert stale_audio["status"] == stale_video["status"] == "error"
    assert stale_audio["mp3_path"] == audio["mp3_path"]
    assert stale_video["mp4_path"] == video["mp4_path"]
    assert "Generate audio" in stale_audio["error_message"]
    for path, content in {**previous, **old_line_files}.items():
        assert path.read_bytes() == content
    new = await tts_api.preview_line(project["id"], PreviewLineRequest(line_id=lines[0]["id"], reuse_cached=True), db)
    new_path = Path(new["data"]["audio_path"])
    assert new_path != Path(lines[0]["audio_cache_path"])
    assert new_path.read_bytes() == b"en-GB-RyanNeural"
    assert new_path.with_suffix(".words.json").is_file()
    assert json.loads(new_path.with_suffix(".tts.json").read_text())["voice_id"] == "en-GB-RyanNeural"
    assert (await audio_service.get_lines_for_mixing(db, project["id"]))[1]["audio_cache_path"] == lines[1]["audio_cache_path"]


async def test_rename_clears_only_lines_whose_spoken_text_changed(db):
    project, lines = await project_with_cache(db)
    await db.execute("UPDATE script_lines SET text='Hello Alex.' WHERE id=?", (lines[1]["id"],))
    await db.commit()
    await project_service.rename_speaker(db, project["id"], project["speakers"][0]["id"], "Ryan")
    current = await audio_service.get_lines_for_mixing(db, project["id"])
    assert current[0]["audio_cache_path"] == lines[0]["audio_cache_path"]
    assert current[1]["audio_cache_path"] is None and current[1]["text"] == "Hello Ryan."


@pytest.mark.parametrize("fails", [False, True])
async def test_stale_tts_cannot_publish_or_overwrite_previous_file(db, monkeypatch, fails):
    project, lines = await project_with_cache(db)
    path = Path(lines[0]["audio_cache_path"])
    previous = path.read_bytes()
    started, release = asyncio.Event(), asyncio.Event()

    async def slow_speech(text, speaker):
        started.set()
        await release.wait()
        if fails:
            raise TTSError("Provider unavailable")
        return b"obsolete speech", [tts_service.WordBoundary("Example", 0, 0.2)]

    monkeypatch.setattr(tts_service, "_synthesize_edge_tts", slow_speech)
    task = asyncio.create_task(tts_api.preview_line(project["id"], PreviewLineRequest(line_id=lines[0]["id"]), db))
    await asyncio.wait_for(started.wait(), 2)
    try:
        await change_voice(db, project)
    finally:
        release.set()
    with pytest.raises(TTSError if fails else ConflictError):
        await asyncio.wait_for(task, 3)
    assert path.read_bytes() == previous
    assert (await audio_service.get_lines_for_mixing(db, project["id"]))[0]["audio_cache_path"] is None


@pytest.mark.parametrize("fails", [False, True])
async def test_stale_mix_does_not_publish_or_mark_new_source_failed(db, monkeypatch, fails):
    project, _ = await project_with_cache(db)
    original, _, previous = await existing_jobs(db, project)
    started, release = asyncio.Event(), asyncio.Event()

    async def slow_mix(snapshot, lines, music):
        assert snapshot["_attempt_id"]
        started.set()
        await release.wait()
        if fails:
            raise AudioMixError("Old attempt failed")
        return {"mp3_path": "obsolete.mp3", "wav_path": "obsolete.wav", "timestamps": [], "word_timestamps": [],
                "duration_seconds": 1, "loudness_lufs": -16}

    monkeypatch.setattr(audio_service, "mix_project", slow_mix)
    task = asyncio.create_task(audio_api.generate_audio(project["id"], GenerateAudioRequest(), db))
    await asyncio.wait_for(started.wait(), 2)
    try:
        await change_voice(db, project)
    finally:
        release.set()
    with pytest.raises(AudioMixError if fails else ConflictError):
        await asyncio.wait_for(task, 3)
    current = await audio_service.get_audio_job(db, project["id"])
    assert current["mp3_path"] == original["mp3_path"]
    assert "Voice or script changed" in current["error_message"]
    for path, content in previous.items():
        assert path.read_bytes() == content


@pytest.mark.parametrize("vertical", [False, True])
async def test_voice_edit_during_render_keeps_last_good_video(db, monkeypatch, vertical):
    project, _ = await project_with_cache(db)
    _, original, previous = await existing_jobs(db, project)
    started, release = asyncio.Event(), asyncio.Event()

    async def slow_render(db, snapshot, audio_job, learning, output_path, **kwargs):
        assert snapshot["_attempt_id"] in output_path.parts
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"obsolete render")
        started.set()
        await release.wait()
        return {"mp4_path": str(output_path), "mode": "remotion"}

    monkeypatch.setattr(video_service, "renderer_problem", lambda: None)
    monkeypatch.setattr(video_renderer_remotion, "render_via_remotion", slow_render)
    method = video_api.generate_vertical if vertical else video_api.generate_video
    task = asyncio.create_task(method(project["id"], GenerateVideoRequest(), db))
    await asyncio.wait_for(started.wait(), 2)
    try:
        await change_voice(db, project)
    finally:
        release.set()
    with pytest.raises(ConflictError):
        await asyncio.wait_for(task, 3)
    current = await video_service.get_video_job(db, project["id"])
    assert current["mp4_path"] == original["mp4_path"]
    assert current["mp4_path_vertical"] == original["mp4_path_vertical"]
    for path, content in previous.items():
        assert path.read_bytes() == content
    with pytest.raises(ValidationError):
        await video_api.generate_video(project["id"], GenerateVideoRequest(), db)


async def test_explicit_invalid_voice_is_not_silently_replaced(monkeypatch):
    async def forbidden(*args):
        raise AssertionError("No provider call for an invalid explicit ID")

    monkeypatch.setattr(tts_service, "_synthesize_edge_tts", REAL_SYNTHESIZE)
    monkeypatch.setattr(tts_service.edge_tts, "Communicate", forbidden)
    with pytest.raises(ValidationError):
        await tts_service._synthesize_edge_tts("Hello", {"voice_id": "not-a-voice", "accent": "american", "gender": "male"})


async def test_soundtrack_uses_selected_attempt_voice_stem(tmp_path, monkeypatch):
    music = tmp_path / "music_library" / "bed.mp3"
    music.parent.mkdir()
    music.write_bytes(b"music")
    canonical = audio_service.voice_stem_path("project")
    canonical.parent.mkdir(parents=True)
    canonical.write_bytes(b"old voice")
    selected = canonical.parent / "new-attempt" / "voice.wav"
    selected.parent.mkdir()
    selected.write_bytes(b"new voice")
    captured = []

    def fake_build(voice, *args):
        captured.append(voice.read_bytes())
        return {"path": "output"}

    monkeypatch.setattr(audio_service, "_build_soundtrack_sync", fake_build)
    job = {"project_id": "project", "wav_path": str(selected.with_name("mix.wav")), "background_music": "bed.mp3", "timestamps": []}
    assert await audio_service.build_soundtrack(job, 0, 1, tmp_path / "out.mp3")
    assert captured == [b"new voice"]
    selected.unlink()
    assert await audio_service.build_soundtrack(job, 0, 1, tmp_path / "out.mp3") is None
    assert captured == [b"new voice"]  # never fall back to an unrelated old stem


async def test_short_render_rejects_voice_change_and_keeps_old_clip(db, monkeypatch):
    project, _ = await project_with_cache(db)
    await existing_jobs(db, project)
    timestamps = [{"start_sec": 0, "end_sec": 45, "text": "Example", "speaker_id": project["speakers"][0]["id"]}]
    await db.execute("UPDATE audio_jobs SET timestamps_json=? WHERE project_id=?", (json.dumps(timestamps), project["id"]))
    clip = await shorts_service.create_clip(db, project["id"], 0, 0, "A clear example")
    folder = shorts_service.clip_folder(project["id"], clip["id"])
    folder.mkdir(parents=True)
    old = folder / "clip.mp4"
    cover = folder / "cover.jpg"
    old.write_bytes(b"previous clip")
    cover.write_bytes(b"previous cover")
    await db.execute("UPDATE short_clips SET status='approved', mp4_path=?, cover_path=? WHERE id=?",
                     (str(old), str(cover), clip["id"]))
    await db.commit()
    started, release = asyncio.Event(), asyncio.Event()

    async def slow_render(db, snapshot, audio_job, learning, output_path, **kwargs):
        assert snapshot["_attempt_id"] in output_path.parts
        output_path.parent.mkdir(parents=True)
        output_path.write_bytes(b"new clip")
        started.set()
        await release.wait()
        return {"mp4_path": str(output_path)}

    async def fake_cover(db, snapshot, clip):
        path = folder / snapshot["_attempt_id"] / "cover.jpg"
        path.write_bytes(b"new cover")
        return str(path)

    monkeypatch.setattr(video_service, "renderer_problem", lambda: None)
    monkeypatch.setattr(video_renderer_remotion, "render_via_remotion", slow_render)
    monkeypatch.setattr(shorts_service, "render_cover", fake_cover)
    task = asyncio.create_task(shorts_api.render_clip(project["id"], clip["id"], shorts_api.RenderRequest(), db))
    await asyncio.wait_for(started.wait(), 2)
    try:
        await change_voice(db, project)
    finally:
        release.set()
    with pytest.raises(ConflictError):
        await asyncio.wait_for(task, 3)
    current = await shorts_service.get_clip(db, project["id"], clip["id"])
    assert current["status"] == "proposed"
    assert current["mp4_path"] == str(old) and current["cover_path"] == str(cover)
    assert old.read_bytes() == b"previous clip" and cover.read_bytes() == b"previous cover"


async def test_remotion_stages_audio_per_attempt(tmp_path, monkeypatch):
    stage = tmp_path / "public-audio"
    monkeypatch.setattr(video_renderer_remotion, "REMOTION_AUDIO_DIR", stage)
    captured = []

    async def props(*args, **kwargs):
        return {"episodeId": "project", "speakers": [], "lines": [], "audioPath": "old.mp3"}

    async def no_brand(*args):
        return []

    async def no_music(*args):
        return None

    def render(input_props, output, frames):
        captured.append(input_props.copy())
        return {"mp4_path": str(output)}

    monkeypatch.setattr(video_renderer_remotion, "_build_input_props", props)
    monkeypatch.setattr(video_renderer_remotion, "_add_brand", no_brand)
    monkeypatch.setattr(video_renderer_remotion, "_build_soundtrack", no_music)
    monkeypatch.setattr(video_renderer_remotion, "_render_via_remotion_sync", render)
    for attempt in ("first", "second"):
        audio = tmp_path / f"{attempt}.mp3"
        audio.write_bytes(attempt.encode())
        await video_renderer_remotion.render_via_remotion(
            None, {"id": "project", "_attempt_id": attempt}, {"mp3_path": str(audio)}, None, tmp_path / f"{attempt}.mp4",
        )
    assert [item["episodeId"] for item in captured] == ["project", "project"]
    assert [item["audioPath"] for item in captured] == [
        "remotion-render/audio/project-first.mp3", "remotion-render/audio/project-second.mp3",
    ]
    assert (stage / "project-first.mp3").read_bytes() == b"first"
    assert (stage / "project-second.mp3").read_bytes() == b"second"


async def test_new_horizontal_after_voice_change_does_not_republish_old_vertical(db, monkeypatch):
    project, lines = await project_with_cache(db)
    _, old_video, previous = await existing_jobs(db, project)
    await change_voice(db, project)
    await tts_api.preview_line(project["id"], PreviewLineRequest(line_id=lines[0]["id"]), db)

    async def new_mix(snapshot, lines, music):
        folder = settings.DATA_DIR / "audio" / project["id"] / snapshot["_attempt_id"]
        folder.mkdir(parents=True)
        for name in ("mix.mp3", "mix.wav"):
            (folder / name).write_bytes(b"new voice mix")
        return {"mp3_path": str(folder / "mix.mp3"), "wav_path": str(folder / "mix.wav"),
                "timestamps": [], "word_timestamps": [], "duration_seconds": 1, "loudness_lufs": -16}

    async def new_render(db, snapshot, audio_job, learning, output_path, **kwargs):
        output_path.parent.mkdir(parents=True)
        output_path.write_bytes(b"new horizontal")
        return {"mp4_path": str(output_path), "mode": "remotion"}

    monkeypatch.setattr(audio_service, "mix_project", new_mix)
    monkeypatch.setattr(video_service, "renderer_problem", lambda: None)
    monkeypatch.setattr(video_renderer_remotion, "render_via_remotion", new_render)
    await audio_api.generate_audio(project["id"], GenerateAudioRequest(), db)
    updated = (await video_api.generate_video(project["id"], GenerateVideoRequest(), db))["data"]
    assert updated["status"] == "complete" and updated["mp4_path"] != old_video["mp4_path"]
    assert updated["mp4_path_vertical"] is None
    for path, content in previous.items():
        assert path.read_bytes() == content
