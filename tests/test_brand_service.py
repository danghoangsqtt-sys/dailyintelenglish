"""Phase 25 (D52-D55): the branded intro/outro lines, voice, timing and soundtrack wiring."""

import math

import numpy as np
import pytest
from pydub import AudioSegment
from pydub.generators import Sine

from app.core.config import settings
from app.core.constants import MUSIC_DUCK_DB
from app.core.exceptions import TTSError
from app.services import audio_service, brand_service, music_bed, video_renderer_remotion

SR = music_bed.SAMPLE_RATE


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path / "data")
    (tmp_path / "data" / "music_library").mkdir(parents=True)


@pytest.fixture
def fake_edge(monkeypatch):
    """Edge TTS without the network: a tone whose length follows the text."""
    calls = []

    class FakeCommunicate:
        def __init__(self, text, voice):
            self.text, self.voice = text, voice

        async def save(self, path):
            calls.append((self.text, self.voice))
            Sine(300).to_audio_segment(duration=60 * len(self.text)).apply_gain(-10).export(path, format="mp3")

    monkeypatch.setattr(brand_service.edge_tts, "Communicate", FakeCommunicate)
    return calls


# --- lines and timing -----------------------------------------------------------------------

def test_lines_are_deterministic_per_project_and_vary_across_projects():
    first = brand_service.brand_lines("project-a")
    assert first == brand_service.brand_lines("project-a")
    assert first["greeting_text"] == f"Welcome to Daily Intel English Channel! {first['wish']}"
    assert first["farewell_text"].startswith("Thanks for watching Daily Intel English! ")
    assert first["wish"] in brand_service.WISHES and first["farewell_line"] in brand_service.FAREWELLS
    wishes = {brand_service.brand_lines(f"project-{index}")["wish"] for index in range(60)}
    assert len(wishes) >= 8  # episodes get different wishes


def test_timing_follows_the_voice_with_a_minimum():
    assert brand_service.brand_timing(7.0, 6.6) == {"intro_s": 8.4, "outro_s": 8.9, "greeting_start_s": 0.4,
                                                    "farewell_start_s": 0.5}
    assert brand_service.brand_timing(None, None)["intro_s"] == brand_service.MIN_SLIDE_S
    assert brand_service.brand_timing(1.0, 1.0)["outro_s"] == brand_service.MIN_SLIDE_S


async def test_voice_is_jenny_and_cached(fake_edge):
    first = await brand_service.synthesize("Welcome to Daily Intel English Channel!")
    again = await brand_service.synthesize("Welcome to Daily Intel English Channel!")
    assert first == again and len(fake_edge) == 1
    assert fake_edge[0][1] == "en-US-JennyNeural"
    assert first["duration_s"] == pytest.approx(60 * 39 / 1000, abs=0.08)
    audio = await brand_service.brand_audio("project-a")
    assert audio["intro_s"] == pytest.approx(0.4 + audio["greeting"]["duration_s"] + 1.0, abs=0.01)


async def test_edge_failure_raises_tts_error_and_leaves_no_file(monkeypatch):
    class Broken:
        def __init__(self, *args):
            pass

        async def save(self, path):
            raise RuntimeError("No audio was received")

    monkeypatch.setattr(brand_service.edge_tts, "Communicate", Broken)
    monkeypatch.setattr(brand_service.asyncio, "sleep", lambda seconds: _noop())
    with pytest.raises(TTSError):
        await brand_service.synthesize("Hello")
    assert not list((settings.DATA_DIR / "brand_voice").glob("*"))


async def _noop():
    return None


# --- soundtrack + Remotion props ------------------------------------------------------------

async def mixed_job(tmp_path):
    line = tmp_path / "line.mp3"
    AudioSegment.silent(duration=3000, frame_rate=24000).export(str(line), format="mp3")
    Sine(110).to_audio_segment(duration=60000).apply_gain(-3).export(
        str(settings.DATA_DIR / "music_library" / "bed.mp3"), format="mp3")
    project = {"id": "proj-brand", "speakers": [{"id": "sp1", "name": "Lan"}]}
    lines = [{"id": "l0", "speaker_id": "sp1", "audio_cache_path": str(line), "text": "x"}]
    job = await audio_service.mix_project(project, lines, background_music_filename="bed.mp3")
    return {**job, "project_id": "proj-brand", "background_music": "bed.mp3", "status": "complete"}


def rms_db(track, start, end):
    window = track[:, int(start * SR):int(end * SR)]
    return 20 * math.log10(max(float(np.sqrt(np.mean(window ** 2))), 1e-9))


async def test_soundtrack_ducks_the_music_under_the_brand_voice(tmp_path):
    job = await mixed_job(tmp_path)
    # A silent "greeting" isolates the bed: open before it, ducked while it plays (2.0-5.0 s).
    greeting = tmp_path / "greeting.mp3"
    AudioSegment.silent(duration=3000, frame_rate=24000).export(str(greeting), format="mp3")
    output = tmp_path / "soundtrack.mp3"
    await audio_service.build_soundtrack(job, 8.0, 20.0, output, [(str(greeting), 2.0)])
    track = music_bed.decode(output)
    assert rms_db(track, 2.2, 4.8) - rms_db(track, 1.1, 1.4) == pytest.approx(MUSIC_DUCK_DB, abs=1.5)
    plain = tmp_path / "plain.mp3"
    await audio_service.build_soundtrack(job, 8.0, 20.0, plain)
    assert rms_db(music_bed.decode(plain), 2.2, 4.8) - rms_db(music_bed.decode(plain), 1.1, 1.4) ==         pytest.approx(0, abs=1.0)  # without the greeting the music stays open there


async def test_soundtrack_places_an_audible_greeting(tmp_path):
    job = await mixed_job(tmp_path)
    greeting = tmp_path / "greeting.mp3"
    Sine(900).to_audio_segment(duration=3000).export(str(greeting), format="mp3")
    voiced = tmp_path / "voiced.mp3"
    await audio_service.build_soundtrack(job, 8.0, 20.0, voiced, [(str(greeting), 2.0)])
    track = music_bed.decode(voiced)

    def band(start, end, hz):
        window = track[0, int(start * SR):int(end * SR)]
        spectrum = np.abs(np.fft.rfft(window))
        freqs = np.fft.rfftfreq(window.size, 1 / SR)
        return float(spectrum[(freqs > hz - 5) & (freqs < hz + 5)].max())

    # (The whole soundtrack is loudness-normalised, so compare within the one track.)
    assert band(2.4, 4.6, 900) > 3 * band(2.4, 4.6, 110)  # Jenny clearly over the ducked bed (~+10 dB)
    assert band(1.1, 1.4, 900) < 0.1 * band(1.1, 1.4, 110)  # before the greeting: music only


async def test_remotion_brand_props_and_timeline(tmp_path, monkeypatch, fake_edge):
    monkeypatch.setattr(video_renderer_remotion, "REMOTION_BRAND_DIR", tmp_path / "brand")
    props = {"lines": [{"endSec": 100.0}], "fps": 30, "introSec": 2.5, "outroSec": 5.0}
    voices = await video_renderer_remotion._add_brand("proj-brand", props)
    brand = props["brand"]
    assert brand["wish"] in brand_service.WISHES and brand["greetingPath"].startswith("remotion-render/brand/")
    assert (tmp_path / "brand" / brand["greetingPath"].split("/")[-1]).is_file()
    assert props["introSec"] > 2.5 and props["outroSec"] >= brand_service.MIN_SLIDE_S
    greeting_voice, farewell_voice = voices
    assert greeting_voice[1] == 0.4
    assert farewell_voice[1] == pytest.approx(
        (round(props["introSec"] * 30) + round(100.0 * 30)) / 30 + 0.5, abs=1e-6)


async def test_remotion_renders_silent_brand_slides_when_edge_is_down(monkeypatch):
    async def down(project_id):
        raise TTSError("offline")

    monkeypatch.setattr(brand_service, "brand_audio", down)
    props = {"lines": [{"endSec": 10.0}], "fps": 30, "introSec": 2.5, "outroSec": 5.0}
    assert await video_renderer_remotion._add_brand("proj", props) == []
    assert props["introSec"] == brand_service.MIN_SLIDE_S and "greetingPath" not in props["brand"]
    assert props["brand"]["wish"] in brand_service.WISHES
