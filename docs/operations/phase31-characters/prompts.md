# Alex and Lina: the owner's identity prompts and how the app uses them (2026-10-07)

The owner wrote long identity prompts for the pictures made outside the app (RealVisXL or another tool). The app can use only a short
part of them: the SDXL text encoders read the **first 77 tokens** of a prompt and ignore the rest, and the app also spends tokens on the
style, the scene, the action and the mood. So the app keeps the words that change the picture most, and leaves the face to the
IP-Adapter, which copies each person's face reference (`face.png`, and `face_turned.png` for the gaze).

## What the app sends for each character

| | Lina | Alex |
|---|---|---|
| Who | young Russian woman | young Russian man |
| Hair (`hair`) | long chocolate brown hair | short swept-back brown hair |
| Detail (`extra`, at most 6 words) | fair porcelain skin, curtain bangs | caramel blond highlights, clean-shaven |
| Eyes | brown eyes | brown eyes |
| Outfit | plain white mini dress, fitted corset bodice, thin straps | plain navy blue suit jacket and suit trousers, white shirt, black bow tie |
| Added to the negative prompt | short hair (single pictures only) and blazer | beard, and nothing against a jacket or a shirt |

What is **not** in the app prompts (it does not fit, or the face reference already carries it): skin pores, eye and nose shapes, lips,
eyebrows, the camera and lighting words (the app has its own editorial style line and the scene sets the light).

## The owner's prompts (kept for the pictures made outside)

The full text of the woman's identity prompt and negative, the man's identity prompt and negative, the "same woman / same man" lock
lines and the two-people template were pasted in the chat of 2026-10-07 and are the owner's working material for the external tool.
Advice that applies there:

- Keep the lock line at the start of every prompt: `same woman, same face, same facial structure, same eyes, same nose, same lips,
  same hairstyle, same body proportions, same outfit` (and the man's equivalent).
- In a two-people picture describe the woman and the man in separate blocks and say "clearly different male and female faces".
- Faces stay stable over many pictures only with a face reference (IP-Adapter FaceID, InstantID or PuLID): separate references for the
  woman and the man, never one shared picture.

## Settings the owner suggested for RealVisXL, against what the app does

| Owner's suggestion | The app |
|---|---|
| RealVisXL | RealVisXL V5.0 (fp16, fp16-fix VAE) |
| Sampler DPM++ 2M Karras | Euler ancestral (`IMAGE_SCHEDULER`); can be compared in a spike |
| Steps 28 to 35, CFG 4.5 to 6 | 30 to 35 steps, CFG 6 to 6.5 |
| Landscape 1344 x 768, portrait 832 x 1216 | 1344 x 768 shots, 832 x 1216 full-body sheets |
| Hires fix 1.5x to 2x, denoise 0.25 to 0.35 | not used (the 12 GB card; a duo is refined person by person instead) |
| IP-Adapter FaceID / InstantID / PuLID, one reference per person | IP-Adapter plus-face, one face reference per person with its own mask |
