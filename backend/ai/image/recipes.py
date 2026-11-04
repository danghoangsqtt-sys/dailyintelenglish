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


def qwen_illustration_prompt(description: str) -> str:
    """Phase 85 (owner 2026-10-28): the picture a Solo / VOX segment asked for -- an everyday photo of ordinary people or
    objects (D123: never the presenter or any cast face)."""
    what = " ".join(str(description or "").split()).rstrip(".") or "an everyday scene that fits the lesson"
    return (f"{QWEN_PHOTO} {what}. Ordinary everyday people of different ages and looks, or simply the objects and the "
            "place, natural and believable, landscape composition with the subject clearly visible. No text, no letters, "
            "no logo, no watermark, no famous person.")


def qwen_collage_prompt(description: str) -> str:
    """Phase 86 (VOX): the picture as an editorial paper cut-out collage of objects -- the Vox look, not a photograph."""
    what = " ".join(str(description or "").split()).rstrip(".") or "objects that show the lesson's idea"
    return ("Editorial paper cut-out collage illustration on warm kraft paper, like a magazine explainer: " f"{what}. "
            "Cut-out objects with torn paper edges and soft shadows, muted warm colours with one green accent, simple and "
            "uncluttered, landscape composition. No faces, no people in close-up, no text, no letters, no logo, no watermark.")


def qwen_word_prompt(description: str) -> str:
    """Phase 96 (D151): a Word of the day picture filling a 9:16 frame, with calm areas for the word over it."""
    what = " ".join(str(description or "").split()).rstrip(".") or "a simple scene that shows the word's meaning"
    return (f"Warm, richly coloured storybook illustration, full frame, portrait composition: {what}. Clear subject, soft "
            "painted light, simple background. If a person is needed show only hands or a figure from behind, with no "
            "visible face. No text, no letters, no numbers, no signs, no logo, no watermark, no frame.")


def qwen_object_prompt(description: str) -> str:
    """Phase 96.5: one object alone on a plain colour for the "What is this called?" Short; the words go over the empty parts."""
    what = " ".join(str(description or "").split()).rstrip(".") or "a simple everyday object"
    return (f"A single object: {what}. Clean realistic product picture, the whole object visible and fairly small, centred "
            "left to right in the upper half of the frame, the whole lower half of the frame empty, soft shadow, plain solid "
            "pale sky-blue background filling the portrait frame. No other objects, no people, no text, no letters, no "
            "numbers, no logo, no watermark.")


def qwen_moment_prompt(description: str) -> str:
    """Phase 96.6 (owner 2026-11-04): the real moment of a phrase: an ordinary made-up person whose feeling reads at a glance. This
    kind has no recurring cast, so a face is allowed here (the reason for D123 does not apply)."""
    what = " ".join(str(description or "").split()).rstrip(".") or "an ordinary person in an everyday moment"
    return (f"Warm, richly coloured storybook illustration, full frame, portrait composition: {what}. An ordinary made-up person "
            "with a clear, expressive feeling in the face and body, one simple pose, natural anatomy with exactly two arms, two "
            "hands and five fingers on each hand, a believable everyday place, soft light, the head in the upper middle of the frame with free space above it. No text on "
            "anything. No text, no letters, no numbers, no signs, no logo, no watermark, no frame.")


def qwen_moment_prompt(description: str) -> str:
    """Phase 96.6 (owner 2026-11-04): the real moment of a phrase: an ordinary made-up person whose feeling reads at a glance. This
    kind has no recurring cast, so a face is allowed here (the reason for D123 does not apply)."""
    what = " ".join(str(description or "").split()).rstrip(".") or "an ordinary person in an everyday moment"
    return (f"Warm, richly coloured storybook illustration, full frame, portrait composition: {what}. An ordinary made-up person "
            "with a clear, expressive feeling in the face and body, a believable everyday place, soft light, the person in the "
            "lower two thirds of the frame. No text, no letters, no numbers, no signs, no logo, no watermark, no frame.")


def qwen_firstperson_prompt(description: str) -> str:
    """Phase 96 (D152): one sentence of a picture story, seen through the speaker's eyes: only hands or feet, so that no two
    pictures of a video show a different person."""
    what = " ".join(str(description or "").split()).rstrip(".") or "hands doing a simple everyday action"
    return (f"First-person point of view, looking down at one's own hands or feet: {what}. Warm, richly coloured storybook "
            "illustration, full frame, portrait composition, natural anatomy with five fingers on each hand, one clear "
            "action, simple everyday background, soft light. No face, no other person, no text, no letters, no numbers, "
            "no signs, no logo, no watermark, no frame.")


def qwen_lineart_prompt(description: str) -> str:
    """Phase 87.4 (roots Short): a simple line drawing on cream paper, like the hand-drawn explainer the owner sent."""
    what = " ".join(str(description or "").split()).rstrip(".") or "a simple object that shows the word's meaning"
    return ("Minimal hand-drawn line art illustration, single-weight dark brown ink lines on plain cream paper, flat, "
            f"no shading: {what}. One small soft green accent fill, lots of empty space, centred, simple and clear like a "
            "textbook doodle. Stick figures only if a person is needed, with a plain round head and no face. No text, "
            "no letters, no numbers, no logo, no watermark, no frame.")


SCENE_COMPOSITION = (
    "Landscape 16:9 background plate, eye-level wide view with believable perspective and open foreground space "
    "for characters added later. The place is completely empty: no people, faces, human figures or silhouettes. "
    "No text, letters, signs, logos or watermarks."
)


def qwen_scene_prompt(scene: Mapping) -> str:
    """One effective prompt for local generation and external copying, including background composition rules."""
    custom = str(scene.get("image_prompt") or "").strip()
    if custom:
        return custom if custom.endswith(SCENE_COMPOSITION) else f"{custom}\n\n{SCENE_COMPOSITION}"
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
    # Owner review 2026-10-14: the first pictures were darker and duller than ChatGPT's -- ask for a bright, sunny,
    # high-key advertising look and a bright (not darkened) left side; the app grades the picture afterwards too.
    # (second try: "high-key" + a close-up blew out the highlights and changed hair colours; the owner's ChatGPT
    # reference is a natural daylight medium shot with the place clearly behind the people)
    return (f"A bright, cheerful photograph of {who}, in {place} on a clear sunny day, natural daylight, well exposed. "
            "Medium shot from the waist up, friendly open gestures, big natural smiles, looking at the viewer. Keep each "
            "person's face, hair colour, hairstyle and clothes exactly as in their picture. The two people stand in the "
            "right part of the picture; the left part shows the place itself, softly out of focus, bright and "
            "colourful, with no people in front. Realistic vivid colours, crisp sharp focus, clean commercial look. "
            "Absolutely no text, no letters, no numbers, no signs, no logo, no badge, no watermark.")
