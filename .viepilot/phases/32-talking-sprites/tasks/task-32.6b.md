# Task 32.6b — Activity Library UI

## Objective

Extend `/shots` with an Activity Library card/grid that lets the owner inspect, correct and review activity cutaway assets without mixing them into scene-shot semantics.

## Paths

- `frontend/pages/shot_library.html` — Activity Library controls and accessible preview/editor dialog.
- `frontend/static/js/api.js` — centralized Activity Library calls.
- `frontend/static/js/shot_library.js` — load, filter, preview, edit and approve/reject flow.
- `frontend/static/css/style.css` — scoped responsive styles only if existing Shot Library styles cannot express the UI.
- `tests/test_activity_library_browser.py` — browser happy/error/reload coverage.

## File-Level Plan

1. Add a separate Activity Library section with pending/approved/rejected filters, generic/character scope, activity/context summary, usage count and thumbnail grid.
2. Add inbox status/import results, full-size preview, metadata editor (scope, activity, contexts, aliases, variant) and explicit approve/reject controls with loading locks and surfaced errors.
3. Reuse API response shape and escaping conventions from the existing Shot Library; reload from persisted state after every mutation.

## Verification

`venv\Scripts\python.exe -m pytest tests/test_activity_library_browser.py -q`

## Acceptance Criteria

- [x] Owner can import, correct metadata, approve/reject and filter an item from `/shots`.
- [x] Preview uses the content API, not raw filesystem paths.
- [x] Double-submit and API failures leave the UI usable.

## Amendment A — Dedicated local Activity Vision (2026-10-09)

### Objective

Replace the smart uploader's direct Gemini dependency with a dedicated local Qwen3-VL
vision runtime. The user still chooses Alex, Lina or Generic; the model only proposes a
canonical activity, context tags and aliases. Every result remains pending until reviewed.

### Paths

- `app/core/config.py` — local provider, model, timeout, VRAM and optional cloud-fallback settings.
- `app/services/visuals/activity_analysis_service.py` — batch provider orchestration, strict result
  validation, local worker execution and safe filename/cloud fallback.
- `app/api/visuals.py` — read uploads first, analyze one batch, then persist each validated result.
- `scripts/activity_vision_worker.py` — optional isolated Hugging Face loader and deterministic JSON inference.
- `requirements-image.txt` — document the existing Transformers/PyTorch worker dependency contract.
- `.env.example` — operator-facing Activity Vision settings.
- `frontend/pages/shot_library.html` — accurate local-first privacy/runtime guidance.
- `frontend/static/js/shot_library.js` — distinguish local, cloud and filename fallback outcomes.
- `tests/test_activity_analysis_service.py` — provider order, subprocess protocol, validation and fallback.
- `tests/test_activity_library.py` — local-default behavior and API batch integration.
- `tests/test_activity_library_browser.py` — uploader remains usable with local analysis results.
- `docs/operations/activity-library-local-vision.md` — setup, first-download, VRAM and recovery guide.

### File-Level Plan

1. Add `ACTIVITY_VISION_PROVIDER=local`, default runtime Ollama with
   `qwen3-vl:4b-instruct-q4_K_M`, optional direct Hugging Face runtime, a bounded timeout,
   conservative VRAM lease threshold, and an opt-in Gemini fallback flag.
2. Resize copies before inference, stage them in a temporary directory, send a JSON manifest to
   `venv-image`, parse an output JSON file, and always remove temporary data. Never pass shell text.
3. Acquire the shared GPU lease. The default Ollama runtime keeps Qwen3-VL loaded across the
   batch and sends `keep_alive=0` on the final request; the optional Hugging Face runtime uses
   one worker process for the batch and exits to release VRAM.
4. Use deterministic generation and a JSON schema. Constrain output to the existing directions
   taxonomy and return one result per input in stable order.
5. Treat model/download/CUDA/timeout/malformed-output failures as recoverable: optional cloud
   fallback first, filename fallback last. Do not lose a valid uploaded image because AI failed.
6. Keep all smart-upload rows pending and expose only provenance/confidence, never model internals
   or local filesystem paths.

### Best Practices / Risks

- The default Q4 Ollama model is roughly 3.3 GB. The optional BF16 Hugging Face repository is
  roughly 8.9 GB; neither may remain resident beside image generation.
- No `trust_remote_code`; use the Transformers-native Qwen3-VL implementation and safetensors.
- Do not infer character identity. Do not auto-approve based on confidence.
- Model download is explicit and may be slow; later runs use the local cache.
- Unit and browser tests mock the worker. A separate opt-in smoke test exercises the real GPU/model.

### Verification

- `venv\Scripts\python.exe -m pytest tests/test_activity_analysis_service.py tests/test_activity_library.py tests/test_activity_library_browser.py -q`
- `venv\Scripts\python.exe -m ruff check app/core/config.py app/services/visuals/activity_analysis_service.py app/api/visuals.py scripts/activity_vision_worker.py tests/test_activity_analysis_service.py`
- `ollama show qwen3-vl:4b-instruct-q4_K_M`
- Optional Hugging Face runtime: `venv-image\Scripts\python.exe scripts\activity_vision_worker.py --self-check`
- Real smoke: analyze one approved direction image and require valid JSON with a direction-preserving label.

### Acceptance Criteria

- [x] Default smart upload does not require or send data to Gemini.
- [x] One local model load analyzes all pictures in the upload batch and then releases VRAM.
- [x] Local failures preserve uploads through deterministic fallback and remain review-gated.
- [x] `go straight`, `turn left`, `turn right` and `cross the street` cannot be merged into one label.
- [x] UI identifies whether metadata came from local AI, cloud fallback or filename fallback.

### Implementation Decision A1 — Ollama default, Hugging Face optional

The target network repeatedly timed out against Hugging Face's Xet CDN and standard HTTPS
shard endpoints during a real model download. Ollama 0.40.1 is already part of this application
and publishes the official Qwen3-VL 4B instruct Q4_K_M conversion. The default local runtime is
therefore Ollama (3.3 GB); the direct Transformers/Hugging Face worker remains available through
`DIE_ACTIVITY_VISION_RUNTIME=huggingface` for environments whose Hugging Face download works.

### Verification Result — PASS (2026-10-09)

- Targeted Activity Library/local-vision/matcher/browser suite: **16 passed**.
- Full project suite: **1,633 passed**, 2 third-party deprecation warnings, 0 failures.
- Ruff, Python compile, frontend `node --check` and `git diff --check`: PASS.
- `venv-image` self-check: CUDA true, torch 2.11.0+cu128, Transformers 5.17.0,
  native Qwen3-VL class available. `torchvision` 0.26.0+cu128 was added to the environment.
- Real RTX 3060 smoke using activity ID `c6d1d2e7-4cc3-4923-94e7-85ed9dd5a5c6`:
  `go straight`, contexts `city street/main road/urban sidewalk`, aliases
  `continue straight/walk straight ahead`, confidence **0.98**, source `local_ai`.
- Post-smoke `ollama ps` was empty; GPU returned to about 10.6 GB free VRAM.
- `/vp-audit`: Tier 1 state consistent after this update; Tier 2 local-vision docs match
  runtime/privacy behavior; Tier 3 lint/schema/path/subprocess/GPU-release checks PASS.
