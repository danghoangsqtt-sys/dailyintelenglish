# Phase 74 — Edge vocal cue listening handoff

Status: implementation verified (276 targeted tests); actual listening and owner acceptance pending (2026-10-23).

## Sample lines

Use the same selected character voice, speed, volume and pitch for each line. Compare the Step 2 Listen preview with the mixed WAV/MP3 and the published SRT/karaoke words.

| Cue | Sample script text | Expected audible behavior |
|---|---|---|
| Legacy laugh | `That was close! [cười] Let's try again.` | Short laughter approximation; dialogue resumes with normal pitch. |
| Ha-ha | `You brought a ladder to the library? [cười:ha-ha] That's creative.` | Selected voice says a short ha-ha approximation. |
| Hi-hi | `I found your secret note. [cười:hi-hi] Don't worry, I won't tell.` | Selected voice says a lighter hi-hi approximation. |
| Sigh | `We missed the last train. [thở dài] Let's call a taxi.` | Brief sigh approximation; normal speech follows. |
| Ahem | `[hắng giọng] We should discuss the budget first. Then move on.` | Short ahem; only the next clause or six words lower in pitch, then normal pitch returns. |
| No cue | `Let's review the next lesson together.` | Existing one-request path and unchanged tone. |

## Voice matrix to record

The pinned voice IDs in existing projects should be checked first. Confirm availability in the current Edge catalog before synthesis.

| Voice | Accent/role | Ha-ha | Hi-hi | Sigh | Ahem + pitch return | Preview/mix timing |
|---|---|---|---|---|---|---|
| `en-US-BrianNeural` | US male | Pending | Pending | Pending | Pending | Pending |
| `en-US-ChristopherNeural` | US male | Pending | Pending | Pending | Pending | Pending |
| `en-US-RogerNeural` | US male | Pending | Pending | Pending | Pending | Pending |
| `en-GB-RyanNeural` | UK male | Pending | Pending | Pending | Pending | Pending |
| `en-US-JennyNeural` | US female | Pending | Pending | Pending | Pending | Pending |
| `en-GB-SoniaNeural` | UK female | Pending | Pending | Pending | Pending | Pending |
| `en-AU-NatashaNeural` | AU female | Pending | Pending | Pending | Pending | Pending |

For each recording, note the exact voice, speed/pitch, date, phrase, whether the sound is acceptable, and any replacement syllables. Check that SRT/learning/YouTube text excludes all recognized cue tags and karaoke timing follows only dialogue words. If a sound is poor, tune the recipe and increment `VOCAL_CUE_RECIPE_VERSION`; retain the previous audio for comparison.

## Current technical review

First live listening track generated 2026-10-23: `data/tmp/phase74-vocal-cues-en-US-BrianNeural.mp3` (43.19 s, mono, 24 kHz, 192 kbps export). It contains a spoken label and example for each legacy laugh, ha-ha, hi-hi, sigh, ahem/low-pitch return, and plain speech. The MP3 was decoded successfully after export. Owner listening result is still pending.

- AI returns a schema-constrained placement plan; the application inserts tags into previously validated dialogue. The optional call falls back to the clean script on failure.
- Quota is `ceil(duration_minutes × 2)` and no more than one new cue per line; approximate word-position spacing rejects closely adjacent suggestions.
- Edge TTS uses the selected voice for interjections. Ahem lowers at most the next clause or six words. Recognized cue lines use a versioned cache fingerprint.
- Shared `caption_text` strips both new laugh variants and the three legacy tags from downstream transcripts.
- 276 targeted tests passed across cue parsing/annotation, script services/jobs/APIs, TTS timing/cache, Step 2 browser, and audio/learning/YouTube exports. Ruff, JavaScript syntax and diff whitespace checks passed on 2026-10-23. Live Edge synthesis/listening remains pending.

Owner listening and release approval remain open. Edge TTS renders spoken approximations; this document does not claim natural human laughter, sighing or throat clearing.
