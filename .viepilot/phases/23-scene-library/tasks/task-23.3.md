# Task 23.3 — Built-in scene pack (16 places) + real-tokenizer budget (doc-first card)

## Pack

The 6 existing built-ins keep their text (users may have shots on them). 10 are added, each
with a category and staging. All are short on purpose: since 23.2 the plate carries the
detail, and the place is the prompt's tail, so it is cut first.

| id | place | staging | category |
|---|---|---|---|
| living-room | a cozy living room | seated | home |
| restaurant | a small family restaurant | seated | food |
| market | a busy outdoor market | standing | food |
| campus | a green university campus | standing | school |
| meeting-room | a bright meeting room | seated | work |
| street | a busy city street | standing | city |
| bus-stop | a city bus stop | standing | travel |
| station | a train station platform | standing | travel |
| countryside | a countryside path | standing | nature |
| beach | a sunny beach | standing | nature |

## Token budget (real CLIP tokenizer, longest character, every recipe)

Measured 2026-10-05: the `single` prompt reached **79 / 78 tokens** for the existing Classroom /
Cafe places, so CLIP dropped the place's last word ("whiteboard", "cafe"); the in-repo estimator
said 74. Fix: the single suffix becomes "close-up, talking" (the pose sets the hand). Target:
every recipe × every built-in place × the longest character ≤ 77 real tokens. The estimator
test is tightened to that measured gap (real ≈ estimator + 6).

## Plates for Gate B-15

A script renders the 16 plates into the owner's real library (scene preview jobs through the
app API) and a contact sheet `docs/operations/phase23-t3-builtin-plates.png` for the owner.
