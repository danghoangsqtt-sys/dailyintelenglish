# API Reference

Auto-generated from `Daily Beyond English`'s real FastAPI OpenAPI schema by `scripts/generate_api_docs.py` — do not hand-edit; re-run the script after changing any route. The live, always-current version of this same schema is also served at `/docs` (Swagger UI) and `/openapi.json` whenever the app is running.

OpenAPI version: `3.1.0`

## ai-jobs

### `GET /api/ai/health`

Ai Health

Report AI runtime health. Never exposes the Gemini key; a failed local probe
degrades this payload, it never fails or delays app startup.

- **Response body:** `object`

### `POST /api/projects/{project_id}/ai-jobs`

Create Ai Job

Create a durable AI job, or return the project's existing active one for
this operation (matches the app's established idempotent-create pattern).

HTTP 202 for a genuinely new job, HTTP 200 when an existing active/idempotent
job was returned instead -- both are explicitly allowed by the API contract.

- **Request body:** `CreateAIJobRequest`
- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/projects/{project_id}/ai-jobs/active`

Get Active Ai Job

Return the project's active job for `operation`, or `null` if none.

Matches this app's established "empty means null/empty payload, not a 404"
style for a "nothing yet" state (e.g. `GET .../script` before generation).

- **Response body:** `object`
- **Parameters:** `project_id`, `operation`

### `GET /api/projects/{project_id}/ai-jobs/{job_id}`

Get Ai Job

Fetch one job's safe status view. 404s if it doesn't belong to `project_id`.

- **Response body:** `object`
- **Parameters:** `project_id`, `job_id`

### `POST /api/projects/{project_id}/ai-jobs/{job_id}/cancel`

Cancel Ai Job

Idempotently request cancellation. A terminal job is returned unchanged.

- **Response body:** `object`
- **Parameters:** `project_id`, `job_id`

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

Generate a Learning Content pack from the project's script and persist it
(synchronous, one request).

Deprecated (Phase 13, Task 13.7): kept for one compatibility release with an
unchanged response contract. The durable-job path (`POST
/api/projects/{project_id}/ai-jobs` with `operation: "learning"`, Task 13.3+) is
the production route.

- **Response body:** `object`
- **Parameters:** `project_id`

## music

### `GET /api/music`

List Music

List background music tracks with their details (Task 22.7).

- **Response body:** `object`

### `POST /api/music`

Upload Music

Upload a validated MP3/WAV track without overwriting an existing file.

- **Response body:** `object`

### `POST /api/music/analyse`

Analyse Music

Task 22.9: classify every track not analysed yet (pace, ~BPM, energy, mood suggestion).

- **Response body:** `object`

### `GET /api/music/options`

Music Options

Task 22.7: the choices for a track's mood, source and licence.

- **Response body:** `object`

### `GET /api/music/{filename}`

Get Music

Stream one library track for native browser audio preview.

- **Response body:** `object`
- **Parameters:** `filename`

### `PATCH /api/music/{filename}`

Edit Music

Task 22.7: edit a track's details; only the fields sent change, an empty value clears.

- **Request body:** `MusicTrackPatch`
- **Response body:** `object`
- **Parameters:** `filename`

### `DELETE /api/music/{filename}`

Delete Music

Delete one library track without allowing paths outside the library.

- **Response body:** `object`
- **Parameters:** `filename`

### `POST /api/projects/{project_id}/music/suggest`

Suggest Music

Task 22.8 (D51): the library track that best fits this episode's topic and length, with the
reason (AI choice among the top candidates, else the deterministic score).

- **Response body:** `object`
- **Parameters:** `project_id`

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

Generate a full script for a project and persist it (synchronous, one request).

Deprecated (Phase 13, Task 13.7): kept for one compatibility release with an
unchanged response contract. The durable-job path (`POST
/api/projects/{project_id}/ai-jobs` with `operation: "script"`, Task 13.3+) is the
production route -- it survives browser navigation/restart and does not hold one
HTTP request open for the whole generation.

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

The previous avatar file (if any) is only deleted after this block's commit has
durably succeeded — see `avatar_service.cleanup_previous_avatar_file` for why.

- **Response body:** `object`
- **Parameters:** `project_id`, `speaker_id`

### `DELETE /api/projects/{project_id}/speakers/{speaker_id}/avatar`

Delete Speaker Avatar

Remove one speaker's avatar image.

The file itself is only deleted after this block's commit has durably
succeeded — see `avatar_service.delete_avatar`'s docstring for why.

- **Response body:** `object`
- **Parameters:** `project_id`, `speaker_id`

## settings

### `GET /api/settings`

Get Settings

Report the cloud provider's status and the current AI_MODE.

Never returns the raw cloud key -- see settings_service.get_cloud_settings_status.
`allow_cloud` (Task 18.3, PM review C3) and `effective_mode`/`effective_reason`
let the Settings page show, and explain, when the selected mode differs from
what actually runs.

- **Response body:** `object`

### `PUT /api/settings/ai-mode`

Update Ai Mode

Save a new AI_MODE (ADR-001 kill switch) -- takes effect immediately, no restart needed.

- **Request body:** `AIModeUpdate`
- **Response body:** `object`

### `PUT /api/settings/cloud`

Update Cloud Settings

Save the cloud provider's base URL/model, and (optionally) its API key --
takes effect immediately, no restart needed.

- **Request body:** `CloudSettingsUpdate`
- **Response body:** `object`

### `DELETE /api/settings/cloud/api-key`

Clear Cloud Api Key

Remove the stored cloud API key and revert to the original .env/environment value.

- **Response body:** `object`

### `PUT /api/settings/cloud/gemini`

Update Gemini Settings

Task 18.8: save Gemini's base URL/model chain, and (optionally) its API
key -- takes effect immediately, no restart needed.

- **Request body:** `GeminiSettingsUpdate`
- **Response body:** `object`

### `DELETE /api/settings/cloud/gemini/api-key`

Clear Gemini Cloud Api Key

Task 18.8: remove the stored Gemini API key, reverting to the original
.env/environment value.

- **Response body:** `object`

### `PUT /api/settings/cloud/opencode-zen`

Update Opencode Zen Settings

Task 18.8: save OpenCode Zen's base URL/model, and (optionally) its API
key -- takes effect immediately, no restart needed.

- **Request body:** `OpenCodeZenSettingsUpdate`
- **Response body:** `object`

### `DELETE /api/settings/cloud/opencode-zen/api-key`

Clear Opencode Zen Api Key

Task 18.8: remove the stored OpenCode Zen API key, reverting to the
original .env/environment value.

- **Response body:** `object`

### `PUT /api/settings/cloud/order`

Update Cloud Provider Order

Task 18.8: save the cloud dispatch order -- takes effect immediately.

- **Request body:** `CloudProviderOrderUpdate`
- **Response body:** `object`

### `POST /api/settings/cloud/test-connection`

Test Cloud Connection

One real, tiny probe call to the cloud provider -- never persists anything.

- **Request body:** `CloudTestConnectionRequest`
- **Response body:** `object`

## storyboard

### `GET /api/projects/{project_id}/storyboard`

Get Storyboard

- **Response body:** `object`
- **Parameters:** `project_id`

### `PUT /api/projects/{project_id}/storyboard`

Put Storyboard

- **Request body:** `StoryboardInput`
- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/projects/{project_id}/storyboard/propose`

Propose Storyboard

Task 24.2: AI proposal (one repair, then the deterministic rule); replaces the draft.

- **Response body:** `object`
- **Parameters:** `project_id`

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
- **Parameters:** `project_id` (optional)

## tts

### `GET /api/projects/{project_id}/tts/cache/{line_id}.mp3`

Get Cached Audio

Serve a previously synthesized line's cached audio file.

- **Response body:** `object`
- **Parameters:** `project_id`, `line_id`

### `POST /api/projects/{project_id}/tts/preview`

Preview Line

Synthesize one script line to audio with Edge TTS and cache it.

No lock is held across the synthesis call itself (network round-trip to Edge
TTS, potentially slow) — same "no lock across slow work" rule already applied
to Gemini calls and audio/video generation elsewhere in this codebase. A short
`read_transaction` snapshots what's needed, then a separate, short
`write_transaction` persists the result.

- **Request body:** `PreviewLineRequest`
- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/tts/engines`

List Engines

Report the TTS engines this app can use: Edge TTS only (D56, owner 2026-10-06).
OmniVoice (never integrated), Kokoro and StyleTTS 2 were removed.

- **Response body:** `object`

## untagged

### `GET /`

Root

Serve the dashboard as the app's landing page.

- **Response body:** `object`

### `GET /characters`

Character Library

Serve the global Character Library.

- **Response body:** `object`

### `GET /health`

Health

Report readiness of the database, ffmpeg, and GPU for the check_dependencies script and UI.

- **Response body:** `object`

### `GET /music`

Music Library

Serve the background Music Library management page.

- **Response body:** `object`

### `GET /settings`

Settings Page

Serve the app-level Settings page (Task 12.1 — Gemini API key).

- **Response body:** `object`

### `GET /shots`

Shot Library

Serve the Shot Library (Task 29.7).

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

Render the project's completed audio mix into an MP4.

Task 19.7: `payload.renderer` ("ffmpeg" default) is only ever actually honored as
"remotion" when `video_service._resolve_renderer`'s kill-switch check agrees (D19.7-b)
-- passing "remotion" here is always safe, it just silently resolves to ffmpeg when the
deployment hasn't opted in via `DIE_VIDEO_RENDERER=remotion`.

- **Request body:** `GenerateVideoRequest`
- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/projects/{project_id}/video/status`

Get Video Status

Return the current video job for a project (404 if video was never generated).

- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/video/health`

Video Health

Task 19.7 (D19.7-d): Remotion availability + the in-memory fallback-rate counters
(process-lifetime only, reset on restart -- same precedent as app/main.py's
`_ai_circuits`, Phase 18).

- **Response body:** `object`

### `GET /api/video/templates`

List Templates

List the fixed set of pre-rendered background templates.

- **Response body:** `object`

## visuals

### `GET /api/projects/{project_id}/visuals`

Get Project Visuals

- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/projects/{project_id}/visuals/activity-coverage`

Activity Coverage

Explain selected/missing reusable activity illustrations before a talking-sprites render.

- **Response body:** `object`
- **Parameters:** `project_id`

### `PUT /api/projects/{project_id}/visuals/cast`

Set Project Cast

- **Request body:** `CastMemberInput`
- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/projects/{project_id}/visuals/library-coverage`

Library Coverage

- **Response body:** `object`
- **Parameters:** `project_id`

### `PUT /api/projects/{project_id}/visuals/scenes`

Set Project Scenes

- **Request body:** `object`
- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/projects/{project_id}/visuals/shots`

Generate Project Shots

- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/projects/{project_id}/visuals/shots/{shot_id}/content`

Project Shot Content

- **Response body:** `object`
- **Parameters:** `project_id`, `shot_id`, `variant` (optional)

### `POST /api/projects/{project_id}/visuals/shots/{shot_id}/regenerate`

Regenerate Project Shot

- **Response body:** `object`
- **Parameters:** `project_id`, `shot_id`

### `POST /api/projects/{project_id}/visuals/shots/{shot_id}/to-library`

Add Project Shot To Library

- **Response body:** `object`
- **Parameters:** `project_id`, `shot_id`

### `GET /api/visuals/assets/{asset_id}/content`

Asset Content

- **Response body:** `object`
- **Parameters:** `asset_id`

### `GET /api/visuals/characters`

List Characters

- **Response body:** `object`

### `POST /api/visuals/characters`

Create Character

- **Request body:** `CharacterInput`
- **Response body:** `object`

### `GET /api/visuals/characters/{character_id}`

Get Character

- **Response body:** `object`
- **Parameters:** `character_id`

### `PATCH /api/visuals/characters/{character_id}`

Edit Character

- **Request body:** `CharacterPatch`
- **Response body:** `object`
- **Parameters:** `character_id`

### `DELETE /api/visuals/characters/{character_id}`

Delete Character

- **Response body:** `object`
- **Parameters:** `character_id`, `force` (optional)

### `PUT /api/visuals/characters/{character_id}/assets/{asset_id}/approve`

Approve Asset

- **Request body:** `ApprovalInput`
- **Response body:** `object`
- **Parameters:** `character_id`, `asset_id`

### `POST /api/visuals/characters/{character_id}/candidates`

Generate Candidates

- **Response body:** `object`
- **Parameters:** `character_id`

### `POST /api/visuals/characters/{character_id}/lock`

Lock Character

- **Response body:** `object`
- **Parameters:** `character_id`

### `PUT /api/visuals/characters/{character_id}/reference`

Pick Reference

- **Request body:** `ReferenceInput`
- **Response body:** `object`
- **Parameters:** `character_id`

### `POST /api/visuals/characters/{character_id}/sheet`

Generate Sheet

- **Request body:** `object`
- **Response body:** `object`
- **Parameters:** `character_id`

### `POST /api/visuals/characters/{character_id}/unlock`

Unlock Character

- **Response body:** `object`
- **Parameters:** `character_id`

### `GET /api/visuals/health`

Visuals Health

- **Response body:** `object`

### `GET /api/visuals/jobs/{job_id}`

Get Image Job

- **Response body:** `object`
- **Parameters:** `job_id`

### `POST /api/visuals/jobs/{job_id}/cancel`

Cancel Image Job

- **Response body:** `object`
- **Parameters:** `job_id`

### `GET /api/visuals/library/activities`

List Library Activities

- **Response body:** `object`
- **Parameters:** `review_state` (optional), `character_id` (optional), `activity` (optional)

### `POST /api/visuals/library/activities/approve-batch`

Approve Library Activities Batch

Approve only the pending activity pictures explicitly selected in the UI.

- **Request body:** `ActivityApproveBatchInput`
- **Response body:** `object`

### `POST /api/visuals/library/activities/import`

Import Library Activities

- **Response body:** `object`

### `POST /api/visuals/library/activities/upload`

Upload Library Activity

Upload one activity picture directly; it always starts pending review.

- **Response body:** `object`

### `POST /api/visuals/library/activities/upload-batch`

Upload Library Activities Batch

Add up to 20 pictures with one owner-entered activity name per file.

- **Response body:** `object`

### `PATCH /api/visuals/library/activities/{activity_id}`

Edit Library Activity

- **Request body:** `ActivityMetadataPatch`
- **Response body:** `object`
- **Parameters:** `activity_id`

### `DELETE /api/visuals/library/activities/{activity_id}`

Delete Library Activity

Delete one library image after its database removal commits.

- **Response body:** `object`
- **Parameters:** `activity_id`

### `GET /api/visuals/library/activities/{activity_id}/content`

Activity Content

- **Response body:** `object`
- **Parameters:** `activity_id`

### `GET /api/visuals/library/activities/{activity_id}/history`

Activity History

- **Response body:** `object`
- **Parameters:** `activity_id`

### `PATCH /api/visuals/library/activities/{activity_id}/review`

Review Library Activity

- **Request body:** `ActivityReviewInput`
- **Response body:** `object`
- **Parameters:** `activity_id`

### `GET /api/visuals/library/backgrounds`

Library Backgrounds

- **Response body:** `object`

### `POST /api/visuals/library/backgrounds/import`

Import Library Backgrounds

- **Response body:** `object`

### `GET /api/visuals/library/inbox`

Library Inbox

- **Response body:** `object`

### `POST /api/visuals/library/inbox/import`

Import Library Inbox

- **Response body:** `object`

### `GET /api/visuals/library/shots`

List Library Shots

- **Response body:** `object`
- **Parameters:** `scene_id` (optional), `kind` (optional), `review_state` (optional), `character_id` (optional)

### `PATCH /api/visuals/library/shots/{shot_id}`

Review Library Shot

- **Request body:** `ShotReviewInput`
- **Response body:** `object`
- **Parameters:** `shot_id`

### `DELETE /api/visuals/library/shots/{shot_id}`

Delete Library Shot

- **Response body:** `object`
- **Parameters:** `shot_id`

### `GET /api/visuals/library/shots/{shot_id}/content`

Library Shot Content

- **Response body:** `object`
- **Parameters:** `shot_id`

### `GET /api/visuals/library/sprites`

Library Sprites

Phase 32: the talking-sprite set of every library character, and the inbox the sets are imported from.

- **Response body:** `object`

### `POST /api/visuals/library/sprites/import`

Import Library Sprites

- **Response body:** `object`

### `GET /api/visuals/library/sprites/{character_id}/{name}/content`

Library Sprite Content

- **Response body:** `object`
- **Parameters:** `character_id`, `name`

### `GET /api/visuals/options`

Visuals Options

- **Response body:** `object`

### `GET /api/visuals/scenes`

List Scenes

- **Response body:** `object`

### `POST /api/visuals/scenes`

Create Scene

- **Request body:** `SceneInput`
- **Response body:** `object`

### `PATCH /api/visuals/scenes/{scene_id}`

Edit Scene

- **Request body:** `ScenePatch`
- **Response body:** `object`
- **Parameters:** `scene_id`

### `DELETE /api/visuals/scenes/{scene_id}`

Delete Scene

- **Response body:** `object`
- **Parameters:** `scene_id`

### `POST /api/visuals/scenes/{scene_id}/duplicate`

Duplicate Scene

- **Response body:** `object`
- **Parameters:** `scene_id`

### `GET /api/visuals/scenes/{scene_id}/preview`

Scene Preview Content

- **Response body:** `object`
- **Parameters:** `scene_id`

### `POST /api/visuals/scenes/{scene_id}/preview`

Generate Scene Preview

- **Response body:** `object`
- **Parameters:** `scene_id`

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
