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

## Owner report after install (2026-11-03, "những lỗi tồn đọng")

The owner sent two frames of the v2 passive video: made-up scene labels ("TÒI THẦM CỦA TO BE", "LỪNG LỘT NGÔN NGỮ") and
an English rule card ("Past Participle (V3) is an adjective; it never changes for tense.") in a Vietnamese video, which
is also a false shortcut. Fixed:

- An English sentence is never drawn as a rule or stamp in a Vietnamese lesson, and an English label or subtitle is left
  out (the pill keeps "PHÂN CẢNH N"); `looks_english` checks for Vietnamese letters and common English words.
- The prompt asks for plain, everyday labels and forbids shortcuts stated as facts ("V3 works like an adjective"); the
  review rewrites made-up phrases and such shortcuts.
- Script runs v5–v7 (scripts only, sandbox, Gemini 3.1 Flash-Lite): v5 wrote "I very like" for the passive topic (told
  never to copy the passive model) → the topic is required and repeated, and a model's own topic may follow it; v6 got
  the "I very like" lesson wrong by borrowing the passive model's "missing TO BE" idea → a second model lesson for the
  `vietnamese_error` kind; a whole sentence as a sticker → drawn as a rule; a table with no fitting row → no summary
  lines. v7: passive, present perfect and "I very like" all on topic, correct, with natural Vietnamese labels.
