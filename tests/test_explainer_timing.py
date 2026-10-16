"""Token coverage, real provider contractions, continuous pauses and refusal of guessed timestamps."""
import copy

import pytest

from backend.core.exceptions import ValidationError
from backend.library.explainer_timing import ScriptIndex, resolve_timeline
from backend.schemas.explainer import ExplainerSegment


LINES = [{"id": "L1", "text": "Let's — build a habit."}, {"id": "L2", "text": "Repeat it daily."}]
AUDIO = {"status": "complete", "duration_seconds": 3.8, "timestamps": [
    {"text": LINES[0]["text"], "start_sec": 0., "end_sec": 1.8},
    {"text": LINES[1]["text"], "start_sec": 2.1, "end_sec": 3.8},
], "word_timestamps": [
    {"line_id": "L1", "words": [{"text": text, "start_sec": start, "end_sec": end} for text, start, end in
        [("Let", .1, .25), ("'s", .25, .3), ("build", .4, .7), ("a", .8, .9), ("habit", 1., 1.4)]]},
    {"line_id": "L2", "words": [{"text": text, "start_sec": start, "end_sec": end} for text, start, end in
        [("Repeat", 2.2, 2.6), ("it", 2.7, 2.8), ("daily", 3., 3.4)]]},
]}


def segment(name, start_line, start_token, end_line, end_token, line_ids=None, gestures=None):
    return ExplainerSegment(id=name, intent="Explain this idea", line_ids=line_ids or [start_line],
        start={"line_id": start_line, "token_index": start_token}, end={"line_id": end_line, "token_index": end_token},
        visual={"kind": "text_card", "title": "An everyday idea"}, gestures=gestures or [])


def valid_segments():
    return [segment("s1", "L1", 0, "L1", 4, gestures=[{"at": {"line_id": "L1", "token_index": 0}, "gesture": "talk"}]),
            segment("s2", "L2", 0, "L2", 3)]


def test_real_word_contractions_punctuation_gaps_and_audio_tail_are_preserved():
    index = ScriptIndex(copy.deepcopy(LINES))
    assert len(index.tokens) == 7 and index.tokens[0].text == "Let's"
    timeline = resolve_timeline(index, copy.deepcopy(AUDIO))
    assert timeline.word_times[0] == (.1, .3), "split contraction events belong to one source token"
    resolved = timeline.segments(valid_segments())
    assert resolved[0]["start_sec"] == 0 and resolved[0]["end_sec"] == resolved[1]["start_sec"] == 2.2
    assert resolved[-1]["end_sec"] == 3.8, "measured silent tail remains covered"
    assert resolved[0]["gestures"][0]["at_sec"] == .1, "gesture uses word time, not the presentation's silent lead"


@pytest.mark.parametrize("segments", [
    [segment("s1", "L1", 1, "L1", 4), segment("s2", "L2", 0, "L2", 3)],
    [segment("s1", "L1", 0, "L1", 3), segment("s2", "L2", 0, "L2", 3)],
    [segment("s1", "L1", 0, "L1", 4), segment("s2", "L1", 3, "L2", 3, ["L1", "L2"])],
    [segment("s1", "L1", 0, "L1", 4)],
    [segment("s1", "missing", 0, "missing", 1)],
])
def test_incomplete_overlap_gap_and_removed_anchors_are_rejected(segments):
    with pytest.raises(ValidationError):
        ScriptIndex(LINES).validate_coverage(segments)


def test_gesture_at_exclusive_end_is_not_a_spoken_token():
    segments = valid_segments()
    segments[0] = segment("s1", "L1", 0, "L1", 4, gestures=[{"at": {"line_id": "L1", "token_index": 4}, "gesture": "wave"}])
    with pytest.raises(ValidationError, match="spoken token"):
        ScriptIndex(LINES).validate_coverage(segments)


@pytest.mark.parametrize("patch", [{"status": "error"}, {"word_timestamps": []}, {"duration_seconds": float("nan")}, {"timestamps": []}])
def test_stale_missing_or_malformed_audio_blocks_approval(patch):
    with pytest.raises(ValidationError):
        resolve_timeline(ScriptIndex(LINES), {**copy.deepcopy(AUDIO), **patch})


def test_provider_multiword_events_cannot_silently_interpolate_token_boundaries():
    audio = copy.deepcopy(AUDIO)
    audio["word_timestamps"][1]["words"] = [{"text": "Repeat it", "start_sec": 2.2, "end_sec": 2.8}, {"text": "daily", "start_sec": 3., "end_sec": 3.4}]
    with pytest.raises(ValidationError, match="combines"):
        resolve_timeline(ScriptIndex(LINES), audio)


def test_wrong_words_nonfinite_times_and_shifted_lines_are_rejected():
    for kind in ("wrong_word", "outside_line", "wrong_line", "duplicate_line"):
        audio = copy.deepcopy(AUDIO)
        if kind == "wrong_word":
            audio["word_timestamps"][0]["words"][0]["text"] = "Different"
        elif kind == "outside_line":
            audio["word_timestamps"][0]["words"][0]["start_sec"] = -1
        elif kind == "wrong_line":
            audio["timestamps"][0]["text"] = "Changed script"
        else:
            audio["word_timestamps"].append(audio["word_timestamps"][0])
        with pytest.raises(ValidationError):
            resolve_timeline(ScriptIndex(LINES), audio)


@pytest.mark.parametrize("start,end", [(True, .3), (float("inf"), .3), (.1, .1), (-.001, .3), (.1, 1.9)])
def test_invalid_word_intervals_are_rejected(start, end):
    audio = copy.deepcopy(AUDIO)
    audio["word_timestamps"][0]["words"][0].update(start_sec=start, end_sec=end)
    with pytest.raises(ValidationError):
        resolve_timeline(ScriptIndex(LINES), audio)


def test_overlapping_provider_events_cannot_clip_the_previous_word():
    audio = copy.deepcopy(AUDIO)
    audio["word_timestamps"][1]["words"][0]["end_sec"] = 2.75
    with pytest.raises(ValidationError, match="out of order"):
        resolve_timeline(ScriptIndex(LINES), audio)
