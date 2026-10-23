# SPEC — Phase 75: OmniVoice Voice Design, local TTS

Source: the owner-approved OmniVoice Voice Design laughter sample and follow-up request to integrate it. This phase adds an optional, local OmniVoice engine; Edge remains the default.

## Goal

Let a speaker use OmniVoice Voice Design to synthesize whole English dialogue lines on the local CUDA GPU, including native `[laughter]` and `[sigh]` tags. Keep speaker identity consistent by generating the full line in one engine. Do not mix an OmniVoice cue over Edge dialogue.

## Requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| R75-01 | Edge remains the default and preserves existing project behavior. OmniVoice is an explicit per-speaker choice. | Existing Edge paths remain unchanged; API and browser checks cover engine selection and reload. |
| R75-02 | OmniVoice uses local Voice Design attributes and optional user description, with no reference audio or cloud Space dependency. | Worker receives text and design instruction locally; setup and status explain model readiness. |
| R75-03 | `[cười]`, `[cười:ha-ha]`, `[cười:hi-hi]` map to OmniVoice `[laughter]`; `[thở dài]` maps to `[sigh]`. Captions/transcripts keep stripping app tags. | Pure parser conversion checks and generated sample review. |
| R75-04 | OmniVoice does not claim to support ahem/throat-clear. Selecting OmniVoice for a line with `[hắng giọng]` produces a clear actionable error; it never silently falls back to Edge. | API/service checks assert exact engine error and no Edge call. |
| R75-05 | The local model is optional and kept out of the app venv and packaged app. A dedicated environment and cache can be prepared separately. | Setup script, runtime readiness checks, and no app requirements/EXE model payload. |
| R75-06 | GPU access is exclusive with existing local image/Ollama consumers; an unavailable model/GPU reports a clear reason. | GPU lease tests and mocked worker tests. |
| R75-07 | Voice engine/design settings affect cache identity and stale-completion checks. OmniVoice lines without word alignment remain honestly marked without word-level karaoke. | Fingerprint tests and existing audio renderer behavior checks. |

## Boundaries

- No Hugging Face Space or external TTS request in production; the Space was only used to create the approved audition sample.
- No voice cloning, reference-audio upload, model fine-tuning, or unsupported ahem tag.
- No schema migration is expected: `speakers.tts_engine`, `speakers.voice_description`, and character voice defaults already exist. Update the plan before adding a migration if code inspection disproves this.
- The first implementation adds the local source/runtime setup and UI. It does not publish or install a new EXE, and does not claim live GPU inference until the weights are available and a local render is heard.

## Delivery gates

1. Edge remains the default; choosing OmniVoice is explicit and persists per speaker.
2. The dedicated worker loads `k2-fsa/OmniVoice` locally, uses the shared GPU lease, returns MP3 audio, and exits/unloads GPU state safely.
3. Supported emotion tags are native OmniVoice tags; ahem and runtime failures are surfaced honestly.
4. Voice/cache revisions prevent reuse after engine or design changes.
5. Installation, model download, readiness, storage size, and local-only behavior are documented.
6. Targeted checks pass. Local generation and owner listening are recorded as separate evidence; this phase is not release approval.
