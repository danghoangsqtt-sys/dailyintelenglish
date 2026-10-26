"""Phase 80: a Short is never one long caption -- a narrator paragraph becomes lines of one or two sentences."""

from backend.ai.llm.prompt_loader import SCRIPT_PROMPTS_DIR
from backend.content.script_pipeline import LanguageNotesOut, SectionLineOut, split_short_paragraphs

PARAGRAPH = ("Are you losing authority in meetings? When you say I think, you sound unsure. Instead, use I propose. "
             "For example, say I propose we update the software. This shows you lead! Follow Daily Beyond English.")


def test_a_long_paragraph_becomes_lines_of_two_sentences_with_the_same_words():
    notes = LanguageNotesOut(collocations=["take the lead"])
    out = split_short_paragraphs([SectionLineOut(speaker_id="s1", text=PARAGRAPH, language_notes=notes)])
    assert [line.text for line in out] == [
        "Are you losing authority in meetings? When you say I think, you sound unsure.",
        "Instead, use I propose. For example, say I propose we update the software.",
        "This shows you lead! Follow Daily Beyond English."]
    assert " ".join(line.text for line in out) == PARAGRAPH
    assert out[0].language_notes.collocations == ["take the lead"] and out[1].language_notes.collocations == []


def test_short_lines_stay_as_they_are():
    lines = [SectionLineOut(speaker_id="s1", text="Today's word is pivot. It means a change of direction.")]
    assert split_short_paragraphs(lines) == lines


def test_the_short_prompt_asks_for_no_welcome():
    text = (SCRIPT_PROMPTS_DIR / "section.txt").read_text(encoding="utf-8")
    assert "No welcome and no\n  greeting" in text and "at most\n  \"Welcome to Daily Beyond English\"" not in text
