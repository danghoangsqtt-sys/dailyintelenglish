# API Reference

Auto-generated from `Daily Intel English Studio`'s real FastAPI OpenAPI schema by `scripts/generate_api_docs.py` — do not hand-edit; re-run the script after changing any route. The live, always-current version of this same schema is also served at `/docs` (Swagger UI) and `/openapi.json` whenever the app is running.

OpenAPI version: `3.1.0`

## audio

### `GET /api/projects/{project_id}/audio/download`

Download Audio

Download the mixed audio as MP3 (default) or WAV.

- **Response body:** `object`
- **Parameters:** `project_id`, `format` (optional)

### `POST /api/projects/{project_id}/audio/generate`

Generate Audio

Mix all of a project's synthesized lines into one podcast track.

- **Request body:** `GenerateAudioRequest`
- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/projects/{project_id}/audio/status`

Get Audio Status

Return the current audio job for a project (404 if audio was never generated).

- **Response body:** `object`
- **Parameters:** `project_id`

## learning

### `GET /api/projects/{project_id}/learning`

Get Learning Content

Fetch the current Learning Content pack for a project (null if not generated yet).

- **Response body:** `object`
- **Parameters:** `project_id`

### `PUT /api/projects/{project_id}/learning`

Update Learning Content

Apply a partial user-edit to an existing Learning Content pack.

- **Request body:** `LearningPackUpdate`
- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/projects/{project_id}/learning/generate`

Generate Learning Content

Generate a Learning Content pack via Gemini from the project's script and persist it.

- **Response body:** `object`
- **Parameters:** `project_id`

## music

### `GET /api/music`

List Music

List background music tracks available in the local music library.

- **Response body:** `object`

### `POST /api/music`

Upload Music

Upload a validated MP3/WAV track without overwriting an existing file.

- **Response body:** `object`

### `GET /api/music/{filename}`

Get Music

Stream one library track for native browser audio preview.

- **Response body:** `object`
- **Parameters:** `filename`

### `DELETE /api/music/{filename}`

Delete Music

Delete one library track without allowing paths outside the library.

- **Response body:** `object`
- **Parameters:** `filename`

## projects

### `GET /api/projects`

List Projects

List all projects for the dashboard grid.

- **Response body:** `object`

### `POST /api/projects`

Create Project

Create a new project from the Step 1 wizard config.

- **Request body:** `ScriptConfig`
- **Response body:** `object`

### `GET /api/projects/{project_id}`

Get Project

Fetch full project detail, including speakers.

- **Response body:** `object`
- **Parameters:** `project_id`

### `PUT /api/projects/{project_id}`

Update Project

Apply a partial update to a project — also used as the auto-save endpoint.

- **Request body:** `ProjectUpdate`
- **Response body:** `object`
- **Parameters:** `project_id`

### `DELETE /api/projects/{project_id}`

Delete Project

Delete a project.

- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/projects/{project_id}/script`

Get Script

Fetch the current script for a project (empty list if not generated yet).

- **Response body:** `object`
- **Parameters:** `project_id`

### `PUT /api/projects/{project_id}/script`

Save Script

Save a user-edited script, replacing the project's current lines.

- **Request body:** `ScriptUpdate`
- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/projects/{project_id}/script/generate`

Generate Script

Generate a full script for a project via Gemini and persist it.

- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/projects/{project_id}/script/regenerate`

Regenerate Script Line

Regenerate a single script line via Gemini, keeping its speaker and position.

- **Request body:** `RegenerateLineRequest`
- **Response body:** `object`
- **Parameters:** `project_id`

### `PATCH /api/projects/{project_id}/speakers/{speaker_id}`

Update Speaker

Update one speaker's TTS engine/speed/pitch/volume in place (Step 4 Audio Studio).

Deliberately separate from `PUT /{project_id}` — see SpeakerUpdate's docstring for why
the full-replace `speakers` path on that route is unsafe to reuse here.

- **Request body:** `SpeakerUpdate`
- **Response body:** `object`
- **Parameters:** `project_id`, `speaker_id`

### `GET /api/projects/{project_id}/speakers/{speaker_id}/avatar`

Get Speaker Avatar

Serve one speaker's stored avatar image.

- **Response body:** `object`
- **Parameters:** `project_id`, `speaker_id`

### `POST /api/projects/{project_id}/speakers/{speaker_id}/avatar`

Upload Speaker Avatar

Upload (or replace) one speaker's avatar image (Task 1.7c — upload only, no lip-sync).

- **Response body:** `object`
- **Parameters:** `project_id`, `speaker_id`

### `DELETE /api/projects/{project_id}/speakers/{speaker_id}/avatar`

Delete Speaker Avatar

Remove one speaker's avatar image.

- **Response body:** `object`
- **Parameters:** `project_id`, `speaker_id`

## thumbnails

### `GET /api/projects/{project_id}/thumbnails`

List Project Thumbnails

List the current persisted thumbnail generation batch for a project.

- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/projects/{project_id}/thumbnails/generate`

Generate Thumbnails

Generate and persist exactly N variants for one project and selected template.

- **Request body:** `ThumbnailGenerateRequest`
- **Response body:** `object`
- **Parameters:** `project_id`

### `PATCH /api/projects/{project_id}/thumbnails/{thumbnail_id}`

Edit Thumbnail

Persist one optimistic headline/palette edit and its fresh image revision.

- **Request body:** `ThumbnailEditRequest`
- **Response body:** `object`
- **Parameters:** `project_id`, `thumbnail_id`

### `PUT /api/projects/{project_id}/thumbnails/{thumbnail_id}/favorite`

Select Thumbnail Favorite

Idempotently select one project thumbnail as its exclusive favorite.

- **Response body:** `object`
- **Parameters:** `project_id`, `thumbnail_id`

### `GET /api/projects/{project_id}/thumbnails/{thumbnail_id}/{aspect}.{image_format}`

Get Thumbnail Content

Serve one validated thumbnail derivative without exposing the runtime data tree.

- **Response body:** `object`
- **Parameters:** `project_id`, `thumbnail_id`, `aspect`, `image_format`

### `GET /api/thumbnails/templates`

List Thumbnail Templates

List the five validated checked-in thumbnail templates.

- **Response body:** `object`

## tts

### `GET /api/projects/{project_id}/tts/cache/{line_id}.mp3`

Get Cached Audio

Serve a previously synthesized line's cached audio file.

- **Response body:** `object`
- **Parameters:** `project_id`, `line_id`

### `POST /api/projects/{project_id}/tts/preview`

Preview Line

Synthesize one script line to audio (OmniVoice if configured, else Edge TTS) and cache it.

- **Request body:** `PreviewLineRequest`
- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/tts/engines`

List Engines

Report which TTS engines are currently usable on this machine.

OmniVoice availability is based on the model directory existing —
actual model loading and GPU checks happen at startup / in
scripts/check_dependencies.py, not on every request here.

- **Response body:** `object`

## untagged

### `GET /`

Root

Serve the dashboard as the app's landing page.

- **Response body:** `object`

### `GET /health`

Health

Report readiness of the database, ffmpeg, and GPU for the check_dependencies script and UI.

- **Response body:** `object`

### `GET /music`

Music Library

Serve the background Music Library management page.

- **Response body:** `object`

### `GET /step1`

Step1 Config

Serve the Step 1 — Script Config wizard.

- **Response body:** `object`

### `GET /step2`

Step2 Script

Serve the Step 2 — AI Script Generation page.

- **Response body:** `object`

### `GET /step3`

Step3 Learning

Serve the Step 3 — Learning Content page.

- **Response body:** `object`

### `GET /step4`

Step4 Tts

Serve the Step 4 — TTS Audio Studio.

- **Response body:** `object`

### `GET /step5`

Step5 Video

Serve the Step 5 — Video Studio page.

- **Response body:** `object`

### `GET /step6`

Step6 Thumbnail

Serve the Step 6 — interactive Thumbnail Generator page.

- **Response body:** `object`

### `GET /step7`

Step7 Youtube

Serve the Step 7 — YouTube Package page.

- **Response body:** `object`

## video

### `GET /api/projects/{project_id}/video/download`

Download Video

Download the generated video as MP4 (default), the 9:16 vertical MP4, or the SRT
subtitle file.

- **Response body:** `object`
- **Parameters:** `project_id`, `format` (optional)

### `POST /api/projects/{project_id}/video/generate`

Generate Video

Render the project's completed audio mix into an MP4 with burned-in subtitles.

- **Request body:** `GenerateVideoRequest`
- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/projects/{project_id}/video/status`

Get Video Status

Return the current video job for a project (404 if video was never generated).

- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/video/templates`

List Templates

List the fixed set of pre-rendered background templates.

- **Response body:** `object`

## youtube

### `GET /api/projects/{project_id}/youtube`

Get Youtube Package

Fetch the current YouTube package for a project (null if not generated yet).

- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/projects/{project_id}/youtube/export`

Export Youtube Package

Download the full YouTube package as a .zip, including transcript/Learning Content.

Requires a generated YouTube package, a completed video, and a selected favorite
thumbnail — a ValidationError names exactly which piece is missing.

- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/projects/{project_id}/youtube/generate`

Generate Youtube Package

Generate a YouTube package (titles/description/tags/chapters) via Gemini.

Chapters are measured from real audio when a completed audio mix exists (Task 1.6),
otherwise estimated from script word count (Sub-task 1.9a's original behavior).

- **Response body:** `object`
- **Parameters:** `project_id`
