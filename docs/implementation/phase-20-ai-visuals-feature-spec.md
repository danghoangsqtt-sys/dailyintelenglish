# Phase 20 — AI Visuals feature specification (Amendment C, implementation source of truth)

- **Status:** design (Coder/PM, doc-first, 2026-10-01). Approved for implementation by
  the owner: *"thôi cứ chốt xây tính năng thật đi và hoàn thiện toàn bộ tính năng này"*
  ("let's lock it in, build the real feature and finish all of it").
- **Implementer:** an external coding agent (the owner's GPT), driven by
  `docs/operations/gpt-prompt-phase20-ai-visuals.md`.
- **Reviewer:** the Claude Code session (AR-06: the implementer never self-approves).
- **Supersedes:** the task list in `.viepilot/phases/20-ai-visuals/proposal-amendment-b-asset-library.md`
  §3.3 (20.3+). The spikes 20.2b–20.2h replaced its M1/M2 compositing design with
  **one-pass generation**.
- **Evidence:** every recipe number below was measured on the owner's RTX 3060. See:
  - reports `docs/operations/phase20-spike-character-v4.md` (r6), `-v5.md` (r7) and
    `-v6.md` (r8);
  - the reference implementations in `scripts/spike_character_v5.py` and
    `scripts/spike_character_v6.py`.

---

## 0. Owner decisions this feature must honour (2026-09-30 → 2026-10-01)

| # | Decision | Source |
|---|---|---|
| O1 | **One global character library**; the user can add characters at any time, built carefully for long-term use | Amendment B §5 |
| O2 | **Channel art style: `r3_watercolor`** only (more stable than `r3_bright`) | r8 verdict |
| O3 | **Characters and their outfits are built and locked first**, then used in scenes | r8 verdict |
| O4 | Outfits: **exactly 1 top + 1 bottom, each one solid colour, no pattern, no multi-colour**; avoid colour confusion | r7 verdict |
| O5 | **Close-up framing** preferred for single shots | r7 verdict |
| O6 | **Two-person conversation shots**: close-up, wide in a school, wide in a café | r7 verdict |
| O7 | **Hand repair** kept ("much improved, very good quality") | r7 verdict |
| O8 | **Strict pose** (ControlNet scale 1.0); characters must not look stiff; actions fit the content | 20.2b/c verdicts |
| O9 | Vietnamese-leaning characters, bright clear depiction | 20.2e verdict |
| O10 | Captions: 20.2d outline style accepted | r4/r5 verdicts |
| O11 | Everything free, legal, local; no vendor watermark; no copyright entanglement (no franchise, artist or studio names; no franchise LoRAs; invented characters only) | 20.2 Q1 |
| O12 | Candidate portraits are prettier; pose-driven shots have more natural movement. So **the picked candidate is the identity reference** and **shots are pose-driven** | r8 verdict |

## 1. Scope

**In scope:**
1. **Character Library** (global): create → candidates → pick → character sheet → lock;
   edit; delete.
2. **Scene Library** (global): built-in and user scenes, i.e. named places with a
   staging type; an optional preview image.
3. **Project visuals:**
   - map speakers to locked characters (the cast);
   - pick 1–3 scenes;
   - generate the shot set (singles + duos) with regional refine and hand repair;
   - review and regenerate single shots.
4. **In-video (Remotion / Enhanced only):**
   - full-bleed shot backgrounds per caption line, with a deterministic timeline rule;
   - the vocab-card position adapts to duo shots;
   - the speaker chips use the character face.
5. **Thumbnail:** an `ai_scene` template that uses a project shot as the base; the
   Pillow templates stay the fallback.
6. **Background job runner** for all image generation, with progress, cancel and
   restart recovery, under the Task 20.1 GPU lease.
7. Tests (no GPU needed), and an owner GPU smoke runbook for Gate B-14.

**Out of scope (later phases):**
- the ffmpeg (Standard) renderer getting AI backgrounds;
- more than 2 characters in one picture;
- animated motion beyond a subtle zoom;
- the script LLM choosing scenes or expressions per line (the timeline rule is
  deterministic for now);
- music (Phase 22, the next task).

## 2. Proven generation recipes (copy exactly; do not "improve" without a gate)

### 2.1 Models (already used by `scripts/image_worker.py`, all cached on the owner's machine)

- **SDXL base 1.0** (`stabilityai/stable-diffusion-xl-base-1.0`, fp16) and the
  `madebyollin/sdxl-vae-fp16-fix` VAE.
  - Mode `base`, **30 steps, CFG 6.0**, default Euler scheduler.
  - **Never Lightning** (20.2b owner verdict: base is prettier).
- **IP-Adapter plus-face** (`h94/IP-Adapter`, `sdxl_models/ip-adapter-plus-face_sdxl_vit-h.safetensors`,
  ViT-H encoder `models/image_encoder`).
- **ControlNet OpenPose** `xinsir/controlnet-openpose-sdxl-1.0` (Apache-2.0).
- **Licences:** SDXL / OpenRAIL++-M; IP-Adapter / Apache-2.0; the ControlNet /
  Apache-2.0.

### 2.2 Style and negatives (the channel style is fixed: O2)

```
STYLE_R3_WATERCOLOR = "hand-painted 2D anime illustration, soft watercolor background, warm natural sunlight, gentle pastel palette, cozy whimsical atmosphere, clean line art"
NEGATIVE = "3d render, photorealistic, photo, text, logo, watermark, blurry, deformed, bad anatomy, extra fingers, deformed hands, hand on face, backpack, hat, cap, jacket, coat, hoodie, scarf, pattern, stripes, plaid, print, multicolored clothes, layered clothes, crowd"
HAND_PROMPT = "detailed hand, five fingers, natural hand"
HAND_NEGATIVE = "extra fingers, missing fingers, fused fingers, deformed hands, bad anatomy, blurry"
```

- **CLIP limit (20.2f finding F3):** SDXL reads 77 tokens (75 of content) and **silently
  drops the rest**.
- The worker reports `prompt_tokens` / `prompt_truncated` per image. The engine must
  **store and surface** `prompt_truncated=true` (the asset/shot shows a warning badge).
- Prompts are built so that the maximum-length user inputs (§4.1 limits) stay ≤ 75; the
  test in §10 guards this with a conservative estimator.

### 2.3 Character prompt assembly

```
character_phrase = f"{age_phrase} {ethnicity} {gender_noun} {role}, {hair}, {eyes}, plain {top_color} {top_item}, plain {bottom_color} {bottom_item}"
gender_noun: female -> "woman", male -> "man"
age_phrase: "young" | "adult" | "middle-aged" | "senior"
duo_person = f"{gender_noun} in plain {top_color} {top_item}"   # NO hair/bottom in the duo base prompt:
#   hair comes from the IP face, the full outfit from the per-person regional refine (§2.7);
#   fewer cross-person attribute words also means less colour bleed (r8 finding).
```

**Measured worst case** (OpenAI CLIP BPE; all inputs at their §4.1 maximum, e.g.
"middle-aged Vietnamese woman English teacher, long wavy black hair, brown eyes, plain
light blue slim-fit shirt, plain navy blue slim trousers", place "a cozy Vietnamese street
cafe"):

| Template | Tokens |
|---|---|
| candidate | 70 |
| full body | 67 |
| portraits | 67–69 |
| single | **74** |
| duo_close | 72 |
| duo_wide standing | 69 |
| duo_wide seated | 72 |
| refine | 66 |
| scene preview | 39 |

**Never lengthen a template** without re-measuring.

### 2.4 Operations and their exact parameters

| Operation | Pipeline / worker lifetime | Size | Prompt (after STYLE) | IP | Other |
|---|---|---|---|---|---|
| **Candidate** portrait | `text2img`, no IP | 1024×1024 | `character_phrase, portrait, facing the viewer, arms down, plain light background` | — | 4 candidates, seeds `base_seed+0..3` |
| **Face crop** of the picked candidate | Pillow | 512×512 | — | — | crop box (0.20W, 0.02H, 0.80W, 0.62H), resize to 512² |
| **Sheet: full body** | `text2img` + IP (with encoder) | 832×1216 | `character_phrase, full body, front view, plain light background` | face crop @ **0.45** | |
| **Sheet: portraits** ×3 | same lifetime | 1024×1024 | `character_phrase, portrait, {calm friendly face \| big happy smile \| surprised face, open mouth}, plain light background` | face crop @ 0.45 | own seed each |
| **Scene preview** (optional) | `text2img`, no IP | 1344×768 | `{scene.place}, empty scene, no people` | — | |
| **Encode** shot prompts | `encode` in the IP lifetime | — | see §2.5 | single: 1 face; duo: 2 faces `ip_adapter_images` [left, right] | CFG on |
| **Shot render** | `controlnet`, `encoders=false`, IP layers only (`image_encoder_folder: null`) | 1344×768 | from embeds | 0.45; duo + `ip_adapter_masks` [left half, right half] | `controlnet_conditioning_scale` **1.0** |
| **Duo regional refine** (new, gate-validated: §2.7) | `inpaint` + IP (with encoder) | 1344×768 | `character_phrase, talking, in {scene.place}` for **one** person | that person's face crop @ 0.5 | mask: §2.7; strength 0.55 |
| **Hand repair** | same `inpaint` lifetime | crop → 768² | `HAND_PROMPT` | the person's face crop @ **0.0** (the worker requires an image while IP is loaded) | strength 0.5; §2.6 |

Each lifetime runs under its own GPU lease (`get_gpu_manager().lease(consumer, min_free_mb=8192)`).
The worker exits at the end of the lifetime, which frees all of its VRAM. This is the
proven pattern from the spikes.

### 2.5 Shot set per project scene, with prompts and pose geometry

Port these **verbatim** (they are unit-tested in the spikes):
- `person_pose`, `draw_people`, `half_masks` and the shot geometry from
  `scripts/spike_character_v6.py`;
- `hand_boxes`, `hand_mask` and `paste_hand` from `scripts/spike_character_v5.py`;
- `draw_pose_pixels`, `_UPPER_BODY` and `_KEYS` from `scripts/spike_character_v2.py`.

| Shot kind | People | Geometry (head_h / nose_y / cx) | Prompt (after STYLE) |
|---|---|---|---|
| `single` (one per cast member) | 1 | 0.30 / 0.36 / 0.32, front, `r_elbow (-1.0,1.9)`, `r_wrist (-0.6,1.35)` | `character_phrase, close-up, talking with a hand gesture, in {place}` |
| `duo_close` | 2 | 0.24 / 0.38 / 0.30 (facing right, left hand gesturing) + 0.70 (facing left) | `two {ethnicity_L} people talking face to face, {duo_person_L} on the left, {duo_person_R} on the right, close-up, in {place}` |
| `duo_wide` (`staging=standing`) | 2 | 0.13 / 0.30 / 0.33 + 0.67, standing legs | `… on the right, standing in {place}` |
| `duo_wide` (`staging=seated`) | 2 | 0.15 / 0.32 / 0.33 + 0.67, arms on the table | `… on the right, sitting at a table in {place}` |

- **Duo order:** the left person = the cast member at the lower `speaker_index` among the
  two used.
- **IP:** face[0] = left and mask[0] = left half; face[1] = right and mask[1] = right
  half.
- **Seeds:** stored per shot; "regenerate" uses a new seed.

### 2.6 Hand repair (r7/r8 proven)

For every person in the shot, and every `hand_boxes(points, size, head_h)` box (in-frame
wrists only):
1. crop the box;
2. resize it to 768²;
3. build the mask with `hand_mask(768, center×scale, radius×scale)`;
4. inpaint at strength 0.5;
5. `paste_hand` it back through the feathered disc.

Keep both `raw.png` and `final.png`.

### 2.7 Duo regional refine (NEW — fixes r8 colour/gender bleed; validated at Gate B-14)

For each of the two people, after the raw duo render, **before** hand repair:
1. Build the mask: the person's silhouette (port `silhouette_mask` from
   `scripts/spike_character_v2.py`, with `head_h` as a parameter), **intersected with
   that person's half**, then dilated and feathered (the same blur as the silhouette).
2. Inpaint the current image with that person's **single** prompt and face only
   (strength 0.55, CFG 6, 30 steps).
3. Composite back through the mask (`keep_scene_outside_mask` semantics: pixels outside
   the mask are unchanged).

Behind the setting `DIE_VISUALS_DUO_REFINE` (default **true**). If Gate B-14 shows harm,
the PM flips the default; the code stays.

## 3. Architecture

```
app/services/visuals/
  __init__.py
  recipes.py        # STYLE/NEGATIVE/HAND constants, prompt builders, token estimator (pure)
  geometry.py       # ported pose/mask/hand helpers (pure, Pillow/numpy)
  engine.py         # ImageEngine protocol + WorkerImageEngine (subprocess to scripts/image_worker.py) + FakeImageEngine
  jobs.py           # image_jobs persistence (create/claim/progress/cancel/recover) 
  runner.py         # ImageJobRunner: asyncio loop, one job at a time, dispatch by kind
  library_service.py# characters, character_assets, scenes (CRUD + lock rules + file layout)
  project_visuals_service.py # cast, project scenes, shots, timeline assignment
  pipelines.py      # job handlers: candidates, sheet, scene_preview, project_shots, shot_regenerate
app/api/visuals.py  # all /api/visuals/* and /api/projects/{id}/visuals/* routes
app/models/visuals.py
app/db/migrations/008_ai_visuals.sql
frontend/pages/characters.html + frontend/static/js/characters.js   # library UI
frontend/static/js/step5_video.js + frontend/pages/step5_video.html   # "Characters & scenes" section
frontend/static/js/step6_thumbnail.js (+html)                        # ai_scene option
video-renderer/src/visuals.ts (+ visuals.test.ts), Episode.tsx, types.ts
app/services/video_renderer_remotion.py, app/services/thumbnail_service.py (extended)
```

- **Engine selection:** setting `DIE_IMAGE_ENGINE` = `worker` (default) | `fake`.
  - `fake` writes deterministic solid-colour PNGs of the requested sizes and returns the
    same response shape as the worker, including `prompt_tokens`.
  - **All automated tests use `fake`.**
- **WorkerImageEngine** reuses the subprocess protocol of
  `scripts/spike_images.py::_WorkerClient`:
  - the `venv-image` Python;
  - line-delimited JSON;
  - a handshake;
  - stderr to a log file under `DATA_DIR/visuals/logs/`.
  - It exposes `session(pipeline, encoders, ip: "none"|"with_encoder"|"layers_only")`
    as an async context manager: lease → spawn → load → `load_ip_adapter` → yield →
    close.
  - Blocking subprocess I/O runs in `asyncio.to_thread`.
- **Kill switch:** `DIE_AI_VISUALS_ENABLED` (default true).
  - When false, or when the `venv-image` Python is missing, generation endpoints return
    409 with a clear message.
  - Every existing flow (templates, ffmpeg, Remotion without visuals) is unchanged.
- **Health:** `GET /api/visuals/health` returns:
  - `{enabled, engine, venv_image_present, queue: {pending, running}}`.
- **Data layout** (all under `settings.DATA_DIR`):
  - `library/characters/<character_id>/{candidates,sheet}/…png`, `face.png`;
  - `library/scenes/<scene_id>/preview.png`;
  - `visuals/<project_id>/shots/<shot_id>/{pose,raw,final}.png`;
  - `visuals/logs/`.
  - Add `"visuals"` to `project_service._PROJECT_ARTIFACT_CATEGORIES`, so project
    deletion removes its shots.

## 4. Data model — `app/db/migrations/008_ai_visuals.sql` (additive only)

```sql
CREATE TABLE IF NOT EXISTS characters (
  id TEXT PRIMARY KEY, name TEXT NOT NULL,
  gender TEXT NOT NULL,              -- female|male
  age_group TEXT NOT NULL,           -- young|adult|middle-aged|senior
  ethnicity TEXT NOT NULL DEFAULT 'Vietnamese',
  role TEXT NOT NULL,                -- e.g. "university student", "English teacher"
  hair TEXT NOT NULL, eyes TEXT NOT NULL, extra TEXT NOT NULL DEFAULT '',
  top_color TEXT NOT NULL, top_item TEXT NOT NULL,
  bottom_color TEXT NOT NULL, bottom_item TEXT NOT NULL,
  style_id TEXT NOT NULL DEFAULT 'r3_watercolor',
  status TEXT NOT NULL,              -- draft|candidates|sheet|locked
  base_seed INTEGER NOT NULL,
  reference_asset_id TEXT,           -- the picked candidate
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS character_assets (
  id TEXT PRIMARY KEY, character_id TEXT NOT NULL,
  kind TEXT NOT NULL,                -- candidate|face|full_body|portrait_calm|portrait_smile|portrait_surprised
  path TEXT NOT NULL, seed INTEGER, prompt_tokens INTEGER, prompt_truncated INTEGER NOT NULL DEFAULT 0,
  approved INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
  FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS scenes (
  id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE,
  place TEXT NOT NULL,               -- prompt phrase, e.g. "a cozy Vietnamese street cafe"
  staging TEXT NOT NULL,             -- standing|seated (duo_wide geometry)
  is_builtin INTEGER NOT NULL DEFAULT 0, preview_path TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS project_cast (
  project_id TEXT NOT NULL, speaker_index INTEGER NOT NULL, character_id TEXT NOT NULL,
  PRIMARY KEY (project_id, speaker_index),
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS project_scenes (
  project_id TEXT NOT NULL, position INTEGER NOT NULL, scene_id TEXT NOT NULL,
  PRIMARY KEY (project_id, position),
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (scene_id) REFERENCES scenes(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS project_shots (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, scene_id TEXT NOT NULL,
  kind TEXT NOT NULL,                -- single|duo_close|duo_wide
  speaker_indexes TEXT NOT NULL,     -- JSON array, e.g. [0] or [0,1]
  seed INTEGER NOT NULL, raw_path TEXT, final_path TEXT,
  prompt_tokens INTEGER, prompt_truncated INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL,              -- pending|complete|error
  error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS image_jobs (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,                -- character_candidates|character_sheet|scene_preview|project_shots|shot_regenerate
  target_id TEXT NOT NULL,           -- character_id | scene_id | project_id | shot_id
  status TEXT NOT NULL,              -- pending|running|complete|error|cancelled
  stage TEXT NOT NULL DEFAULT '', progress INTEGER NOT NULL DEFAULT 0,
  payload_json TEXT NOT NULL DEFAULT '{}', result_json TEXT, error TEXT,
  cancel_requested INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_image_jobs_status ON image_jobs(status, created_at);
```

**Why `project_cast` is keyed by `speaker_index` and not `speakers.id`:**
`project_service._replace_speakers` deletes and re-inserts speaker rows on every speaker
update, so a `speakers.id` foreign key would be silently lost.

**Built-in scenes** are seeded idempotently on startup (`INSERT OR IGNORE` by name):

| name | place | staging |
|---|---|---|
| Classroom | a sunny classroom with a whiteboard | standing |
| Cafe | a cozy Vietnamese street cafe | seated |
| Library | a bright university library | standing |
| Kitchen | a bright home kitchen | standing |
| Park | a green city park | standing |
| Office | a modern bright office | seated |

### 4.1 Validation limits (keep prompts ≤ 75 CLIP tokens: §2.3 measured table)

- Limits are **word counts** (whitespace-separated), plus a 40-character cap per field:
  - `role` ≤ 2 words;
  - `hair` ≤ 4 words;
  - `eyes` ≤ 2 words;
  - `ethnicity` = 1 word (default "Vietnamese");
  - scene `place` ≤ 5 words.
- Letters, spaces and hyphens only; no commas (they would split the phrase).
- `name` ≤ 40 characters; it never enters a prompt.
- The column `extra` exists for a later phase. **The API rejects a non-empty `extra`
  in this phase** (422), because any extra words break the budget.
- **Colours** (solid only):
  - white, black, navy blue, light blue, red, yellow, green, beige, grey, pink, brown,
    orange.
- **Tops:** t-shirt, shirt, slim-fit shirt, sweater, blouse, polo shirt.
- **Bottoms:** jeans, trousers, slim trousers, skirt, shorts.
- **Rule:** `top_color != bottom_color` (422 otherwise).
- In a project cast, two characters sharing a `top_color` is **allowed but returns a
  warning** (bleed risk, O4).

## 5. Lifecycles and rules

### 5.1 Character

1. **create** → `draft`.
2. **generate candidates** → job → `candidates` (4 `candidate` assets).
3. **pick candidate** (`reference_asset_id`):
   - creates the `face` asset (face crop);
   - a new pick resets the sheet.
4. **generate sheet** → job → `sheet` (4 assets).
5. **approve** each sheet asset; regenerate any single sheet asset (a job with
   `payload {kind}`).
6. **lock**:
   - requires a reference and all 4 sheet assets approved;
   - **while locked, the appearance and outfit fields are read-only**;
   - **unlock** → `sheet` is allowed only if no project cast uses the character, else
     409.
7. **delete**: 409 if used in any project cast, unless `?force=true`, which removes the
   cast rows.

### 5.2 Project visuals

1. **set cast:** `[{speaker_index, character_id}]`. Only `locked` characters; the
   speaker index must exist.
2. **set scenes:** an ordered list of 1–3 scene ids.
3. **generate shots** (job `project_shots`):
   - deletes the previous shots, then for each project scene generates:
     - one `single` per cast member;
     - plus, if ≥ 2 cast members: `duo_close` + `duo_wide` for the first two by
       `speaker_index`.
   - **Order of worker lifetimes:**
     1. **L1** `text2img` + IP, with the encoder: encode all prompts.
     2. **L2** `controlnet` with IP layers: render all raws.
     3. **L3** `inpaint` + IP with the encoder: refine the duos, then repair the hands
        of all shots.
   - Progress and stage are updated per image; cancellation is checked between images.
4. **regenerate one shot** (job `shot_regenerate`): the same 3 lifetimes for that shot
   only, with a new seed.

### 5.3 Jobs

- One job runs at a time; FIFO.
- **Duplicate guard:** a second active job of the same `kind`+`target_id` returns the
  existing job.
- **On startup:** `running` → `error` ("interrupted by app restart"); `pending` stays
  queued.
- **Cancel:** sets `cancel_requested`. The runner stops at the next image boundary and
  marks the job `cancelled`, keeping the completed files.
- **A `GpuUnavailableError` from the lease** marks the job `error` with the lease
  reason. No silent CPU fallback: the worker refuses CPU unless `--allow-cpu`, which the
  app never passes.

## 6. API (`app/api/visuals.py`; every response uses `ok()`; errors use the existing exceptions)

```
GET    /api/visuals/health
GET    /api/visuals/options                      -> {colors, tops, bottoms, age_groups, genders, style_id}
GET    /api/visuals/characters                   -> list (with reference/face/sheet URLs, status)
POST   /api/visuals/characters                   -> create (draft)
GET    /api/visuals/characters/{id}
PATCH  /api/visuals/characters/{id}              -> edit fields (409 if locked)
DELETE /api/visuals/characters/{id}[?force=true]
POST   /api/visuals/characters/{id}/candidates   -> job
PUT    /api/visuals/characters/{id}/reference    {asset_id}
POST   /api/visuals/characters/{id}/sheet        [{kind}] -> job (all 4, or one kind)
PUT    /api/visuals/characters/{id}/assets/{asset_id}/approve   {approved: bool}
POST   /api/visuals/characters/{id}/lock | /unlock
GET    /api/visuals/assets/{asset_id}/content    -> image/png (path validated under DATA_DIR/library)
GET    /api/visuals/scenes | POST | PATCH /{id} | DELETE /{id} (built-ins: no delete, 409)
POST   /api/visuals/scenes/{id}/preview          -> job
GET    /api/visuals/scenes/{id}/preview          -> image/png
GET    /api/visuals/jobs/{job_id} | POST /api/visuals/jobs/{job_id}/cancel
GET    /api/projects/{project_id}/visuals        -> {cast, scenes, shots, warnings, active_job}
PUT    /api/projects/{project_id}/visuals/cast   [{speaker_index, character_id}]
PUT    /api/projects/{project_id}/visuals/scenes [scene_id,...]
POST   /api/projects/{project_id}/visuals/shots  -> job
POST   /api/projects/{project_id}/visuals/shots/{shot_id}/regenerate -> job
GET    /api/projects/{project_id}/visuals/shots/{shot_id}/content?variant=final|raw -> image/png
```

## 7. UI

### 7.1 New page `/characters` ("Character Library", English UI per D19.7n1-b)

- Linked from the dashboard header, next to ⚙️, and from Step 5.
- **Characters tab:** cards (face, name, status badge) and a "New character" button.
- **Editor:** a form with the §4.1 fields; colours and items are `<select>` elements.
  Then a 4-step strip:
  1. **Candidates:** a "Generate 4" button, then a 2×2 grid; click to pick.
  2. **Sheet:** full body + 3 expressions, each with ✓ Approve / ↻ Regenerate.
  3. **Lock:** the button is enabled only when all are approved.
  4. **Locked:** a read-only summary and an "Unlock" button.
- Job progress uses the existing `GenerationStatus` component, polling
  `/api/visuals/jobs/{id}`.
- A `prompt_truncated` asset shows a "⚠ description too long" badge.
- **Scenes tab:** a list (built-ins badged), create/edit (name, place, staging) and an
  optional "Preview" (job).
- When `health.enabled` is false or `venv_image_present` is false: every generate
  button is disabled, with a tooltip explaining why. Browsing still works.

### 7.2 Step 5: a "Characters & scenes" section (above the renderer chips)

- For each speaker, a `<select>` of locked characters (plus "— none —"), with the
  character's face.
- A multi-select of up to 3 scenes, in order.
- Cast warnings (shared top colour).
- **"Generate shots":** a job with progress, then a grid of shots grouped by scene. Each
  shot has a raw/final toggle and ↻ Regenerate.
- The section notes: "Shots appear in Enhanced (Remotion) renders."

### 7.3 Step 6

- When the project has ≥ 1 complete shot, the template picker shows an extra **"AI
  scene"** template.
- The existing generate flow renders it through `thumbnail_service` (§9).

## 8. Remotion integration (Enhanced renderer only)

- **Props (`types.ts`, optional with a default so old props still render):**
  - `visuals: { shots: Record<string,{url:string, kind:'single'|'duo_close'|'duo_wide'}>, lineShots: (string|null)[] }`;
  - the default is `{shots:{}, lineShots:[]}`.
  - `video_renderer_remotion._build_input_props` fills it when the project has complete
    shots:
    - it copies each `final.png` to `video-renderer/public/remotion-render/visuals/<project_id>/<shot_id>.png`
      (the same convention as the audio and avatars);
    - it computes `lineShots` with `assign_line_shots()`.
- **`assign_line_shots(lines, chapters, scenes, shots)`** is pure Python and
  unit-tested, so it is deterministic:
  - chapter `c` uses scene `scenes[c % len(scenes)]`;
  - **the first line of each chapter** → that scene's `duo_wide`;
  - every 4th line in a chapter (index % 4 == 3) → `duo_close`;
  - every other line → the line speaker's `single` in that scene;
  - **fallbacks**, in order: `single` → `duo_close` → `duo_wide` → any complete shot of
    the scene → `null` (the midnight background).
- **`Episode.tsx` (`AudioWindowContent`):**
  - draws the active line's shot as a full-bleed `<Img>` behind every overlay;
  - a 10-frame crossfade when the shot changes;
  - a subtle 1.00→1.04 scale over the line duration ("not stiff", O8);
  - midnight when `null`.
  - The intro and outro stay unchanged.
- **Vocab card position (`visuals.ts`, a pure function, vitest):**
  - `top-right` (as today) for `single`/`null`;
  - `top-center` for `duo_close`/`duo_wide`, which avoids covering the right-hand
    person's head (20.2h finding).
- **Speaker chips:** if a speaker has no uploaded avatar but has a cast character, use
  the character's `face.png` as `avatarUrl`.
- **Captions:** unchanged (20.2d `outline` default).
- The ffmpeg path is unchanged.

## 9. Thumbnail integration

- A new pseudo-template `ai_scene` is listed by `GET /api/thumbnails/templates?project_id=`
  only when the project has a complete shot.
- **Base image:** the first complete `duo_close`, else a `single`, else any shot,
  ImageOps-fitted:
  - **16:9:** centre;
  - **9:16:** a crop window centred on `cx`, the left person or the single subject.
- **Text:** the same suggestion/palette flow, over a left-side dark gradient scrim (0 →
  70% opacity).
- **Headline:** white with a 3 px black stroke.
- Failure or no shot → the existing templates (invariant 47).

## 10. Tests (all with `DIE_IMAGE_ENGINE=fake`; no GPU)

- **Migration:**
  - 008 applies on a fresh DB and on a DB at 007;
  - re-running `init_db` is a no-op;
  - the built-in scenes are seeded once.
- **`recipes.py`:**
  - prompt builders produce the §2 strings exactly;
  - **every template, with all inputs at their §4.1 maximum (the §2.3 worst-case
    example), stays ≤ 75** under the estimator
    `len(re.findall(r"[A-Za-z]+|\d+|[^\sA-Za-z\d]", s))`.
    - For this vocabulary the estimator equals the real CLIP count (measured: 39–74 on
      every template).
    - Rare words can split into more real tokens, so the worker's `prompt_truncated`
      stays the ground truth and is surfaced (§2.2).
- **`geometry.py`:** the r6–r8 unit checks:
  - head below the chip row;
  - duo halves;
  - far ear hidden;
  - hand crops in-frame and past the wrist;
  - `paste_hand` changes only the discs;
  - the refine mask lies inside the person's half.
- **Jobs:**
  - FIFO;
  - the duplicate guard;
  - cancel at an image boundary;
  - restart recovery;
  - `GpuUnavailableError` → `error`.
- **API:**
  - the full character lifecycle (create → candidates → pick → sheet → approve → lock
    → 409 on edit → unlock rules → delete rules);
  - scenes CRUD, with built-in protection;
  - cast validation (unlocked → 422; bad speaker index → 422; shared top colour →
    warning);
  - **the cast survives a speaker update** (`_replace_speakers`);
  - shots generation produces the right set for 1 and 2 cast members and for 1–3
    scenes;
  - regenerate;
  - content endpoints refuse path traversal;
  - the kill switch → 409.
- **Remotion:**
  - `_build_input_props` includes visuals, with files copied;
  - `assign_line_shots` covers the rule and every fallback;
  - vitest for the `visuals` default, the vocab position and the background selection.
- **Thumbnail:** `ai_scene` appears only with shots, renders 16:9 + 9:16, and falls back
  when the shot is missing.
- **Playwright:**
  - the library page: create, generate, pick, approve, lock, read-only after lock, and
    the disabled state when health is off;
  - the Step 5 section: cast/scene selection, generate, the grid, regenerate;
  - Step 6: "AI scene" appears.
- **The full suite must stay green** (current baseline: all tests pass on the owner's
  machine; in the cloud, the 3 known environment-only failures are documented in
  `.viepilot/phases/20-ai-visuals/tasks/task-20.2d.md`).

## 11. Task breakdown (implement in this order; one commit series per task)

| Task | Content | Done when |
|---|---|---|
| **20.3** | Foundation: migration 008 + built-in seed, `visuals/recipes.py` + `geometry.py` (ported, tested), `engine.py` (worker + fake), `jobs.py` + `runner.py` (started in `lifespan`), settings `DIE_AI_VISUALS_ENABLED` / `DIE_IMAGE_ENGINE` / `DIE_VISUALS_DUO_REFINE`, `/api/visuals/health` | the §10 migration / recipes / geometry / jobs tests are green |
| **20.4** | The library backend: characters + assets + scenes, services, API, the candidates / sheet / scene-preview pipelines | the §10 API lifecycle tests are green |
| **20.5** | The library UI `/characters` + the dashboard link + `api.js` methods | the Playwright library tests are green |
| **20.6** | Project visuals: cast, scenes, the shots pipeline (L1/L2/L3 incl. duo refine + hand repair), regenerate, project deletion cleanup, the Step 5 section | the §10 shots / cast tests + Step 5 Playwright are green |
| **20.7** | Remotion visuals (props, copy, `assign_line_shots`, Episode background, vocab position, chip avatar) + the thumbnail `ai_scene` + Step 6 | the vitest + Remotion props + thumbnail tests are green; `tsc` clean |
| **20.8** | `scripts/smoke_ai_visuals.py` (a real-engine end-to-end on a temp `DIE_DATA_DIR`: 2 characters → sheets → lock → a project with 2 speakers → 2 scenes → shots → one Remotion still per shot kind), `docs/operations/owner-runbook-gate-b14.md`, CHANGELOG, PHASE-STATE rows | the docs are written and the smoke script passes `--fake` in CI-style runs |

**Gate B-14** (owner, real GPU, after 20.8) checks:
- the duo refine (on vs off);
- the shot quality across 3 real episodes;
- the render time per project.

## 12. Non-negotiable rules for the implementer

1. **Never** put a studio, franchise, artist or real-person name in any prompt, default,
   test fixture or UI hint. Characters are invented (O11).
2. **Never** change the §2 numbers or prompt wording without a PM decision. If something
   seems wrong, write it in the handover; do not "fix" it.
3. **Additive only:** no change to the existing table shapes; existing endpoints keep
   their contracts. The ffmpeg path and the template thumbnails behave byte-identically
   when no visuals exist.
4. **No new Python dependency in the main `venv`** (Pillow and numpy are already there).
   No new npm dependency.
5. All GPU work goes through `get_gpu_manager().lease(...)` and the worker subprocess.
   The app process never imports torch or diffusers.
6. Blocking I/O and subprocess calls run in `asyncio.to_thread`; no blocking on the
   event loop.
7. Paths served by content endpoints are validated to resolve under their own `DATA_DIR`
   sub-tree.
8. Follow the existing code style: ruff, `ok()` envelopes, `AppError` subclasses,
   `read_transaction` / `write_transaction`, and the vanilla JS + `Api` client pattern.
