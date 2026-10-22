# PLAN — Phase 72: Audience — international, Vietnamese or both (ENH-054)

Status: execution_authorized 2026-10-22 — the owner asked to plan and build it.

| Task | Scope |
|---|---|
| 72.1 | Data: migration 036 (`channel_series.audience`, `projects.audience`, NULL = inherit); `backend/content/audience.py` — the channel default in `app_settings` (`both`), `resolve(project)` = video › series (through its episode) › channel, the prompt line per audience. API: `GET/PUT /api/audience` (channel), `GET/PUT /api/projects/{id}/audience` (with the inherited value), series patch (`channel` = inherit), the Shorts batch's audience on its series |
| 72.2 | AI: `{{ audience_line }}` replaces "Vietnamese learners" in the 8 prompts (script, outline, learning pack — which still writes both languages — thumbnail, YouTube, Shorts clips, topic ideas, channel plan). YouTube: titles always English; the hook and summary in English (international), Vietnamese (Vietnamese) or English then a Vietnamese line (both); the composed description lists the vocabulary with the English definition, the Vietnamese meaning or both, with Vietnamese headings in the Vietnamese mode |
| 72.3 | Renderer: `learning.audience`; the long video's vocabulary cards and the quick-learning Shorts (word of the day, top 5) show the English definition, the Vietnamese meaning or both; the batch preview follows it |
| 72.4 | UI: Settings → General "Channel audience"; Channel plan series select (Channel default / International / Vietnamese / Both); Step 1 select; Shorts batch select; EN + VI |
| 72.5 | Tests (inheritance, API, prompts, description, renderer in the 3 modes, browser); real renders of a word-of-the-day Short in the 3 modes; full pytest + Vitest + tsc |

Decided at planning (the brainstorm's open questions): news, text-on-blur, quiz and listening Shorts stay as they are; the pinned comment stays (English transcript). A video already rendered shows the new audience after a new render; its YouTube description's vocabulary list follows at once.
