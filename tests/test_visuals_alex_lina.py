"""Phase 31: the characters Alex (navy suit, white shirt, black bow tie) and Lina (white mini dress), both Russian. (Their
SDXL prompts, colour check and library pictures went with RealVisXL in Phase 44, D123.)"""

from __future__ import annotations

import pytest

from backend.schemas.visuals import CharacterInput

LINA = {
    "gender": "female", "age_group": "young", "ethnicity": "Russian", "role": "English teacher",
    "hair": "long chocolate brown hair", "eyes": "brown eyes", "extra": "fair porcelain skin, curtain bangs",
    "top_color": "white", "top_item": "mini dress", "bottom_color": "white", "bottom_item": "mini dress",
}
ALEX = {
    "gender": "male", "age_group": "young", "ethnicity": "Russian", "role": "university student",
    "hair": "short swept-back brown hair", "eyes": "brown eyes", "extra": "caramel blond highlights, clean-shaven",
    "top_color": "navy blue", "top_item": "suit jacket", "bottom_color": "navy blue", "bottom_item": "suit trousers",
}


def test_the_two_characters_are_valid_and_a_dress_is_one_garment():
    assert CharacterInput(name="Lina", **LINA).top_item == "mini dress"
    assert CharacterInput(name="Alex", **ALEX).bottom_item == "suit trousers"
    with pytest.raises(ValueError, match="one garment"):
        CharacterInput(name="Lina", **{**LINA, "bottom_item": "skirt"})
    with pytest.raises(ValueError, match="one garment"):
        CharacterInput(name="Lina", **{**LINA, "bottom_color": "black"})
    with pytest.raises(ValueError, match="one garment"):
        CharacterInput(name="Alex", **{**ALEX, "top_item": "mini dress"})
    assert CharacterInput(name="Lina", **LINA).extra == "fair porcelain skin, curtain bangs"
    for bad in ("one two three four five six seven", "x" * 51, "digits 123"):
        with pytest.raises(ValueError, match="extra"):
            CharacterInput(name="Lina", **{**LINA, "extra": bad})
