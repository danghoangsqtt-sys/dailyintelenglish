# PLAN — Phase 67: review studio on the Automation page (ENH-049)

Status: execution_authorized 2026-10-22 — the owner asked for it directly; the layout follows the request (schedule visible, the made videos, the video on the right with its YouTube texts, review in place). Not a new mode: the Automation page is redesigned, its settings keep working.

Layout (desktop; it stacks on narrow screens):
- **Top — the schedule strip:** the next 14 days as columns (today first), each with the episodes due that day as small cards — the thumbnail when there is one, the title, the kind (Conversation / Solo / VOX / the Short template) and a coloured state: planned · being made (with the step) · waiting for review · needs attention · approved · published. The night window and "next run tonight at 23:00" (or "Running now") above it; Run now / Stop and the settings move into a compact "Schedule settings" drawer.
- **Left — the videos:** a grid of video cards (thumbnail, duration, kind, date, state) with filter chips: Waiting for review · Needs attention · Approved · Published · All. A card for an episode that stopped shows its reason in one line.
- **Right — the review panel (sticky):** the selected video playing (vertical Shorts and 16:9 videos fit), then tabs: **YouTube** (the composed title options, description, tags, hashtags, pinned comment — each with Copy), **Thumbnail** (the chosen one and the other variants), **Script** (the lines), **Details** (series, dates, the automation log of that episode). Actions: **Approve** (marks it reviewed and ready to upload), **Needs changes** (with a note; opens the right step page), **Mark published** (paste the YouTube link — the existing Channel rule), Download MP4 / SRT, Open in Step 5 / Step 7.

| Task | Scope |
|---|---|
| 67.1 | Data + API: migration `035_episode_review.sql` (`channel_episodes.review_status` '' / approved / changes, `review_note`); `GET /api/automation/board?days=14` (the strip: days → episodes with state, step, kind, thumbnail URL; the videos: every episode with a project, its video state, duration, thumbnail URL, last automation message, review status) and `PATCH /api/channel/episodes/{id}` accepts `review_status` / `review_note` |
| 67.2 | Frontend: the Automation page rebuilt as the review studio (strip, grid, panel) using the existing video, thumbnail, YouTube and script APIs for the panel; the old settings and report kept in the drawer and a "Run log" tab; light/dark themes; Vietnamese strings |
| 67.3 | Tests: board API states and dates, review PATCH rules, browser test (strip shows the dated episodes, filter chips, selecting a card plays its video and shows the YouTube texts with Copy, Approve updates the card), a screenshot check in the sandbox with the real batch videos; full pytest + Vitest |

Kept: Automation behaviour, settings, the Channel plan and the step pages unchanged; nothing uploads to YouTube. No version bump; CHANGELOG `[Unreleased]`.

## Amendment A — the studio look (owner 2026-10-22)

Owner: "sửa và bố cục lại trang TỰ ĐỘNG đẹp và trực quan chuyên nghiệp hơn như một studio". Execution authorized; same data and APIs, a new layout:

| Task | Scope |
|---|---|
| 67.A1 | **Studio bar** (dark brand band): title, a live **On/Off switch** (saves `enabled`), the next run ("Tonight 23:00–06:00 · up to 2 videos" / "Running: <episode> — <step>"), Run now (primary), Stop, ⚙ Settings. **KPI tiles**: due in 14 days · being made · waiting for review · needs attention · published — a tile click filters the library |
| 67.A2 | **Calendar**: day columns with the weekday and a big date number, today highlighted, a count, the episodes as thumbnail chips with a coloured state edge; arrow buttons scroll it. **Library**: cards with the state badge and the duration on the thumbnail, the kind as a chip, a play overlay on hover; segmented filters with counts |
| 67.A3 | **Monitor** (dark, like an editor's program monitor): the player on black, the title and a state badge, the action bar right under the video (Approve · Needs changes · Mark published with the link · MP4 · Step 7), then the YouTube / Thumbnail / Script / Details tabs with tidy copy cards |
| 67.A4 | **Settings slide-over** from the right (schedule form, queue, run log) instead of the bottom drawer; light and dark themes; Vietnamese strings; tests updated (the drawer opens from ⚙), full pytest + Vitest; screenshots at 1024 / 1440 px |
