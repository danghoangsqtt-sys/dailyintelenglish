# Owner-machine results r9 (Phase 20 verification + Gate B-14 part 1) 2026-10-01
- Pinned commit: ecaeaf02bf1a44cb37f864b566955b0e233d9eb2
- Env: Python 3.14.7; torch 2.11.0+cu128, CUDA 12.8, available True, diffusers 0.40.0; Node v24.20.0.

## Automated checks
- pytest: 1273 passed, 2 warnings in 493.89s (0:08:13); failing test names: none.
- ruff: All checks passed!; tsc: empty; vitest: Tests  39 passed (39).
- fake smoke: shot_count 8, shot_generation_seconds 4.6, three_stills_seconds 9.61; error: none.

## Real smoke
- refine ON: shot_count 8, seed 20261001, duo_refine true, shot_generation_seconds 630.12, three_stills_seconds 10.91, prompt_truncated count 0 (evidence.shots), error: none.
- refine OFF: shot_count 8, seed 20261001, duo_refine false, shot_generation_seconds 465.61, three_stills_seconds 10.39, prompt_truncated count 0 (evidence.shots), error: none.
- faces identical between runs?: yes. The two `characters/Lan/face.png` files have the same SHA-256, `AC4C27B9BED55778536345C0AEE513C50C73381F2147D6A3505E86EB331AE0A0`.
- Packaged files: refine ON has 38 PNGs, including 16 shot PNGs and both characters' candidates, faces, and sheets. Refine OFF has 20 PNGs, including 16 shot PNGs; its duplicate character files were left out. No file was missing or larger than 25 MB.

## Visual checklist (executor observations)

| run | shot label | variant | people visible (count) | Lan top yellow? | Lan bottom navy? | Minh top light blue? | Minh bottom black? | extra person? | hands visibly malformed? (count) | notes (≤ 12 words) |
|---|---|---|---:|---|---|---|---|---|---:|---|
| on | 00_Cafe_single_0 | raw | 1 | yes | n/a | n/a | n/a | no | 0 | Lan holds a cup; lower body cropped. |
| on | 00_Cafe_single_0 | final | 1 | yes | n/a | n/a | n/a | no | 0 | Lan holds a cup; lower body cropped. |
| on | 01_Cafe_single_1 | raw | 1 | n/a | n/a | yes | n/a | no | 0 | Pale blue open shirt over white undershirt. |
| on | 01_Cafe_single_1 | final | 1 | n/a | n/a | yes | n/a | no | 0 | Pale blue open shirt over white undershirt. |
| on | 02_Cafe_duo_close_0-1 | raw | 3 | yes | n/a | no | n/a | yes | 0 | Short-haired person in yellow stands between Lan and Minh. |
| on | 02_Cafe_duo_close_0-1 | final | 3 | yes | n/a | no | n/a | yes | 0 | Short-haired person in yellow stands between Lan and Minh. |
| on | 03_Cafe_duo_wide_0-1 | raw | 2 | yes | n/a | no | n/a | no | 0 | Minh wears tan overshirt above blue inner shirt. |
| on | 03_Cafe_duo_wide_0-1 | final | 2 | yes | n/a | no | n/a | no | 0 | Minh wears tan overshirt above blue inner shirt. |
| on | 04_Classroom_single_0 | raw | 1 | yes | n/a | n/a | n/a | no | 0 | Lan holds pen and paper; lower body cropped. |
| on | 04_Classroom_single_0 | final | 1 | yes | n/a | n/a | n/a | no | 0 | Lan holds pen and paper; lower body cropped. |
| on | 05_Classroom_single_1 | raw | 1 | n/a | n/a | yes | n/a | no | 0 | Pale blue open shirt over white undershirt. |
| on | 05_Classroom_single_1 | final | 1 | n/a | n/a | yes | n/a | no | 0 | Pale blue open shirt over white undershirt. |
| on | 06_Classroom_duo_close_0-1 | raw | 2 | yes | n/a | no | n/a | no | 0 | Lan has short brown hair; Minh wears ivory shirt. |
| on | 06_Classroom_duo_close_0-1 | final | 2 | yes | n/a | no | n/a | no | 0 | Lan has short brown hair; Minh wears ivory shirt. |
| on | 07_Classroom_duo_wide_0-1 | raw | 2 | yes | no | yes | no | no | 0 | Lan's jeans and Minh's trousers appear gray-green. |
| on | 07_Classroom_duo_wide_0-1 | final | 2 | yes | no | yes | no | no | 0 | Lan's jeans and Minh's trousers appear gray-green. |
| off | 00_Cafe_single_0 | raw | 1 | yes | n/a | n/a | n/a | no | 0 | Lan holds a cup; lower body cropped. |
| off | 00_Cafe_single_0 | final | 1 | yes | n/a | n/a | n/a | no | 0 | Lan holds a cup; lower body cropped. |
| off | 01_Cafe_single_1 | raw | 1 | n/a | n/a | yes | n/a | no | 0 | Pale blue open shirt over white undershirt. |
| off | 01_Cafe_single_1 | final | 1 | n/a | n/a | yes | n/a | no | 0 | Pale blue open shirt over white undershirt. |
| off | 02_Cafe_duo_close_0-1 | raw | 3 | yes | n/a | no | n/a | yes | 0 | Short-haired person in yellow stands between Lan and Minh. |
| off | 02_Cafe_duo_close_0-1 | final | 3 | yes | n/a | no | n/a | yes | 0 | Short-haired person in yellow stands between Lan and Minh. |
| off | 03_Cafe_duo_wide_0-1 | raw | 2 | yes | n/a | no | n/a | no | 0 | Minh wears tan overshirt above blue inner shirt. |
| off | 03_Cafe_duo_wide_0-1 | final | 2 | yes | n/a | no | n/a | no | 0 | Minh wears tan overshirt above blue inner shirt. |
| off | 04_Classroom_single_0 | raw | 1 | yes | n/a | n/a | n/a | no | 0 | Lan holds pen and paper; lower body cropped. |
| off | 04_Classroom_single_0 | final | 1 | yes | n/a | n/a | n/a | no | 0 | Lan holds pen and paper; lower body cropped. |
| off | 05_Classroom_single_1 | raw | 1 | n/a | n/a | yes | n/a | no | 0 | Pale blue open shirt over white undershirt. |
| off | 05_Classroom_single_1 | final | 1 | n/a | n/a | yes | n/a | no | 0 | Pale blue open shirt over white undershirt. |
| off | 06_Classroom_duo_close_0-1 | raw | 2 | yes | n/a | no | n/a | no | 0 | Lan has short brown hair; Minh wears ivory shirt. |
| off | 06_Classroom_duo_close_0-1 | final | 2 | yes | n/a | no | n/a | no | 0 | Lan has short brown hair; Minh wears ivory shirt. |
| off | 07_Classroom_duo_wide_0-1 | raw | 2 | yes | no | yes | no | no | 0 | Lan's jeans and Minh's trousers appear gray-green. |
| off | 07_Classroom_duo_wide_0-1 | final | 2 | yes | no | yes | no | no | 0 | Lan's jeans and Minh's trousers appear gray-green. |

- Caption text is readable in `single.png`, `duo_close.png`, and `duo_wide.png` in both runs.
- No vocabulary card is visible in either run's `duo_close.png` or `duo_wide.png`; face coverage by a vocabulary card is n/a.
- Extra person in duo shots: ON raw 1/final 1; OFF raw 1/final 1.
- Outfit colour mismatches: ON 10, OFF 10 visible expected-garment cells marked `no` in the table.

## Owner decisions (LEAVE EMPTY -- the owner fills this in)
- Duo refine: keep ON or switch OFF?:
- Third person / colour drift acceptable, or needs a recipe change?:
- Close-up and wide shots good enough to build real episodes (Gate B-14 part 2)?:
