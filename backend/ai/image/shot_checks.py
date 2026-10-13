"""Task 28.5: the extra-person rule of a shot (pure, no GPU).

Task 20.11 detected a third person with the worker's anime cut-out; on photographs that cut-out is blind (it said
0.0 on a market full of vendors and let a three-person duo through, Task 28.4b). The worker now counts FACES with a
small detector (`count_faces`), and the rule is: a face beyond the people the shot is meant to show is an extra person.
"""

from __future__ import annotations


def extra_faces(faces: int, people: int) -> int:
    """Faces beyond the people in the shot. Fewer faces than people is not an extra person (someone may be turned
    away); an insert shows nobody, so any face in it is extra."""
    return max(0, faces - people)
