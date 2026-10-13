"""Pure, explainable selection of reviewed activity images for storyboard insert beats."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

MATCH_THRESHOLD = 70


def normalize(value: str) -> str:
    plain = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    return " ".join(re.findall(r"[a-z0-9]+", plain))


def _contains(query: str, phrase: str) -> bool:
    words = set(normalize(query).split())
    wanted = set(normalize(phrase).split())
    return bool(wanted) and wanted <= words


def _score(candidate: dict[str, Any], query: str, contexts: list[str]) -> tuple[int, str] | None:
    if _contains(query, candidate["activity"]):
        score, reason = 80, f"activity '{candidate['activity']}'"
    else:
        alias = next((value for value in candidate.get("aliases", []) if _contains(query, value)), None)
        if alias is None:
            return None
        score, reason = 70, f"alias '{alias}'"
    matching_contexts = [tag for tag in candidate.get("context_tags", []) if tag in contexts]
    if matching_contexts:
        score += min(15, 5 * len(matching_contexts))
        reason += f" + context {', '.join(matching_contexts)}"
    return score, reason


def suggest(candidates: list[dict[str, Any]], text: str, limit: int = 3) -> list[str]:
    """Gate B-23 finding: the closest library activities for an insert that matched none, by the share of the activity's words
    found in ``text`` (a word also counts when the text has it with an ending: "finding" for "find")."""
    words = normalize(text).split()
    scored: dict[str, float] = {}
    for candidate in candidates:
        wanted = normalize(candidate["activity"]).split()
        if not wanted:
            continue
        found = sum(any(word == want or (len(want) >= 3 and word.startswith(want)) for word in words) for want in wanted)
        if found:
            scored[candidate["activity"]] = max(scored.get(candidate["activity"], 0.0), found / len(wanted))
    return [name for name, _ in sorted(scored.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def beat_speaker_index(beat: dict[str, Any], line_speakers: list[int | None], line_texts: list[str]) -> int | None:
    """Task 32.8a (BUG-029, D76): whose activity pictures an insert beat should prefer.

    One index in ``beat["speakers"]`` names that person. Otherwise (the storyboard leaves inserts as ``[]``) the beat's own
    lines decide: a single speaker wins; with two, the speaker of the one line that mentions the action, else the first line's.
    ``line_speakers``/``line_texts`` are indexed by line index; ``None`` means the speaker is unknown.
    """
    speakers = beat.get("speakers") or []
    if len(speakers) == 1:
        return speakers[0]
    span = range(max(0, beat["line_from"]), min(beat["line_to"], len(line_speakers) - 1) + 1)
    lines = [(line_speakers[index], line_texts[index]) for index in span if line_speakers[index] is not None]
    distinct = list(dict.fromkeys(speaker for speaker, _ in lines))
    if len(distinct) <= 1:
        return distinct[0] if distinct else None
    naming = list(dict.fromkeys(speaker for speaker, text in lines if _contains(text, beat.get("action") or "")))
    return naming[0] if len(naming) == 1 else lines[0][0]


def match_activity(
    candidates: list[dict[str, Any]], character_id: str | None, action: str, dialogue: str, contexts: list[str] | None = None,
) -> dict[str, Any] | None:
    """Return the best approved candidate or ``None``; callers provide only valid approved rows.

    Character-specific candidates have an absolute priority over generic ones once both clear the semantic threshold. Other named
    characters are excluded before scoring. Lower use count/older last use rotates equal semantic variants deterministically.
    """
    query, normalized_contexts = f"{action} {dialogue}", [normalize(value) for value in contexts or []]
    ranked = []
    for candidate in candidates:
        scope = candidate.get("character_id")
        if scope not in (None, character_id):
            continue
        scored = _score(candidate, query, normalized_contexts)
        if scored is None or scored[0] < MATCH_THRESHOLD:
            continue
        score, reason = scored
        ranked.append((0 if scope == character_id and character_id else 1, -score, candidate.get("use_count", 0),
                       candidate.get("last_used_at") or "", candidate["id"], score, reason, candidate))
    if not ranked:
        return None
    _, _, _, _, _, score, reason, candidate = min(ranked)
    return {"activity_id": candidate["id"], "match_type": "character" if candidate.get("character_id") else "generic",
            "score": score, "reason": reason, "asset": candidate}
