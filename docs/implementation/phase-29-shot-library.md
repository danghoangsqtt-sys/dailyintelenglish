# Phase 29: Ready-made shot library of Lan and Minh (ENH-020)

**Status:** planned 2026-10-07 from the owner's request. **Order:** after Gate B-20 (the first full episode in the new
style), so the library is built on a pipeline the owner has already approved.

## 0. The owner's idea (2026-10-07)

A library of pre-rendered shots of the two characters talking: many angles, scenes and positions, mouth open or closed,
laughing, expressions, hand and body gestures. The video job takes ready shots from it and generates **only the
combinations that are missing**, so an episode no longer waits for every picture to be drawn from scratch.

## 1. What the numbers say (measured on the real job, 2026-10-06)

- One shot costs about **3.7 minutes** on the RTX 3060 (the 12-shot Demo Episode took 45 minutes). A 12-shot episode
  therefore waits about 45 minutes for pictures; with a good library it waits only for the missing ones.
- The combinations explode: 10 scenes x 4 framings x 7 expressions x 12 gestures = 3 360 shots = about 8 days of GPU.
  So the library cannot be "every combination": it has to be a **curated core set plus cheap variants**, and it must
  **grow by itself** (every shot a real episode generates is offered to the library).

## 2. Design

**A shot is described by tags** (a controlled vocabulary, so a match is a lookup, not a guess):

| Tag | Values (first proposal) |
|---|---|
| characters | the pair (Lan + Minh) or one of them |
| scene | a library scene (start with about 8 popular ones) |
| framing | single, duo close, duo wide, plus new camera angles: over-the-shoulder, three-quarter, side |
| staging | seated, standing |
| expression | calm, smile, laugh, surprised, thinking, worried, serious (the app's seven) |
| mouth | open (speaking) or closed (listening): matters for a talking video |
| gesture | talking with a hand gesture, listening and nodding, pointing, drinking coffee, reading, checking a phone, shrugging, counting on fingers, waving, handshake, walking together |

**Cheap variants:** one drawn pose per scene and framing, then **expression and mouth variants by repainting only the
face** with the character's face reference (about 35 s instead of 3.7 min): a spike decides whether the quality holds.

**Matching (storyboard to library):** a beat asks for a scene, who speaks, an action and an expression. The matcher
needs the **same scene, speakers and framing**; then ranks by expression, mouth, gesture; avoids repeating a library shot
inside one episode (and prefers one not used lately); a beat with no acceptable match is generated as today. The
storyboard prompt is told the library's gestures, so its actions land on tags more often.

**Growing:** every generated shot that passed its checks gets an "Add to library" button (and an automatic option).

**Safety:** a library shot is tied to the **face reference of each character**; if a character is regenerated or
changed, its shots are marked stale instead of silently reused.

## 3. Tasks

| Task | What | Accept when |
|---|---|---|
| 29.1 | **Design and spike (GPU):** fix the vocabulary and the budget; test (a) expression and mouth variants by face repaint, (b) gesture pose maps (arms, hands), (c) three new camera angles; measure seconds and look at the pictures | the owner sees the samples and approves the vocabulary and the size of the core set |
| 29.2 | **Data model and service:** `shot_library` table (migration), files under `data/library/shots/`, add / list / filter / delete / mark stale; API | tests green |
| 29.3 | **Matcher and the library-first job:** the project shot job resolves each shot spec against the library, copies a match (no GPU) and generates only the rest; the project shot records `source` (library or generated) | a fake-engine test generates only the missing shots; a real run on the Demo Episode |
| 29.4 | **Batch generator:** a resumable job that renders the core set overnight from a plan file, with the shot checks (colours, faces) and a coverage report | the core set is generated and looked at by sheets |
| 29.5 | **Shot Library UI:** a library page (grid, filters by scene / framing / expression / gesture), "from library" and "Add to library" in Step 5, and a coverage view ("what is missing for this storyboard") | tests green; screenshots |
| 29.6 | **Gate B-21:** the owner makes an episode and times it against generating everything | owner PASS |

## 4. Decisions needed from the owner (asked after the Gate B-20 episode)

1. How much GPU time to spend overnight on the core set (for scale: about 130 duo shots per 8 hours).
2. Which scenes first (proposed: Cafe, Classroom, Library, Park, Office, Living room, City street, Kitchen).
3. The gesture list above: add or remove.
4. Repeating a picture: acceptable across episodes if a slow zoom or a crop varies it?
