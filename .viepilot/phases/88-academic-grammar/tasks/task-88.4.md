# Task 88.4 — Verify

Full pytest, vitest, tsc, ruff; two real `grammar` Shorts made in the sandbox from source (Shorts batch, audience
Việt Nam): passive voice and present perfect; check transcript, length (≤ 3 min), frames (cards stack, table fills,
colours), into `D:\Videos\Kiểm tra Ngữ pháp 2026-11-03`. Real-run problems are fixed and recorded here.

## Results (2026-11-03)

Sandbox server from source (`studio-p87`, port 8030, sandbox data), Shorts batch "Make videos now", audience Việt Nam,
narrator Lina → VieNeu Ngọc Huyền. The local model (qwen3.5:9b) failed the lesson schema every time and the router
fell back to Gemini 3.1 Flash-Lite, which also did the review pass.

| Run | Result | Problems found → fixed |
|---|---|---|
| v1 | both stopped at the script: "only 0 scenes of the lesson have cards to show" | the AI left every card out (card was optional) → card required on every step |
| v2 | passive 94.1 s, present perfect 101.1 s, 1080×1920 | `**` Markdown drawn; sentence-long summary cells made the table run into the caption; a scene opened on an empty screen (first card unusable); vague or wrong images ("V3 đứng im như một chiếc máy lạnh", "đã được puts"); a rule card in English; a long point name as a three-line title → Markdown removed, short cells asked for and the stack shrinks to fit, a scene shows its first card from its first line, a model lesson (sample B) in the prompt, a stricter review, a plain point name, smaller long titles |
| v3 | stopped and restarted as v4 to include the last prompt fixes | — |
| v4 | **Câu bị động 69.4 s, Thì hiện tại hoàn thành 56.0 s**, 1080×1920 | the scene stamp covered the example sentence → in a scene the stamp is a card under the others (checked on a still; not re-rendered for real) |

v4 scripts follow the sample: formulas → "Quên hết đi!" stamp → promise → state / sticker V3 / TO BE carries the tense
→ summary table row by row → core rule → quick quiz with countdown. One sentence remains loose ("không thêm s hay ed gì
cả" for V3). Frame sheets: `docs/operations/phase88-screens/`.

Tests: full pytest 2285 passed + 3 browser tests that failed only while a video was rendering and pass alone (16/16);
vitest 203; tsc and ruff clean.
