# Phase 86 summary — VOX videos on the viral explainer formula

Done 2026-10-29 on `owner-runs/20261001-r9` (not pushed).

## What changed

- **Script** (86.1): a VOX script opens cold on an English example and one question (no greeting), promises what the
  viewer will understand, gives evidence blocks that say an English example before explaining it, comes back to the
  opening example with the answer, adds a tip and ends on one follow line. The editor keeps the cold open.
- **Plan** (86.2): evidence first (highlighted quotes), a visual every ~5-8 s (segments over 24 words are split into a
  quote), text cards that carry an example, the recap as the last segment.
- **Pictures** (86.3): Qwen draws VOX slots as paper cut-out collages of objects (no faces, no text).
- **Cold open and motion** (86.4): no intro slide or greeting for VOX (the branded ending stays); collage pictures jitter
  in 12 fps steps.

## Fixed on the way (real and sandbox runs)

1. Long VOX scripts came back 30 % short → the outline names every example (5 for 3 minutes) and the section writes
   one ~70-word block per example; VOX scripts are judged at ±20 % (`fb53399`).
2. Split into sections, the formula restarted (two cold opens, a follow line mid-script) → a VOX script is one
   section; a follow line or a second promise before the end fails the script check (`fb53399`).
3. The plan still ended on a "Thanks for watching / Subscribe" card → the follow-line segment joins the recap; a
   thanks card on the last segment becomes a quote of the narrator's last point (`fb53399`, `4f488d5`).
4. A broken JSON answer from the fact check stopped a video → asked once more (`4f488d5`).
5. A re-proposal of a split plan failed on its segment IDs → a plan nobody edited is replaced freely (`4f488d5`).
6. "grammar has 3 point(s), need 1-2" stopped a video → extra items are trimmed (`d4ba5bc`).
7. Gemini was briefly unavailable (ProviderUnavailableError) during the session; the retries covered it.

## Real checks (installed app, `D:\Videos\Kiểm tra VOX 2026-10-28`)

- VOX why v2: cold open "Knight. Why do we write a K that nobody says?", 20 segments (13 evidence quotes, 3 drawn
  pictures, a timeline), recap quote, stamped Subscribe, branded ending; 144.6 s at 1920x1080. No intro slide.
- VOX how v2: cold open "Sofa…", 24 segments (16 quotes, a map); its plan was made before fix 3, so it ends on the old
  card.
- VOX list v3: cold open "Awful…", 24 segments, ends on a recap card.
- VOX Short v2: cold open "OK. Why…", 8 segments (5 quotes, a map), ends on a recap quote.
- Full pytest 2254 passed. Package `dist/2.0-phase86d-20261029` (ZIP 138754776 bytes, SHA256 `3babd4267c25f7e3bf88b60c141a91d09a1fce666ffb57b9d629f10f672deb43`).
