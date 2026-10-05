# Task 23.3b — Exam-setting scene pack: IELTS + Cambridge listening, school, countryside (doc-first card)

**Owner request 2026-10-05:** "thêm vào các bối cảnh thường xuất hiện trong các bài thi nghe ielts và
cambridge, ở trường học và nông thôn" — add the settings that recur in IELTS and Cambridge listening
tests, in schools and in the countryside.

## Where the settings come from

- **IELTS Listening:** Part 1 everyday transactions (hotel reception, travel agency, sports-centre
  membership, letting agency, clinic registration); Part 2 guided tours and local facilities (museum,
  botanical garden, farm visit, community centre); Part 3 student discussions (tutor's office, seminar
  room, common room, lab); Part 4 lectures (lecture hall).
- **Cambridge KET/PET/FCE Listening:** school life (canteen, sports hall, schoolyard, art and computer
  rooms), shopping, cinema, zoo, swimming pool, camping, farm and village life.
- **Vietnamese countryside** for the channel's learners: rice fields, village road and market.

## Pack (39 new built-ins → 55 total) — revised with the owner's three groups (2026-10-05)

Owner, refining the request: urban (cinema, supermarket, bookshop, cafe, restaurant…), school
(lecture hall, lab, library, schoolyard…), countryside (fields, stream, mountain forest, rural
market, summer camp…). So the pack is grouped as **city / school / countryside**, plus a few travel
and work settings from IELTS Part 1. New category **countryside**; no "leisure" category. Existing
built-ins move to the owner's grouping only while they still carry their seeded category:
Cafe, Restaurant, Market (food → city), Park (nature → city), Countryside (nature → countryside).

| Category | New places (place text; seated if marked) |
|---|---|
| city (12) | a cinema lobby · a supermarket aisle · a cozy bookshop · a quiet museum gallery · a sports centre reception · an indoor swimming pool · a city zoo · a community centre hall · a small medical clinic (seated) · a busy shopping mall · a small post office · a botanical garden |
| school (11) | a university lecture hall (seated) · a school science laboratory · a busy school canteen (seated) · a school sports hall · a sunny schoolyard · a school computer room (seated) · a small tutor office (seated) · a student common room (seated) · a school art room · a small seminar room (seated) · a school gate |
| countryside (12) | a small family farm · green rice fields · a quiet village road · a clear mountain stream · a misty mountain forest · a rural village market · a summer camp · a peaceful riverside · a cozy farmhouse kitchen (seated) · a fruit orchard · a quiet lakeside · a mountain hiking trail |
| travel (3) | a hotel reception desk · a small travel agency (seated) · an airport check-in hall |
| work (1) | a letting agency office (seated) |

Unmarked = standing. Place texts carry no apostrophes (the user-scene validator allows letters, spaces
and hyphens only, and built-ins follow the same rule).

## Checks

- Real CLIP tokenizer: every recipe × every built-in × the longest character ≤ 77 tokens; the
  estimator test (≤ 72) runs over all 55.
- Tests updated for 55 built-ins and the countryside category.
- All 39 new plates rendered into the owner's library (people-free plate negative), contact sheets
  `docs/operations/phase23-t3b-exam-plates-*.png` for Gate B-15.

## Results (2026-10-05)

- 55 built-ins: city 17 · school 14 · countryside 13 · travel 5 · work 3 · home 2 · nature 1.
  Category moves follow `PREVIOUS_BUILTIN_CATEGORIES` (a user re-categorisation is kept, tested).
- Real tokenizer: all 39 new places ≤ 77 tokens with the longest character (worst: airport check-in
  hall, 77 / estimate 72).
- 39 plates rendered into the owner's library (backup `data/backups/app_before_scene_pack_23_3b_20261005.db`).
  Plate review found 4 misses, fixed with new place texts through `PREVIOUS_BUILTIN_PLACES` (only rows
  still on the old text change; their plate is cleared and re-rendered; tested):
  - "a city zoo": no animals → "a zoo with elephants";
  - "a student common room": a bedroom → "a student lounge with sofas";
  - "a summer camp": an RV → "a summer camp with tents";
  - "a quiet village road": a European village → "a Vietnamese village road".
- Gate B-15 sheets: `docs/operations/phase23-builtin-plates-{city,school,countryside,travel,work,home,nature}.png`.
- Tests: full suite 1295 passed before the place-fix commit, plus 1 new test (scenes v2 + foundation:
  18 passed).
