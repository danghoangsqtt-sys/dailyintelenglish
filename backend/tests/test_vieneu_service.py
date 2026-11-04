"""Phase 87 (D125): the local VieNeu Vietnamese voice.

No real model runs here: the worker contract is exercised with a fake worker script run by this interpreter.
"""

import json
import sys
import textwrap

import pytest

from backend.ai.tts import tts_service, vieneu_service
from backend.content import project_service
from backend.core.exceptions import TTSError, ValidationError
from backend.core.voice import line_fingerprint, voice_parameters
from backend.schemas.project import ScriptConfig, SpeakerConfig, SpeakerUpdate


@pytest.fixture(autouse=True)
def isolated_files(tmp_path, monkeypatch):
    from backend.core.config import settings
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    yield
    vieneu_service.shutdown()


def test_capitalised_words_are_lowered_so_the_engine_does_not_spell_them():
    assert vieneu_service.tts_text("COM nghĩa là cùng nhau, PRESS là ép: EXPRESS.") == "com nghĩa là cùng nhau, press là ép: express."
    # acronyms without a vowel and known exam names stay; single letters and normal words are untouched
    assert vieneu_service.tts_text("BBC, IELTS và I like Compress") == "BBC, IELTS và I like Compress"


def test_align_words_takes_whisper_times_for_matched_words():
    heard = [{"text": "Compress", "start": 0.1, "end": 0.7}, {"text": "nén", "start": 0.8, "end": 1.0},
             {"text": "lại.", "start": 1.0, "end": 1.3}]
    boundaries, ratio = vieneu_service.align_words("Compress: nén lại.", heard, 1.5)
    assert ratio == 1.0
    assert boundaries == [("Compress", 0.1, 0.6), ("nén", 0.8, 0.2), ("lại", 1.0, 0.3)]


def test_align_words_spreads_unheard_words_over_the_gap_without_inventing_text():
    # Whisper heard "phaser ESS" for "press": the script word keeps its text and fills the gap between neighbours
    heard = [{"text": "con", "start": 0.0, "end": 0.3}, {"text": "phaser", "start": 0.4, "end": 0.7},
             {"text": "là", "start": 1.0, "end": 1.2}, {"text": "ép", "start": 1.2, "end": 1.5}]
    boundaries, ratio = vieneu_service.align_words("Com: press là ép", heard, 2.0)
    assert [b[0] for b in boundaries] == ["Com", "press", "là", "ép"]
    assert ratio == 0.5  # "Com" folds to "com", not "con"; "press" is not heard
    starts = [b[1] for b in boundaries]
    assert starts == sorted(starts)
    assert boundaries[0] == ("Com", 0.0, 0.375)  # shares 0.0..1.0 with "press" by length (3 : 5)
    assert boundaries[1] == ("press", 0.375, 0.625) and boundaries[2][1] == 1.0


def test_align_words_handles_an_empty_transcript_and_an_empty_line():
    boundaries, ratio = vieneu_service.align_words("Xin chào bạn", [], 1.2)
    assert ratio == 0.0 and [b[0] for b in boundaries] == ["Xin", "chào", "bạn"]
    assert boundaries[-1][1] + boundaries[-1][2] == pytest.approx(1.2, abs=0.01)
    assert vieneu_service.align_words("…", [], 1.0) == ([], 0.0)


def test_vieneu_speakers_accept_only_presets_and_resolve_a_default_voice():
    assert SpeakerConfig(name="A", tts_engine="vieneu", voice_id="Thiện Minh").voice_id == "Thiện Minh"
    with pytest.raises(ValueError):
        SpeakerConfig(name="A", tts_engine="vieneu", voice_id="en-US-GuyNeural")
    assert SpeakerUpdate(tts_engine="vieneu").tts_engine == "vieneu"
    params = voice_parameters({"tts_engine": "vieneu", "gender": "male", "speed": 0.9, "pitch": 0.4})
    assert params == {"engine": "vieneu", "speed": 0.9, "volume": 1.0, "voice_id": "Thiện Minh", "locale": "vi-VN"}
    with pytest.raises(ValidationError):
        voice_parameters({"tts_engine": "vieneu", "voice_id": "en-US-GuyNeural"})


async def test_synthesize_line_audio_uses_vieneu_and_writes_edge_shaped_word_timings(db, monkeypatch):
    config = ScriptConfig(name="VieNeu", topic="Word roots", cefr_level="B1", duration_minutes=1.0, num_speakers=1,
                          genre="small_talk", accent="american",
                          speakers=[SpeakerConfig(name="Cô Huyền", gender="female", tts_engine="vieneu")])
    project = await project_service.create_project(db, config)
    speaker = project["speakers"][0]
    assert speaker["resolved_voice_id"] == "Ngọc Huyền"
    line = {"id": "line-1", "speaker_id": speaker["id"], "text": "PRESS là ép."}
    seen = {}

    async def fake(text, spk):
        seen["text"], seen["voice"] = text, spk.get("voice_id")
        return b"ID3-fake", [("PRESS", 0.0, 0.4), ("là", 0.4, 0.2), ("ép", 0.6, 0.3)]

    monkeypatch.setattr(vieneu_service, "synthesize", fake)
    result = await tts_service.synthesize_line_audio(project, line)
    assert result["engine_used"] == "vieneu"
    from pathlib import Path
    words = json.loads(Path(result["audio_path"]).with_suffix(".words.json").read_text(encoding="utf-8"))
    assert words[0] == {"text": "PRESS", "offset_sec": 0.0, "duration_sec": 0.4}
    assert tts_service.cache_matches(project, {**line, "audio_cache_path": result["audio_path"]})
    assert line_fingerprint(project, line)["engine"] == "vieneu"


async def test_missing_environment_is_a_clear_error(monkeypatch, tmp_path):
    monkeypatch.setattr(vieneu_service, "VIENEU_PYTHON", tmp_path / "missing" / "python.exe")
    with pytest.raises(TTSError, match="setup_vieneu.ps1"):
        await vieneu_service.synthesize("Xin chào", {"tts_engine": "vieneu", "gender": "female"})


FAKE_WORKER = textwrap.dedent('''
    import json, sys, wave
    print(json.dumps({"status": "ready", "voices": ["Ngọc Huyền"]}), flush=True)
    count = 0
    for line in sys.stdin:
        request = json.loads(line)
        count += 1
        with wave.open(request["output_path"], "wb") as out:
            out.setnchannels(1); out.setsampwidth(2); out.setframerate(48000)
            out.writeframes(b"\\x00\\x00" * 48000)
        # the first take is "misheard" entirely; the second matches the script
        words = [] if count == 1 else [{"text": w, "start": i * 0.3, "end": i * 0.3 + 0.25}
                                       for i, w in enumerate(request["text"].split())]
        print(json.dumps({"status": "ok", "sample_rate": 48000, "duration_sec": 1.0, "words": words,
                          "echo": request["text"]}), flush=True)
''')


async def test_worker_contract_retries_a_misheard_take_and_scales_timings_to_the_speed(monkeypatch, tmp_path):
    worker = tmp_path / "fake_worker.py"
    worker.write_text(FAKE_WORKER, encoding="utf-8")
    monkeypatch.setattr(vieneu_service, "VIENEU_PYTHON", type(tmp_path)(sys.executable))
    monkeypatch.setattr(vieneu_service, "VIENEU_WORKER", worker)
    audio, boundaries = await vieneu_service.synthesize(
        "PRESS là ép", {"tts_engine": "vieneu", "voice_id": "Ngọc Huyền", "speed": 0.8})
    assert audio[:3] == b"ID3" or audio[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")
    assert [b[0] for b in boundaries] == ["PRESS", "là", "ép"]
    assert boundaries[1][1] == pytest.approx(0.3 / 0.8, abs=0.002)  # second take's times, slowed to 0.8
