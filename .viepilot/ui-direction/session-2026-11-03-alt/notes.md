# UI direction — three new directions for Home (2026-11-03)

Owner, after the studio-sidebar prototype (`../session-2026-11-03-ia/`): "giao diện quá nhiều khoảng trống, chữ thì nhỏ,
bố cục không hợp lý", then "Không chốt giao diện này, tạo lại giao diện khác đi".

Three Home screens, each a different idea, all filling a 1920×1080 screen with 16px body text and no empty sidebar.
A switcher at the bottom moves between them. Serve the repo root (`python -m http.server 8040`) and open
`/.viepilot/ui-direction/session-2026-11-03-alt/a-board.html`. Lina's frames come from
`../session-2026-11-03-ia/mascot/build_lina.py` (run it once if `mascot/lina/` is missing).

| File | Idea | Lina |
|---|---|---|
| `a-board.html` | **Production board**: green top bar, every video as a card in five columns (Ý tưởng → Nội dung → Sản xuất → Chờ bạn duyệt → Đã lên lịch), like Trello | a chat panel on the right: messages, buttons, her half body at the bottom, a box to message her |
| `b-studio.html` | **Dark studio** like CapCut: icon rail, queue on the left, the selected video big in the middle, its steps and publish box on the right, the week as a two-track timeline at the bottom | stands beside the player and points at the video |
| `c-bento.html` | **Bright tiles** (bento) like Apple / Notion homes: top bar, one screen of tiles: videos to review (large), Lina, the week, work in progress, quick create | her own green tile, waving, with two buttons |

Content kept from the earlier work: the five areas, the 7 steps in 3 stages, no repeated numbers, Lina as the mascot.

## Owner's answers after A–C ("vẫn rất xấu", 2026-11-03)

- Worst: **layout and type size** (not the colours, covers or mascot).
- Likes: **Canva, Notion / Linear, Duolingo**.
- Mascot: **Lina**.

Direction D (`d-friendly.html`) follows those: Canva's labelled left nav with coloured icons, a big gradient search band
with template chips; Notion/Linear's one clear type scale (34/26/20/17 px, Nunito for headings) on an 8 px grid;
Duolingo's round bold face, chunky buttons with a solid bottom edge, a red count badge, a streak line, Lina inside the
band with her own speech column. Checked at 1920×1080 and 1366×768. Nunito comes from Google Fonts in the prototype
(the app would ship the font file).

## Pages inventory

| File | Purpose |
|---|---|
| `base.css` | shared basics and the direction switcher |
| `a-board.html` | direction A, Home |
| `b-studio.html` | direction B, Home |
| `c-bento.html` | direction C, Home |
| `d-friendly.html` | direction D, Home (Canva + Notion + Duolingo) |

## Open question for the owner

- Which direction (A, B or C), or which parts of each? Then the other pages are built in that direction.
