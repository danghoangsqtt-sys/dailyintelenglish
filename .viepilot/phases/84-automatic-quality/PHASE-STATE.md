# Phase 84 state

Status: in_progress (2026-10-28).

| Task | Scope | Status |
|---|---|---|
| 84.1 | Plan boundaries repaired | done — ScriptIndex.snap chains the AI segments before the coverage check |
| 84.2 | Short script length | done — Shorts checked at ±20 % (SCRIPT_SHORT_WORD_TOLERANCE); pinned ±10 % kept for long scripts |
| 84.3 | Producer tries again | done — audio, visual plan (proposed afresh), video and thumbnail run once more; a doubtful fact (OwnerStop) is never retried |
| 84.4 | AI fact check | done — POST explainer-plan/fact-check; automation approves News / VOX / long presenter plans only when every segment is ok; invented VOX chart / map data becomes a card |
| 84.5 | Editor pass | done — script_editor: 6 scores, one rewrite under 4 kept only when it passes every check; script_reviews (041); Step 2 card + manual run; Producer runs it after the script |
| 84.6 | Long videos at 1080p | done — Remotion --scale=1.5; real render 1920x1080, 258 s, 11 min; IPA double slashes fixed |
| 84.7 | Verify | in_progress |
