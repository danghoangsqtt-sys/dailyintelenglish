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

## 2b. Owner feedback on the Gate B-20 episode (2026-10-07), added to this phase

1. **Cuts are too ghosty.** The shot-to-shot dissolve is 10 frames (0.33 s), 18 for inserts, and the dialogue changes
   speaker line by line, so two faces overlap on screen. Fix: near-hard cuts (4 frames, 9 for inserts).
2. **The two people talk but both look at the camera.** Unnatural. Cause (measured): the face reference given to the
   refine is a frontal face, which pulls every head to the camera although the skeleton turns the heads. Plan: use the
   character sheet's **three-quarter view** (mirrored for the left person) as the face reference of a duo, add gaze words
   ("looking at the man on the left"), and for a **single** shot of a speaker turn the head toward the off-screen partner.
   Gaze toward the partner becomes a **tag** of every library shot and a check in the owner's review.
3. **Illustration shots should be able to show a character.** An insert today is "no characters" (a person in it is a
   stranger). New: an insert may name a speaker, and is drawn as that character doing the action (checking a phone,
   eating oatmeal, stretching) with the face reference, no scene plate needed.
4. **Fix the errors discussed so far:** the outfit swap (Minh in white), the false alarms and the weak checks. A library
   shot is **reviewed once by the owner** (approve or reject in a grid); only approved shots are ever reused, so a wrong
   outfit or a stare at the camera cannot reach an episode.

## 3. Tasks

| Task | What | Accept when |
|---|---|---|
| 29.0 | **Cleaner cuts:** near-hard cuts between shots (4 frames, 9 for inserts) | done: vitest green, real render checked |
| 29.1 | **Gaze toward the other person (spike, then the fix):** a turned face reference, gaze words, a setting to compare them on the real job | the owner sees A / B / C sheets; the winner is the default |
| 29.2 | **Inserts with a character:** an insert may name a speaker and is drawn as that character doing the action | a real insert shows the right person |
| 29.3 | **Library vocabulary spike (GPU):** expression and mouth variants by face repaint, gesture pose maps, camera angles; seconds and pictures | the owner approves the vocabulary and the size of the core set |
| 29.4 | **Data model and service:** `shot_library` table (migration) with a review state (pending / approved / rejected), files under `data/library/shots/`, add / list / filter / delete / mark stale; API | tests green |
| 29.5 | **Matcher and the library-first job:** the project shot job resolves each shot spec against the **approved** library shots, copies a match (no GPU) and generates only the rest; the project shot records `source` | a fake-engine test generates only the missing shots; a real run on the Demo Episode |
| 29.6 | **Batch generator:** a resumable job that renders the core set overnight from a plan file, with the shot checks (colours, faces, gaze) and a coverage report | the core set is generated and looked at by sheets |
| 29.7 | **Shot Library UI:** a library page (grid, filters, approve / reject), "from library" and "Add to library" in Step 5, a coverage view ("what is missing for this storyboard") | tests green; screenshots |
| 29.8 | **Gate B-21:** the owner makes an episode and times it against generating everything | owner PASS |

## 4. Decisions needed from the owner (asked after the Gate B-20 episode)

1. How much GPU time to spend overnight on the core set (for scale: about 130 duo shots per 8 hours).
2. Which scenes first (proposed: Cafe, Classroom, Library, Park, Office, Living room, City street, Kitchen).
3. The gesture list above: add or remove.
4. Repeating a picture: acceptable across episodes if a slow zoom or a crop varies it?
