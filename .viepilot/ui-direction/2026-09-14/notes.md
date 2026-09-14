# Daily Intel English Studio — UI Direction Notes

Session: `2026-09-14`
Mode: multi-page UI direction
Target: desktop web app, 1440×900 recommended; existing app already enforces `min-width: 1024px` on `body` (see `frontend/static/css/style.css:42`) — this direction keeps that floor.
Responsive strategy: same as the shipped app — reflow down to 1024px only, not a phone-first product (per `.viepilot/ROADMAP.md` Task 2.3d, already verified at 1024px for the current UI).

## Why this session exists

User feedback (2026-09-14): current UI is "too plain / unprofessional," dark-only, insufficient text/background contrast, and the user — accustomed to video-editing tools (CapCut, Camtasia) — wants that workspace paradigm instead of 7 disconnected wizard pages. User pointed at their own in-progress project `D:\DataAdmin\capcap_dubbing\CapCap\.viepilot\ui-direction\2026-09-09\` as a concrete reference.

Separately, the user reported Script/Learning/Audio/Video "not working." **PM verified live against the running app before this session**: created a real project via the running API and called `POST .../script/generate` twice — both times Gemini (`gemini-3.8-flash`) returned a real HTTP 503 "model overloaded, try again later." This is an upstream transient condition, not a defect in this app, and explains the reported cascade (Learning depends on the same Gemini call; Audio/Video depend on Script/Learning existing first). One real gap was found and logged separately (not part of this UI session): the app's retry/backoff only retries on HTTP 429, not 503 — a transient-overload retry is a legitimate future Task 2.2-adjacent item, tracked outside this UI Direction work.

## Source of truth

- Reference layout: `D:\DataAdmin\capcap_dubbing\CapCap\.viepilot\ui-direction\2026-09-09\` (`style.css`, `pages\workspace.html`) — borrowed the **layout paradigm** (topbar + sidebar workflow list + main stage + right inspector, plus a bottom timeline/clip-track), not its dark color tokens.
- Current shipped pages (for id/class continuity so a real implementation can graft onto existing JS with minimal rework): `frontend/pages/dashboard.html`, `frontend/pages/step2_script.html`, `frontend/static/css/style.css`.
- Original product brainstorm: `docs/brainstorm/session-2026-09-10.md`.

## Pages inventory

| Slug | File | Title | Purpose | Key sections | Navigation |
|---|---|---|---|---|---|
| hub | `index.html` | UI Direction Hub | Entry point, links to all 9 built screens | rationale, screen grid | all pages |
| dashboard | `pages/dashboard.html` | Dashboard | Project library / launcher | hero + CTA, filter/search, project card grid | config, workspace-script |
| config | `pages/config.html` | Cấu hình (Step 1) | Create-project form | form fields, chip selectors, inspector live-preview of current selection | dashboard |
| workspace-script | `pages/workspace-script.html` | Workspace — Script (Step 2) | Flagship screen: resizable 3-panel shell + timeline | sidebar (7-step workflow, collapsible), main stage (script lines), bottom timeline (3 tracks), inspector (selected-line editor) | dashboard |
| workspace-learning | `pages/workspace-learning.html` | Workspace — Learning (Step 3) | Vocabulary/idioms/grammar/quiz review | sidebar, tabbed content list, inspector (selected vocab item detail) — no timeline | dashboard |
| workspace-tts | `pages/workspace-tts.html` | Workspace — TTS (Step 4) | Per-line voice generation + mix | sidebar (speakers, background music), main (line list, generation status), timeline (subtitle/voice/music tracks), inspector (speed/pitch/volume) | dashboard |
| workspace-video | `pages/workspace-video.html` | Workspace — Video (Step 5) | Render preview + review | sidebar (background templates), main (video preview frame), timeline (video/subtitle/audio tracks — closest to the reference screenshot), inspector (selected subtitle cue) | dashboard |
| thumbnail | `pages/thumbnail.html` | Workspace — Thumbnail (Step 6) | Variant gallery + editor | sidebar (templates), main (variant grid), inspector (edit selected variant: headline/colors/aspect) — no timeline | dashboard |
| youtube | `pages/youtube.html` | Workspace — YouTube (Step 7) | Package review + export | sidebar (step nav only), main (titles/description/chapters), inspector (export-readiness checklist + zip download) — no timeline | dashboard |
| music-library | `pages/music-library.html` | Music Library | Cross-project shared utility | single-column layout (NOT the 3-panel shell — deliberate, see decision 11) | dashboard |

Inventory invariant: every HTML file in the pages directory appears exactly once above, and every row resolves to an existing file. **All 9 real app pages now have a corresponding mockup** (user approved the Revision-2 direction on 2026-09-14 and asked to complete the remaining set immediately).

## Key UX decisions

1. **Keep the existing multi-page architecture** (separate HTML file per step, vanilla JS, no SPA framework) rather than merging steps into one client-side view. Rationale: the app already has tested, non-trivial per-page async-safety machinery (double-submit locks, coalesced trailing autosave, dirty-navigation guards — CR-06/`SYSTEM-RULES.md`) built around page-load boundaries; collapsing to a true SPA would be a rewrite far beyond a "redesign the visuals" request and would risk every one of those 493 passing tests. Instead, every step page shares one **persistent-look shell** (same topbar, same sidebar workflow list, same inspector pattern) via the shared `style.css` — visually one continuous app, technically still one page per step, same pattern CapCap itself uses (6 separate real HTML files, one shared shell).
2. **Sidebar workflow list replaces the current horizontal `StepNav` pill row.** Same underlying data (7 steps, current step, done/active state) — `frontend/static/js/step_nav.js`'s `StepNav.render()` logic can be reused, only its rendered markup/CSS target changes from a horizontal pill bar to this vertical sidebar list.
3. **Inspector panel is new** — no current page has a dedicated side panel. It's populated by whatever is "selected" in the main stage (a script line, later: a TTS speaker row, a thumbnail variant, a YouTube section). For Script specifically, it replaces the current pattern of "click text inline to edit in place" with "click a line → edit its full detail in a stable side panel" — a real interaction change the user should confirm before Codex builds anything (see Open questions).
4. **Timeline clip-track is decorative + navigational, not a real audio/video editing timeline** — the app has no scrubbable media at the Script step. It renders the same script lines as small clickable "clips" (color-coded by speaker, same visual language as the reviewed CapCap track) purely so the screen *reads* like a familiar editor, and to make jumping between many lines faster than scrolling a long card list. At the Video Studio step (Step 5) this can evolve into a literal timeline once real audio/video timestamps exist (`AudioService`'s real per-line timestamps already exist — see `app/services/audio_service.py`).
5. **Contrast is deliberately GitHub-Primer-like, not pastel.** Muted text (`--muted: #495164`) on white is ~7.5:1 contrast — far above the WCAG AA 4.5:1 floor most "light theme" apps stop at, directly answering "chữ và nền phải tương phản rõ nét." Status colors (`--success`, `--warning`, `--danger`) are darkened versions chosen to stay readable as *text*, not just as a background wash — pastel yellow-on-white (a common light-theme mistake) was deliberately avoided for `--warning`.
6. **Dark mode is not removed** — the existing `theme.js` toggle stays; this session only redefines what the *default*/primary theme should look like. The icon-toggle in these mocks is present but shown in its "switch to dark" state, implying light is now the default.

## Design tokens

```yaml
color:
  bg: "#FFFFFF"
  bgCanvas: "#F1F3F7"
  surface: "#FFFFFF"
  surface2: "#F7F8FB"
  border: "#D7DCE3"
  borderStrong: "#B9C0CC"
  text: "#12151C"
  textMuted: "#495164"
  accent: "#6425C4"
  accentSoft: "#F1E9FD"
  success: "#146C2E"
  warning: "#8A5B00"
  error: "#B3261E"
  info: "#0757B8"
type:
  family: "Inter, Segoe UI, system-ui, sans-serif"
  base: "14px/1.5"
spacing: [4, 8, 12, 16, 24, 32]
radius: {sm: 6, md: 10, lg: 14, pill: 999}
layout:
  sidebar: 260
  inspector: 340
  minViewport: "1024px+ (matches shipped app floor)"
```

Contrast check (against `--bg: #FFFFFF`): `--text` #12151C ≈ 18.5:1, `--text-2` #2C3242 ≈ 13.6:1, `--muted` #495164 ≈ 7.5:1 — all comfortably above WCAG AA (4.5:1) for normal text, including the "muted" tier that is usually the first thing to fail contrast checks in light themes.

## Out of scope for this direction (so far)

- Learning / TTS / Video / Thumbnail / YouTube / Music Library screens — same shell, not yet mocked; explicitly deferred until Dashboard + Workspace-Script are approved, to avoid building 7 screens on an unapproved pattern.
- Any change to backend/API/DB — pure frontend visual direction.
- The real Gemini-503 retry gap raised alongside this feedback — tracked separately, not a UI Direction concern.
- True SPA rewrite — explicitly rejected in decision 1 above.

## Validation checklist

- [x] Hub opens and links to both built screens.
- [x] Both pages link back toward the hub/dashboard.
- [x] Status colors include a textual label (pill text), never color-only.
- [x] Contrast of text tiers computed against white background, all pass AA.
- [ ] Visual review by user at 1440×900 in an actual browser — pending (artifacts written, not yet opened/screenshotted).
- [ ] Remaining 7 screens mocked — pending user sign-off on the shell pattern first.

## Revision 2 (2026-09-14, same day — user provided a reference screenshot + more specific layout requirements)

User attached a screenshot of a real commercial subtitle/dubbing editor ("ezmaxsub Studio") and asked for: (a) left column holding the entire "create project" flow, resizable/collapsible at will; (b) same for the video-preview column, the subtitle/property-editing column; (c) a bottom timeline for editing video, adjusting subtitles, and inserting background music. User also pointed at the real CapCap Python source (not just its own UI-direction mockup) and suggested checking it directly.

**Source verification done (real code, not assumed):**
- `D:\DataAdmin\capcap_dubbing\CapCap\ui\main_window.py` — confirmed a real `QSplitter` (`self.preview_timeline_splitter`) between the preview area and the timeline: vertical drag, a minimum timeline height is actively enforced (`splitter.setSizes(...)` recomputed whenever the window resizes so the timeline never gets squeezed below its usable minimum), and the splitter's drag handle is explicitly disabled while a video is playing (`splitter.handle(1).setEnabled(not review_mode)`) so an accidental drag can't disrupt playback. The left panel is a scrollable fixed container synced to its own width (`sync_left_panel_container_width`), not a drag-splitter — i.e. even CapCap's own real app doesn't make every single panel a splitter.
- Web research on video-editor panel architecture and on implementing resizable split-panes in plain JS (queries run 2026-09-14; sources below) confirmed the standard pattern: a flex row of panes separated by a thin drag "gutter"; JS rewrites `flex-basis` on only the pane being dragged (the sibling pane is `flex:1 1 0` and just absorbs the rest); per-pane min/max constraints; keyboard-accessible separators (`role="separator"`, arrow keys); and — specifically for timelines — pin-to-bottom with independent vertical resize, since "the timeline is the operational center of the product, not just another panel."

**Decisions added:**
7. Implemented **real, working drag-to-resize** in the mockup (not a static picture of a resize handle) — `pages/workspace-script.html` now has functional pointer-event-driven resizers between sidebar↔main and main↔inspector (vertical drag) and above the timeline (horizontal drag), each with sensible min/max (sidebar 56–420px, inspector 260–480px, timeline 110px–70vh). Open it in a real browser and drag the thin bars between panels to verify the feel directly, the same way you'd verify code by running it.
8. **Sidebar collapses to an icon rail (56px), not to zero** — click "⟨⟨ Thu gọn" or drag it all the way down. Matches "cột trái ... thu gọn tuỳ ý" without losing the ability to still see which step is active (a fully-hidden sidebar with no icons would lose that).
9. **Timeline is now 3 real tracks**, matching what this app actually has (not invented capability): 📝 Phụ đề (script lines, reuses the same clip element from Revision 1), 🔊 Giọng đọc (one clip per synthesized TTS line — maps to `app/services/tts_service.py`'s per-line audio), 🎵 Nhạc nền (one long clip — maps to the existing Music Library feature + `audio_service.py`'s background-music ducking, already shipped in Task 1.6b). No 4th "video" track was added here because Script step has no video yet — Step 5 (Video Studio) is where a real video/frame track belongs.
10. Did **not** implement full dockable/rearrangeable panels (drag a panel to a totally different position, float it, etc.) — web research explicitly flagged that as something that "can feel overwhelming" and "confusing" if over-implemented, and it's not what CapCap's own real, shipped app does either (CapCap only splitters preview↔timeline; its left panel is fixed-position, just resizable/scrollable). Resize + collapse on 3 fixed regions matches the reference screenshot's actual behavior without over-engineering.

Sources consulted:
- [Web-Based Video Editor Architecture — React Video Editor](https://www.reactvideoeditor.com/blog/web-based-video-editor-architecture)
- [Designing A Timeline For Mobile Video Editing — IMG.LY](https://img.ly/blog/designing-a-timeline-for-mobile-video-editing/)
- [Timeline UI Design: Patterns, Examples & UX Tips — Eleken](https://www.eleken.co/blog-posts/timeline-ui-design)
- [Building a resizable split view from scratch — DEV Community](https://dev.to/dev48v/building-a-resizable-split-view-from-scratch-one-number-pointer-capture-and-the-aria-separator-1pe4)
- [Creating Resizable Split Panes from Scratch — OpenReplay](https://blog.openreplay.com/resizable-split-panes-from-scratch/)

## Revision 3 (2026-09-14, same day) — user approved direction, remaining 7 pages built

User: "tôi thấy khá ổn rồi đấy anh bạn" (satisfied with the 2-screen direction) and asked to build the remaining pages immediately rather than pause for a separate implementation-scoping round.

**Open questions 1 and 3 resolved:**
- **Q1 (inline vs. inspector editing) — PM decision, user explicitly deferred ("tôi không biết chọn cái nào"):** kept **both** — inline click-to-edit stays exactly as today's real `step2_script.js` behavior (lowest risk: doesn't touch the tested autosave/dirty-state machinery), and the inspector panel is additive, surfacing secondary actions (listen, regenerate-this-line, language notes) that today live awkwardly inline. Same hybrid pattern applied consistently to Learning (inspector = vocab item detail) and TTS (inspector = per-line voice sliders) rather than inventing a different split per page.
- **Q3 (timeline scope) — user confirmed the recommended option:** timeline tracks only exist on `workspace-script.html`, `workspace-tts.html`, `workspace-video.html`. Config, Learning, Thumbnail, YouTube, Music Library have no timeline element at all — confirmed by grepping each page's real HTML/JS ids before mocking it (see Pages inventory) rather than assumed.

**New decisions from completing the full set:**
11. **Music Library deliberately does NOT use the 3-panel shell.** It's a cross-project utility (accessible from Step 4/5, not itself part of the 7-step sequence) — forcing a "which step is this" sidebar onto it would be fake chrome. It keeps a Dashboard-like single-column layout instead. This was a judgment call, not something the user specified; flagged here so it can be challenged.
12. **Shared resize/collapse behavior extracted into `shell.js`**, mounted the same way on every page (`WorkspaceShell.init({...})`) — mirrors how the real app already shares `step_nav.js`/`keyboard_shortcuts.js`/`save_indicator.js` across pages, so a real implementation would follow the exact same file-organization precedent, not a new one.
13. **Inspector content is page-specific, not a generic "properties panel"**: Script → line editor, Learning → vocab detail, TTS → voice sliders, Video → subtitle cue, Thumbnail → the actual variant editor (colors/headline/aspect — this ties: the current real `/step6` already has this exact editor, just relocated from center-column to the inspector rail), YouTube → export-readiness checklist (a genuinely new grouping — today's real page has no equivalent single checklist, it's implied by which buttons are enabled).

## Open questions (remaining — need user/PM decision before Codex implements anything)

1. ~~Inline vs inspector editing~~ — resolved above (Revision 3).
2. **Scope for this redesign as a real implementation task**: reskin CSS tokens only (fast, low risk, all 9 pages, no interaction changes) vs. rebuild every page's HTML structure into the resizable sidebar+stage+inspector(+timeline) shell (slower, touches every page's JS wiring — especially the 3 pages gaining a genuinely new inspector grouping — and needs new regression tests alongside the existing 493, e.g. for drag-resize and collapse behavior) — **this is the next real decision needed** before any `.viepilot/phases/02-testing-polish/` (or new Phase) task card is written. Full-shell is clearly what was asked for and approved, but PM should confirm the user wants it done in one task vs. incrementally per page.
3. ~~Timeline scope~~ — resolved above (Revision 3): Script/TTS/Video only.
4. YouTube's inspector introduces a checklist grouping that doesn't exist in the real page today (see decision 13) — confirm this is wanted as new information architecture, not just a visual reskin, same class of question as the original Q1.
