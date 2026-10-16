"""Script token coverage and actual mixed-audio word boundaries for Solo plans."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

from backend.core.constants import EXPLAINER_TIMING_EPSILON_SECONDS as TIMING_EPSILON_SECONDS
from backend.core.exceptions import ValidationError
from backend.schemas.explainer import ExplainerSegment, TokenAnchor


def normalized_word(text: str) -> str:
    """Compare source/provider spelling across punctuation, curly apostrophes and contractions."""
    return "".join(character for character in text.casefold() if character.isalnum())


@dataclass(frozen=True)
class SpeechToken:
    """A spoken whitespace token with exact original character offsets; punctuation-only chunks are excluded."""
    line_id: str
    token_index: int
    text: str
    char_start: int
    char_end: int


class ScriptIndex:
    """Stable script order and end-exclusive boundary validation, independent of audio availability."""

    def __init__(self, lines: list[dict]) -> None:
        self.lines = lines
        self.tokens: list[SpeechToken] = []
        self.offsets: dict[str, int] = {}
        self.counts: dict[str, int] = {}
        self.positions: dict[str, int] = {}
        for position, line in enumerate(lines):
            lid = str(line["id"])
            if lid in self.offsets:
                raise ValidationError("Script line IDs must be unique")
            self.offsets[lid] = len(self.tokens)
            self.positions[lid] = position
            chunks = [match for match in re.finditer(r"\S+", line["text"]) if normalized_word(match.group())]
            if not chunks:
                raise ValidationError("Each explainer line needs spoken words; remove empty/punctuation-only lines")
            self.counts[lid] = len(chunks)
            self.tokens.extend(SpeechToken(lid, i, match.group(), match.start(), match.end()) for i, match in enumerate(chunks))
        if not self.tokens:
            raise ValidationError("Write a script before proposing an explainer plan")

    def boundary(self, anchor: TokenAnchor) -> int:
        """Resolve a source anchor into one global boundary, including the final end boundary."""
        if anchor.line_id not in self.offsets:
            raise ValidationError(f"Script line {anchor.line_id} no longer exists; review or unlock its segment")
        if anchor.token_index > self.counts[anchor.line_id]:
            raise ValidationError(f"Token anchor exceeds the current words in line {anchor.line_id}")
        return self.offsets[anchor.line_id] + anchor.token_index

    def line_ids(self, start: TokenAnchor, end: TokenAnchor) -> list[str]:
        """Ordered anchor-inclusive line IDs; actual coverage is always checked at token level."""
        self.boundary(start)
        self.boundary(end)
        first, last = self.positions[start.line_id], self.positions[end.line_id]
        if first > last:
            raise ValidationError("Segment anchors are reversed")
        return [str(line["id"]) for line in self.lines[first:last + 1]]

    def validate_coverage(self, segments: list[ExplainerSegment]) -> list[tuple[int, int]]:
        """Require every spoken token exactly once, in script order, with no gaps/overlaps."""
        spans = []
        cursor = 0
        for segment in segments:
            start, end = self.boundary(segment.start), self.boundary(segment.end)
            if start != cursor:
                reason = "overlaps" if start < cursor else "leaves a gap before"
                raise ValidationError(f"Segment {segment.id} {reason} the preceding script span")
            if end <= start:
                raise ValidationError(f"Segment {segment.id} contains no spoken tokens or is reversed")
            if segment.line_ids != self.line_ids(segment.start, segment.end):
                raise ValidationError(f"Segment {segment.id} line IDs must follow its current anchors in script order")
            for cue in segment.gestures:
                at = self.boundary(cue.at)
                if cue.at.token_index >= self.counts[cue.at.line_id] or not start <= at < end:
                    raise ValidationError(f"Gesture in segment {segment.id} must point to a spoken token inside that segment")
            spans.append((start, end))
            cursor = end
        if cursor != len(self.tokens):
            raise ValidationError("Explainer segments must cover the complete spoken script")
        return spans


@dataclass(frozen=True)
class SpeechTimeline:
    """Actual word starts/ends plus continuous presentation boundaries including measured silent gaps/tails."""
    index: ScriptIndex
    word_times: tuple[tuple[float, float], ...]
    boundaries: tuple[float, ...]
    duration_seconds: float

    def segments(self, segments: list[ExplainerSegment]) -> list[dict]:
        """Resolve segment/cue timing from the same verified source index."""
        spans = self.index.validate_coverage(segments)
        results = []
        for segment, (start, end) in zip(segments, spans, strict=True):
            if self.boundaries[end] <= self.boundaries[start]:
                raise ValidationError("A segment's real audio interval is empty; review its token boundaries")
            results.append({"id": segment.id, "start_sec": self.boundaries[start], "end_sec": self.boundaries[end],
                            "gestures": [{"gesture": cue.gesture, "at_sec": self.word_times[self.index.boundary(cue.at)][0]}
                                         for cue in segment.gestures]})
        return results


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValidationError("Audio word timing must contain finite numbers")
    return float(value)


def _line_times(tokens: list[SpeechToken], words: list[dict], start: float, end: float) -> list[tuple[float, float]]:
    events = []
    character_cursor = 0
    last_end = start
    for word in words:
        key = normalized_word(str(word.get("text", "")))
        if not key:
            continue
        begin, finish = _number(word.get("start_sec")), _number(word.get("end_sec"))
        if begin < start - TIMING_EPSILON_SECONDS or finish > end + TIMING_EPSILON_SECONDS or finish <= begin or begin < 0 or begin < last_end - TIMING_EPSILON_SECONDS:
            raise ValidationError("Audio word timings are outside or out of order within their line; regenerate audio")
        events.append((character_cursor, character_cursor + len(key), begin, finish, key))
        character_cursor += len(key)
        last_end = finish
    if "".join(normalized_word(token.text) for token in tokens) != "".join(event[4] for event in events):
        raise ValidationError("Word timings do not match the current script; regenerate audio before approval")
    starts = {event[0]: event[2] for event in events}
    ends = {event[1]: event[3] for event in events}
    times = []
    cursor = 0
    for token in tokens:
        length = len(normalized_word(token.text))
        if cursor not in starts or cursor + length not in ends:
            raise ValidationError("A provider event combines several script words; exact token timing is unavailable")
        times.append((starts[cursor], ends[cursor + length]))
        cursor += length
    return times


def resolve_timeline(index: ScriptIndex, audio: dict | None) -> SpeechTimeline:
    """Verify complete audio and map punctuation/contractions without estimating timestamps."""
    if not audio or audio.get("status") != "complete":
        raise ValidationError("Generate current audio with word timings before approving this plan")
    duration = _number(audio.get("duration_seconds"))
    if duration <= 0:
        raise ValidationError("Audio duration must be positive")
    measured_lines = audio.get("timestamps") or []
    if len(measured_lines) != len(index.lines):
        raise ValidationError("Audio line timings no longer match the script; regenerate audio")
    by_line = {}
    for item in audio.get("word_timestamps") or []:
        lid = item.get("line_id")
        if lid in by_line:
            raise ValidationError("Duplicate line word timings")
        by_line[lid] = item.get("words") or []
    if set(by_line) != set(index.offsets):
        raise ValidationError("Some script lines have missing or stale word timings; regenerate audio")
    times = []
    previous_end = 0.0
    for line, measured in zip(index.lines, measured_lines, strict=True):
        if " ".join(line["text"].split()) != " ".join(str(measured.get("text", "")).split()):
            raise ValidationError("Audio line content no longer matches the script; regenerate audio")
        start, end = _number(measured.get("start_sec")), _number(measured.get("end_sec"))
        if start < 0 or start < previous_end - TIMING_EPSILON_SECONDS or end <= start or end > duration + TIMING_EPSILON_SECONDS:
            raise ValidationError("Audio line intervals are invalid or overlapping")
        lid = str(line["id"])
        offset, count = index.offsets[lid], index.counts[lid]
        times.extend(_line_times(index.tokens[offset:offset + count], by_line[lid], start, end))
        previous_end = end
    if len(times) != len(index.tokens):
        raise ValidationError("Audio cannot resolve every spoken script token")
    # Use the measured audio extent for leading/trailing silence. Internal boundaries
    # are real next-word starts, so pauses remain visible and no word gets clipped.
    boundaries = (0.0, *(time[0] for time in times[1:]), duration)
    if any(right < left for left, right in zip(boundaries, boundaries[1:])):
        raise ValidationError("Audio token boundaries are not ordered")
    return SpeechTimeline(index, tuple(times), boundaries, duration)
