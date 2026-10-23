# Inline vocal cues in script lines

## Goal

Editors insert `[cười]`, `[thở dài]`, or `[hắng giọng]` at the caret in Step 2. TTS produces an audible interjection at that position. Captions and word highlighting show only spoken dialogue.

## Research and limits

- Edge TTS, the project's sole engine, permits voice and prosody options but not custom SSML. Source: https://github.com/rany2/edge-tts#custom-ssml
- Azure Speech can embed recorded audio and express styles through its separate keyed API; these features are unavailable in Edge TTS. Source: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-voice
- Implement vocal approximations by synthesizing English interjections with the selected speaker voice. Their naturalness varies by voice; do not present them as native emotional controls.

## Bounded implementation plan

| File | Change |
|---|---|
| `backend/ai/tts/vocal_cues.py` | Parse only the three supported tags and provide spoken interjections and caption text. |
| `backend/ai/tts/tts_service.py` | Synthesize each text/cue part, join decoded audio in a worker thread, offset word boundaries from measured durations, preserve normal one-call path. |
| `backend/media/audio_service.py` | Remove cue tags from published line timestamps for video captions. |
| `backend/content/learning_service.py` | Remove cue tags from the learning prompt transcript. |
| `backend/content/youtube_service.py` | Remove cue tags from YouTube prompts, chapters and published transcripts. |
| `frontend/static/js/step2_script.js` | Add caret insertion controls, explain Edge's approximation, and wait for the saved script ID before preview. |
| `frontend/static/css/style.css` | Style the compact insertion controls. |
| `frontend/static/js/i18n_vi.js` | Translate the insertion controls and preview guidance in Vietnamese mode. |

## Risks and verification

- More than one Edge request per tagged line increases generation latency; unchanged lines keep the existing single request.
- MP3 decoding/reencoding can introduce small padding. Offset words using decoded segment lengths and inspect the result.
- Preserve unsupported bracket text literally; only documented tags are directives.
- Naturalness requires listening to a live Edge preview; automated checks cannot prove it.

## Current result

The three tags are inserted from the Step 2 editor and rendered as same-voice interjections in TTS. Published captions, YouTube transcripts, and learning prompts omit the tags. Python and JavaScript syntax checks passed; a live voice listening review is still needed to judge naturalness.
