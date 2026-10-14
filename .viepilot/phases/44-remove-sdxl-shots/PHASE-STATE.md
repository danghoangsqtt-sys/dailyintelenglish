# PHASE-STATE — Phase 44: remove RealVisXL/SDXL, the two-person shots and the "with characters" video (D123)

- **Status:** planned 2026-10-14 (owner answers in chat); 44.1 done (tool ready; `--apply` runs right before migration 026), 44.2 in progress.
- **Why (owner, 2026-10-14):** Step 5 still offered "Generate shots" (single / duo close / duo wide pictures of the
  cast drawn by RealVisXL), whose faces never match the real characters. The owner had asked to drop RealVisXL:
  illustrations in a conversation come from the **generic Activity Library or the local AI (Qwen)** and show **no
  speaking character** -- the action, hand gestures and activities only -- so no picture can show a wrong face. The
  old two-person shot library is an old version.

## D123 (owner, 2026-10-14)

Remove, after a backup:
1. **The two-person shots and the "Podcast: with characters" video mode** -- Step 5 "Generate shots", the
   `project_shots` sets (single/duo), the SDXL shot pipeline (ControlNet pose, hand repair, colour pass, gaze), shot
   regeneration and "add to library", and the `illustrated` video mode that played them. Talking characters becomes the
   default mode; one still scene and black screen stay.
2. **The two-person Shot Library** (`shot_library`) on the Shots page. The **Activity Library** (generic pictures) and
   the **sprite sets** stay.
3. **Inserts with the speaking character's face** (Qwen-Image-Edit drawing a cast member doing the action). Insert
   pictures come only from the Activity Library or `activity_illustrations` (Qwen-Image-2.1, ordinary people, no cast
   face).
4. **RealVisXL / SDXL everywhere**: the fallback of activity illustrations and scene plates, the scene-library preview
   fallback, the old character candidate/sheet generation, IP-Adapter, ControlNet, inpaint, the SDXL worker commands
   and settings; the model files (~24 GB: RealVisXL V5, SDXL base, ControlNet openpose + depth, IP-Adapter, the fp16
   VAE) and the unused anime-seg cut-out model. Without Qwen the app says so; it never falls back silently.
5. **Old data:** back up the DB (data/backups/) and zip the old shot pictures before deleting them (24 project shots,
   12 library shots). Rendered videos are kept.

Kept: Qwen-Image-2.1-Turbo (illustrations, plates, topic pictures), Qwen-Image-Edit-2511 (Phase 43 AI-scene
thumbnails only), the ONNX face detector (`count_faces`, Phase 43), the Activity Library, sprites, talking characters,
still scene, black screen, the composed / outside-AI / AI-scene thumbnails.

## Tasks

| Task | Description | Status |
|---|---|---|
| 44.1 | **Backup and archive.** DB backup `data/backups/app-before-migration-026-<time>.db`; zip every project-shot and library-shot picture to `data/backups/phase44-shots-<time>.zip`; a script `scripts/archive_old_shots.py` (dry-run listing first) | done |
| 44.2 | **Backend removal.** `pipelines.py`: character candidates/sheet, project shots, shot regenerate, the shot contexts/colour/hand/gaze passes, character inserts, SDXL fallbacks (activity illustrations, plates, scene preview -> Qwen only, clear error without it). `image_worker.py` / `engine.py`: SDXL load/encode/generate/IP-Adapter/ControlNet/inpaint/remove_background and `session()`; keep `qwen_generate`, `qwen_installed`, `count_faces`. `recipes.py`: SDXL prompt builders no longer used. `shot_library_service.py`, the shot parts of `project_visuals_service.py`, `library_service` SDXL bits. API routes: candidates, sheet, library shots (list/review/delete/content), project shots (generate/regenerate/content/to-library), library coverage. Settings `IMAGE_ILLUSTRATION_ENGINE` / `IMAGE_CHARACTER_ENGINE` / `IMAGE_BASE_REPO` / scheduler. Migration 026: drop `project_shots`, `shot_library`; old projects' `illustrated` visual mode -> `podcast_sprites`; old image-job kinds closed | in_progress |
| 44.3 | **Renderer.** Remove the `illustrated` shot track from `Episode.tsx` / `visuals.ts` / `Root.tsx` / `types.ts`; modes: `podcast_sprites` (default), `podcast_still`, `podcast_black`; Vitest updated | planned |
| 44.4 | **Frontend.** Step 5: no "Generate shots" section, no "with characters" chip, talking characters selected by default, the insert-picture panel says "generic library or local AI (no cast face)"; Shots page: Activity Library + sprite sets only; Characters page (scenes): Qwen scene preview only; `api.js` methods for removed routes deleted | planned |
| 44.5 | **Models and docs.** Delete the SDXL model folders and anime-seg from `backend/ai/models/image` (owner approved deletion with D123), trim `backend/ai/image/requirements.txt` (controlnet/ip-adapter extras if unused), update ARCHITECTURE / README / API reference, CHANGELOG | planned |
| 44.6 | **Verification.** Full pytest + Vitest; grep shows no SDXL/RealVisXL/shot code left; real app: Ep. 2 Step 5 (talking characters with generic/Qwen inserts) render; Gate B-28 owner review | planned |

## Risks

- Old projects that used "with characters" can no longer be re-rendered in that mode (owner accepted: their videos are
  kept, their shot pictures archived).
- Character-specific Activity Library entries (made earlier from a cast member's pictures) stay in the library; new
  pictures are generic only. The matcher keeps preferring generic pictures for any speaker.

## As built

- **44.1 (2026-10-14):** `scripts/archive_old_shots.py` (dry run by default; `--apply` = DB backup via the SQLite
  backup API, a verified zip of `data/visuals/*/shots/` + `data/library/shots/`, then removal; plates and videos
  untouched). Dry run on the real data: 238 pictures, 200.8 MB. Test: `tests/test_phase44_remove_sdxl_shots.py`.
