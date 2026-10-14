"""The image prompts. Phase 44 (D123): only Qwen draws, so only its sentence prompts remain (illustrations, plates, the
topic picture, the AI-scene thumbnail) plus the outside-AI prompt of an activity picture."""

from collections.abc import Mapping

# The kinds of picture a character profile keeps (the profile slots still use these names).
SHEET_KINDS = ("full_body", "portrait_calm", "portrait_smile", "portrait_surprised")
TIME_OF_DAY_LIGHT = {
    "morning": "soft morning light", "day": "", "sunset": "golden sunset light", "night": "night, warm lamps",
}


def activity_outside_prompt(action: str, place: str = "") -> str:
    """D102: the prompt the owner pastes into an outside AI for the same picture (no attachment needed)."""
    where = f" in {place}" if place else ""
    return (f"Create a semi-realistic illustration, landscape 16:9 (1344 x 768), of one ordinary adult {action}{where}. "
            "Show the action clearly in the middle of the picture, natural light, friendly everyday mood, a simple uncluttered "
            "background. No text, no letters, no logo, no watermark, no famous person, no cartoon style.")


# Phase 39 (D118): Qwen reads whole sentences (no CLIP 77-token limit), so its prompts describe the picture in plain
# English instead of comma tags. D110: illustrations show a few ordinary people of different looks (the benchmark showed
# Qwen repeats one face unless asked for variety).
QWEN_PHOTO = "Photorealistic editorial photograph, soft natural light, crisp sharp focus."


def qwen_activity_prompt(action: str, place: str = "") -> str:
    where = f" in {place}" if place else ""
    return (f"{QWEN_PHOTO} A natural candid moment: ordinary people {action or 'going about the day'}{where}. One to three "
            "everyday people of different ages, genders and looks, the action clearly visible in the middle of the frame, "
            "realistic faces and hands, casual clothes. No text, no letters, no logo, no watermark.")


def qwen_scene_prompt(scene: Mapping) -> str:
    light = TIME_OF_DAY_LIGHT.get(scene.get("time_of_day", "day"), "")
    return (f"{QWEN_PHOTO} A wide view of {scene['place']}{', ' + light if light else ''}. The place is completely empty, "
            "with no people at all. Realistic details. No text, no letters, no logo.")


def qwen_topic_prompt(topic: str, illustration: str) -> str:
    """The thumbnail's topic picture: the background the composer draws the characters, headline and badges on. Gate
    B-26 r1: naming a "thumbnail" or a "title" made the model letter the picture and put a person in front, so it is
    described as a plain scene with objects only (the cast and the text are added by the composer)."""
    short_topic = topic.split(". ")[0].strip().rstrip(".")
    subject = illustration or short_topic
    return (f"{QWEN_PHOTO} A vivid, colourful still-life scene about {short_topic.lower()}: {subject}, shown with objects "
            "only. The main objects fill the right half of the frame; the left half is a softly blurred, calm, slightly "
            "darker background. Bright colours, high contrast. Absolutely no people, no hands, no text, no letters, "
            "no signs, no logo, no watermark.")


def qwen_thumbnail_scene_prompt(names: list[str], topic: str, scene: str = "") -> str:
    """Phase 43 (D122): the AI-scene thumbnail -- Qwen-Image-Edit-2511 draws the episode's characters (picture 1, 2 =
    their sprites) together in a scene of the topic. The same composition rules as the outside-AI prompt (2026-10-14
    thumbnail research): head-and-shoulders, big faces, heads apart, a plain side for the headline the app adds, no
    lettering. The picture is drawn wider than the frame (1536x720); the app then picks the 1280x720 window."""
    short_topic = topic.split(". ")[0].strip().rstrip(".")
    place = (scene or f"a real place that fits {short_topic.lower()}").strip().rstrip(".")
    if len(names) >= 2:
        who = (f"{names[0]} (the person in picture 1) and {names[1]} (the person in picture 2) standing side by side, "
               f"{names[0]} on the left, turned slightly towards each other; shoulders may touch but their heads and "
               "faces do not overlap")
    elif names:
        who = f"{names[0]} (the person in picture 1)"
    else:
        who = "two friendly young adults side by side"
    return (f"{QWEN_PHOTO} A bright, eye-catching photo of {who}, in {place}. Head-and-shoulders close-up, each face "
            "large, big natural smiles, looking at the viewer. Keep each person's face, hair and clothes exactly as in "
            "their picture. The two people stand in the right part of the picture; the left part is only softly blurred "
            "background, calm and slightly darker, with no people and no objects in front. Vivid colours, high "
            "contrast. Absolutely no text, no letters, no numbers, no signs, no logo, no badge, no watermark.")
