# OmniVoice local TTS

> Retired by the owner on 2026-10-24. Phase 77 restores Edge-only plain speech and removes this option from the application. The instructions below are historical, not the supported setup; the worker, `scripts/setup_omnivoice.ps1` and the `DIE_OMNIVOICE_*` settings were deleted from source on 2026-10-26. See [plain Edge speech](edge-plain-speech.md).

OmniVoice is an optional, per-speaker TTS engine in Step 4. Edge TTS remains the default. OmniVoice uses Voice Design from the speaker's gender, accent, pitch, and optional description; no reference recording or cloud service is sent. The model's `instruct` Voice Design and native non-verbal tags are documented in the [official OmniVoice README](https://github.com/k2-fsa/OmniVoice#python-api).

## Install on Windows

From the project root, run:

```powershell
./scripts/setup_omnivoice.ps1
```

The script creates `.venv-omnivoice` with Python 3.11, installs the CUDA 12.8 PyTorch wheels and OmniVoice dependencies, then downloads the model to `data/models/omnivoice` (roughly 3.3 GB). It leaves `.venv` and `.venv-image` unchanged. Use `-SkipModelDownload` to prepare only the isolated Python environment.

The model is not bundled with the application or either 2.0.0 ZIP. The first model download needs Hugging Face access and about 3.3 GB of disk space. The script checks that CUDA is visible before it starts that download. In a packaged desktop build, the one-shot worker script is included with the application; its separate Python environment and model remain under the linked project workspace/data directory.

## Use

In **Step 4 — TTS Audio Studio**, choose **OmniVoice (local GPU)** for a speaker. Add an optional English voice description and use **Preview Voice Design** for a short audition; script-line preview and full-episode generation use the same selected engine. The engine list reports whether the local environment and model files are present.

OmniVoice supports the app's `[cười]`, `[cười:ha-ha]`, `[cười:hi-hi]`, and `[thở dài]` cues by converting them to native `[laughter]` and `[sigh]` tags. OmniVoice does not document a throat-clearing tag: a line containing `[hắng giọng]` fails with an explanation, and the app does not switch it to Edge behind the scenes. Remove that cue or select Edge TTS for that speaker.

Each line is generated as one utterance in an isolated child process while holding the shared GPU lease. The child exits after synthesis to release VRAM. OmniVoice provides no word timings through this integration, so generated lines have normal line-level audio/subtitles but no karaoke word highlighting. Edge TTS keeps its existing word timings.

## Configuration and diagnostics

Defaults can be overridden with environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `DIE_OMNIVOICE_PYTHON` | `<workspace>/.venv-omnivoice/Scripts/python.exe` | Dedicated worker interpreter; workspace is resolved from the desktop runtime locator |
| `DIE_OMNIVOICE_MODEL_PATH` | `data/models/omnivoice` | Local Hugging Face model directory |
| `DIE_OMNIVOICE_MIN_FREE_MB` | `8192` | Minimum free VRAM requested from the GPU manager |
| `DIE_OMNIVOICE_TIMEOUT_SECONDS` | `600` | Per-line worker deadline |

The 8192 MiB threshold is conservative and configurable; OmniVoice's real peak use and latency have not yet been measured on this RTX 3060. If generation reports insufficient GPU memory, close other GPU workloads or raise free memory before retrying. A missing environment/model gives an actionable setup error. A worker failure stays an error and never falls back silently.

The local inference and VRAM listening gate remains open until the setup script completes and a real line is generated from this machine. The accepted sample was produced through the public Hugging Face Space; it confirms interest in the sound, not local GPU performance.
