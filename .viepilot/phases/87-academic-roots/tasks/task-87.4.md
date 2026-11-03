# Task 87.4 — Line-art pictures

See [PLAN.md](../PLAN.md) (Q5 default: line icons + Qwen line art).

## Design (written before code)

- The word family gives each word (and the quiz) a `picture` (an object scene in English) and `icons` (one or two
  names from a fixed list of bundled MIT line icons, Tabler Icons). Unknown icon names are dropped.
- **Qwen line art** (`recipes.qwen_lineart_prompt`): single-weight dark-brown ink line drawing, flat, cream paper, one
  green accent, no faces, no text. Drawn when the video is made (`backend/media/roots_pictures.py`, called from the
  roots props build): one picture per word, cached in `DATA_DIR/visuals/{project}/roots/{word}.png` and reused, kept in
  the Activity Library as an approved generic picture tagged `lineart`. Without Qwen the video is still made.
- **Icons** (`renderer/src/lineartIcons.ts`, generated from Tabler Icons 3.x, MIT, licence kept next to it): the
  renderer draws a word's icons stroke by stroke (`pathLength = 1`, dash offset) when the word has no Qwen picture.
- Line icons are a fallback and a quick look; Qwen pictures are what the owner sees in a normal run.

## Paths

`backend/content/word_family.py` (icons + prompt), `backend/ai/image/recipes.py`, `backend/media/roots_pictures.py`
(new), `backend/media/video_renderer_remotion.py`, `renderer/src/lineartIcons.ts` (new, generated),
`renderer/LICENSE-tabler-icons.txt`, `scripts/build_lineart_icons.py` (new), tests.

## Result (2026-11-03)

The Activity Library only keeps 16:9 cutaways, so pictures are drawn at 1344x768 (Qwen's usual size). Tabler v3.24.0
has no `megaphone`, `bridge` or `handshake`: 145 icons kept. Tests: fake engine draws once, two library copies,
cached on the next render, no pictures (and no failure) without the image model.
