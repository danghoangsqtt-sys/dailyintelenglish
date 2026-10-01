"""The fixed Phase 20 image prompts and conservative CLIP token estimator."""

import re
from collections.abc import Mapping

STYLE_R3_WATERCOLOR = (
    "hand-painted 2D anime illustration, soft watercolor background, warm natural sunlight, "
    "gentle pastel palette, cozy whimsical atmosphere, clean line art"
)
NEGATIVE = (
    "3d render, photorealistic, photo, text, logo, watermark, blurry, deformed, bad anatomy, "
    "extra fingers, deformed hands, hand on face, backpack, hat, cap, jacket, coat, hoodie, "
    "scarf, pattern, stripes, plaid, print, multicolored clothes, layered clothes, crowd"
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
    return ", ".join((STYLE_R3_WATERCOLOR, *parts))


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


def scene_preview_prompt(scene: Mapping) -> str:
    return _styled(scene["place"], "empty scene, no people")


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


def hand_prompt() -> str:
    return _styled(HAND_PROMPT)
