# Phase 85 summary — Pictures in 16:9 videos, and the 16:9 test set

Done 2026-10-28 on `owner-runs/20261001-r9` (not pushed).

## What changed

- **85.1** the Producer approves the conversation storyboard it proposes (`202de88`, committed before the plan): the
  automatic 16:9 conversation had played on the default background with none of its scenes or inserts.
- **85.2** the presenter plan asks for a picture in about every second segment (library first, else a photo slot).
- **85.3** image job `explainer_illustrations` / `POST explainer-plan/illustrate`: Qwen-Image-2.1 draws each empty photo
  slot from its description (no presenter face), the picture is set on the segment and kept in the Activity Library
  (approved, tagged qwen); the Producer draws before approving a plan.
- **85.4** the Producer draws (D102) and approves storyboard inserts with no library picture.
- After the test run: a long script that says goodbye in the middle and greets again (two episodes in one) is refused
  by the script check, sections are told not to greet / say goodbye unless first / last (`2cf5be4`); the fact check
  judges facts only.

## Real checks

- Sandbox: Qwen drew 2 matching photos for a presenter plan in 150 s; the conversation's approved storyboard matched all
  6 inserts to library pictures.
- Installed app (`3059a99`), `D:\Videos\Kiểm tra 16 9 2026-10-28`:
  - Presenter how: 7 of 11 segments with pictures (5 drawn, 2 library); Presenter list 5 of 9; VOX how 4 of 13;
    VOX list 3 of 10 (plus quotes, diagram, timeline). Before this phase: 0.
  - Presenter why: stopped by the fact check, which spotted the script was two episodes in one (fixed after).
  - VOX why: stopped by the fact check: its chart claimed an invented "10x more effective" figure (correct stop).
  - Own-script conversation (`own_dialogue.txt`, verbatim): 19 of 19 lines identical (speaker and words), nothing added;
    storyboard approved, 4 inserts with library pictures; 157 s at 1920x1080 in `D:\Videos\Planning a team lunch`.
- Full pytest: 2239 passed.
