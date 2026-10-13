# Daily Beyond English Studio — Final Project Report

**Version:** 1.3.0 · **Closed:** 2026-10-13 · **Branch:** `owner-runs/20261001-r9`

## 1. What was built

A local web studio that turns a topic into a finished English-learning episode for the **Daily Beyond English**
YouTube channel (Vietnamese learners), in seven steps:

1. **Script config** — topic, CEFR level (A1–C2), length, 2–6 speakers chosen from character profiles, genre, accent.
2. **AI script** — cloud-first generation (Gemini 3.1 Flash-Lite → OpenRouter free models → local qwen on the RTX
   3060), section by section with length, repetition and speaker-balance repairs; inline edit, per-line regenerate.
3. **Learning pack** — vocabulary, idioms, collocations, phrasal verbs, sentence patterns, grammar and a listening
   quiz, with Vietnamese meanings.
4. **Audio** — Edge TTS with per-word timings, loudness-normalised mix, a background bed chosen by topic and pace,
   ducked under the voice.
5. **Video** — one Remotion (React/TypeScript) renderer: talking characters (visual-novel sprites with lip-sync,
   expressions, gestures, man left / woman right), storyboard beats, the Scene, Shot and Activity libraries,
   illustrations drawn on the local GPU or made with an outside AI, word-level karaoke captions, vocabulary cards,
   branded intro and outro; **and** a vertical 1080x1920 episode plus AI-proposed Shorts/TikTok highlight clips.
6. **Thumbnail** — the episode's characters over its picture with a headline, CEFR badge and logo, or an
   outside-AI picture; 16:9 and 9:16.
7. **YouTube package** — titles, an SEO description within 5,000 characters, hashtags, the transcript as the
   pinned comment, chapters, the music credit; copy buttons and a .zip export.

Around the pipeline: a **Channel plan** (topics → series → numbered episodes, an AI channel map and a rotating
two-week calendar), a **channel cockpit dashboard** (stats, Today, a 5-stage roadmap, a Kanban board), the
Character, Shot, Activity and Music libraries, Settings, and a standalone Windows `.exe`.

## 2. Timeline

| | Plan | Actual |
|---|---|---|
| Start | 2026-09-10 | 2026-09-10 |
| Original scope (Phases 1–3: build, test, document) | 21 days, by 2026-09-30 | done **Day 6** (2026-09-15, `v1.0.0-beta`) |
| Whole project (37 phases, owner-added scope) | — | **34 calendar days, 30 working days**, closed 2026-10-13 |

Releases: `v1.0.0-beta` 2026-09-15 · `v1.1.0-beta` 2026-09-26 (cloud-first AI) · `v1.2.0-beta` 2026-10-05
(Remotion video) · **`v1.3.0` 2026-10-13** (visual studio, publishing package, channel plan, Shorts/TikTok).

Phases 4–37 came from the owner's requests and independent audits after the original plan was complete, decided
in recorded brainstorm sessions (decisions D1–D108, `docs/brainstorm/`).

| Period | Phases | Theme |
|---|---|---|
| 09-10 → 09-15 | 1–3 | Full pipeline, tests, docs (`v1.0.0-beta`) |
| 09-16 → 09-18 | 4–12 | Polish, three audits' fixes, Settings, `.exe` packaging |
| 09-18 → 09-26 | 13–18 | AI reliability: local AI, gateway, stability, cloud-first chain (`v1.1.0-beta`, 2.8× faster scripts) |
| 09-28 → 10-05 | 19–24 | Remotion video, AI visuals, music, scenes, storyboard (`v1.2.0-beta`) |
| 10-05 → 10-12 | 25–34 | Brand, rebrand, picture style, shot library, podcast modes, Alex & Lina, talking characters, profiles v2, hygiene |
| 10-13 | 35–37 | Legacy cleanup, YouTube package + channel plan + cockpit, Shorts/TikTok |

## 3. Results in numbers

| Measure | Value |
|---|---|
| Commits | 720+ over 30 working days |
| Phases | 37: 35 complete (7 older gates closed by owner decision D109), 1 closed won't-fix (better TTS); Phase 37 waits for Gate B-25 |
| Owner decisions recorded | 109 (D1–D109) |
| Requests tracked | 30 bugs, 30 enhancements (all closed except ENH-015, deferred) |
| Backend | 98 Python modules (~22,000 lines), 15 API routers, 24 SQLite migrations |
| Frontend | 13 pages, vanilla HTML/CSS/JS (~12,600 lines) |
| Renderer | Remotion 4 / React 19 / TypeScript (~2,600 lines) |
| Tests | **1,686 pytest** (unit, API, Playwright browser) + **70 Vitest**, all passing; Ruff clean |
| Script generation | ~45 s median for a B1 8-minute script (cloud-first) vs ~127 s local |
| Rendering | an 8-minute episode in a few minutes on the RTX 3060 machine; a 45 s Short in ~46 s |

## 4. Quality and acceptance

- **Measured gates:** B-2 to B-13 checked scripts, AI reliability and speed, and media against real runs (reports in
  `docs/operations/`).
- **Owner sign-offs:** B-18 (brand intro/outro), B-22 (talking characters), B-23 (character profiles v2, "video rất
  tốt"), B-24 (YouTube package and a real 3-episode series).
- **Independent audits:** three `/vp-audit` passes during the project and this close-out audit (§5).
- **Real-AI lesson:** cloud models rename JSON fields; every AI output now passes through a normaliser and every
  prompt shows the exact JSON shape.
- **Data safety:** every migration on the real database was preceded by a backup (`data/backups/`); rehearsals ran
  on a sandbox copy (port 8010).

## 5. Close-out audit (2026-10-13)

- **Source:** no TODO/FIXME, no debug prints or `console.log`, no unreferenced modules, pages, scripts or prompts;
  every dependency in `requirements.txt` is imported; leftover mentions of removed features are only the
  compatibility mapping and old migrations. Ruff lint clean.
- **Fixed:** BUG-025 (a scene lookup hid database and disk errors) with regression tests.
- **Records:** stale request statuses reconciled (ENH-012..ENH-023, ENH-014 already done in `5475e3e`); roadmap
  headings for Phases 33, 35, 36 corrected; the missing `v1.2.0-beta` tag created.
- **Layout:** loose guides moved to `docs/user/`, reports to `docs/report/`; 19 redundant `.gitkeep` files and the
  unused `prompts/tts/` removed; 74 MB of Gate B-12 evidence videos taken out of the tree (kept in git history).
- **Not touched without the owner's say-so:** `data/` (real episodes, libraries, backups), `models/` (29 GB of
  local AI models), `venv/` and `venv-image/`, the built `dist/` app, and local scratch folders (§6).

## 6. Open items

| Item | State |
|---|---|
| Gate B-25 (Phase 37) | Built and rehearsed on the sandbox (the real AI proposed 3 good clips; one rendered with hook banner, captions, cover and texts). Needs the real app restarted for migration 024, then the owner reviews real clips. |
| Gates B-14, B-15, B-16, B-17, B-19, B-20, B-21 (Phases 20, 22, 23, 24, 27, 28, 29) | **Closed by owner decision D109** (2026-10-13): their features (characters, scenes, storyboard, music bed, brand, picture style, libraries) are part of every episode accepted at B-22, B-23 and B-24. |
| ENH-015 | Deferred: tune the section prompt so Gemini's first pass hits its length (saves calls); needs real-call measurement. |
| Known limits | Edge TTS is the only voice (better engines failed the owner's listening tests); the local GPU draws one picture at a time; publishing to YouTube/TikTok is copy-and-paste (no upload API). |

## 7. Suggested next steps

1. Close Gate B-25 on real clips, then post the first Shorts and measure retention.
2. Use the Channel plan to keep a weekly rhythm (one full episode + 2–3 Shorts).
3. ENH-015 prompt tuning when quota allows; consider YouTube Data API upload once the channel is verified.
