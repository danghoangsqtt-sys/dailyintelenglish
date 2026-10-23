"""Generates and persists YouTube Package metadata via the AI provider gateway (Task 1.9).

Migrated from a duplicated direct-Gemini transport onto the shared `AIRouter` gateway
in Phase 13, Task 13.7 -- see `backend/content/script_service.py::generate_script` for the
identical reasoning.

Chapter timestamps are ESTIMATED from a fixed reading speed when no audio mix exists yet
(Sub-task 1.9a's original behavior), or MEASURED from AudioService's real per-line
timestamps once one does (Sub-task 1.9b) — `chapters_estimated` on the persisted package
says which. `build_export_zip` assembles the final downloadable package (video +
thumbnail + SRT + metadata + transcript/Learning Content) once the existing media
prerequisites exist.
"""

import io
import json
import logging
import uuid
import re
import zipfile
from datetime import datetime, timezone

import aiosqlite
from pydantic import TypeAdapter

from backend.ai.tts.vocal_cues import caption_text
from backend.core.config import settings
from backend.core.constants import YOUTUBE_CHAPTER_MIN_LINES, YOUTUBE_CHAPTER_WORDS_PER_MINUTE
from backend.core.exceptions import ProviderError, SchemaValidationError, ValidationError, YouTubePackageGenerationError
from backend.ai.llm.prompt_loader import render_youtube_prompt
from backend.schemas.youtube import YouTubePackageOut
from backend.ai.llm.contracts import GenerationRequest
from backend.ai.llm.router import AIRouter, build_ai_router_from_settings
from backend.ai.llm.validation import parse_and_validate

logger = logging.getLogger(__name__)

_PACKAGE_ADAPTER = TypeAdapter(YouTubePackageOut)


def _now() -> str:
    """Current UTC timestamp in ISO8601, used for created_at/updated_at."""
    return datetime.now(timezone.utc).isoformat()


def _chapter_label(text: str, max_words: int = 6) -> str:
    """Build a short chapter label from a line's leading words."""
    words = text.split()
    label = " ".join(words[:max_words])
    return f"{label}…" if len(words) > max_words else label


def estimate_chapters(script_lines: list[dict]) -> str:
    """Estimate YouTube chapter markers from script text alone.

    No real audio duration exists yet (Task 1.7/AudioService are blocked on ffmpeg),
    so each chapter's timestamp is estimated from the cumulative word count of every
    preceding line at a fixed reading speed (YOUTUBE_CHAPTER_WORDS_PER_MINUTE) — an
    approximation for a draft aid, not a measurement. A new chapter starts every
    YOUTUBE_CHAPTER_MIN_LINES lines (a simple topic-shift heuristic); the first
    chapter is always "00:00 Introduction".

    Returns:
        Plain-text "MM:SS Label" lines (YouTube's chapter format), one per line,
        or "" if there are no script lines.
    """
    if not script_lines:
        return ""
    chapters: list[str] = []
    cumulative_words = 0
    for index, line in enumerate(script_lines):
        if index == 0:
            chapters.append("00:00 Introduction")
        elif index % YOUTUBE_CHAPTER_MIN_LINES == 0:
            seconds = round(cumulative_words / YOUTUBE_CHAPTER_WORDS_PER_MINUTE * 60)
            minutes, secs = divmod(seconds, 60)
            chapters.append(f"{minutes:02d}:{secs:02d} {_chapter_label(caption_text(line['text']))}")
        cumulative_words += len(caption_text(line["text"]).split())
    return "\n".join(chapters)


def real_chapters_from_timestamps(timestamps: list[dict]) -> str:
    """Build YouTube chapter markers from AudioService's real measured per-line timestamps.

    Same topic-shift heuristic as `estimate_chapters` (new chapter every
    YOUTUBE_CHAPTER_MIN_LINES lines, first chapter always "00:00 Introduction"), but using
    real `start_sec` values and real line text (both present in AudioService's timestamps
    since Task 1.7) instead of a word-count projection.

    Returns:
        Plain-text "MM:SS Label" lines, or "" if there are no timestamps.
    """
    if not timestamps:
        return ""
    chapters: list[str] = []
    for index, cue in enumerate(timestamps):
        if index == 0:
            chapters.append("00:00 Introduction")
        elif index % YOUTUBE_CHAPTER_MIN_LINES == 0:
            minutes, secs = divmod(round(cue["start_sec"]), 60)
            chapters.append(f"{minutes:02d}:{secs:02d} {_chapter_label(cue.get('text', ''))}")
    return "\n".join(chapters)


async def generate_package(
    project: dict,
    script_lines: list[dict],
    timestamps: list[dict] | None = None,
    router: AIRouter | None = None,
) -> dict:
    """Generate a full YouTube package (titles/description/tags/chapters).

    Migrated from a duplicated direct-Gemini retry/fallback-model transport to
    `AIRouter` (Phase 13, Task 13.7) -- see `script_service.generate_script` for the
    identical reasoning.

    `timestamps` is the project's completed `audio_jobs.timestamps` (Task 1.6), when one
    exists. When present, chapters are measured from real audio; otherwise they fall back
    to `estimate_chapters`' word-count projection (Sub-task 1.9a's original behavior,
    preserved for a project with no audio yet).

    Args:
        project: Project-shaped dict as returned by project_service.get_project —
            must include name, topic, cefr_level, and genre.
        script_lines: The project's persisted script lines, in order. Must be
            non-empty — their text is joined into the transcript Gemini uses,
            and is also used to estimate chapter timestamps.
        router: Injected `AIRouter` (tests pass a `FakeProvider`-backed one with
            zero network calls); defaults to `build_ai_router_from_settings()`.

    Returns:
        A dict shaped like a persisted package row's public form: titles,
        description, tags, chapters_text.

    Raises:
        ValidationError: If the script is empty.
        YouTubePackageGenerationError: If every provider attempt this mode
            allows fails, or the response is malformed/fails schema
            validation. (Phase 18: an unconfigured cloud key/model no longer
            raises here -- `build_ai_router_from_settings()`'s
            `compute_effective_mode` already degrades to local automatically,
            per invariant 32.)
    """
    if not script_lines:
        raise ValidationError("Cannot generate a YouTube package: script is empty")

    transcript_text = "\n".join(caption_text(line["text"]) for line in script_lines)
    prompt = await render_youtube_prompt(
        project_name=project["name"],
        topic=project["topic"],
        genre=project["genre"],
        cefr_level=project["cefr_level"],
        transcript_text=transcript_text,
        audience=project.get("audience_effective"),
    )
    router = router or build_ai_router_from_settings()
    if project.get("presentation_mode") == "solo_explainer":
        prompt += ("\nFORMAT: A knowledge explainer monologue by one presenter. Describe the actual ideas and learning "
                   "points in this transcript. Do not invent a dialogue, co-host, interview, or second speaker. "
                   f"Presenter: {project['speakers'][0]['name']}. Structure: {project.get('explainer_structure', 'why')}.")
    request = GenerationRequest(
        prompt=prompt,
        json_schema=YouTubePackageOut.model_json_schema(),
        deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS,
        purpose="youtube_package",
    )
    try:
        result = await router.generate(request)
    except ProviderError as exc:
        raise YouTubePackageGenerationError(f"YouTube package generation failed: {exc}") from exc

    try:
        package = parse_and_validate(result.text, _PACKAGE_ADAPTER)
    except SchemaValidationError as exc:
        raise YouTubePackageGenerationError(str(exc)) from exc

    if timestamps:
        chapters_text = real_chapters_from_timestamps(timestamps)
        chapters_estimated = False
    else:
        chapters_text = estimate_chapters(script_lines)
        chapters_estimated = True

    return {
        "titles": [title.model_dump() for title in package.titles],
        "description": package.description,
        "tags": package.tags,
        "hook": package.hook,
        "hashtags": normalize_hashtags(package.hashtags),
        "chapters_text": chapters_text,
        "chapters_estimated": chapters_estimated,
    }


def _row_to_package(row: aiosqlite.Row) -> dict:
    """Convert a youtube_packages row to a dict, decoding its JSON column."""
    package = dict(row)
    package["titles"] = json.loads(package.pop("title_options_json"))
    package["tags"] = [tag.strip() for tag in package["tags"].split(",") if tag.strip()]
    package["chapters_estimated"] = bool(package["chapters_estimated"])
    package["hashtags"] = json.loads(package.pop("hashtags_json") or "[]")
    return package


async def get_package(db: aiosqlite.Connection, project_id: str) -> dict | None:
    """Fetch a project's YouTube package, or None if never generated."""
    cursor = await db.execute(
        "SELECT id, project_id, title_options_json, description, chapters_text, tags, "
        "chapters_estimated, hook, hashtags_json, created_at, updated_at FROM youtube_packages WHERE project_id = ?",
        (project_id,),
    )
    row = await cursor.fetchone()
    return None if row is None else _row_to_package(row)


async def save_package(
    db: aiosqlite.Connection, project_id: str, package: dict, commit: bool = True
) -> dict:
    """Create or replace the YouTube package for a project (UPSERT on project_id).

    A repeat call (Regenerate) replaces the previous package rather than erroring
    or duplicating a row.
    """
    now = _now()
    await db.execute(
        "INSERT INTO youtube_packages "
        "(id, project_id, title_options_json, description, chapters_text, tags, "
        "chapters_estimated, hook, hashtags_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(project_id) DO UPDATE SET "
        "title_options_json = excluded.title_options_json, "
        "description = excluded.description, "
        "chapters_text = excluded.chapters_text, "
        "tags = excluded.tags, "
        "chapters_estimated = excluded.chapters_estimated, "
        "hook = excluded.hook, "
        "hashtags_json = excluded.hashtags_json, "
        "updated_at = excluded.updated_at",
        (
            str(uuid.uuid4()),
            project_id,
            json.dumps(package["titles"]),
            package["description"],
            package["chapters_text"],
            ", ".join(package["tags"]),
            int(package.get("chapters_estimated", True)),
            package.get("hook", ""),
            json.dumps(normalize_hashtags(package.get("hashtags", []))),
            now,
            now,
        ),
    )
    if commit:
        await db.commit()
    return await get_package(db, project_id)


# ---------------------------------------------------------------- Task 36.2 (D93/D94/D97): the published text

DESCRIPTION_LIMIT = 5000  # YouTube's description limit
COMMENT_LIMIT = 10000  # YouTube's comment limit
HASHTAG_LIMIT = 15  # more than 15 and YouTube ignores every hashtag
BRAND_HASHTAG = "DailyBeyondEnglish"
SUBSCRIBE_LINE = "🔔 Subscribe to Daily Beyond English for a new English conversation every week."
# (section, heading, how many at most): the learning items offered to the description, in this order.
LEARNING_SECTIONS = (
    ("vocabulary", "📚 Vocabulary", 8), ("idioms", "💬 Idioms", 4), ("collocations", "🔗 Collocations", 4),
    ("phrasal_verbs", "🧩 Phrasal verbs", 4), ("patterns", "🧱 Sentence patterns", 3),
)


def normalize_hashtags(values: list[str]) -> list[str]:
    """`#learn english!` -> `LearnEnglish`: one word, no `#`, no duplicates (case-insensitive), the brand tag kept, <= 15."""
    result: list[str] = []
    for value in values:
        words = re.findall(r"[A-Za-z0-9]+", value or "")
        if not words:
            continue
        tag = "".join(word if word[0].isupper() or word.isdigit() else word[0].upper() + word[1:] for word in words)
        if tag.lower() not in {existing.lower() for existing in result}:
            result.append(tag)
    if BRAND_HASHTAG.lower() not in {tag.lower() for tag in result}:
        result = result[:HASHTAG_LIMIT - 1] + [BRAND_HASHTAG]
    return result[:HASHTAG_LIMIT]


# Phase 72 (ENH-054): the description in Vietnamese for a Vietnamese audience (the English learning items stay English)
VI_HEADINGS = {"vocabulary": "📚 Từ vựng", "idioms": "💬 Thành ngữ", "collocations": "🔗 Cụm từ cố định",
               "phrasal_verbs": "🧩 Cụm động từ", "patterns": "🧱 Mẫu câu"}
VI_LINES = {
    "listening": "🎧 Luyện nghe (đáp án ở bình luận ghim)",
    "transcript": "📜 Toàn bộ lời thoại ở bình luận ghim.",
    "subscribe": "🔔 Đăng ký Daily Beyond English để có một đoạn hội thoại tiếng Anh mới mỗi tuần.",
}


def _meaning(item: dict, english: str, vietnamese: str, audience: str) -> str:
    """The English definition, the Vietnamese meaning, or both, for the audience."""
    en, vi = (item.get(english) or "").strip(), (item.get(vietnamese) or "").strip()
    if audience == "international":
        return en or vi
    if audience == "vietnamese":
        return vi or en
    return f"{en} / {vi}" if en and vi else en or vi


def _learning_line(section: str, item: dict, audience: str = "vietnamese") -> str:
    if section == "vocabulary":
        return f"• {item['word']} ({item['part_of_speech']}) — {_meaning(item, 'definition_en', 'definition_vi', audience)}"
    if section == "patterns":
        return f"• {item['pattern']} — {_meaning(item, 'use_en', 'use_vi', audience)}"
    return f"• {item['phrase']} — {_meaning(item, 'meaning_en', 'meaning_vi', audience)}"


def _listening_questions(learning: dict | None, count: int = 3) -> list[dict]:
    """The multiple-choice questions first (they read well in a description), at most `count`."""
    questions = (learning or {}).get("questions", [])
    return ([item for item in questions if item.get("options")] + [item for item in questions if not item.get("options")])[:count]


def _question_text(number: int, item: dict) -> str:
    options = "  ".join(f"{chr(65 + index)}) {option}" for index, option in enumerate(item.get("options") or []))
    return f"{number}. {item['question']}" + (f"\n   {options}" if options else "")


def _series_lines(episode: dict | None) -> tuple[str | None, str | None]:
    """Task 36.5 (D103): the series line under the summary and the "watch next" block before the subscribe line."""
    if not episode:
        return None, None
    head = f"📺 {episode['series']} — Episode {episode['number']} of {episode['total']} ({episode['topic']})"
    links = []
    if (episode.get("previous") or {}).get("url"):
        links.append(f"⏮ Previous: Ep. {episode['previous']['number']} {episode['previous']['title']} {episode['previous']['url']}")
    if (episode.get("next") or {}).get("url"):
        links.append(f"⏭ Next: Ep. {episode['next']['number']} {episode['next']['title']} {episode['next']['url']}")
    if episode.get("playlist_url"):
        links.append(f"📃 The whole series: {episode['playlist_url']}")
    return head, "\n".join(links) or None


def compose_description(package: dict, learning: dict | None, credit: str | None, episode: dict | None = None,
                        audience: str = "both") -> str:
    """The description pasted into YouTube, within 5,000 characters. The fixed parts come first; the learning items fill
    what is left, section by section, so a long pack shortens the lists instead of breaking the limit."""
    series_head, series_links = _series_lines(episode)
    head = [part for part in (package.get("hook", "").strip(), package["description"].strip(), series_head) if part]
    vietnamese = audience == "vietnamese"
    if package.get("chapters_text", "").strip():
        head.append(("⏱ Mục lục" if vietnamese else "⏱ Chapters") + "\n" + package["chapters_text"].strip())
    questions = _listening_questions(learning)
    tail = []
    if questions:
        tail.append((VI_LINES["listening"] if vietnamese else "🎧 Listening practice (answers in the pinned comment)") + "\n"
                    + "\n".join(_question_text(number, item) for number, item in enumerate(questions, start=1)))
    tail.append(VI_LINES["transcript"] if vietnamese else "📜 The full transcript is in the pinned comment.")
    if series_links:
        tail.append(series_links)
    tail.append(VI_LINES["subscribe"] if vietnamese else SUBSCRIBE_LINE)
    if credit:
        tail.append(credit.strip())
    hashtags = package.get("hashtags") or []
    if hashtags:
        tail.append(" ".join(f"#{tag}" for tag in hashtags))

    def total(blocks: list[str]) -> int:
        return len("\n\n".join(blocks))

    middle: list[str] = []
    for section, heading, limit in LEARNING_SECTIONS:
        heading = VI_HEADINGS[section] if vietnamese else heading
        lines: list[str] = []
        for item in ((learning or {}).get(section) or [])[:limit]:
            candidate = "\n".join([heading, *lines, _learning_line(section, item, audience)])
            if total(head + middle + [candidate] + tail) > DESCRIPTION_LIMIT:
                break
            lines.append(_learning_line(section, item, audience))
        if lines:
            middle.append("\n".join([heading, *lines]))
    text = "\n\n".join(head + middle + tail)
    return text if len(text) <= DESCRIPTION_LIMIT else text[:DESCRIPTION_LIMIT - 1].rstrip() + "…"


def pinned_comments(project: dict, script_lines: list[dict], learning: dict | None) -> list[str]:
    """The full transcript (and the listening answers) as pinned comment text, split at line breaks into parts that each
    fit one YouTube comment; a part says "(2/3)" when there is more than one."""
    names = {speaker["id"]: speaker["name"] for speaker in project["speakers"]}
    lines = [f"{names.get(line['speaker_id'], line['speaker_id'])}: {caption_text(line['text'])}" for line in script_lines]
    questions = _listening_questions(learning)
    answers = [f"{number}. {item.get('correct_answer') or item.get('explanation', '')}"
               for number, item in enumerate(questions, start=1)]
    blocks = ["📜 Full transcript", *lines]
    if answers:
        blocks += ["", "✅ Listening practice answers", *answers]
    reserve = 12  # room for the " (n/m)" label
    parts: list[list[str]] = [[]]
    for line in blocks:
        while len(line) > COMMENT_LIMIT - reserve:  # a single overlong line (never in practice) is cut, not lost
            parts.append([line[:COMMENT_LIMIT - reserve]])
            line = line[COMMENT_LIMIT - reserve:]
        if parts[-1] and len("\n".join(parts[-1] + [line])) > COMMENT_LIMIT - reserve:
            parts.append([])
        parts[-1].append(line)
    texts = ["\n".join(part).strip() for part in parts if any(entry.strip() for entry in part)]
    if len(texts) > 1:
        texts = [f"{text} ({index}/{len(texts)})" for index, text in enumerate(texts, start=1)]
    return texts


def transcript_text(project: dict, script_lines: list[dict]) -> str:
    names = {speaker["id"]: speaker["name"] for speaker in project["speakers"]}
    title = project.get("name") or "Daily Beyond English"
    body = "\n".join(f"{names.get(line['speaker_id'], line['speaker_id'])}: {caption_text(line['text'])}" for line in script_lines)
    return f"{title}\nDaily Beyond English\n\n{body}\n"


def compose(package: dict | None, project: dict, script_lines: list[dict], learning: dict | None,
            credit: str | None, episode: dict | None = None) -> dict | None:
    """The package as Step 7 and the export show it: the stored parts plus the composed description, the hashtags line and
    the pinned comment(s)."""
    if package is None:
        return None
    result = {**package, "summary": package["description"], "music_credit": credit}
    result["description"] = compose_description(package, learning, credit, episode, project.get("audience_effective") or "both")
    result["audience"] = project.get("audience_effective") or "both"
    result["episode"] = episode
    result["hashtags_text"] = " ".join(f"#{tag}" for tag in package.get("hashtags") or [])
    result["pinned_comments"] = pinned_comments(project, script_lines, learning)
    return result


def _build_metadata_text(package: dict) -> str:
    """Render the package's text fields as a plain-text metadata.txt for the export zip."""
    lines = ["=== TITLES ===", ""]
    for title in package["titles"]:
        lines.append(f"[{title['variant']}] {title['text']}")
    lines += ["", "=== DESCRIPTION ===", "", package["description"]]
    if package.get("hashtags_text"):
        lines += ["", "=== HASHTAGS ===", "", package["hashtags_text"]]
    lines += ["", "=== TAGS ===", "", ", ".join(package["tags"])]
    chapter_kind = "Estimated (word-count projection)" if package["chapters_estimated"] else "Measured (from real audio)"
    lines += ["", f"=== CHAPTERS ({chapter_kind}) ===", "", package["chapters_text"]]
    return "\n".join(lines) + "\n"


def _build_transcript_and_learning_text(
    project: dict, script_lines: list[dict], learning_content: dict | None
) -> str:
    """Render the full transcript and optional Learning Content as UTF-8-ready text."""
    speaker_names_by_id = {
        speaker["id"]: speaker["name"] for speaker in project["speakers"]
    }
    lines = ["=== FULL TRANSCRIPT ===", ""]
    for script_line in script_lines:
        speaker_id = script_line["speaker_id"]
        speaker_name = speaker_names_by_id.get(speaker_id, speaker_id)
        lines.append(f"{speaker_name}: {caption_text(script_line['text'])}")

    if learning_content is None:
        lines += ["", "Learning Content was not generated for this project."]
        return "\n".join(lines) + "\n"

    lines += ["", "=== VOCABULARY ===", ""]
    vocabulary = learning_content.get("vocabulary", [])
    if vocabulary:
        for item in vocabulary:
            lines.append(
                f"{item['word']} ({item['part_of_speech']}) — {item['ipa']} — "
                f"{item['definition_en']} — {item['definition_vi']} — "
                f"{item['example_sentence']}"
            )
    else:
        lines.append("No items.")

    lines += ["", "=== IDIOMS & COLLOCATIONS ===", ""]
    idioms = learning_content.get("idioms", [])
    if idioms:
        for item in idioms:
            lines.append(
                f"{item['phrase']} — {item['meaning_en']} — {item['meaning_vi']} — "
                f"{item['example_sentence']}"
            )
    else:
        lines.append("No items.")

    for section, heading in (("collocations", "COLLOCATIONS"), ("phrasal_verbs", "PHRASAL VERBS")):
        items = learning_content.get(section, [])
        if items:
            lines += ["", f"=== {heading} ===", ""]
            lines += [f"{item['phrase']} — {item['meaning_en']} — {item['meaning_vi']} — {item['example_sentence']}"
                      for item in items]
    patterns = learning_content.get("patterns", [])
    if patterns:
        lines += ["", "=== SENTENCE PATTERNS ===", ""]
        lines += [f"{item['pattern']} — {item['use_en']} — {item['use_vi']} — {item['example_sentence']}" for item in patterns]

    lines += ["", "=== GRAMMAR POINTS ===", ""]
    grammar = learning_content.get("grammar", [])
    if grammar:
        for item in grammar:
            examples = " | ".join(item.get("examples", [])) or "None"
            lines.append(
                f"{item['point']} — {item['structure']} — {item['explanation_en']} — "
                f"{item['explanation_vi']} — Examples: {examples}"
            )
    else:
        lines.append("No items.")

    lines += ["", "=== COMPREHENSION QUESTIONS ===", ""]
    questions = learning_content.get("questions", [])
    if questions:
        for item in questions:
            parts = [item["question"]]
            if item.get("options"):
                parts.append(f"Options: {' | '.join(item['options'])}")
            parts += [
                f"Correct answer: {item.get('correct_answer', '')}",
                f"Explanation: {item.get('explanation', '')}",
            ]
            lines.append(" — ".join(parts))
    else:
        lines.append("No items.")

    return "\n".join(lines) + "\n"


def build_export_zip(
    package: dict,
    video_job: dict,
    thumbnail_row: dict,
    project: dict,
    script_lines: list[dict],
    learning_content: dict | None,
) -> bytes:
    """Assemble the full downloadable YouTube package as an in-memory zip.

    Args:
        package: A YouTube package dict (from `get_package`).
        video_job: A completed `video_jobs` row (from `video_service.get_video_job`) —
            caller must have already checked `status == "complete"`.
        thumbnail_row: The project's favorite (`is_selected`) thumbnail row.
        project: Project dict containing the speakers used to label transcript lines.
        script_lines: The project's persisted script lines, in order.
        learning_content: The project's Learning Content pack, or None if not generated.

    Returns:
        Raw zip file bytes, ready to stream as an HTTP response body.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(video_job["mp4_path"], arcname="video.mp4")
        archive.write(video_job["srt_path"], arcname="subtitles.srt")
        archive.write(thumbnail_row["image_path_16x9"], arcname="thumbnail.png")
        archive.writestr("metadata.txt", _build_metadata_text(package))
        transcript_text = _build_transcript_and_learning_text(
            project, script_lines, learning_content
        )
        archive.writestr(
            "transcript_and_vocabulary.txt", transcript_text.encode("utf-8")
        )
        if package.get("pinned_comments"):  # Task 36.2: paste each part as a comment, pin the first
            archive.writestr("pinned_comment.txt", "\n\n----------\n\n".join(package["pinned_comments"]).encode("utf-8"))
    return buffer.getvalue()
