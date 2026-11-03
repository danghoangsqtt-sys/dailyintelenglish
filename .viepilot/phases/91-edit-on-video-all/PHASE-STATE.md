# Phase 91 state

Status: implemented_verified (2026-11-03, sandbox; not built, installed or pushed). Owner: "áp dụng sửa trên video cho các dạng video khác, điều chỉnh tính năng cho phù
hợp với các dạng khác nhau". Plan and task cards committed before code; defaults D131–D133.

| Task | Scope | Status |
|---|---|---|
| 91.1 | Step 2 keeps unchanged voices | done — save_script keeps id + voice of lines with the same position, speaker and text; Step 4 and automation already reuse matching voices; test |
| 91.2 | Line-drawn Shorts in the editor | done — slow podcast (translation), flashcards (part of speech, IPA, meaning saved to the lesson), chat / would you rather (messages by speaker) in the Phase 90 editor; Step 5 mounts it for every line-drawn Short; checked in the sandbox (flashcard meaning and slow podcast translation live on the video); 3 API tests |
| 91.3 | Spoken lines in the existing editors | done — shared "Các câu đọc" panel (save one line, voice for changed lines only, then the solo preview refreshes) under the solo explainer editor and the conversation storyboard; checked on a news Short (8 lines) and a 16:9 conversation (26 lines); 2 browser tests |
| 91.4 | Verify | done — flashcards / slow podcast live edits; news Short one line → voice 6 s, render 48 s; chat one message → voice 3 s, render 35 s; solo preview after a voice change fixed (plan saved again, approval asked); full pytest 2308 + 1 test updated for D133 + 1 order flake |
