"""Phase 28 (Task 28.3): the semi-realistic look in the app -- single-colour outfits, the editorial recipes,
RealVisXL in the worker request and the photographic white/black colour rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.schemas.visuals import CharacterInput

ROOT = Path(__file__).resolve().parent.parent

LAN = {
    "gender": "female", "age_group": "young", "ethnicity": "Vietnamese", "role": "English teacher",
    "hair": "long straight black hair", "eyes": "dark eyes",  # the form allows 4 hair words at most
    "top_color": "white", "top_item": "blouse", "bottom_color": "white", "bottom_item": "trousers",
}
MINH = {
    "gender": "male", "age_group": "young", "ethnicity": "Vietnamese", "role": "English teacher",
    "hair": "tousled black hair", "eyes": "dark eyes",
    "top_color": "black", "top_item": "slim-fit shirt", "bottom_color": "black", "bottom_item": "slim trousers",
}
TWO_COLOURS = {**LAN, "top_color": "light blue", "bottom_color": "navy blue", "top_item": "slim-fit shirt",
               "bottom_item": "slim trousers"}


def test_character_with_one_colour_is_accepted_and_a_bad_colour_is_not():
    fields = {"name": "Lan", **LAN}
    assert CharacterInput(**fields).top_color == CharacterInput(**fields).bottom_color == "white"
    with pytest.raises(ValueError, match="solid colours"):
        CharacterInput(**{**fields, "bottom_color": "plaid"})
