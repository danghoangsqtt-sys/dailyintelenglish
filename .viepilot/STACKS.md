# Stack Research Index

This index records the official guidance used by planning artifacts. Phase 33 was validated on 2026-10-10 against the pinned project dependencies.

| Capability | Project version | Global cache |
|---|---:|---|
| FastAPI multipart uploads | FastAPI 0.141.1, python-multipart 0.0.32 | `C:/Users/Admin/.viepilot/stacks/fastapi-uploadfile/` |
| SQLite persistence | SQLite via aiosqlite 0.22.1 | `C:/Users/Admin/.viepilot/stacks/sqlite-versioned-assets/` |
| Browser file workflows | Native HTML/JavaScript, `fetch`, `FormData` | `C:/Users/Admin/.viepilot/stacks/browser-file-workflows/` |
| Image validation | Pillow 12.3.0 | `C:/Users/Admin/.viepilot/stacks/pillow-image-validation/` |
| Inline vocal cues and prosody | Edge TTS + pydub/ffmpeg (existing stack) | `C:/Users/Admin/.viepilot/stacks/edge-tts-vocal-cues/` |
| Local OmniVoice Voice Design | OmniVoice 0.2.1 + PyTorch 2.8 CUDA 12.8 in `.venv-omnivoice`; optional, no main-app imports | [Operations guide](../docs/operations/omnivoice-local-tts.md), [Phase 75](phases/75-omnivoice-local-tts/PLAN.md) |

Read `SUMMARY.md` first. Open `BEST-PRACTICES.md` and `ANTI-PATTERNS.md` when implementing the related task. `SOURCES.md` contains official links and validation dates.

