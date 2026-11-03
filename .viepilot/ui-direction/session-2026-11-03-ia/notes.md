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

## Mascot and less repeated data (v5, owner 2026-11-03)

Owner: the mascot (3D-cartoon young woman, brown wavy hair, round black glasses, heart sticker on the cheek, beige
shirt, jeans, black sneakers) should stand in a screen corner, move softly and talk; "the interface is clean but
still has many problems and much extra data".

- `mascot/stand-900.png` and `mascot/face.png` are cut out of the owner's sheets (plain studio grey removed by
  colour). In the corner she breathes and sways (CSS), hops once when she starts talking, types her line into a
  bubble and reads it aloud when the computer has a Vietnamese voice; one or two buttons act on what she says.
  "Thu nhỏ" folds her into a round face with a dot; a click brings her back. Reduced-motion turns the motion off.
- Each page gives her one short, useful line about that page (what waits for you, what changed, the next step).
  She replaces the welcome banner, the bell and the footer hints.
- In the real app: blinking and mouth movement need extra frames (eyes closed, mouth open, a wave), made with the
  same character-sprite pipeline the talking characters already use; the voice would be the app's own VieNeu voice,
  and the mouth would follow its loudness. Her lines come from the app's state (jobs, reviews, schedule).
- Removed repeats: Home's welcome banner and KPI row (same numbers as the lists below), the sidebar's series list,
  automation box, bell and avatar (all repeated Kênh or Hôm nay), the series line under a video's title, the video
  title in the breadcrumbs, the footer hints, the "Bước 7/7" column, page subtitles that restated the tab counts,
  per-section counts, the "đang bật" tab label, the Series and Tự động panels under the calendar (they have tabs),
  Step 1's second copy of the example clip, and Step 5's "instant preview" note.

## Lina as the mascot (v6, owner 2026-11-03)

Owner: use Lina from the character library, half body like a VTuber, moving between the front view and the turned view;
then "delete every picture of Lina in the high-neck dress" (87 orphan files of an old front set and its generation run
were moved to the Windows Recycle Bin; no database row pointed at them; the 57 pictures the app uses are intact).

- `mascot/build_lina.py` cuts her current front set (calm, blink, 8 gestures, mouth closed/open) and three-quarter set
  (7 expressions, blink, 7 gestures, mouth closed/open) to a half-body frame, scaled by the eye-to-chin distance so the
  head keeps its size when she turns. The frames (`mascot/lina/`, 1.7 MB) are not committed: run the script to rebuild.
- `shell.js`: mouth and blink swap frames at once; a pose or a turn cross-fades with a slight squash. She blinks every
  2.5–6 s (sometimes twice), breathes and sways; while talking she faces you, makes the page's gesture (`data-pose`),
  flaps her mouth with the words and nods; afterwards she turns three-quarter toward the page, sometimes smiles or listens.
  The bubble steps aside 9 s after she stops.
- Still to make for full VTuber smoothness: more mouth shapes and in-between head angles (the Characters page slots).

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
| `style.css`, `icons.svg`, `shell.js` | shared look (v4), line icons, sidebar + top bar + stage bar + mascot | — |
| `mascot/stand-900.png`, `mascot/face.png` | the mascot, cut out | owner's character sheets |
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

- The mascot's name, and whether she reads her lines aloud by default or only when asked.

- Keep "Tự động" as its own item in the sidebar (some owners like a big on/off), or only inside Kênh as proposed?
- "Video của tôi": v4 shows a table (with a grid toggle); keep the table as default?
- Build the step pages as drawn in `flow-*.html` (bigger change), or first only add the shared frame and the stage bar
  around today's step pages?
