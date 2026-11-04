# Phase 96 state

Status: implemented_verified (2026-11-04, sandbox). Not installed or pushed.

| Task | Scope | Status |
|---|---|---|
| 96.1 | Word of the day | done — real video, English and Vietnamese |
| 96.2 | Shared picture tools | done — `short_pictures.py`: draw, library stand-in, redraw, upload |
| 96.3 | Pilot pictures for C | done — owner: "okey ổn rồi đấy tiếp tục" |
| 96.4 | A picture for each sentence | done — real videos (beach, cooking rice) |
| 96.5 | What is this called? | done — real video; a silent 1-2-3 after the question (owner's correction) |
| 96.6 | Basic vs Advanced | done — real video; no presenter, real-moment pictures (D156, D157) |
| 96.7 | Finish | done — sample clips, labels; full pytest 2379 passed, Vitest 212 passed |

Known limits: nothing detects a wrong picture (an extra arm, writing on a sign, an odd action): a person must look, then Draw again or
Upload on Step 5. The AI's phrases and sentences can be weak; the story rule asks for one ordinary task in real order, and they can be
edited on Step 5. The upload and redraw buttons were covered by unit tests and seen on the page, not clicked through in a browser test.
