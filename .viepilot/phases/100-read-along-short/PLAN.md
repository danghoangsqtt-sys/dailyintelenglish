# Phase 100 - Read Along Short

## Scope
Add an independent 9:16 template to Studio. An illustrated upper panel, a short title and the entire passage remain visible. During narration, use actual audio timings to highlight the current sentence and its current word. Without timings, keep the passage legible. Generate a new passage from the topic and CEFR level rather than reusing the sample text. Use one editable landscape illustration for the whole Short. Keep Phase 98's separate verification gate open.

## Implementation
- Follow the existing card-Short script job, card editor, picture generation, upload, renderer, and batch paths. Persist one sentence per line with a shared title and picture key.
- Enforce a bounded passage and short sentences in the AI response. Fit the displayed passage as a whole and keep the page stable during highlighting.
- Verify generation from the real script job, image orientation, render props, and the current sentence/word selection. Run renderer typecheck, Vitest, and a browser smoke test where available.
