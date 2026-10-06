# Phase 26 — Professional look for the app (UI polish)

**Status:** planned 2026-10-06 (owner request).
**Owner request:** "chỉnh sửa lại giao diện của trang và hệ thống để đẹp và chuyên nghiệp hơn".

## 0. Principles

- **One visual identity with the videos.** The app takes on the brand the owner approved for the
  intro and outro (Phase 25, spike 25.1):
  - the deep-indigo/violet → cyan gradient;
  - the "DI" logo mark;
  - Montserrat for headings and Inter for body text.
- **Look only. No behaviour changes.** Element ids, roles, labels and flows stay, so all 1400+
  tests keep guarding the behaviour.
- **Shared first.** Design tokens and components live in `frontend/static/css/style.css`. Page
  `<style>` blocks shrink to layout only.
- **Light and dark themes both kept.** Contrast is AA or better, and the existing theme toggle is
  kept.
- **Checked by eye:** before/after screenshots of every page, at desktop and narrow width, in light
  and dark.

## 1. Scope

| Area | What changes |
|---|---|
| Tokens | Brand palette (violet `#7C3AED` → cyan `#22D3EE` gradient, indigo surfaces in dark), type scale, spacing scale, radius, elevation, focus ring |
| Typography | Montserrat (already bundled, OFL) for headings and the brand; Inter (or the system UI font) for body text |
| App chrome | A shared top bar with the DI logo mark + wordmark, consistent page headers, step navigation styled as a progress rail |
| Components | Buttons (primary gradient, ghost, danger), inputs/selects, cards, badges/chips, tabs, messages/toasts, empty states, progress bars, tables |
| Dashboard | Hero header, project cards with status chips and step progress, quick links (Music, Characters, Settings) |
| Workflow steps 1–7 | Consistent section headers, card spacing and inspector panels; no layout rewrites |
| Library pages | Characters, Music, Settings brought in line |

## 2. Tasks

| Task | What | Accept when |
|---|---|---|
| 26.1 | Audit: screenshots of all 11 pages (light/dark, desktop/narrow); list the inconsistencies | report + screenshots |
| 26.2 | Design tokens + typography + shared components in `style.css`; shared top bar/logo | all pages pick them up; tests green |
| 26.3 | Dashboard + step pages polish | before/after screenshots; tests green |
| 26.4 | Library and Settings pages polish | before/after screenshots; tests green |
| 26.5 | Owner review (Gate B-19) | owner OK |
