# Task 78.3 — 9:16 repairs (renderer and Shorts & TikTok section)

## Objective
Fix V1–V8 from the plan so the vertical outputs can be judged and produced without surprises.

## Paths
- `renderer/src/Episode.tsx`: SpeakerChips take an opacity; `PodcastLayer` passes `1 - hookShown`.
- `renderer/src/hook.test.ts`: the chips' fade follows the hook envelope (pure helper).
- `frontend/static/js/step5_shorts.js`: clip card rebuild.
- `frontend/static/js/step5_video.js`: 9:16 result player for a vertical main video; tell the Shorts module the project is a Short.
- `frontend/pages/step5_video.html`: clip card / vertical player CSS; result player aspect class.
- `frontend/static/js/i18n_vi.js`: copy.
- `tests/test_step5_shorts_after_render.py`, `tests/test_shorts.py`: approve keeps edited lines; card shows the sketch and accessible names.

## File-Level Plan
- Renderer: export `chipsOpacity(hookShown)` (= `1 - hookShown`), use it in `SpeakerChips` style.
- Clip card: left = 9:16 media (the rendered video with its cover as poster, else `BeatPreview.frame` of the beat covering `line_from` with the hook banner and the first line as caption, labelled "Phác thảo — chưa render"); right = fields row (Lines from/to, hook) with attributes set via `setAttribute`, live duration from the audio timestamps (`Api.getAudioStatus`) with a 30–90 s warning, reason as its own paragraph (no negative margin), status chip, actions (Save, Approve sends lines + hook, Render / Render again, downloads, Delete), the Shorts / TikTok texts in a collapsible group (open by default once rendered).
- Vertical episode: an inline 9:16 `<video>` (max-height 70vh) with the download link when `mp4_path_vertical` exists.
- Vertical main video (chat / wyr Short): `.result-player.is-vertical` (9:16 box, max-height 70vh, centred); the Shorts section shows a note that the main video is already 9:16 and hides the full-vertical button and highlight clips (they need 30–90 s).

## Best practices
No duplicated geometry: the sketch reuses `beat_preview.js`. Buttons disabled while busy. All texts through i18n.

## Verification
`cd renderer && npx vitest run && npx tsc --noEmit`; `pytest tests/test_shorts.py tests/test_step5_shorts_after_render.py -q`; browser check of a clip card in the sandbox (sketch, live duration, approve with edited lines).
