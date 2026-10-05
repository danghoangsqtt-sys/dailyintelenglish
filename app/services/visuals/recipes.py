"""The fixed Phase 20 image prompts and conservative CLIP token estimator."""

import re
from collections.abc import Mapping

# Style spike 2026-10-04 (owner's references): a 1990s hand-drawn cel-anime film look --
# clean dark ink outlines, flat 2-tone cel shading, saturated natural colours, a lush
# gouache-painted background in warm sunlight. It replaces the r3 watercolor preset, whose
# "watercolor / pastel" words produced the washed-out, low-contrast, semi-realistic faces.
# Task 20.10 (O11): no studio, artist or franchise names -- the look comes from neutral words
# (A/B against the named wording: docs/operations/phase20-t10-neutral-style-ab.png).
STYLE_CEL_ANIME = (
    "hand-drawn 1990s anime film still, clean ink outlines, flat cel shading, "
    "lush painted background, warm sunlight, vivid colors"
)
# CLIP reads 77 tokens of the negative too, so the style guards come first and the
# outfit-lock words (owner 20.2h: 1 plain top + 1 plain bottom) follow.
NEGATIVE = (
    "watercolor, pastel, washed out, faded, overexposed, photorealistic, realistic face, 3d render, "
    "glossy skin, text, watermark, deformed, bad anatomy, extra fingers, deformed hands, extra person, "
    "crowd, backpack, hat, jacket, hoodie, scarf, stripes, plaid, print, multicolored clothes"
)
HAND_PROMPT = "detailed hand, five fingers, natural hand"
HAND_NEGATIVE = "extra fingers, missing fingers, fused fingers, deformed hands, bad anatomy, blurry"
SHEET_KINDS = ("full_body", "portrait_calm", "portrait_smile", "portrait_surprised")
SHEET_SUFFIX = {
    "full_body": "full body, front view, plain light background",
    "portrait_calm": "portrait, calm friendly face, plain light background",
    "portrait_smile": "portrait, big happy smile, plain light background",
    "portrait_surprised": "portrait, surprised face, open mouth, plain light background",
}


def token_count(prompt: str) -> int:
    """The §2.3 estimator; worker tokenizer metadata remains authoritative."""
    return len(re.findall(r"[A-Za-z]+|\d+|[^\sA-Za-z\d]", prompt))


def _styled(*parts: str) -> str:
    return ", ".join((STYLE_CEL_ANIME, *parts))


def character_phrase(character: Mapping) -> str:
    gender_noun = "woman" if character["gender"] == "female" else "man"
    return (
        f"{character['age_group']} {character['ethnicity']} {gender_noun} {character['role']}, "
        f"{character['hair']}, {character['eyes']}, plain {character['top_color']} "
        f"{character['top_item']}, plain {character['bottom_color']} {character['bottom_item']}"
    )


def duo_person(character: Mapping) -> str:
    gender_noun = "woman" if character["gender"] == "female" else "man"
    return f"{gender_noun} in plain {character['top_color']} {character['top_item']}"


def candidate_prompt(character: Mapping) -> str:
    return _styled(character_phrase(character), "portrait, facing the viewer, arms down, plain light background")


def sheet_prompt(character: Mapping, kind: str) -> str:
    return _styled(character_phrase(character), SHEET_SUFFIX[kind])


TIME_OF_DAY_LIGHT = {
    "morning": "soft morning light", "day": "", "sunset": "golden sunset light", "night": "night, warm lamps",
}


def scene_preview_prompt(scene: Mapping) -> str:
    """The scene plate (Task 23.2): the place at its time of day, wide and empty."""
    light = TIME_OF_DAY_LIGHT.get(scene.get("time_of_day", "day"), "")
    return _styled(scene["place"], *((light,) if light else ()), "wide view, empty scene, no people")


def single_prompt(character: Mapping, scene: Mapping) -> str:
    return _styled(character_phrase(character), f"close-up, talking with a hand gesture, in {scene['place']}")


def duo_prompt(left: Mapping, right: Mapping, scene: Mapping, kind: str) -> str:
    base = (
        f"two {left['ethnicity']} people talking face to face, {duo_person(left)} on the left, "
        f"{duo_person(right)} on the right"
    )
    if kind == "duo_close":
        return _styled(base, f"close-up, in {scene['place']}")
    if scene["staging"] == "seated":
        return _styled(base, f"sitting at a table in {scene['place']}")
    return _styled(base, f"standing in {scene['place']}")


def refine_prompt(character: Mapping, scene: Mapping) -> str:
    return _styled(character_phrase(character), f"talking, in {scene['place']}")


def garment_refine_prompt(character: Mapping, scene: Mapping) -> str:
    """Task 20.11 colour retry: the garments lead (right after the style), so the locked
    colours carry the most weight when one person's region is repainted."""
    gender_noun = "woman" if character["gender"] == "female" else "man"
    return _styled(
        f"plain {character['top_color']} {character['top_item']}, plain {character['bottom_color']} "
        f"{character['bottom_item']}, {character['age_group']} {character['ethnicity']} {gender_noun}, "
        f"{character['hair']}, talking, in {scene['place']}"
    )


def hand_prompt() -> str:
    return _styled(HAND_PROMPT)
