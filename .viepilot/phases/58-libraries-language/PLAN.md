# PLAN — Phase 58: Character / Music / Settings rework and app language (ENH-040)

Status: execution_authorized 2026-10-22 — the owner chose the four designs (language EN + VI with English by default; character profile tabs; compact music list with one player; Settings left menu).

| Task | Scope | Depends on |
|---|---|---|
| [58.1](tasks/task-58.1.md) | Language layer: `i18n.js` (exact-text dictionary + patterns, attributes, MutationObserver, `translate="no"` content), `i18n_vi.js` dictionary, top-bar EN/VI switch, loaded on all 13 pages | — |
| [58.2](tasks/task-58.2.md) | Settings: left menu General · AI · AI providers; language and theme in General; provider status dots | 58.1 |
| [58.3](tasks/task-58.3.md) | Character Library: fixed profile header + tabs Conversation pictures · Presenter pictures · Voice · Details | — |
| [58.4](tasks/task-58.4.md) | Music Library: upload button, compact list with search + mood chips, one shared player, side edit panel, missing-licence flag | — |
| [58.5](tasks/task-58.5.md) | Vietnamese dictionary coverage pass over every page; verification (full pytest + renderer, screenshots EN/VI, light/dark) | all |

One session, sequential. No version bump; CHANGELOG `[Unreleased]`.

Design of the language layer: the pages keep their English source text (tests and server messages stay English). `i18n.js` runs after the page builds its DOM and on every DOM change: a text node or `placeholder`/`title`/`aria-label` whose trimmed English text is a dictionary key is replaced; regex patterns cover texts with numbers ("Step 2 of 7", "29 pictures"). Elements marked `translate="no"` (script lines, names, titles, voices, user text) and form values are never touched. The choice lives in `localStorage` (`dbe.lang`, default `en`); English mode does nothing at all, so the default app is byte-for-byte today's behaviour.

Out of bounds: Phase 55 Solo files. Risks: a user-typed text that exactly equals a dictionary key would be shown translated in VI mode (mitigated by `translate="no"` on content areas); untranslated strings simply stay English.
