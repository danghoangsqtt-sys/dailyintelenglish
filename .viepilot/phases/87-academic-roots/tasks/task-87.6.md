# Task 87.6 — Verify

See [PLAN.md](../PLAN.md) task 87.6.

## How (sandbox, not the installed app)

The plan puts build and install after the owner's go-ahead, so the real check ran from source: a sandbox data folder in
the session scratchpad with a backup copy of `data/app.db` (no links to the real libraries, so new library pictures
stay in the sandbox), the server on port 8030 (`studio-p87` in `.claude/launch.json`), the real VieNeu worker
(`.venv-vieneu`), the real Qwen image worker (`.venv-image`), Gemini for the script. Each run: the Shorts batch
"Make videos now" for two ideas, audience Việt Nam, narrator Lina (female → VieNeu "Ngọc Huyền"). Videos go to
`D:\Videos\Kiểm tra Gốc từ 2026-11-03\<series>\`.

## Runs

| Run | Gốc PRESS | Hậu tố -tion | Found |
|---|---|---|---|
| v1 (`Gốc từ`) | 94.8 s, 1080×1920, 22 lines, Qwen line art for every word | stopped: "only 2 words of the family have parts that spell them" | empty "-" suffix part → a stray "+"; no origin beat (AI left it empty); suffix words split by base word (decide + sion); meanings too long |
| v2 (`Gốc từ v2`) | 92.2 s, origin beat "Gốc Latin · premere = ấn, ép", no stray "+" | 76.6 s | the AI skipped `picture` for all words but the quiz (optional field); a suffix family marked the base, not the suffix, in green; "-tion / -sion" did not match the checked list (no origin) |
| v3 (`Gốc từ v3`) | 82.2 s, every word drawn, origin beat | 122.6 s, every word drawn, origin "-tio", TION in green, splits deci + sion / educat + ion / adop + tion | one Vietnamese sentence had Chinese characters in it (now stripped) |

Fixes: `1c26aa1` (fitted splits, checked origins, required pictures, the family's own part in green, shorter meanings
and clues) and the CJK clean-up in this task's commit. Frame sheets: `docs/operations/phase87-screens/`.

Transcript of the first 40 s of v1 (faster-whisper small, Vietnamese): every line present and in order, English
examples clear ("He wanted to express his love to her."); the two-letter prefix "EX" is heard like "S" — for the owner
to judge when listening.

## Tests

Full pytest 2277 passed (18 min; one earlier run had a dashboard browser timeout while two videos were rendering,
which passed alone and in the clean full run); vitest 26 files / 198 tests passed; `tsc --noEmit` clean; ruff clean.

## Not done here

- No build, no install, no push: the owner decides (plan: "build and install after the owner's go-ahead").
- The owner has not listened to the Shorts yet.
