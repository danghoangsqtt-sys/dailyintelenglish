# Phase 94 — The new studio look: the seven steps and Lina (2026-11-04, planned)

Follows [Phase 93](../93-studio-ui-frame/PLAN.md) (tokens, rail, main areas). Approved look:
`.viepilot/ui-direction/session-2026-11-03-alt/e/step-1.html` … `step-7.html`; Lina as the mascot (owner 2026-11-03:
"Lấy luôn nhân vật Lina được không? cử động linh hoạt giữa chính diện và góc nghiêng", then "Mascot nên là ai? → Lina").

## Today

- Steps 1–7 are separate pages with `step_nav.js` (a row of 7 links) and their own layouts; Step 5 holds the Phase 90/91
  beat editor ("Sửa trên video"), Step 2 the line panel.
- Lina has two talking-sprite sets in the library (front, three-quarter), same outfit; no assistant exists in the app.

## Decisions (defaults; the owner may change them)

- **D143 — one frame for every step:** the video's title, CEFR level and "Đã lưu" on top; the 7 steps grouped in three
  stages (Nội dung 1–3, Sản xuất 4–5, Đăng 6–7) as one bar; a sticky Back / Next bar at the bottom. Each step keeps its
  IDs, scripts and behaviour; only its layout and look change (main column + helper column, as drawn).
- **D144 — Lina is the assistant character:** a setting "Trợ lý" chooses any library character with talking sprites
  (default Lina). On Home she is the band (wave on open, then calm with blinks; breathing); on working pages she is a
  one-line note with her face inside the content, never floating over it. Mouth moves only while a line is being read.
- **D145 — her lines come from the app's state**, not chatter: what waits for review, what changed (e.g. a line the AI
  fixed), the next step, an empty day in the week, an error. At most one line per page; no idle remarks.
- **D146 — reading aloud is off by default** (a speaker button reads the line with the app's own VieNeu voice); her half-body
  frames are cut on the server from the character's sprites (the prototype's `build_lina.py` method) and cached.

## Tasks

1. **94.1 Step frame** — `step_nav.js` → the stage bar and the sticky Back / Next bar (D143); the title strip reads the
   project; every step page uses it.
2. **94.2 Steps 1–4** — Step 1 (chosen template, topic, explanation style, CEFR, audience, length, extras, folder; helper:
   example clip and what Lina will do), Step 2 (script by scenes, outline with times, the selected line's editor, the
   review result), Step 3 (cards table with "Hiện ở", preview), Step 4 (voices per speaker, lines with waveforms and
   "changed, not read yet", whole-episode voice, music).
3. **94.3 Steps 5–7** — Step 5 (the beat editor in the E frame: beats, phone preview, properties, timeline of cards /
   voice / music; "Nhân vật và cảnh" and "Short và TikTok" as its other modes), Step 6 (three options, edit panel),
   Step 7 (three titles, description, tags, pinned comment, playlist, publish mode and slot, SEO ring and checks, what
   viewers will see).
4. **94.4 Lina service** — `GET /api/assistant/frames/{character}` (half-body crops from the sprite sets, cached),
   `GET /api/assistant/line?page=…&project=…` (D145 rules over existing state), the "Trợ lý" setting; front-end
   `assistant.js` (band and note, blink / wave / mouth while reading, reduced motion).
5. **94.5 Verify** — browser tests for every step (frame, IDs, flows still work: beat edit + render, voice remake, publish
   package), phone and dark checks, the assistant line rules (unit tests), full pytest, design self-audit ≥ 90, the
   owner's look.

Task cards are written when the phase starts.
