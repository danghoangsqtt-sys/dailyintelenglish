"""The fixed Phase 20 image prompts and conservative CLIP token estimator."""

import re
from collections.abc import Mapping

# Phase 28 (owner, 2026-10-06): the pictures are crisp editorial photographs, like the channel banner,
# drawn by RealVisXL V5.0 (the cel-anime look of 2026-10-04 was replaced). Spike evidence:
# docs/operations/phase28-spike-style.md. No blur or bokeh (the owner disliked it), no studio, artist or
# franchise names.
STYLE_EDITORIAL = "editorial photograph, soft natural light, crisp sharp focus, high resolution"
# CLIP reads 77 tokens of the negative too, so the style guards come first and the
# outfit-lock words (owner 20.2h: 1 plain top + 1 plain bottom) follow.
NEGATIVE = (
    "blurry, bokeh, low resolution, cartoon, anime, 3d render, plastic skin, ugly, asymmetrical face, "
    "text, watermark, deformed, bad anatomy, extra fingers, deformed hands, extra person, crowd, glasses, "
    "backpack, hat, jacket, hoodie, scarf, stripes, plaid, print, multicolored clothes"
)
# Task 23.3: the scene plate must be empty -- a person in the plate is carried into shots by
# the scene reference (the Market and Office plates of the first built-in run had people).
PLATE_NEGATIVE = (
    "person, people, man, woman, girl, boy, child, crowd, character, figure, blurry, bokeh, cartoon, anime, "
    "illustration, 3d render, low resolution, text, watermark"
)
def negative_for(*characters: Mapping) -> str:
    """`NEGATIVE` for the people in a picture, naming the colours this cast tends to drift into (Task 28.4b): a
    black outfit drifts to navy, a white one gets a blazer or blue jeans. A navy outfit (or jeans) is never fought.
    Stays within 77 real CLIP tokens (tested)."""
    colours = {character[key] for character in characters for key in ("top_color", "bottom_color")}
    negative = NEGATIVE
    suit = any(character["top_item"] == "suit jacket" for character in characters)
    if suit:  # Phase 31: a suit is a jacket over a white shirt and a tie: do not fight any of it
        negative = negative.replace("jacket, ", "").replace(", multicolored clothes", "")
    if "black" in colours and "navy blue" not in colours:
        negative = negative.replace("multicolored clothes", "navy blue clothes")
    if len(characters) == 1 and characters[0].get("extra") and "long" in characters[0]["hair"]:
        negative += ", short hair"  # Phase 31: a long-haired woman keeps her hair (not in a duo: the man's would be fought)
    if any("clean-shaven" in (character.get("extra") or "") for character in characters):
        negative += ", beard"
    if "white" in colours:
        if not suit:
            negative += ", blazer"
        if not any(character["bottom_item"] in ("jeans", "mini dress") for character in characters):
            negative += ", blue jeans"  # (a dress has no trousers to drift into jeans)
    return negative


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
    return ", ".join((STYLE_EDITORIAL, *parts))


# Phase 31: what is always worn with a garment (Alex's suit comes with a white shirt and a black bow tie).
ACCESSORIES = {"suit jacket": ", white shirt, black bow tie", "mini dress": ", fitted corset bodice, thin straps"}


def outfit_phrase(character: Mapping) -> str:
    """The locked outfit. A single-colour outfit (the Phase 28 characters: the woman all white, the man
    all black) names its colour once; two colours name each garment; a dress is one garment."""
    accessory = ACCESSORIES.get(character["top_item"], "")
    if character["top_item"] == character["bottom_item"]:
        return f"plain {character['top_color']} {character['top_item']}{accessory}"
    if character["top_color"] == character["bottom_color"]:
        return f"plain {character['top_color']} {character['top_item']} and {character['bottom_item']}{accessory}"
    return (f"plain {character['top_color']} {character['top_item']}, plain {character['bottom_color']} "
            f"{character['bottom_item']}{accessory}")


def hair_phrase(character: Mapping) -> str:
    """The hair and the owner's identity detail (`extra`: skin, bangs...), as one prompt part."""
    extra = (character.get("extra") or "").strip()
    return f"{character['hair']}, {extra}" if extra else character["hair"]


def character_phrase(character: Mapping) -> str:
    gender_noun = "woman" if character["gender"] == "female" else "man"
    return (
        f"{character['age_group']} {character['ethnicity']} {gender_noun} {character['role']}, "
        f"{hair_phrase(character)}, {character['eyes']}, {outfit_phrase(character)}"
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


def gaze_words(side: str | None) -> tuple[str, ...]:
    """Task 29.1: where a person looks ("right" / "left"), as prompt parts; nothing when `side` is None."""
    return (f"looking to the {side}",) if side else ()


def single_prompt(character: Mapping, scene: Mapping, gaze: str | None = None) -> str:
    # Task 23.3: "close-up, talking" (was "..., talking with a hand gesture"): with the longest
    # character the real CLIP tokenizer counted 78-79 tokens for the built-in Cafe/Classroom
    # places, cutting the place's last word (the estimator said 74). The pose sets the hand.
    return _styled(character_phrase(character), "close-up, talking", *gaze_words(gaze), f"in {scene['place']}")


def duo_prompt(left: Mapping, right: Mapping, scene: Mapping, kind: str, gaze: bool = False) -> str:
    base = (
        f"two {left['ethnicity']} people talking face to face, {duo_person(left)} on the left, "
        f"{duo_person(right)} on the right" + (", looking at each other" if gaze else "")
    )
    if kind == "duo_close":
        return _styled(base, f"close-up, in {scene['place']}")
    if scene["staging"] == "seated":
        return _styled(base, f"sitting at a table in {scene['place']}")
    return _styled(base, f"standing in {scene['place']}")


def refine_prompt(character: Mapping, scene: Mapping, gaze: str | None = None) -> str:
    return _styled(character_phrase(character), "talking", *gaze_words(gaze), f"in {scene['place']}")


def garment_refine_prompt(character: Mapping, scene: Mapping, gaze: str | None = None) -> str:
    """Task 20.11 colour retry: the garments lead (right after the style), so the locked
    colours carry the most weight when one person's region is repainted."""
    gender_noun = "woman" if character["gender"] == "female" else "man"
    return _styled(
        f"{outfit_phrase(character)}, {character['age_group']} {character['ethnicity']} {gender_noun}, "
        f"{hair_phrase(character)}, talking" + (f", {gaze_words(gaze)[0]}" if gaze else "") + f", in {scene['place']}"
    )


def hand_prompt() -> str:
    return _styled(HAND_PROMPT)


# Task 24.3: a beat's expression and action in its pictures.
EXPRESSION_WORDS = {
    "calm": "calm friendly face", "smile": "warm smile", "laugh": "laughing happily",
    "surprised": "surprised face", "thinking": "thoughtful look", "worried": "worried look",
    "serious": "serious expression",
}
# Calibrated in Task 23.3: `token_count` <= 72 keeps the real CLIP count <= 77 on these prompts.
BEAT_TOKEN_BUDGET = 72


def compact_phrase(character: Mapping) -> str:
    """`character_phrase` without the role and eye colour: in beat shots the face IP-Adapter carries
    identity, and the freed tokens go to the action and the expression."""
    gender_noun = "woman" if character["gender"] == "female" else "man"
    return (
        f"{character['age_group']} {character['ethnicity']} {gender_noun}, {hair_phrase(character)}, "
        f"{outfit_phrase(character)}"
    )


_TRAILING = {"a", "an", "the", "at", "in", "on", "to", "with", "of", "and", "for", "from", "by"}


def _cut(words: list[str], keep: int) -> list[str]:
    words = words[:keep]
    while len(words) > 1 and words[-1].lower() in _TRAILING:
        words = words[:-1]
    return words


def fit_budget(build, action: str, place: str) -> str:
    """`build(action, place)` -> prompt within BEAT_TOKEN_BUDGET, so CLIP never cuts the tail
    itself. The action carries the beat, the place is also carried by the Task 23.2 plate, so:
    shorten the action to 4 words, then drop the place, then shorten the action to 2 words.
    A cut never ends on a dangling "at"/"a"/"the"."""
    words = action.split()
    prompt = build(" ".join(words), place)
    while token_count(prompt) > BEAT_TOKEN_BUDGET and len(words) > 4:
        words = _cut(words, len(words) - 1)
        prompt = build(" ".join(words), place)
    if token_count(prompt) > BEAT_TOKEN_BUDGET:
        place = ""
        prompt = build(" ".join(words), place)
    while token_count(prompt) > BEAT_TOKEN_BUDGET and len(words) > 2:
        words = _cut(words, len(words) - 1)
        prompt = build(" ".join(words), place)
    return prompt


def insert_prompt(subject: str) -> str:
    """Task 24.5a: an insert illustrates what a speaker describes (no characters, no plate)."""
    return _styled(subject, "wide view, detailed scene")


def insert_person_prompt(character: Mapping, subject: str) -> str:
    """Task 29.2: an insert that shows a cast character doing what the speaker describes (checking a phone, eating
    oatmeal, stretching). The face reference carries identity; the locked outfit is named; no pose, no plate."""
    def build(act: str, place: str) -> str:
        return _styled(compact_phrase(character), "medium shot", act or "relaxed, natural")

    return fit_budget(build, subject, "")


def beat_single_prompt(character: Mapping, scene: Mapping, action: str, expression: str,
                       gaze: str | None = None) -> str:
    feeling = EXPRESSION_WORDS.get(expression, EXPRESSION_WORDS["calm"])

    def build(act: str, place: str) -> str:
        return _styled(compact_phrase(character), "close-up", feeling, *gaze_words(gaze), act or "talking",
                       *((f"in {place}",) if place else ()))

    return fit_budget(build, action, scene["place"])


def beat_duo_prompt(left: Mapping, right: Mapping, scene: Mapping, kind: str, action: str, expression: str,
                    gaze: bool = False) -> str:
    feeling = EXPRESSION_WORDS.get(expression, EXPRESSION_WORDS["calm"])
    base = (
        f"two {left['ethnicity']} people talking face to face, {duo_person(left)} on the left, "
        f"{duo_person(right)} on the right" + (", looking at each other" if gaze else "")
    )
    framing = ("close-up" if kind == "duo_close" else
               "sitting at a table" if scene["staging"] == "seated" else "standing")

    def build(act: str, place: str) -> str:
        return _styled(base, framing, feeling, *((act,) if act else ()), *((f"in {place}",) if place else ()))

    return fit_budget(build, action, scene["place"])
