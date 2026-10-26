# English TTS audition

Date: 2026-10-23 (Asia/Bangkok). Status: comparison recordings generated and technically verified; owner subsequently reports Chatterbox has higher quality. Owner explicitly requested English voice counts, candidate selection, and actual comparison recordings.

## Scope and paths

- `data/tmp/english-tts-comparison-20261023/`: isolated research sources, Python environment, model cache, scripts, reference audio, generated samples, manifest and listening page.
- `data/exports/english-tts-comparison-20261023/` and its ZIP: persistent listening deliverables and the English voice inventory.
- `docs/brainstorm/english-tts-audition-2026-10-23.md`: record selection, methodology, exact engine/model versions, voice counts and results.
- `docs/brainstorm/session-2026-10-23-tts-emotion.md`: link the audition results.

The owner request authorizes the isolated model/dependency setup and synthesis needed for the audition. Production source, installed application and project voice settings are outside this audition's scope.

## Plan

1. Query the current Edge catalogue using the app's normalization; distinguish fixed English voices from designed/cloned voices. Check the named candidate models' actual English and emotion capabilities.
2. Select an English-focused expressive model. First candidate: Chatterbox Turbo, with documented native non-verbal tags and MIT model card. It has no advertised fixed English voice roster comparable to Edge; references define the character voices. Free-form emotion sliders are not supported in Turbo, despite similar argument names in its API.
3. Create an isolated environment and download the official weights. Generate neutral reference clips with four existing English Edge voices (US/UK, male/female). These are internal audition references, not four bundled Chatterbox preset voices or a claim of identical voice reproduction.
4. Generate the same English dialogue using Edge's current vocal-cue code and Chatterbox's supported native cues. Record engine-specific text and parameters. Do not substitute coughing for throat clearing, or label an unsupported emotion as supported.
5. Export individual and paired MP3s plus an HTML listening page, use equal comparison loudness, and verify that the audio decodes, is non-silent and contains expected durations. Record real generation errors and timing. Owner listening determines quality acceptance.

## Initial evidence

- Fresh Edge query: 47 English voices, 23 male / 24 female across 14 locales. The normalized catalogue is saved as `edge_catalog.json` in the audition directory.
- VieNeu's preset count refers to its own (primarily Vietnamese-described) roster; it is not evidence of 25 native-English actor voices. SEA-G2P generates no voices.
- OmniVoice Studio wraps underlying engines. OmniVoice Voice Design/cloning can create English speaker variations but is not a finite named catalogue. Its weights' published non-commercial condition remains relevant to choosing a production engine.
- Chatterbox Turbo's `generate` implementation explicitly ignores nonzero CFG/exaggeration controls; the audition will assess documented non-verbal tags and reference-conditioned voice quality, not promise arbitrary angry/sad/whisper instructions.

Sources: [Chatterbox Turbo model card](https://huggingface.co/ResembleAI/chatterbox-turbo), [Turbo code](https://github.com/resemble-ai/chatterbox/blob/master/src/chatterbox/tts_turbo.py), [previous research](tts-engine-research-2026-10-23.md).

## Candidate capability verification

The official Turbo demo lists nine event tags, including `[clear throat]`, `[sigh]`, `[chuckle]` and `[laugh]`. This adds documented throat clearing to the first README-only review. The model's added-token file also contains ten style/affect tokens, including `[happy]`, `[angry]` and `[whispering]`; presence in a tokenizer alone is not an audio-quality guarantee. Those three are explicitly exploratory conditions in this audition.

Qwen3-TTS CustomVoice documents nine multilingual speakers, of which Ryan and Aiden are labelled native English (both male). VoiceDesign/voice cloning can expand that roster but are separate model workflows. VieNeu's 25 preset roster has no separately documented native-English bank; English synthesis capability must not be counted as 25 native-English actors. OmniVoice/Studio and Chatterbox likewise should not be assigned a fabricated fixed voice count.

Sources: [official demo event list](https://huggingface.co/spaces/ResembleAI/chatterbox-turbo-demo/raw/main/app.py), [model added tokens](https://huggingface.co/ResembleAI/chatterbox-turbo/raw/main/added_tokens.json), [Qwen native-language table](https://github.com/QwenLM/Qwen3-TTS#custom-voice-generate).

## Setup notes

The standalone Python 3.11 Torch download was stopped because a compatible CUDA stack was already installed. The audition instead uses a Python 3.14 overlay venv that reads the existing `.venv-image` Torch/CUDA libraries and app support libraries, with additional packages installed only into the audition venv. Existing environments' package installations are not modified. Source is pinned to Chatterbox commit `5de7a54aa4e5e2baadb0182dde554908b48b85c2`; model revision is `749d1c1a46eb10492095d68fbcf55691ccf137cd`. The weights are approximately 2.8 GiB; unused original S3Gen weights are excluded. PyPI downloads stalled, so the audition-only dependency retry uses the Tsinghua PyPI mirror.

## Results

- Selected candidate for the English-only requirement: **Chatterbox Turbo**. Its English focus, nine documented event cues including all three required event types, reference-conditioned character voices, and published MIT model card make it the strongest fit for this audition. This is a technical suitability selection, not a claim that listening acceptance has passed.
- Produced 32 Edge samples using the current application's `_synthesize_with_vocal_cues` and 32 candidate samples using local CUDA. Four neutral references came from Brian/Jenny (US) and Ryan/Sonia (UK); the candidate voices are clones of those audition references, not four native named presets shipped by Chatterbox.
- Cases: neutral, laugh, chuckle, sigh, throat clearing; exploratory happy, angry and whispering tokens. For the last three, Edge receives the same dialogue without an emotion instruction because the current engine controls do not implement those styles. Edge's ahem also lowers the following short clause; the candidate test uses its native throat-clearing event only.
- All 64 individual MP3s decode and are non-silent. Original candidate WAVs and baseline MP3s remain in the audition workspace. Listening deliverables use constant loudness gain toward -20 LUFS with a -1 dBFS peak cap, no time stretching or cue editing.
- Candidate output length: 3.28–5.80 seconds. Median synthesis time after model load/reference enrollment: 1.609 seconds; median RTF 0.342. Model load in the successful worker: 6.018 seconds. Peak PyTorch allocated memory: 2873.9 MiB, excluding CUDA context/other processes/reserved memory. These are short-sample measurements on this RTX 3060, not an episode-length benchmark.
- A NumPy 2.x compatibility issue promoted the SDK's reference-loudness output to float64. The PoC restores float32 after the same gain operation, without changing model weights or cue text. This adjustment is recorded in `candidate_metadata.json`; production integration would need to handle it explicitly.
- No synthetic speaker settings or production application source were changed. An application instance was found running during setup; the existing read-only idle-job preflight passed and the worker repeats that check before each sample. GPU memory returned to its pre-inference free level after worker exit.

## Listening deliverables

- `data/exports/english-tts-comparison-20261023/LISTEN.html`: four voice selections and eight A/B cases per voice. A = current Edge, B = local Chatterbox; local audio metadata and all four selector changes verified in a headless browser, with no JavaScript errors.
- `QUICK_COMPARE.mp3`: 158.5 seconds; voice order US male, US female, UK male, UK female. Within each voice: laugh, sigh, throat clearing; Edge first then candidate in each pair.
- `comparisons/*_A_Edge_B_Chatterbox.mp3`: all eight cases for each voice, in fixture order.
- `english_edge_voices.csv`: the full 47-entry current English catalogue.
- `manifest.json`: exact source text, parameters, reference hashes, output hashes, timing and package/model revisions.
- `data/exports/english-tts-comparison-20261023.zip`: complete listening pack.

Owner subsequently reports: “rõ ràng là chatter bõ cho chất lượng cao hơn”. Record this as an overall listening preference for Chatterbox over the current system in this audition. It does not separately certify each voice, event, or exploratory style token. The owner now asks how to expand Chatterbox voices and support karaoke; see [voice library and karaoke design](chatterbox-voices-karaoke-2026-10-23.md). Production integration and episode-length acceptance remain pending.
