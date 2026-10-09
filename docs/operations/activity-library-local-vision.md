# Activity Library — local vision setup

Smart upload uses Qwen3-VL 4B Instruct locally by default. The user chooses
Alex, Lina or Generic; the model proposes only activity metadata. New pictures always
remain **Needs review** until the owner approves them.

## Runtime design

- The default runtime is Ollama `qwen3-vl:4b-instruct-q4_K_M` (about 3.3 GB).
- The model stays loaded across one upload batch and receives `keep_alive=0` on the last image,
  so VRAM is released immediately afterward.
- The main application never imports PyTorch or Transformers.
- An optional direct Hugging Face runtime uses one `venv-image` worker for the batch, then exits.
- The original upload is not sent to the model. A JPEG copy bounded to 1280 pixels is staged
  under `data/tmp/activity_vision` and deleted after the worker exits.
- Ollama stores its model in the normal Ollama cache. Direct Hugging Face files are cached under
  `models/activity-vision`; the optional worker disables Xet and uses resumable HTTP.
- Results are Pydantic-validated. A failure falls back to filename metadata and never
  auto-approves an image.

## Check the environment

```powershell
ollama show qwen3-vl:4b-instruct-q4_K_M
```

Install once if the model is absent:

```powershell
ollama pull qwen3-vl:4b-instruct-q4_K_M
```

For the optional direct Hugging Face runtime, run
`venv-image\Scripts\python.exe scripts\activity_vision_worker.py --self-check`.

## Configuration

```dotenv
DIE_ACTIVITY_VISION_PROVIDER=local
DIE_ACTIVITY_VISION_RUNTIME=ollama
DIE_ACTIVITY_VISION_MODEL=qwen3-vl:4b-instruct-q4_K_M
DIE_ACTIVITY_VISION_HF_MODEL=Qwen/Qwen3-VL-4B-Instruct
DIE_ACTIVITY_VISION_TIMEOUT_SECONDS=900
DIE_ACTIVITY_VISION_MIN_FREE_MB=10240
DIE_ACTIVITY_VISION_CLOUD_FALLBACK=false
```

Provider choices:

- `local`: local Qwen3-VL; filename fallback if unavailable.
- `cloud`: Gemini only, when cloud AI and a Gemini key are enabled.
- `filename`: no image analysis; metadata starts from the filename.

Set `DIE_ACTIVITY_VISION_CLOUD_FALLBACK=true` only if sending a resized copy to the
configured Gemini provider is acceptable when local analysis fails.

## Recovery

- **CUDA or VRAM error:** close other GPU applications and retry. The upload is still added
  with fallback metadata if the worker cannot start.
- **Model missing:** run the `ollama pull` command above. The picture still imports with filename
  metadata if the local model is not ready.
- **Hugging Face first-run timeout:** increase `DIE_ACTIVITY_VISION_TIMEOUT_SECONDS`, then retry.
- **Wrong direction:** correct the pending item before approval. The controlled prompt treats
  a forward arrow as `go straight`, left/right arrows separately, and a crosswalk as
  `cross the street`.
