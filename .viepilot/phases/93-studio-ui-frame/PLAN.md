# Phase 93 — The new studio look: frame and main areas (2026-11-04, planned)

Owner (2026-11-03): "Các tính năng Bảng điều khiển + Kế hoạch kênh + Tự động + Short hàng loạt bố cục rời rạc và thiếu
khoa học … Các loại thư viện tách rời … dễ dùng hơn nữa, rõ ràng và không rối mắt", then after many prototype rounds
"tôi muốn thiết kế lại giao diện và muốn điểm tối thiểu là 90", "Làm tiếp" (direction E for every page) and
"Lập kế hoạch" (2026-11-04).

Approved look: `.viepilot/ui-direction/session-2026-11-03-alt/e/` (12 pages, self-scored 91/100 on Anthropic's interface
guidance; notes in `../notes.md`). This phase builds its frame and main areas in the real app; Phase 94 builds the seven
step pages and Lina in the app.

## Today

- 15 pages (`frontend/pages/*.html`), each with its own copy of the sidebar markup (8 links: Dashboard, Channel plan,
  Automation, Shorts batch, Character / Activity / Music libraries, Settings), `app_sidebar.js` (collapse, drawer),
  `theme.js` (dark / light), `style.css` + `studio.css` (781 lines), Inter and Montserrat.
- The dashboard holds the cockpit numbers, "Start here", the production board, the two-week schedule and every project.
- Review of night videos is on Automation; new videos start on the dashboard, the Shorts batch page or Channel plan.

## Decisions (defaults; the owner may change them)

- **D138 — five areas + Settings:** Hôm nay (`/`), Tạo video (`/create`), Kênh (`/channel`, with tabs Lịch đăng · Series ·
  Tự động), Video (`/videos`), Thư viện (`/library`, with tabs Nhân vật · Cảnh và hình · Giọng đọc · Nhạc · Thương hiệu).
  Old addresses keep working: `/automation` → `/channel#auto`, `/shorts-batch` → the "Nhiều Short cùng lúc" mode of
  `/create` (the same page and script, moved), `/characters`, `/activities`, `/music` → their Thư viện tab. No feature is
  removed; only where it sits changes.
- **D139 — direction E tokens in one file** (`tokens.css`): light and dark, one accent (brand green), separate state
  colours (amber waiting, red error, blue running), tinted neutrals; Baloo 2 headings and Be Vietnam Pro body text
  (both SIL OFL, shipped as local font files so the desktop app works offline), 16 px body, the 40/30/24/17 px scale.
  Every page reads colours from the tokens; the theme toggle keeps working.
- **D140 — one shared rail** drawn by `app_sidebar.js` from one list (no more 15 copies of the markup); under 860 px it
  becomes a bottom tab bar; the `#app-sidebar` id and the theme toggle stay.
- **D141 — Home shows only what needs you or is moving:** Lina's band (summary + "Duyệt N video" + the next-topic box),
  Chờ bạn duyệt (review rows, from Automation's review list and projects needing a fix), Đang làm (running jobs with the
  7-step strip), Tuần này (the channel's slots); the project grid moves to Video. Numbers appear once.
- **D142 — Video is a table by default** (state, 7-step strip, SEO score, schedule or views), a "Theo bước" board view
  as the second option, rows stack on phones.

## Tasks

1. **93.1 Tokens and fonts** — `frontend/static/css/tokens.css` (new), Baloo 2 + Be Vietnam Pro font files and OFL
   texts in `frontend/static/fonts/`, base components (button incl. the chunky primary, panel, row, state pill, tabs,
   chips, segmented control, inputs, focus ring, reduced motion) restyled in `style.css` / `studio.css` from the tokens.
2. **93.2 One rail** — `app_sidebar.js` draws the rail and the phone tab bar from one list (D138, D140); every page's
   sidebar markup becomes one empty `<aside id="app-sidebar">`; redirects for the old addresses in `backend/main.py`.
3. **93.3 Hôm nay** — `dashboard.html` / `dashboard.js` / `dashboard_channel.js` rebuilt as D141 from the existing APIs
   (projects, automation review, jobs, channel schedule); Lina's band uses her front calm / wave / blink frames
   (cut by the Phase 94 helper; until then a still frame).
4. **93.4 Tạo video** — new `/create` page: the two modes (one video → Step 1 with the kind chosen; many Shorts → the
   Shorts batch flow moved here), the template gallery with the Phase 92 clips (`template_samples.js` reused), filters.
5. **93.5 Kênh** — `channel.html` gains the tabs: Lịch đăng (the week as Short / long-video lanes), Series (today's
   channel plan), Tự động (today's Automation page content, moved; its review list now also feeds Home).
6. **93.6 Video** — new `/videos` page: tabs by state, search and filters, the table (D142), the board view.
7. **93.7 Thư viện** — new `/library` hub with tabs; the character, activity (scenes and pictures) and music pages
   become tab content in the shared frame; voices list (from the voice catalogue) and the brand box (from Settings).
8. **93.8 Copy** — English base strings and their Vietnamese in `i18n_vi.js` for every new label.
9. **93.9 Verify** — browser tests: every page has the rail, no sideways scroll at 375 px, light and dark tokens apply,
   keyboard focus visible, old addresses redirect, all existing browser tests pass (IDs kept); full pytest; a design
   self-audit against the 10 criteria (target ≥ 90); the owner's look in the sandbox.

Task cards are written when the phase starts. Phase 94 (steps 1–7 and Lina) follows: [plan](../94-studio-ui-steps-lina/PLAN.md).
