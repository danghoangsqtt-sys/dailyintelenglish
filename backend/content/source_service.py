"""Phase 57 (ENH-039): a project made from the owner's own material, and help choosing what a video is about.

- `parse_dialogue` / `parse_vocabulary`: read a pasted dialogue ("A: …" lines) or a vocabulary list.
- `topic_ideas`: six AI ideas for a video from its type, level and an optional hint.
- `read_image`: the English text of a photographed dialogue or word list, read by the cloud AI.
Nothing here is saved; Step 1 shows the result for the owner to edit.
"""

from __future__ import annotations

import base64
import difflib
import hashlib
import io
import re

from pydantic import BaseModel, Field, TypeAdapter

from backend.ai.llm.contracts import GenerationRequest
from backend.ai.llm.prompt_loader import render_source_prompt
from backend.ai.llm.router import AIRouter, build_ai_router_from_settings
from backend.ai.llm.validation import parse_and_validate
from backend.core.config import settings
from backend.core.exceptions import ProviderError, ProviderRequestRejectedError, SchemaValidationError, ValidationError

SOURCE_TEXT_MAX = 12000
VOCABULARY_MAX = 80
VOCABULARY_ITEM_MAX = 120
AVOID_MAX = 60
IMAGE_MAX_BYTES = 8 * 1024 * 1024
IMAGE_MAX_SIDE = 1600
_LABEL = re.compile(r"^\s*([^:\n]{1,30}?)\s*[:：]\s*(.+)$")
_IDEAS = 6
DIALOGUE_SPEAKERS_MAX = 4
VERBATIM_MIN_SIMILARITY = 0.98


class TopicIdea(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    topic: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=400)


class TopicIdeas(BaseModel):
    ideas: list[TopicIdea] = Field(min_length=1)


class ReadText(BaseModel):
    text: str = ""


_IDEAS_ADAPTER = TypeAdapter(TopicIdeas)
_READ_ADAPTER = TypeAdapter(ReadText)


# ---------------------------------------------------------------------------- parsing the owner's material


def parse_dialogue(text: str, speakers: list[dict]) -> list[dict]:
    """Turn "Label: words" lines into script lines `{speaker_id, text}`.

    A label that equals a speaker's name (any case) is that speaker; other labels take the remaining speakers in
    order of first appearance. A line without a label continues the previous turn. Raises `ValidationError` when the
    text has no labelled line or more labels than the project has speakers.
    """
    by_name = {speaker["name"].strip().lower(): speaker["id"] for speaker in speakers}
    assigned: dict[str, str] = {}
    lines: list[dict] = []
    for raw in text.splitlines():
        row = raw.strip()
        if not row:
            continue
        match = _LABEL.match(row)
        if match:
            label, words = match.group(1).strip(), match.group(2).strip()
            key = label.lower()
            if key not in assigned and len(assigned) >= DIALOGUE_SPEAKERS_MAX:
                raise ValidationError(f"A dialogue can have at most {DIALOGUE_SPEAKERS_MAX} speakers.")
            if key not in assigned:
                speaker_id = by_name.get(key)
                if speaker_id is None or speaker_id in assigned.values():
                    free = [speaker["id"] for speaker in speakers if speaker["id"] not in assigned.values()]
                    if not free:
                        raise ValidationError(
                            f"The dialogue has more speakers than the video ({len(speakers)}): “{label}” has no character "
                            "left. Use one label per character, for example A: and B:.")
                    speaker_id = free[0]
                assigned[key] = speaker_id
            lines.append({"speaker_id": assigned[key], "text": words})
        elif lines:
            lines[-1]["text"] = f"{lines[-1]['text']} {row}"
        else:
            raise ValidationError("Each turn of the dialogue needs a speaker label, for example “A: Hello!”.")
    if not lines:
        raise ValidationError("The dialogue is empty: write one turn per line, for example “A: Hello!”.")
    verify_verbatim(text, lines)
    return lines


def _spoken(text: str) -> str:
    """Words only, lower case: what "the same words" means for the word-for-word check."""
    return " ".join(re.findall(r"[a-z0-9']+", text.casefold()))


def verify_verbatim(text: str, lines: list[dict]) -> float:
    """The owner's words must survive word for word: the script lines, compared with the input without its speaker
    labels after whitespace/punctuation normalization, must be at least 98 % similar. Returns the similarity."""
    original = " ".join(match.group(2) if (match := _LABEL.match(row.strip())) else row.strip()
                        for row in text.splitlines() if row.strip())
    stored = " ".join(line["text"] for line in lines)
    ratio = difflib.SequenceMatcher(None, _spoken(original), _spoken(stored), autojunk=False).ratio()
    if ratio < VERBATIM_MIN_SIMILARITY:
        raise ValidationError(f"The dialogue could not be kept word for word ({ratio:.0%} the same); check the labels, "
                              "or let the AI rewrite it.")
    return ratio


def image_sha(content: bytes) -> str:
    """The SHA-256 kept for a photo the owner read a text from (the photo itself is never stored)."""
    return hashlib.sha256(content).hexdigest()


def parse_vocabulary(text: str) -> list[str]:
    """The words or phrases of a vocabulary list: one per line or comma separated, de-duplicated, at most 60.

    A "word - meaning" / "word: meaning" line keeps only the word."""
    words: list[str] = []
    seen: set[str] = set()
    for row in re.split(r"[\n,;]+", text):
        word = re.split(r"\s+[-–—=]\s+|\s*[:：]\s+|\t", row.strip(), maxsplit=1)[0]
        word = re.sub(r"^\s*(\d+[.)]|[-•*])\s*", "", word).strip(" .")
        if len(word) > VOCABULARY_ITEM_MAX:
            raise ValidationError(f"“{word[:40]}…” is too long for one vocabulary item (at most {VOCABULARY_ITEM_MAX} characters).")
        if word and word.lower() not in seen:
            seen.add(word.lower())
            words.append(word)
    if not words:
        raise ValidationError("The vocabulary list is empty: write one word or phrase per line.")
    if len(words) > VOCABULARY_MAX:
        raise ValidationError(f"The vocabulary list has {len(words)} items; one video can teach at most {VOCABULARY_MAX}.")
    return words


# ---------------------------------------------------------------------------- AI help


def _normalized(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


async def topic_ideas(presentation_mode: str, cefr_level: str, hint: str = "", explainer_subject: str | None = None,
                      avoid: list[str] | None = None, router: AIRouter | None = None, audience: str | None = None) -> list[dict]:
    """Six ideas `{name, topic, description}` for a new video; raises a readable `ValidationError` on failure.

    `avoid` holds the topics of recent projects (at most 60): they go into the prompt, and an idea whose name or topic
    matches one of them after normalization is dropped."""
    avoid = [topic for topic in (avoid or []) if topic.strip()][:AVOID_MAX]
    prompt = await render_source_prompt(
        "topic_ideas.txt", presentation_mode=presentation_mode, cefr_level=cefr_level, hint=hint.strip(),
        explainer_subject=(explainer_subject or "topic") if presentation_mode == "solo_explainer" else None, avoid=avoid,
        **({"audience_line": __import__("backend.content.audience", fromlist=["line"]).line(audience)} if audience else {}))
    router = router or build_ai_router_from_settings()
    try:
        result = await router.generate(GenerationRequest(
            prompt=prompt, json_schema=TopicIdeas.model_json_schema(),
            deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS, purpose="topic_ideas"))
        ideas = parse_and_validate(result.text, _IDEAS_ADAPTER).ideas
    except SchemaValidationError as exc:
        raise ValidationError("The AI's ideas were not usable; try again") from exc
    except ProviderError as exc:
        raise ValidationError(f"The AI could not suggest ideas right now ({type(exc).__name__}); try again") from exc
    known = {_normalized(topic) for topic in avoid}
    fresh: list[dict] = []
    for idea in ideas:
        keys = {_normalized(idea.name), _normalized(idea.topic)}
        if keys & known:
            continue
        known |= keys
        fresh.append(idea.model_dump())
    if not fresh:
        raise ValidationError("The AI only repeated topics the channel already has; try again or add a direction")
    return fresh[:_IDEAS]


def _image_data_url(content: bytes) -> str:
    """A JPEG data URL of the picture, at most 1600 px on its longer side."""
    from PIL import Image, UnidentifiedImageError

    if len(content) > IMAGE_MAX_BYTES:
        raise ValidationError("The picture is larger than 8 MB.")
    try:
        with Image.open(io.BytesIO(content)) as image:
            image = image.convert("RGB")
            image.thumbnail((IMAGE_MAX_SIDE, IMAGE_MAX_SIDE))
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=88)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationError("That file is not a picture (use PNG, JPEG or WebP).") from exc
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


async def read_image(content: bytes, kind: str, router: AIRouter | None = None) -> str:
    """The English text of a photographed dialogue (`kind` "dialogue") or word list ("vocabulary")."""
    if kind not in ("dialogue", "vocabulary"):
        raise ValidationError("kind must be dialogue or vocabulary")
    if not settings.AI_ALLOW_CLOUD:
        raise ValidationError("Reading photos is off: cloud AI is turned off on this computer (DIE_AI_ALLOW_CLOUD=false). "
                              "Paste the text instead.")
    image = _image_data_url(content)
    prompt = await render_source_prompt("read_image.txt", kind=kind)
    router = router or build_ai_router_from_settings()
    try:
        result = await router.generate(GenerationRequest(
            prompt=prompt, images=[image], json_schema=ReadText.model_json_schema(),
            deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS, purpose="read_image"))
        text = parse_and_validate(result.text, _READ_ADAPTER).text.strip()
    except ProviderRequestRejectedError as exc:
        raise ValidationError("Reading pictures needs a cloud AI that can see images (Settings → AI); "
                              "you can still paste the text.") from exc
    except SchemaValidationError as exc:
        raise ValidationError("The AI's reading was not usable; try again") from exc
    except ProviderError as exc:
        raise ValidationError(f"The AI could not read the picture right now ({type(exc).__name__}); try again") from exc
    if not text:
        raise ValidationError("No English text was found in the picture.")
    return text[:SOURCE_TEXT_MAX]
