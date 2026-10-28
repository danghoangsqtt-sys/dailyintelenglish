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

    def _start_anchor(self, boundary: int) -> TokenAnchor:
        token = self.tokens[boundary]
        return TokenAnchor(line_id=token.line_id, token_index=token.token_index)

    def _end_anchor(self, boundary: int) -> TokenAnchor:
        token = self.tokens[boundary - 1]  # end anchors are exclusive: just after the segment's last word
        return TokenAnchor(line_id=token.line_id, token_index=token.token_index + 1)

    def snap(self, segments: list[ExplainerSegment]) -> list[ExplainerSegment]:
        """Phase 84 (real run 2026-10-28): the AI writes each segment's word anchors itself and one off-by-a-word anchor
        ("overlaps the preceding script span" / "leaves a gap") failed the whole plan, stopping automatic videos. Chain
        the segments instead: each starts where the previous ends, the first at the first word, the last ends at the last
        word; a segment left with no words is merged away; line ids and gestures follow. Anchors naming lines that do not
        exist are left for `validate_coverage` to explain."""
        try:
            ends = [self.boundary(segment.end) for segment in segments]
        except ValidationError:
            return segments
        snapped: list[ExplainerSegment] = []
        cursor, total = 0, len(self.tokens)
        for position, (segment, end) in enumerate(zip(segments, ends)):
            end = total if position == len(segments) - 1 else min(end, total)
            if end <= cursor:
                continue  # its words already belong to the previous segment
            start_anchor, end_anchor = self._start_anchor(cursor), self._end_anchor(end)
            gestures = [cue for cue in segment.gestures if cue.at.line_id in self.offsets
                        and cue.at.token_index < self.counts[cue.at.line_id] and cursor <= self.boundary(cue.at) < end]
            snapped.append(segment.model_copy(update={"start": start_anchor, "end": end_anchor, "gestures": gestures,
                                                      "line_ids": self.line_ids(start_anchor, end_anchor)}))
            cursor = end
        if snapped and cursor < total:  # the last segment was dropped as empty: the one before takes the rest
            last = snapped[-1]
            end_anchor = self._end_anchor(total)
            snapped[-1] = last.model_copy(update={"end": end_anchor, "line_ids": self.line_ids(last.start, end_anchor)})
        return snapped or segments

    def split_long(self, segments: list[ExplainerSegment], max_tokens: int, min_part: int = 6) -> list[ExplainerSegment]:
        """Phase 86 (VOX pace): a segment of more than `max_tokens` spoken words is cut at the sentence end nearest its
        middle; the later part becomes a quote of its own words with one highlighted word, so the picture changes at
        least every ~8 s. Segments already chained by `snap`; a locked owner segment or one without a sentence end to
        cut at is kept whole."""
        result: list[ExplainerSegment] = []
        queue = list(segments)
        taken = {segment.id for segment in segments}
        while queue:
            segment = queue.pop(0)
            start, end = self.boundary(segment.start), self.boundary(segment.end)
            cuts = [b for b in range(start + min_part, end - min_part + 1)
                    if self.tokens[b - 1].text.rstrip("\"'”’)").endswith((".", "!", "?"))]
            locked = segment.locks.content or segment.locks.visual
            if end - start <= max_tokens or not cuts or locked:
                result.append(segment)
                continue
            cut = min(cuts, key=lambda b: abs(b - (start + end) / 2))
            words = [token.text for token in self.tokens[cut:end]]
            text = " ".join(words)
            if len(text) > 220:
                text = text[:220].rsplit(" ", 1)[0]
            plain = [word.strip(".,!?;:\"'”’“‘()") for word in text.split()]
            highlight = max(plain, key=len) if plain else ""
            number, new_id = 2, f"{segment.id}-b"
            while new_id in taken:
                number += 1
                new_id = f"{segment.id}-b{number}"
            taken.add(new_id)
            first_end, second_start = self._end_anchor(cut), self._start_anchor(cut)
            first = segment.model_copy(update={
                "end": first_end, "line_ids": self.line_ids(segment.start, first_end),
                "gestures": [cue for cue in segment.gestures if self.boundary(cue.at) < cut]})
            second = ExplainerSegment.model_validate({
                "id": new_id, "intent": segment.intent, "start": second_start.model_dump(), "end": segment.end.model_dump(),
                "line_ids": self.line_ids(second_start, segment.end),
                "visual": {"kind": "quote", "text": text, "highlight": highlight if len(highlight) >= 4 else ""},
                "scene": segment.scene.model_dump() if segment.scene else None,
                "gestures": [cue.model_dump() for cue in segment.gestures if self.boundary(cue.at) >= cut],
                "source_notes": segment.source_notes})
            queue[:0] = [first, second]
        return result

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
