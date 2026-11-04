# Phase 93 state

Status: implemented_verified (2026-11-04, sandbox; not built, installed or pushed). Owner: "Chạy Phase 93" with the defaults D138–D142. Task cards written and committed before code.

| Task | Scope | Status |
|---|---|---|
| 93.1 | Tokens and fonts | done — tokens.css, Baloo 2 + Be Vietnam Pro bundled, palette and base components in style.css, AA contrast kept |
| 93.2 | One rail | done — one list in app_sidebar.js, light rail, phone tab bar, waiting count |
| 93.3 | Hôm nay | done — home.html at /, Lina band from the assistant frames route, waiting / in progress / week |
| 93.4 | Tạo video | done — /create with modes and gallery; Step 1 prefill; the batch page stays its own tab |
| 93.5 | Kênh | done — area tabs Publishing plan / Automation (pages keep their addresses) |
| 93.6 | Video | done — /videos: the project list as table rows (D142) and the production board + roadmap as the second view |
| 93.7 | Thư viện | done — /library: voices and brand; characters, scenes, music as tabs |
| 93.8 | Copy | done — 98 texts and 8 patterns added where not mapped yet |
| 93.9 | Verify | done — full pytest 2360 passed + 3 tests updated for the moved rail items (then passing); new tests 16 |

## Design self-audit (Task 93.9, 10 criteria from Anthropic's interface guidance, 2026-11-04)

| Page | Score | Notes |
|---|---|---|
| Today `/` | 90 | as drawn in direction E; real data; Lina from the library; both themes, phone tab bar |
| Create video `/create` | 89 | as drawn; clips on hover / focus; the area tabs sit above the title (slightly busy) |
| Library `/library` | 86 | voices and brand only; the other tabs are the former pages |
| Videos `/videos` | 86 | the project cards laid out as table rows (same IDs and actions); By step view |
| Channel, Automation, Characters, Activities, Music, Shorts batch, Settings | 72–78 | new tokens, type, rail and area tabs, but their own former layouts |
| Steps 1–7 | 70–75 | new tokens and rail only (the rail now starts collapsed on every step, so Step 1's cards have room); rebuilt in Phase 94 |

Not done from the plan: the redirects of D138 (not needed: the old pages stay as area tabs).
