# UI direction — the studio in five areas (2026-11-03)

Owner (2026-11-03): "Các tính năng Bảng điều khiển + Kế hoạch kênh + Tự động + Short hàng loạt bố cục rời rạc và thiếu
khoa học … Các loại thư viện tách rời như hiện tại thì sao? có gộp được không? … dễ dùng hơn nữa, rõ ràng và không rối
mắt, cân đối giữa kỹ thuật và mỹ thuật, giữa SEO và trải nghiệm người dùng", then "Làm bản mẫu".

Static prototype (sample data, buttons do nothing). Serve the repo root (`python -m http.server 8040`) and open
`/.viepilot/ui-direction/session-2026-11-03-ia/index.html`; images come from `frontend/static`.

## Look (v4, after "chưa chuyên nghiệp và chưa đẹp")

v2 (cream, big posters) and v3 (green hero, round gradient buttons) still read as a consumer app. v4 follows studio
tools (YouTube Studio, Linear, CapCut desktop): a labelled 244px sidebar with the channel at the top, one green
"Tạo video" button and the running series; a top bar with breadcrumbs, search (Ctrl K) and notifications; one 14px
type scale (Inter; Montserrat only for page titles); 8/12px radii; hairline borders and light shadows; neutral grey-green
surfaces ("Sáng", picked by the owner 2026-11-03); green only for the primary action and the current place; amber only
for "needs you". Status is a small dot badge; lists are tables or rows, not big posters. `shell.js` draws the shared
sidebar, top bar and, inside one video, the stage bar and the bottom Back / Next bar.

The one-video workflow keeps the app's seven steps (Config, Script, Learning, Audio, Video, Thumbnail, YouTube) and
groups them in three stages: Nội dung (1–3), Sản xuất (4–5), Đăng (6–7). Each step page has the same frame: title
with autosave, the stage bar, the work in the middle, a helper panel on the right, and one "next" button at the bottom.

## Why (checked in the app)

- The schedule is shown three times (Dashboard "next two weeks", Automation "14 days", Channel plan episode dates).
- Review is in two places (Dashboard "Review the night's videos", Automation "✓ Approve").
- Making videos starts in three places (Dashboard "New project", Shorts batch, Channel plan "Plan with AI").
- The Dashboard holds a 7-step explainer, the production board, the channel roadmap and every project in one long page.
- Libraries are split in three pages; voices live in Step 4 and brand assets in Settings.

## Decisions proposed (for the owner)

1. Five areas + Settings: **Hôm nay**, **Tạo video**, **Kênh**, **Video của tôi**, **Thư viện**.
2. One schedule (Kênh → Lịch) replaces the three; Automation becomes a panel and a tab of Kênh.
3. One way in to make videos (Tạo video) with two modes — one video / many Shorts — sharing the kind cards (grouped by
   purpose: with characters / academic / quick text templates) and their example clips.
4. One Thư viện with tabs: Hình ảnh (activities, line art, scenes), Nhân vật, Âm nhạc, Giọng đọc, Thương hiệu; shared
   search, review state and "used in N videos".
5. A video's 7 steps grouped in 3 stages (Nội dung · Sản xuất · Đăng); the SEO score and checklist live in Đăng, and
   "Video của tôi" shows each video's SEO score.
6. One page frame: title and one primary action at the top, content, an optional right panel; brand green only for the
   primary action and the current place, yellow only for "needs you"; long help text becomes "?" tips.
7. Every existing feature is kept; only where it sits changes.

## Pages inventory

| File | Area | Replaces / gathers |
|---|---|---|
| `index.html` | hub | — |
| `style.css`, `icons.svg`, `shell.js` | shared look (v4), line icons, sidebar + top bar + stage bar | — |
| `pages/home.html` | Hôm nay | Dashboard top, Automation review |
| `pages/create.html` | Tạo video | Step 1 type cards, Shorts batch |
| `pages/channel.html` | Kênh | Channel plan, Automation, Dashboard schedule |
| `pages/videos.html` | Video của tôi | Dashboard project list |
| `pages/library.html` | Thư viện | Character / Scene / Activity / Music libraries, voices, brand assets |
| `pages/flow-1-setup.html` | One video · 1 Thiết lập | Step 1 Config |
| `pages/flow-2-script.html` | One video · 2 Kịch bản | Step 2 Script, line panel |
| `pages/flow-3-learning.html` | One video · 3 Học liệu | Step 3 Learning |
| `pages/flow-4-voice.html` | One video · 4 Giọng đọc | Step 4 TTS Audio Studio, music |
| `pages/flow-5-video.html` | One video · 5 Video | Step 5 Video Studio, beat editor (Phase 90/91), Shorts & TikTok |
| `pages/flow-6-thumbnail.html` | One video · 6 Ảnh bìa | Step 6 Thumbnail |
| `pages/flow-7-youtube.html` | One video · 7 YouTube | Step 7 YouTube package, SEO score |

## Open questions for the owner

- Keep "Tự động" as its own item in the sidebar (some owners like a big on/off), or only inside Kênh as proposed?
- "Video của tôi": v4 shows a table (with a grid toggle); keep the table as default?
- Build the step pages as drawn in `flow-*.html` (bigger change), or first only add the shared frame and the stage bar
  around today's step pages?
