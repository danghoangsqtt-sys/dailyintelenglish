"""Owner 2026-10-27: "Segment intro-1: use only an activity_id from AVAILABLE ACTIVITY PICTURES" stopped a Solo plan.
A proposal that names a picture or place it was not offered is kept, with a text card / an offered scene instead."""

from types import SimpleNamespace

from backend.library import explainer_stage
from backend.schemas.explainer import SceneReference, SegmentLocks


def _segment(activity_id, scene_id="cafe", locked=False, intent="Greet the viewer and name the topic"):
    return SimpleNamespace(id="intro-1", intent=intent, scene=SceneReference(scene_id=scene_id),
                           visual=SimpleNamespace(kind="activity", activity_id=activity_id), locks=SegmentLocks(visual=locked))


def test_an_unoffered_activity_becomes_a_text_card_and_the_plan_passes():
    captured = {"available_scenes": [{"id": "office"}], "available_activities": [{"id": "act-1"}]}
    good, bad = _segment("act-1", "office"), _segment("invented-id")
    explainer_stage.repair_proposal([good, bad], captured)
    assert good.visual.kind == "activity" and good.scene.scene_id == "office"
    assert bad.visual.kind == "text_card" and bad.visual.title == "Greet the viewer and name the topic"
    assert bad.scene.scene_id == "office"  # the unoffered "cafe" became the first offered scene
    explainer_stage.check_proposal([good, bad], captured)  # no ValidationError any more


def test_nothing_offered_means_no_activity_and_no_scene():
    segment = _segment("act-1", intent="")
    explainer_stage.repair_proposal([segment], {"available_scenes": [], "available_activities": []})
    assert segment.visual.kind == "text_card" and segment.visual.title == "Key idea" and segment.scene is None


def test_a_locked_owner_visual_is_left_alone():
    segment = _segment("owner-picture", locked=True)
    explainer_stage.repair_proposal([segment], {"available_scenes": None, "available_activities": []})
    assert segment.visual.kind == "activity" and segment.scene.scene_id == "cafe"


def test_a_repaired_activity_card_shows_the_narrators_words_not_the_planning_note():
    """Phase 84 (real run 2026-10-28): "Provide concrete examples of changing blunt commands..." reached the screen."""
    segment = _segment("not-offered", intent="Provide concrete examples of changing blunt commands to polite requests")
    segment.line_ids = ["l1"]
    lines = [{"id": line_id, "text": "Instead of 'send me that report', say 'could you send me that report?' It sounds kinder."}
             for line_id in segment.line_ids]
    explainer_stage.repair_proposal([segment], {"available_scenes": [], "available_activities": []}, lines)
    assert segment.visual.kind == "text_card"
    assert segment.visual.title == "Instead of 'send me that report', say 'could you send me that report?'"
    assert explainer_stage.card_title("word " * 40).endswith("…") and len(explainer_stage.card_title("word " * 40)) <= 121
    assert explainer_stage.card_title("", "Fallback note") == "Fallback note"
