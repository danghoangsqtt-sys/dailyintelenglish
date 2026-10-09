from app.services.visuals.activity_matcher import match_activity


def _asset(asset_id, character_id, activity, aliases=(), contexts=(), uses=0, last=None):
    return {"id": asset_id, "character_id": character_id, "activity": activity, "aliases": list(aliases),
            "context_tags": list(contexts), "use_count": uses, "last_used_at": last}


def test_character_asset_wins_then_generic_and_never_other_character():
    alex, lina = "alex", "lina"
    candidates = [_asset("wrong", lina, "cooking"), _asset("generic", None, "cooking"), _asset("alex", alex, "cooking")]
    match = match_activity(candidates, alex, "cooking dinner", "I cook dinner every night")
    assert match["activity_id"] == "alex" and match["match_type"] == "character"
    generic = match_activity(candidates[:2], alex, "cooking dinner", "I cook dinner every night")
    assert generic["activity_id"] == "generic" and generic["match_type"] == "generic"


def test_alias_context_and_least_used_tie_breaking_are_explainable():
    candidates = [_asset("newer", None, "exercise", aliases=("work out",), contexts=("morning",), uses=2),
                  _asset("older", None, "exercise", aliases=("work out",), contexts=("morning",), uses=0)]
    match = match_activity(candidates, None, "", "I work out every morning", ["morning"])
    assert match["activity_id"] == "older" and match["score"] == 75 and "alias" in match["reason"]


def test_weak_or_unrelated_activity_is_missing():
    assert match_activity([_asset("cook", None, "cooking")], None, "", "I read a book") is None


def test_direction_image_matches_the_instruction_without_crossing_directions():
    straight = _asset(
        "straight", None, "go straight",
        aliases=("continue straight", "walk straight ahead", "keep going straight"),
        contexts=("directions", "navigation", "city street"),
    )
    match = match_activity([straight], None, "", "Keep going straight for two blocks", ["directions"])
    assert match["activity_id"] == "straight" and match["score"] == 75
    assert "alias 'keep going straight'" in match["reason"]
    assert match_activity([straight], None, "turn right", "Turn right at the corner", ["directions"]) is None
