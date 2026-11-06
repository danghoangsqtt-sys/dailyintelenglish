# Phase 100 state

Status: implemented_verified (2026-11-06): an automatic Studio export passes (below). Committed with Phase 98 (f5be5647).

- Read Along is available in the 9:16 template gallery, individual project setup and Shorts batch setup. The gallery includes a five-second silent example using the original sample passage.
- Verified 37 focused backend tests and 220 renderer tests. Browser playback showed the shared illustration, the complete stationary passage and changing highlights. A two-second Remotion H.264 render passed with system FFmpeg after the bundled FFmpeg exited during encoding.
- The current source accepts the new template, while the running Studio API on port 8001 still advertises the previous schema. Start Studio from current workspace code and verify one export from an actual generated passage, narration and illustration.

## Automatic Studio export (2026-11-06, Phase 98/99 close-out)

A Channel-plan Read Along series (A2, narrator Lina, "My Morning Walk") made by the night runner's Producer on an isolated copy:
script 21.1 s, learning 6.0 s, audio 6.6 s, render 124.4 s, thumbnail 7.5 s, YouTube 3.8 s -> waiting for review. MP4 24.733 s, 1080x1920,
H.264/AAC, A/V in sync, no black or long silent span, SRT valid. A frame at 12 s shows the title, the whole passage, the current sentence and
the current word highlighted.

Open points: the script answer was written by the local model both times (the cloud answer did not pass the Passage schema and the
one-shot local retry served it); the first run timed out while Qwen held the GPU for another video. The picture came from the library
(three students), not drawn for the passage.
