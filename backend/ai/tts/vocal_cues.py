"""Strip retired emotion directions from legacy scripts; never synthesize them."""

import re


_CUE = re.compile(
    r"\[\s*(?:cười(?::ha-ha|:hi-hi)?|thở dài|hắng giọng|tức giận|"
    r"laugh(?:ter)?|chuckle|sigh|clear throat|ahem|angry|happy|whispering|"
    r"cough|crying|dramatic|fear|gasp|groan|narration|sarcastic|shush|sniff|"
    r"surprised|advertisement)\s*\]",
    re.IGNORECASE,
)


def has_vocal_cues(text: str) -> bool:
    """Identify retired tags without interpreting unrelated bracketed text."""
    return _CUE.search(text) is not None


def caption_text(text: str) -> str:
    """Remove legacy directions while leaving unannotated dialogue untouched."""
    if not has_vocal_cues(text):
        return text
    plain = " ".join(_CUE.sub(" ", text).split())
    return re.sub(r"\s+([,.!?;:])", r"\1", plain)
