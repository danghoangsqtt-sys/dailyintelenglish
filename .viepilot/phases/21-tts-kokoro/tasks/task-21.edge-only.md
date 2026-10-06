# Chore: Edge TTS only — remove Kokoro, StyleTTS 2 and OmniVoice (owner 2026-10-06, D56)

## Objective

Owner: "Bỏ kokoro khỏi hệ thống giọng đọc chỉ sử dụng Edge, có thể xóa luôn Kokoro để hệ thống giảm
bớt dung lượng". This means drop Kokoro, use only Edge, and delete files to save disk. The owner then
confirmed removing StyleTTS 2 and OmniVoice too, so the system has a single voice engine: **Edge
TTS**. The voices heard today do not change: OmniVoice always fell back to Edge, and Kokoro and
StyleTTS 2 were never wired in.

## Done before this card

- **Kokoro removed:** commit `99575b6`. `venv-kokoro` (1.06 GB) and `models/kokoro` (0.31 GB)
  were deleted.
- **Deleted from disk (approved):** `venv-styletts2` (5.02 GB), `models/styletts2` (1.73 GB) and
  `models/omnivoice` (3.04 GB).

## Paths

- `app/core/constants.py`
- `app/models/project.py`
- `app/db/migrations/013_tts_edge_only.sql` (new)
- `app/services/tts_service.py`
- `app/api/tts.py`
- `app/core/config.py`
- `app/services/gpu_model_manager.py` (docstring example)
- `app/main.py` (comment)
- `frontend/static/js/step1_config.js`
- `scripts/check_dependencies.py`
- `scripts/styletts2_worker.py` (delete)
- `scripts/spike_styletts2.py` (delete)
- `requirements-styletts2.txt` (delete)
- `.gitignore`
- `requirements-image.txt` (comment)
- `tests/conftest.py`
- `tests/test_tts_service.py`
- `tests/test_tts_api.py`
- `tests/test_gpu_model_manager.py`
- the other tests that send `"omnivoice"`

## File-Level Plan

1. **`TTS_ENGINES = ["edge_tts"]`.** The legacy value `"omnivoice"` is still **accepted and
   normalised to `edge_tts`** in the speaker validators, so an old browser tab or saved request
   never fails.
2. **Migration 013:** `UPDATE speakers SET tts_engine = 'edge_tts' WHERE tts_engine IS NOT
   'edge_tts'`. This is additive data only. The existing column default stays, because
   `project_service` always writes the value explicitly.
3. **`tts_service`:**
   - Edge only;
   - remove `_synthesize_omnivoice`, `_OmniVoiceUnavailableError` and the semaphore;
   - `engine_used` is always `edge_tts`;
   - keep the Edge retry and word boundaries unchanged.
4. **`/api/tts/engines`** lists only `edge_tts`.
5. **Config:** remove `OMNIVOICE_MODEL_PATH` and `GPU_MIN_FREE_MB_STYLETTS2` (no runtime use).
6. **Step 1 JS:** new speakers send `edge_tts`.
7. **Scripts:**
   - delete the StyleTTS 2 worker, spike and requirements;
   - drop the OmniVoice check in `check_dependencies.py`;
   - remove the `venv-styletts2` ignore lines.
8. **Tests:** update the OmniVoice cases to the Edge-only behaviour, plus the legacy-value
   normalisation and the migration.

## Verification

- The full suite is green.
- `grep` finds no runtime reference to omnivoice, styletts or kokoro in `app/` except the
  documented legacy normalisation.
- A real Edge TTS line preview still works.

## Results (done 2026-10-06)

- **Code:** commit `c1522ee`. Built as planned.
- **Migration 013, checked on a sqlite backup copy of the real DB** (the real `data/app.db` was only
  read; it migrates on the next app start):
  - speakers before: `edge_tts` 3, `omnivoice` 13;
  - after: `edge_tts` 16.
- `/api/tts/engines` lists only `edge_tts`.
- A real Edge TTS preview of a real line through the API succeeded (`engine_used: edge_tts`).
- `scripts/check_dependencies.py` passes all checks, with no OmniVoice check.
- **Disk freed** (Kokoro + StyleTTS 2 + OmniVoice): 1.37 + 6.75 + 3.04 = **11.2 GB**.
- **Full suite: 1412 passed.**
