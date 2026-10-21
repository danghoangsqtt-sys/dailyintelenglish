# Task 57.5 — Step 1 UI

Status: planned 2026-10-21.

## Paths
- frontend/pages/step1_config.html, frontend/static/js/step1_config.js, frontend/static/js/api.js
- tests/test_step1_sources_browser.py (new); existing Step 1 / explainer config browser tests follow the select → cards change

## File-Level Plan
"1. Video type": two radio cards (👥 Conversation — two characters · 🎤 Solo presentation — one presenter on a field, product or subject) driving the existing `presentation-mode` value (the select stays in the DOM, hidden, so existing code keeps working). "2. Where does the content come from?": Type a topic (today's fields) · ✨ AI topic ideas (hint box + "Suggest" → six idea cards; a click fills name + topic) · 📄 From your material (Dialogue | Vocabulary list; a textarea, "Read a photo" button that fills the textarea with the text read, and for a conversation dialogue the switch "Use it word for word / Let the AI rewrite it"). The topic stays required; with material and an empty topic the first line of the material is proposed. Edit mode (existing project) shows the saved material read-only.

## Tests
Browser: cards switch the type (Solo hides speaker 2 as today); ideas (mocked API) fill the form; a pasted word-for-word dialogue creates a project whose Step 2 already shows the lines; the photo button (mocked API) fills the textarea.
