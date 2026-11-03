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

## Quality round (owner 2026-11-03: "tạo thêm 3 video về ngữ pháp và gốc từ… xóa bỏ bản lỗi")

The faulty grammar test folders (v2–v4, script runs v5–v7) were moved to the Recycle Bin and their sandbox projects
deleted. Made again from source in the sandbox (Shorts batch, Việt Nam, VieNeu Ngọc Huyền):

| Short | Length | Found → fixed |
|---|---|---|
| Ngữ pháp v8 · Câu bị động | 58.3 s | — |
| Ngữ pháp v8 · Hiện tại hoàn thành | 62.1 s | — |
| Ngữ pháp v8 · I very like | 63.0 s | "really" / "very much" marks drawn in the beige plain-chip colour (invisible) → ink with a yellow underline, re-rendered; a long pill ran under the channel logo → narrower, smaller |
| Gốc từ v4 · SPECT | 69.9 s | SUS + PECT, SPECTA + TOR → a root family's words split around the whole root |
| Gốc từ v4 · RE- | 79.0 s | an English quiz clue in a Vietnamese video → the quiz word's parts and meanings in Vietnamese; stray ";" after meanings |
| Gốc từ v4 · -MENT | 104.7 s | no picture: Qwen ran out of Windows virtual memory (the installed app, VieNeu and the sandbox were running at once) and the AI's icon names were not in the bundled set; "enjoyment = khoảnh khắc vui vẻ" is a loose meaning (not fixed) |

Also found while showing the owner the screens: Step 2 "Regenerate this line" replaced a roots/grammar line with an
English line and dropped its card → hidden for these Shorts and refused by the API; Step 5 showed an empty "Scene
picture" list (a remembered "one still scene" choice) and caption choices these Shorts do not use → hidden; the batch
and Step 5 copy said Shorts last at most a minute → three for these two kinds. Frame sheets in
`docs/operations/phase88-screens/` (v8-*, roots-v4-*).

Editing on the video (owner question): today the owner edits the spoken text in Step 2; the cards (formula chips, rule,
table, labels) are not editable and any change needs a new audio take for the changed lines and a full re-render.
Card editing with a live 9:16 preview is proposed as a follow-up.
