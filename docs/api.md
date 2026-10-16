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

## channel

### `GET /api/channel`

Get Channel

- **Response body:** `object`

### `GET /api/channel/dashboard`

Get Dashboard

Task 36.7 (D106-D108): stats, today's actions, the roadmap, the production board and the next two weeks.

- **Response body:** `object`

### `PATCH /api/channel/episodes/{episode_id}`

Patch Episode

- **Request body:** `EpisodePatch`
- **Response body:** `object`
- **Parameters:** `episode_id`

### `DELETE /api/channel/episodes/{episode_id}`

Delete Episode

- **Response body:** `object`
- **Parameters:** `episode_id`

### `POST /api/channel/plan/apply`

Apply Plan

- **Request body:** `ApplyPlanRequest`
- **Response body:** `object`

### `POST /api/channel/plan/propose`

Propose Plan

The AI's channel map (nothing saved): topics -> series -> episode titles.

- **Request body:** `PlanRequest`
- **Response body:** `object`

### `GET /api/channel/projects/{project_id}`

Project Context

- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/channel/schedule`

Schedule

Publishing dates for the unpublished episodes, rotating topics over the chosen weekdays (D105).

- **Request body:** `ScheduleRequest`
- **Response body:** `object`

### `PATCH /api/channel/series/{series_id}`

Patch Series

- **Request body:** `SeriesPatch`
- **Response body:** `object`
- **Parameters:** `series_id`

### `DELETE /api/channel/series/{series_id}`

Delete Series

- **Response body:** `object`
- **Parameters:** `series_id`

### `POST /api/channel/series/{series_id}/episodes`

Add Episode

- **Request body:** `EpisodeInput`
- **Response body:** `object`
- **Parameters:** `series_id`

### `POST /api/channel/series/{series_id}/projects`

Create Projects

One numbered project per planned episode of the series, with its cast.

- **Response body:** `object`
- **Parameters:** `series_id`

### `POST /api/channel/topics`

Create Topic

- **Request body:** `TopicInput`
- **Response body:** `object`

### `PATCH /api/channel/topics/{topic_id}`

Patch Topic

- **Request body:** `TopicPatch`
- **Response body:** `object`
- **Parameters:** `topic_id`

### `DELETE /api/channel/topics/{topic_id}`

Delete Topic

- **Response body:** `object`
- **Parameters:** `topic_id`

### `POST /api/channel/topics/{topic_id}/series`

Create Series

- **Request body:** `SeriesInput`
- **Response body:** `object`
- **Parameters:** `topic_id`

## character profiles

### `GET /api/visuals/profiles`

List Profiles

- **Response body:** `object`
- **Parameters:** `q` (optional), `state` (optional)

### `POST /api/visuals/profiles`

Create Profile

- **Request body:** `ProfileQuickCreate`
- **Response body:** `object`

### `GET /api/visuals/profiles/options`

Profile Options

- **Response body:** `object`

### `GET /api/visuals/profiles/{character_id}`

Get Profile

- **Response body:** `object`
- **Parameters:** `character_id`

### `PATCH /api/visuals/profiles/{character_id}`

Patch Profile

- **Request body:** `ProfilePatch`
- **Response body:** `object`
- **Parameters:** `character_id`

### `DELETE /api/visuals/profiles/{character_id}`

Delete Profile

- **Response body:** `object`
- **Parameters:** `character_id`

### `POST /api/visuals/profiles/{character_id}/archive`

Archive Profile

- **Response body:** `object`
- **Parameters:** `character_id`

### `POST /api/visuals/profiles/{character_id}/assets/approve`

Approve Assets

- **Request body:** `ApproveManyInput`
- **Response body:** `object`
- **Parameters:** `character_id`, `view` (optional)

### `GET /api/visuals/profiles/{character_id}/assets/{asset_id}/content`

Asset Content

- **Response body:** `object`
- **Parameters:** `character_id`, `asset_id`

### `PUT /api/visuals/profiles/{character_id}/assets/{asset_id}/review`

Review Asset

- **Request body:** `ReviewInput`
- **Response body:** `object`
- **Parameters:** `character_id`, `asset_id`, `view` (optional)

### `GET /api/visuals/profiles/{character_id}/dependencies`

Profile Dependencies

- **Response body:** `object`
- **Parameters:** `character_id`

### `POST /api/visuals/profiles/{character_id}/duplicate`

Duplicate Profile

- **Response body:** `object`
- **Parameters:** `character_id`

### `GET /api/visuals/profiles/{character_id}/prompt-pack.txt`

Prompt Pack

- **Response body:** `object`
- **Parameters:** `character_id`, `view` (optional)

### `POST /api/visuals/profiles/{character_id}/restore`

Restore Profile

- **Response body:** `object`
- **Parameters:** `character_id`

### `GET /api/visuals/profiles/{character_id}/slots`

List Slots

- **Response body:** `object`
- **Parameters:** `character_id`, `view` (optional)

### `POST /api/visuals/profiles/{character_id}/slots/upload-batch`

Upload Batch

Bulk shortcut: files named after a slot go into it (the base first); every other file is listed, not guessed.

- **Response body:** `object`
- **Parameters:** `character_id`, `view` (optional)

### `GET /api/visuals/profiles/{character_id}/slots/{slot_key}/input.png`

Slot Input

- **Response body:** `object`
- **Parameters:** `character_id`, `slot_key`, `view` (optional)

### `POST /api/visuals/profiles/{character_id}/slots/{slot_key}/upload`

Upload Slot

The slot comes from the card the picture was dropped on, never from the file name (D84).

- **Response body:** `object`
- **Parameters:** `character_id`, `slot_key`, `view` (optional)

## explainer

### `GET /api/projects/{project_id}/explainer-plan`

Get Plan

Read a draft or approved version together with live source issues.

- **Response body:** `object`
- **Parameters:** `project_id`

### `PATCH /api/projects/{project_id}/explainer-plan`

Save Plan

Save an owner edit against both the expected revision and current source.

- **Request body:** `ExplainerPlanPatch`
- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/projects/{project_id}/explainer-plan/approve`

Approve Plan

Validate source/assets/audio/layouts before pinning the reviewed revision.

- **Request body:** `ExplainerApproval`
- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/projects/{project_id}/explainer-plan/history`

Plan History

Read immutable project revisions in order.

- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/projects/{project_id}/explainer-plan/layout`

Arrange Plan

Suggest collision-checked layouts without implicitly saving or approving a plan.

- **Request body:** `ExplainerApproval`
- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/projects/{project_id}/explainer-plan/preview`

Preview Plan

Resolve verified draft preview props without approving factual content.

- **Response body:** `object`
- **Parameters:** `project_id`, `aspect` (optional)

### `POST /api/projects/{project_id}/explainer-plan/propose`

Propose Plan

Create or return the existing durable proposal job.

- **Request body:** `ExplainerProposalRequest`
- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/projects/{project_id}/explainer/assets`

List Assets

List the project's available illustration versions.

- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/projects/{project_id}/explainer/assets`

Upload Asset

Read a bounded multipart image; service owns decoding and guarded publication.

- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/projects/{project_id}/explainer/assets/{asset_id}/{version}/content`

Asset Content

Serve only a scoped, verified immutable PNG version.

- **Response body:** `object`
- **Parameters:** `project_id`, `asset_id`, `version`

## export

### `GET /api/projects/{project_id}/export`

Get Export

- **Response body:** `object`
- **Parameters:** `project_id`

### `PUT /api/projects/{project_id}/export`

Save Export

Set the folder and the ticked components, then copy what already exists.

- **Request body:** `ExportSettings`
- **Response body:** `object`
- **Parameters:** `project_id`

### `DELETE /api/projects/{project_id}/export`

Clear Export

Stop exporting (the folder and its files stay as they are).

- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/projects/{project_id}/export/open`

Open Export Folder

Open the folder in Windows Explorer (the app runs on the owner's computer).

- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/projects/{project_id}/export/sync`

Sync Export

- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/system/choose-folder`

Choose Folder

The native folder picker on the owner's screen; `path` is null when cancelled or unavailable.

- **Request body:** `FolderRequest`
- **Response body:** `object`

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

### `POST /api/projects/{project_id}/copy-settings`

Copy Project Settings

Start a new draft from pinned configuration without copying media or approvals.

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

## shorts

### `GET /api/projects/{project_id}/shorts`

List Clips

- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/projects/{project_id}/shorts`

Create Clip

- **Request body:** `ClipInput`
- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/projects/{project_id}/shorts/propose`

Propose

The AI's 1-3 highlight clips (30-90 s, complete, with a hook); they replace the clips not rendered yet.

- **Request body:** `ProposeRequest`
- **Response body:** `object`
- **Parameters:** `project_id`

### `PATCH /api/projects/{project_id}/shorts/{clip_id}`

Update Clip

- **Request body:** `ClipPatch`
- **Response body:** `object`
- **Parameters:** `project_id`, `clip_id`

### `DELETE /api/projects/{project_id}/shorts/{clip_id}`

Delete Clip

- **Response body:** `object`
- **Parameters:** `project_id`, `clip_id`

### `GET /api/projects/{project_id}/shorts/{clip_id}/cover.jpg`

Clip Cover

- **Response body:** `object`
- **Parameters:** `project_id`, `clip_id`

### `POST /api/projects/{project_id}/shorts/{clip_id}/render`

Render Clip

Render an approved clip (a frame range of the vertical episode) and its 9:16 cover.

- **Request body:** `RenderRequest`
- **Response body:** `object`
- **Parameters:** `project_id`, `clip_id`

### `GET /api/projects/{project_id}/shorts/{clip_id}/video.mp4`

Clip Video

- **Response body:** `object`
- **Parameters:** `project_id`, `clip_id`

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

### `GET /api/projects/{project_id}/thumbnails/ai-scenes`

List Ai Scenes

- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/projects/{project_id}/thumbnails/ai-scenes`

Draw Ai Scenes

Phase 43 (D122): draw 1-3 scenes of the episode's characters on the local GPU (Qwen-Image-Edit-2511, ~1.5 min
load + ~1.5 min per picture); each is framed on its faces. Replaces the previous scenes.

- **Request body:** `object`
- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/projects/{project_id}/thumbnails/ai-scenes/{index}`

Get Ai Scene

- **Response body:** `object`
- **Parameters:** `project_id`, `index`

### `POST /api/projects/{project_id}/thumbnails/ai-scenes/{index}/redraw`

Redraw Ai Scene

Phase 43: draw one scene again (a new seed), e.g. when it came out crowded.

- **Response body:** `object`
- **Parameters:** `project_id`, `index`

### `POST /api/projects/{project_id}/thumbnails/generate`

Generate Thumbnails

Generate and persist exactly N variants for one project and selected template.

- **Request body:** `ThumbnailGenerateRequest`
- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/projects/{project_id}/thumbnails/outside-image`

Get Outside Image

- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/projects/{project_id}/thumbnails/outside-image`

Upload Outside Image

Task 36.4 (D90): the owner's thumbnail picture made with an outside AI; the `outside_ai` thumbnail draws on it.

- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/projects/{project_id}/thumbnails/outside-prompt`

Get Outside Prompt

Task 36.4 (D90): the prompt to paste into an outside AI and the character pictures to attach with it.

- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/projects/{project_id}/thumbnails/topic-picture`

Get Topic Picture

- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/projects/{project_id}/thumbnails/topic-picture`

Draw Topic Picture

Phase 39 (D118): draw the episode's topic picture on the local GPU with Qwen-Image-2.1-Turbo (~1-2 min with the
model load). The composed thumbnail then uses it as its background, under the characters, headline and badges.

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

The two thumbnail kinds (Task 36.3/36.4): composed, and the owner's outside-AI picture once uploaded.

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

### `GET /api/tts/voices`

List Voices

Discover actual English voices, including explicit cache freshness metadata.

- **Response body:** `object`
- **Parameters:** `locale` (optional), `gender` (optional), `q` (optional), `refresh` (optional)

### `POST /api/tts/voices/preview`

Preview Voice

Audition a selected voice independently of every project and production cache.

- **Request body:** `VoicePreviewRequest`
- **Response body:** `object`

### `GET /api/tts/voices/preview/{preview_id}.mp3`

Voice Preview Media

Serve a bounded audition already read into memory; no open file can race cleanup.

- **Response body:** `object`
- **Parameters:** `preview_id`

## untagged

### `GET /`

Root

Serve the dashboard as the app's landing page.

- **Response body:** `object`

### `GET /channel`

Channel Page

Task 36.5 (D103-D105): the channel plan -- topics, series, episodes and the publishing calendar.

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

Serve the Shots page: the Activity Library and the scene-background import (Phase 44, D123).

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

Render the project's completed audio mix into the episode MP4 with Remotion (Task 35.5: the only renderer; a
failure fails the job with its reason).

- **Request body:** `GenerateVideoRequest`
- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/projects/{project_id}/video/status`

Get Video Status

Return the current video job for a project (404 if video was never generated).

- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/projects/{project_id}/video/vertical`

Generate Vertical

Phase 37 (D98/D100): the whole episode in 1080x1920 for TikTok. Needs the horizontal video first (same audio,
storyboard and cast).

- **Request body:** `GenerateVideoRequest`
- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/video/health`

Video Health

Whether the video renderer (Remotion, the only one since Task 35.5) can run, and if not, why.

- **Response body:** `object`

## visuals

### `GET /api/projects/{project_id}/visuals`

Get Project Visuals

- **Response body:** `object`
- **Parameters:** `project_id`

### `GET /api/projects/{project_id}/visuals/activity-coverage`

Activity Coverage

Explain selected/missing reusable activity illustrations before a talking-sprites render (Task 33.10: with the
closest library activities, the pending picture and the outside-AI prompt for each missing one).

- **Response body:** `object`
- **Parameters:** `project_id`

### `POST /api/projects/{project_id}/visuals/activity-illustrations`

Draw Activity Illustrations

D102: draw (local GPU) a pending library picture for every insert that has neither a match nor a pending picture.

- **Response body:** `object`
- **Parameters:** `project_id`

### `PUT /api/projects/{project_id}/visuals/cast`

Set Project Cast

- **Request body:** `CastMemberInput`
- **Response body:** `object`
- **Parameters:** `project_id`

### `PUT /api/projects/{project_id}/visuals/scenes`

Set Project Scenes

- **Request body:** `object`
- **Response body:** `object`
- **Parameters:** `project_id`

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

### `POST /api/visuals/characters/{character_id}/lock`

Lock Character

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

### `GET /api/projects/{project_id}/youtube/transcript.txt`

Download Transcript

Task 36.2 (D93): the full transcript as a text file, to attach or share with the episode.

- **Response body:** `object`
- **Parameters:** `project_id`
