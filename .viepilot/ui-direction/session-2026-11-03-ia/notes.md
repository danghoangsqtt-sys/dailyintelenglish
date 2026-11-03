# UI direction — the studio in five areas (2026-11-03)

Owner (2026-11-03): "Các tính năng Bảng điều khiển + Kế hoạch kênh + Tự động + Short hàng loạt bố cục rời rạc và thiếu
khoa học … Các loại thư viện tách rời như hiện tại thì sao? có gộp được không? … dễ dùng hơn nữa, rõ ràng và không rối
mắt, cân đối giữa kỹ thuật và mỹ thuật, giữa SEO và trải nghiệm người dùng", then "Làm bản mẫu".

Static prototype (sample data, buttons do nothing). Serve the repo root (`python -m http.server 8040`) and open
`/.viepilot/ui-direction/session-2026-11-03-ia/index.html`; images come from `frontend/static`.

## Look (v2, after the owner's "chưa đẹp")

The brand's Canva/CapCut feel (owner 2026-10-06): warm cream page like the banner, white cards, Montserrat headings,
line icons (`icons.svg`) instead of emoji, a light Canva-style rail with one green "+" create button. Pictures lead:
video covers as 9:16 posters, the template gallery shows the real example clips' covers, the library shows real
characters, scenes and pictures. Home opens with the channel banner (the teacher on the right, the lettering covered
by a cream wash). Green marks the place you are and the one primary action; yellow only marks "needs you".

## Look (v3, after a second "chưa đẹp")

v2 was all beige (page, covers, stats) and its banner crop showed a lone giant face; the 9:16 posters were too big and
their tiny in-video text looked busy. v3: Home opens with a brand-green hero and a waving presenter cut-out from the
character library, a round quick-create row (Canva's "what will you make"), "Cần bạn" as cards with a small cover
beside the reason and the actions, and a week strip. A switcher (bottom right) compares three colour directions on
every page: **Sáng** (neutral light), **Tối** (CapCut-like dark), **Kem** (v2's cream).

**Owner picked Sáng (2026-11-03).** The switcher and the other two palettes are gone. Tạo video now opens with a
search band and round category buttons like Canva, templates are smaller posters (6-7 a row); Video của tôi puts the
"Cần bạn" cards first, then all videos as a poster grid; the calendar covers are larger.

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
| `style.css`, `icons.svg` | shared look (Sáng), line icons | — |
| `pages/home.html` | Hôm nay | Dashboard top, Automation review |
| `pages/create.html` | Tạo video | Step 1 type cards, Shorts batch |
| `pages/channel.html` | Kênh | Channel plan, Automation, Dashboard schedule |
| `pages/videos.html` | Video của tôi | Dashboard project list |
| `pages/library.html` | Thư viện | Character / Activity / Music libraries, voices, brand assets |
| `pages/project.html` | One video | Steps 1–7 as 3 stages, SEO in Đăng |

## Open questions for the owner


- Keep "Tự động" as its own item in the sidebar (some owners like a big on/off), or only inside Kênh as proposed?
- "Video của tôi": v2 shows a poster grid (with a list toggle); keep the grid as default, or the dense table?
- Should the Step 2–6 pages keep their current layout inside the 3 stages for now (smaller change), with only the
  stage bar on top?
