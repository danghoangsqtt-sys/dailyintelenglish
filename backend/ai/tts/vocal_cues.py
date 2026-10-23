"""Supported inline vocal directions in an otherwise English script line."""

import re
from itertools import islice
from typing import NamedTuple

from backend.core.constants import VOCAL_CUE_LOW_CLAUSE_MAX_WORDS, VOCAL_CUE_LOW_PITCH_DELTA_HZ


class VocalPart(NamedTuple):
    """A dialogue span or a named vocal cue, in source order."""

    kind: str
    text: str
    pitch_delta_hz: int = 0


_CUE = re.compile(r"\[(cười(?::ha-ha|:hi-hi)?|thở dài|hắng giọng)\]", re.IGNORECASE)
_SPOKEN = {
    "cười": "Ha, ha, ha!",
    "cười:ha-ha": "Ha, ha!",
    "cười:hi-hi": "Hee, hee!",
    "thở dài": "Ahh...",
    "hắng giọng": "Ahem.",
}
_CLAUSE_PUNCTUATION = re.compile(r"[,.!?;:]")


def to_omnivoice_text(text: str) -> str:
    """Translate supported app cues to OmniVoice's native non-verbal tokens.

    OmniVoice documents laughter and sigh tags, but not throat-clearing. Refuse that
    line rather than pronounce the editorial cue or silently switch engines.
    """
    if re.search(r"\[h\u1eafng gi\u1ecdng\]", text, re.IGNORECASE):
        raise ValueError("OmniVoice does not support [hắng giọng] yet. Remove that cue or use Edge TTS.")
    text = re.sub(r"\[c\u01b0\u1eddi(?::ha-ha|:hi-hi)?\]", "[laughter]", text, flags=re.IGNORECASE)
    return re.sub(r"\[th\u1edf d\u00e0i\]", "[sigh]", text, flags=re.IGNORECASE)


def has_vocal_cues(text: str) -> bool:
    """Whether a line contains a recognized direction requiring a cue recipe."""

    return _CUE.search(text) is not None


def _append_speech(parts: list[VocalPart], text: str, *, after_ahem: bool) -> None:
    """Limit the ahem pitch change to the next clause or a few words."""

    spoken = text.strip()
    if not spoken:
        return
    if not after_ahem:
        parts.append(VocalPart("speech", spoken))
        return

    end = 0
    for word in islice(re.finditer(r"\S+", spoken), VOCAL_CUE_LOW_CLAUSE_MAX_WORDS):
        punctuation = _CLAUSE_PUNCTUATION.search(word.group())
        end = word.start() + punctuation.end() if punctuation else word.end()
        if punctuation:
            break
    lowered, remainder = spoken[:end].strip(), spoken[end:].strip()
    if lowered and re.search(r"\w", lowered):
        parts.append(VocalPart("speech", lowered, VOCAL_CUE_LOW_PITCH_DELTA_HZ))
    elif lowered:
        remainder = f"{lowered} {remainder}".strip()
    if remainder:
        parts.append(VocalPart("speech", remainder))


def split_vocal_cues(text: str) -> list[VocalPart]:
    """Split recognized Vietnamese tags while retaining all other bracketed text."""

    parts: list[VocalPart] = []
    cursor = 0
    after_ahem = False
    for match in _CUE.finditer(text):
        _append_speech(parts, text[cursor:match.start()], after_ahem=after_ahem)
        cue = match.group(1).lower()
        parts.append(VocalPart("cue", _SPOKEN[cue]))
        after_ahem = cue == "hắng giọng"
        cursor = match.end()
    _append_speech(parts, text[cursor:], after_ahem=after_ahem)
    return parts


def caption_text(text: str) -> str:
    """Return dialogue without vocal directions for subtitles and exports."""

    plain = " ".join(_CUE.sub(" ", text).split())
    return re.sub(r"\s+([,.!?;:])", r"\1", plain)
