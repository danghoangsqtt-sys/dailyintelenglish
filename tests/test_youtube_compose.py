"""Task 36.2 (D93/D94/D97): the published description, hashtags and pinned comment(s)."""

from __future__ import annotations

from backend.content import youtube_service as yt

PROJECT = {"name": "Weekend plans", "speakers": [{"id": "s1", "name": "Alex"}, {"id": "s2", "name": "Lina"}]}
PACKAGE = {
    "hook": "English conversation for B1 learners: plan a weekend trip.",
    "description": "Alex and Lina plan a mountain weekend and practise everyday travel English.",
    "chapters_text": "00:00 Welcome\n00:40 The cabin", "hashtags": ["LearnEnglish", "EnglishConversation", "DailyBeyondEnglish"],
    "tags": ["learn english"], "titles": [],
}


def _learning(size: int = 1) -> dict:
    phrase = {"phrase": "split the cost", "meaning_en": "share", "meaning_vi": "chia tiền", "example_sentence": "x"}
    return {
        "vocabulary": [{"word": f"word{index}", "part_of_speech": "noun", "ipa": "/x/", "definition_en": "d",
                        "definition_vi": "nghĩa " * size, "example_sentence": "e"} for index in range(8)],
        "idioms": [{**phrase, "phrase": "a piece of cake", "meaning_vi": "dễ như ăn bánh"}],
        "collocations": [phrase], "phrasal_verbs": [{**phrase, "phrase": "look forward to", "meaning_vi": "mong chờ"}],
        "patterns": [{"pattern": "It would be + comparative + than", "use_en": "compare", "use_vi": "so sánh",
                      "example_sentence": "e"}],
        "grammar": [],
        "questions": [
            {"question": "Where are they going?", "options": ["The beach", "The mountains"], "correct_answer": "The mountains",
             "explanation": ""},
            {"question": "Why a cabin?", "options": [], "correct_answer": "", "explanation": "It is cheaper."},
        ],
    }


def test_the_description_has_every_part_in_order_with_vietnamese_meanings():
    text = yt.compose_description(PACKAGE, _learning(), "🎵 Music: Morning")
    order = [PACKAGE["hook"], PACKAGE["description"], "⏱ Chapters", "📚 Vocabulary", "• word0 (noun) — nghĩa",
             "💬 Idioms", "• a piece of cake — dễ như ăn bánh", "🔗 Collocations", "🧩 Phrasal verbs", "• look forward to — mong chờ",
             "🧱 Sentence patterns", "🎧 Listening practice", "1. Where are they going?", "A) The beach  B) The mountains",
             "📜 The full transcript", yt.SUBSCRIBE_LINE, "🎵 Music: Morning", "#LearnEnglish #EnglishConversation"]
    positions = [text.index(part) for part in order]
    assert positions == sorted(positions) and text.endswith("#DailyBeyondEnglish")
    assert "The mountains" not in text.split("🎧 Listening practice")[0]


def test_a_long_learning_pack_shortens_the_lists_but_never_breaks_5000_characters():
    text = yt.compose_description(PACKAGE, _learning(size=120), "🎵 Music: Morning")
    assert len(text) <= yt.DESCRIPTION_LIMIT
    assert yt.SUBSCRIBE_LINE in text and text.endswith("#DailyBeyondEnglish")  # the fixed tail always survives
    assert text.count("• word") < 8


def test_hashtags_are_one_camelcase_word_without_duplicates_and_keep_the_brand():
    tags = yt.normalize_hashtags(["#learn english!", "LearnEnglish", "B1 English", "travel-tips", ""])
    assert tags == ["LearnEnglish", "B1English", "TravelTips", "DailyBeyondEnglish"]
    many = yt.normalize_hashtags([f"Tag{index}" for index in range(30)])
    assert len(many) == yt.HASHTAG_LIMIT and many[-1] == "DailyBeyondEnglish"


def test_the_pinned_comment_holds_the_transcript_and_answers_and_splits_at_10000_characters():
    lines = [{"speaker_id": "s1" if index % 2 == 0 else "s2", "text": f"Line {index} " + "word " * 60} for index in range(80)]
    parts = yt.pinned_comments(PROJECT, lines, _learning())
    assert len(parts) >= 2 and all(len(part) <= yt.COMMENT_LIMIT for part in parts)
    assert parts[0].startswith("📜 Full transcript\nAlex: Line 0") and parts[0].endswith(f"(1/{len(parts)})")
    assert "✅ Listening practice answers\n1. The mountains\n2. It is cheaper." in parts[-1]
    joined = "\n".join(parts)
    assert all(f"Line {index} " in joined for index in range(80))  # nothing lost between parts
    short = yt.pinned_comments(PROJECT, [{"speaker_id": "s1", "text": "Hi."}, {"speaker_id": "s2", "text": "Hello."}], None)
    assert short == ["📜 Full transcript\nAlex: Hi.\nLina: Hello."]


def test_compose_keeps_the_summary_and_adds_the_published_fields():
    lines = [{"speaker_id": "s1", "text": "Hello there."}]
    result = yt.compose(PACKAGE, PROJECT, lines, None, None)
    assert result["summary"] == PACKAGE["description"] and result["description"].startswith(PACKAGE["hook"])
    assert result["hashtags_text"] == "#LearnEnglish #EnglishConversation #DailyBeyondEnglish"
    assert result["pinned_comments"] == ["📜 Full transcript\nAlex: Hello there."]
    assert yt.compose(None, PROJECT, lines, None, None) is None
    assert yt.transcript_text(PROJECT, lines) == "Weekend plans\nDaily Beyond English\n\nAlex: Hello there.\n"


def test_titles_given_by_variant_are_accepted():
    """Task 36.2 real-AI finding: `titles` as an object keyed by variant."""
    from backend.schemas.youtube import YouTubePackageOut

    package = YouTubePackageOut.model_validate({
        "titles": {"click_worthy": "A", "educational": "B", "seo": "C"}, "description": "Summary.", "tags": ["english"]})
    assert [(title.variant, title.text) for title in package.titles] == [("click_worthy", "A"), ("educational", "B"), ("seo", "C")]


def test_a_series_episode_names_its_series_and_links_its_neighbours():
    """Task 36.5 (D103): the series line under the summary; previous/next/playlist links before the subscribe line."""
    episode = {"series": "Weekend Trip with Friends", "topic": "Travel English", "number": 2, "total": 3,
               "playlist_url": "https://youtube.com/playlist?list=T",
               "previous": {"number": 1, "title": "Planning the Trip", "url": "https://youtu.be/one"},
               "next": {"number": 3, "title": "Packing Day", "url": ""}}
    text = yt.compose_description(PACKAGE, None, None, episode)
    head = "📺 Weekend Trip with Friends — Episode 2 of 3 (Travel English)"
    assert text.index(PACKAGE["description"]) < text.index(head) < text.index("⏱ Chapters")
    assert "⏮ Previous: Ep. 1 Planning the Trip https://youtu.be/one" in text and "⏭ Next" not in text  # not published yet
    assert text.index("📃 The whole series: https://youtube.com/playlist?list=T") < text.index(yt.SUBSCRIBE_LINE)
    assert "📺" not in yt.compose_description(PACKAGE, None, None)
