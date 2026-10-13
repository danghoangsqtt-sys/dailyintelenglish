# TTS Setup Guide

## Edge TTS — the sole official engine

**Decision (2026-09-13):** Edge TTS is the only officially supported TTS engine. Real
OmniVoice GPU integration was investigated and deliberately not pursued — see the
"OmniVoice" section below for why. `SpeakerConfig.tts_engine` defaults to `"edge_tts"`
and Step 4's UI does not offer any other engine as a selectable option.

### Setup
No installation beyond `pip install -r requirements.txt` (`edge-tts` is already pinned
there) — it's a free, network-based Microsoft neural TTS endpoint, not a local model.
An internet connection is required at synthesis time; no API key is needed.

### Voice map
`app/core/constants.py::EDGE_TTS_VOICE_MAP` resolves each (accent, gender) pair to a real
Edge TTS neural voice id, covering all 10 accents in `ACCENTS` × 3 genders:

| Accent | Male | Female | Neutral |
|---|---|---|---|
| american | en-US-GuyNeural | en-US-JennyNeural | en-US-AriaNeural |
| british | en-GB-RyanNeural | en-GB-SoniaNeural | en-GB-LibbyNeural |
| australian | en-AU-WilliamMultilingualNeural | en-AU-NatashaNeural | en-AU-NatashaNeural |
| canadian | en-CA-LiamNeural | en-CA-ClaraNeural | en-CA-ClaraNeural |
| irish | en-IE-ConnorNeural | en-IE-EmilyNeural | en-IE-EmilyNeural |
| scottish | en-GB-RyanNeural | en-GB-SoniaNeural | en-GB-LibbyNeural |
| indian | en-IN-PrabhatNeural | en-IN-NeerjaNeural | en-IN-NeerjaNeural |
| singaporean | en-SG-WayneNeural | en-SG-LunaNeural | en-SG-LunaNeural |
| new_zealand | en-NZ-MitchellNeural | en-NZ-MollyNeural | en-NZ-MollyNeural |
| south_african | en-ZA-LukeNeural | en-ZA-LeahNeural | en-ZA-LeahNeural |

**Known limitation — `scottish` duplicates `british`:** Microsoft's neural voice lineup
has no dedicated Scottish-accented voice at all (confirmed live against the real
`edge-tts --list-voices` catalog during Task 2.1c's QA pass). This is an upstream gap,
not a code defect, and isn't fixable by changing this app. Step 1's Scottish accent
option/chip discloses this via a `title` tooltip (Task 2.5c) so the user isn't surprised
by identical-sounding output.

### Reliability
`_synthesize_edge_tts()` (`app/services/tts_service.py`) retries once on an empty audio
response before failing the line — Edge TTS's free endpoint occasionally returns "no
audio received" under rapid-fire requests, which succeeds on immediate retry (observed
live during Sub-task 1.6a). `MAX_CONCURRENT_TTS = 2` caps concurrent synthesis calls
during "Generate All".

### Voice parameters
Per-speaker speed/volume/pitch sliders (Step 4) map to Edge TTS's `rate`/`volume`/`pitch`
SSML-style parameters: speed/volume are `±N%` around the 1.0 multiplier default, pitch is
`±N Hz` (normalized -1.0..1.0 maps to -50Hz..+50Hz, matching Azure's documented safe
pitch-shift range for neural voices).

## OmniVoice — downloaded, verified, permanently not integrated

**Decision (2026-09-13, by the user):** real OmniVoice GPU voice synthesis will not be
built. This section documents the investigation so it isn't re-litigated from scratch.

### What was actually verified
The real [k2-fsa/OmniVoice](https://github.com/k2-fsa) project (Apache 2.0) was
installed and run for real on this machine's RTX 3060: `torch==2.11.0+cu128` +
`torchaudio==2.11.0+cu128` + `omnivoice==0.2.1`, with the real ~3.27GB model weights
downloaded via `huggingface_hub.snapshot_download` into `models/omnivoice/`. The model
was confirmed to actually load onto the GPU (`torch.cuda.is_available()` checked, not
assumed — an earlier unpinned `torch` install had silently resolved to a CPU-only build)
and report real VRAM usage (2.03GB). `scripts/check_dependencies.py` reported this GREEN.

### Why it was not pursued further
OmniVoice's real inference API is `model.generate(text=..., ref_audio="ref.wav",
ref_text=...)` — **zero-shot voice cloning from a reference audio sample**, not the
natural-language "voice design" (`speaker.voice_description`) the original project plan
assumed. Closing that gap would require either the user's own licensed voice recordings
or a royalty-free reference-voice preset library, and either path raises consent/rights
questions this project can't resolve on its own — for a result that wouldn't clearly beat
the already-working, live-verified Edge TTS (10 accents × 3 genders, 20/20 real
synthesis calls succeeded in Task 2.1c's QA pass).

### What's left in the code, and why
- `_synthesize_omnivoice()` in `tts_service.py` permanently and honestly raises
  `_OmniVoiceUnavailableError("OmniVoice model not loaded")` — not a TODO stub pretending
  to work, an explicit statement that this path was investigated and correctly never
  wired to real inference.
- The `asyncio.Semaphore(MAX_CONCURRENT_TTS)` + automatic fallback-to-Edge-TTS logic
  around it stays in place, tested, and harmless — if `speaker["tts_engine"]` is ever set
  to `"omnivoice"` and `models/omnivoice/` exists, the code correctly falls back rather
  than crashing.
- `torch`/`torchaudio`/`omnivoice` are deliberately **not** in `requirements.txt` — they
  were installed manually for this one investigation, not as an app dependency.
- Step 4's per-speaker engine picker was removed (there's no real behavior difference to
  choose between anymore); only speed/pitch/volume remain editable per speaker.

## Piper TTS (offline, availability-checked only)

`scripts/check_dependencies.py` checks for a `piper` binary on `PATH` as an
availability signal but nothing in the app currently calls it — it is not a selectable
or implemented synthesis path, only a dependency-check placeholder for a possible future
fully-offline mode.
