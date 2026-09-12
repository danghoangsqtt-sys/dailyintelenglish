# Task 1.8: Step 6 — Thumbnail Generator

## Meta
- **ID**: 1.8
- **Phase**: 1
- **Status**: in_progress (Sub-task 1.8a done)
- **Priority**: medium
- **Assignee**: AI (Codex)

## Paths
- `app/services/thumbnail_service.py`
- `app/api/thumbnail.py`
- `frontend/pages/step6_thumbnail.html`
- `frontend/static/js/step6_thumbnail.js`

## Acceptance Criteria
- [x] 5 Pillow thumbnail templates (minimal, bold, split, dark, educational) — deterministic, PM-verified visually (see PM Acceptance)
- [x] AI prompt generation for headline & color palette via Gemini — `responseJsonSchema` contract, exact-count + duplicate-rejection validation
- [ ] Interactive manual text editor and layout tweaks — deferred to Sub-task 1.8b
- [x] Export 1280x720 PNG/JPG — done, plus 720x1280 (bonus, matches ROADMAP's "both aspects" note)

## Forbidden Scope
- No blocking filesystem operations
- No hardcoded font paths that fail cross-platform

## Verification Commands
- `venv\Scripts\python -m pytest tests/`

## Implementation Notes (2026-09-12, proposed split for PM review)

### Environment preflight

Command:
`venv\Scripts\python -c "from PIL import Image, ImageDraw, ImageFont; import PIL; ..."`

```text
PILLOW_IMPORT_OK=True
PILLOW_VERSION=12.3.0
IMAGEFONT_DEFAULT_OK=True
```

A second font-specific probe returned:

```text
FreeTypeFont
<_io.BytesIO object at 0x000001F363695580>
(0, 17, 575, 85)
```

Repository inventory returned `FONT_FILE_COUNT=0`; both `prompts/thumbnail/` and
`frontend/static/thumbnail_templates/` contain only `.gitkeep`.

### Proposed task split

- **Sub-task 1.8a — backend generation vertical slice (proposed now):** strict Gemini text
  suggestions, five deterministic Pillow template assets/configs, 3-5 meaningful A/B
  variants, PNG/JPG rendering at 1280x720 and 720x1280, filesystem + SQLite persistence,
  list/template/content APIs, and backend tests. No browser UI in this slice.
- **Sub-task 1.8b — interactive UI (separate plan/review after 1.8a):** template gallery,
  generate workflow, select-favorite behavior, manual headline/color/layout editor,
  re-render/save APIs, preview/download controls, async/race guards, reload persistence, and
  Playwright coverage for happy/error/reload/race paths.

This split makes the deterministic rendering/API contract reviewable before the UI builds on
it, while keeping every full Task 1.8 acceptance criterion assigned to one of the two slices.

### Font decision for Sub-task 1.8a

Use `PIL.ImageFont.load_default(size=...)`, available because the project requires
Pillow >= 10.4. The preflight proves Pillow 12.3.0 returns a scalable in-memory
`FreeTypeFont`, so rendering has no hardcoded system path, no Windows font assumption, and no
new binary/license dependency. Generated headlines are English, matching the product domain.
Font loading will be isolated behind one helper so a bundled OFL font can replace it later
without changing renderer call sites. No fallback will silently substitute a missing system
font because no system font is requested in the first place.

### Template mapping

Use ROADMAP-compatible IDs/files while covering the five task-card styles:

- `minimal_clean` → minimal
- `gradient_bold` → bold
- `modern_split` → split
- `dynamic_wave` → dark/dynamic
- `podcast_classic` → educational/podcast

Each template has one checked-in 1280x720 grayscale PNG base plus one JSON layout config.
Pillow colorizes the base with each Gemini palette and overlays text using normalized zones,
so the same config can render 16:9 and 9:16 without a machine-specific asset pipeline. A
deterministic generator script makes the five binary base images reproducible and testable.

### Sub-task 1.8a behavior and approach

1. Add Pydantic request/output/config models. Gemini output is a pack of 3-5 distinct variants,
   each containing a nonblank bounded English headline, optional supporting text/topic keywords,
   and strict hexadecimal primary/secondary/accent/text colors. Pydantic semantic validation
   rejects duplicate or invalid variants.
   `ThumbnailGenerateRequest.template_name` is required and must be one of the five approved
   template IDs. If Gemini returns `N` suggestions, suggestion `i` creates exactly one database
   row with `variant_index=i` and `template_name=request.template_name`; that suggestion is
   rendered only with the selected template. Therefore one generation batch always creates
   exactly `N` thumbnail rows (`3 <= N <= 5`), never `N x 5`. Each row owns four derivative
   files (16:9 PNG/JPG and 9:16 PNG/JPG), which do not create additional database rows.
2. Add one Jinja2 prompt file and async prompt-loader entry point. The Gemini REST call follows
   the existing Script/Learning pattern: `responseMimeType=application/json`,
   `responseJsonSchema=<Pydantic JSON schema>`, 429-only exponential backoff, prompt-hash/token/
   latency logging, no prompt/key logging, and Pydantic validation after JSON parsing. Tests
   monkeypatch the network layer; a real key is not required.
3. Load and validate template JSON, load/colorize its grayscale PNG, render text with wrapping
   and fit-to-zone sizing, and export lossless PNG plus flattened RGB JPEG for both 1280x720 and
   720x1280. All Pillow and filesystem work runs in `asyncio.to_thread`.
4. Store outputs under `settings.DATA_DIR / "thumbnails" / project_id / variant_id/` with a
   JSON sidecar containing the validated render specification. Persist the existing
   `thumbnails` table rows without a migration; JPG paths are derived from the same safe
   variant directory/stem while the existing DB columns retain canonical PNG paths.
5. Render a complete replacement set before entering the connection-wide DB write transaction.
   Insert the new rows atomically; on render/DB failure, remove only the new set. After a
   successful commit, remove superseded files. Never hold a DB lock across Gemini or Pillow.
6. Expose the three documented endpoints (`POST .../thumbnails/generate`,
   `GET .../thumbnails`, `GET /api/thumbnails/templates`) plus one narrowly scoped safe content
   route needed to consume generated images without mounting all runtime data:
   `GET /api/projects/{project_id}/thumbnails/{thumbnail_id}/{aspect}.{format}` where aspect and
   format are validated enums. Add that content route to ARCHITECTURE in the same slice.

### Proposed `allowed_files` for Sub-task 1.8a

- `.viepilot/phases/01-full-feature-build/tasks/task-1.8.md` — plan/evidence only; never change
  task status or acceptance checkboxes.
- `.viepilot/ARCHITECTURE.md` — add only the approved thumbnail content route if PM approves it.
- `app/core/constants.py` — thumbnail dimensions, variant bounds, JPEG quality, template IDs.
- `app/core/exceptions.py` — typed `ThumbnailGenerationError`.
- `app/core/prompt_loader.py` — isolated thumbnail Jinja environment/render function.
- `app/models/thumbnail.py` — strict API, Gemini-output, template, render, and response models.
- `app/services/thumbnail_service.py` — Gemini suggestions, rendering, persistence, cleanup,
  listing, template discovery, and safe content resolution.
- `app/api/thumbnail.py` — thin async routes using `_read_transaction`/
  `_write_transaction`, with Gemini/Pillow work outside DB locks.
- `app/main.py` — register the thumbnail router only.
- `prompts/thumbnail/thumbnail_suggestions.txt` — the sole Gemini prompt source.
- `scripts/generate_thumbnail_template_assets.py` — deterministic grayscale PNG generator.
- `frontend/static/thumbnail_templates/modern_split.png`
- `frontend/static/thumbnail_templates/modern_split.json`
- `frontend/static/thumbnail_templates/gradient_bold.png`
- `frontend/static/thumbnail_templates/gradient_bold.json`
- `frontend/static/thumbnail_templates/minimal_clean.png`
- `frontend/static/thumbnail_templates/minimal_clean.json`
- `frontend/static/thumbnail_templates/dynamic_wave.png`
- `frontend/static/thumbnail_templates/dynamic_wave.json`
- `frontend/static/thumbnail_templates/podcast_classic.png`
- `frontend/static/thumbnail_templates/podcast_classic.json`
- `tests/test_thumbnail_prompt.py`
- `tests/test_thumbnail_service.py`
- `tests/test_thumbnail_api.py`

No frontend page/JS, browser route, manual editor, selection endpoint, audio/video integration,
system-font lookup, real Gemini call, task status update, commit, push, or unrelated refactor is
included in Sub-task 1.8a.

### Risks and limits

- The task card and ROADMAP use different template labels; the explicit mapping above avoids
  creating ten overlapping templates and requires PM confirmation.
- The extra content route is absent from the current architecture but is required for any UI to
  display runtime files safely. It will not accept arbitrary filenames or paths.
- Lightweight default-font coverage is appropriate for English headlines but not guaranteed for
  arbitrary multilingual glyphs; adding Inter later would require committed TTF files and OFL
  license text as an explicitly approved asset change.
- Filesystem output and SQLite cannot share one physical transaction. The staged-new-set,
  DB-transaction, cleanup-old-set sequence minimizes orphan/data-loss risk and needs explicit
  failure-path tests.
- JPEG has no alpha channel; export must flatten onto the variant background before saving.
- The known unrelated retry/backoff flaky test may recur only in the full suite. If it does,
  report its exact output and isolated rerun without changing it under this task.

### Verification commands for Sub-task 1.8a

- `venv\Scripts\python scripts/generate_thumbnail_template_assets.py --check`
- `venv\Scripts\python -m pytest tests/test_thumbnail_prompt.py -q`
- `venv\Scripts\python -m pytest tests/test_thumbnail_service.py -q`
- `venv\Scripts\python -m pytest tests/test_thumbnail_api.py -q`
- `venv\Scripts\python -m pytest tests/ -q`
- `venv\Scripts\python -m ruff check app/ tests/ scripts/generate_thumbnail_template_assets.py`
- `git diff --check`

PM approved the split, font decision, five-template mapping, content route, and bounded
`allowed_files`. PM then approved the clarified one-row-per-suggestion mapping in step 1;
implementation proceeded only after that approval.

## Implementer Evidence (2026-09-12, awaiting PM acceptance)

### Implemented scope

- Added a strict Gemini JSON-schema/Pydantic contract for 3-5 distinct headline and palette
  suggestions. The network path follows the existing 429-only retry pattern and does not log
  prompt text or API keys.
- Added five deterministic Pillow templates and validated JSON layouts. Rendering uses Pillow's
  scalable in-memory default font, produces 1280x720 and 720x1280 derivatives, and exports both
  PNG and RGB JPEG without any system font path, ffmpeg, pydub, GPU, or real Gemini dependency.
- Added exactly-one-template-per-batch persistence: suggestion `i` maps to one row with
  `variant_index=i`; each row owns four derivative files. Regeneration stages the full new set,
  atomically replaces the SQLite rows, cleans failed new sets, and removes superseded files only
  after commit.
- Added template discovery, generation, project listing, and validated content routes. Public API
  records expose content URLs and render metadata, not local filesystem paths.
- Added focused prompt/service/API coverage, including all five templates and both aspect ratios,
  exact-N row behavior, invalid Gemini payloads/counts, cleanup on partial render failure,
  regeneration cleanup, missing projects, invalid content parameters, media types, and prevention
  of local-path disclosure.
- Visually inspected real 16:9 and 9:16 rendered PNGs from the test output: text sizing/wrapping,
  palette application, portrait crop, template composition, and accent rendering were valid.
- Updated only the approved Thumbnail route line in `ARCHITECTURE.md`. No task status, acceptance
  checkbox, tracker, commit, push, tag, frontend editor, or unrelated code was changed.

### Changed files

- `.viepilot/phases/01-full-feature-build/tasks/task-1.8.md`
- `.viepilot/ARCHITECTURE.md`
- `app/core/constants.py`
- `app/core/exceptions.py`
- `app/core/prompt_loader.py`
- `app/models/thumbnail.py`
- `app/services/thumbnail_service.py`
- `app/api/thumbnail.py`
- `app/main.py`
- `prompts/thumbnail/thumbnail_suggestions.txt`
- `scripts/generate_thumbnail_template_assets.py`
- `frontend/static/thumbnail_templates/{minimal_clean,gradient_bold,modern_split,dynamic_wave,podcast_classic}.{png,json}`
- `tests/test_thumbnail_prompt.py`
- `tests/test_thumbnail_service.py`
- `tests/test_thumbnail_api.py`

### Verification evidence

`venv\Scripts\python scripts/generate_thumbnail_template_assets.py --check`

```text
OK: 5 thumbnail template assets match deterministic sources
```

`venv\Scripts\python -m pytest tests/test_thumbnail_prompt.py -q`

```text
......                                                                   [100%]
6 passed in 0.53s
```

`venv\Scripts\python -m pytest tests/test_thumbnail_service.py -q`

```text
...........                                                              [100%]
11 passed in 1.43s
```

`venv\Scripts\python -m pytest tests/test_thumbnail_api.py -q`

```text
..........                                                               [100%]
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
10 passed, 2 warnings in 3.98s
```

`venv\Scripts\python -m pytest tests/ -q`

```text
........................................................................ [ 24%]
........................................................................ [ 48%]
........................................................................ [ 72%]
........................................................................ [ 96%]
..........                                                               [100%]
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
298 passed, 2 warnings in 65.68s (0:01:05)
```

`venv\Scripts\python -m ruff check app/ tests/ scripts/generate_thumbnail_template_assets.py`

```text
All checks passed!
```

`git diff --check`

```text
warning: in the working copy of '.viepilot/ARCHITECTURE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of '.viepilot/phases/01-full-feature-build/tasks/task-1.8.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/core/constants.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/core/exceptions.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/core/prompt_loader.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/main.py', LF will be replaced by CRLF the next time Git touches it
```

The warnings above are Git's line-ending notices and the two pre-existing TestClient dependency
deprecations; no verification command failed. Sub-task 1.8b remains unimplemented and requires a
separate PM-approved plan.

## PM Acceptance (2026-09-12)

Independently re-verified, not just trusted:
- `pytest tests/` (full suite): 298 passed (matches). `ruff check app/ tests/ scripts/`: clean (matches).
- Re-derived the variant→template resolution myself from `app/models/thumbnail.py` +
  `app/api/thumbnail.py` before reading the plan's restated answer: `ThumbnailGenerateRequest.template_name`
  is a required, validated field; `generate_thumbnails` calls `render_batch(project_id, template, suggestions.variants)`
  with that one template for the whole batch — confirms my requested clarification is resolved correctly
  and matches the existing `thumbnails` table shape (one row per `(template_name, variant_index)`).
- **Independently rendered real images**, not just trusted the "visually inspected" claim: called
  `_render_image` directly for all 5 templates with test suggestions/palettes and viewed the actual PNGs.
  All 5 are genuinely distinct, professional-looking, and thematically appropriate (podcast_classic even
  has a microphone icon); text wrapping/shrink-to-fit works correctly on both 16:9 and 9:16 independently.
- Read `_render_batch_sync`/`generate_thumbnails`: new files are rendered into fresh UUID directories
  before the DB write transaction opens; on a DB failure the except-branch cleans up only the new set
  (`cleanup_rows(rendered)`) and re-raises, leaving old rows/files untouched; old files are removed only
  *after* a successful commit. This is the correct ordering — a crash can only ever orphan harmless new
  files, never lose the existing set.
- Read `_public_record`/`resolve_content_path`: API responses expose `/api/projects/{id}/thumbnails/{id}/{aspect}.{format}`
  URLs only, never a raw filesystem path; `_resolve_content_sync` re-checks path containment via
  `.resolve()` + `parents` even though inputs are already server-controlled — good defense in depth.
- `tests/test_thumbnail_service.py::test_render_failure_removes_every_partial_variant_directory`
  genuinely forces a mid-batch failure and asserts the partial directory is gone — not just a
  happy-path-only test suite.

All PM-required items from the plan-review round are satisfied. **Accepted.** This closes Sub-task 1.8a.
Full Task 1.8 stays `in_progress` — the interactive manual editor (Sub-task 1.8b) is next, pending its
own plan and PM review.

## Implementation Notes (2026-09-12, Sub-task 1.8b plan for PM review)

### Environment and UI preflight

`node --version` and a real syntax check against an existing project script returned:

```text
v24.20.0
NODE_CHECK_OK=True
```

Python Playwright and its installed Chromium were verified by launching and closing a real
headless browser, not by import-only inspection:

```text
PLAYWRIGHT_IMPORT_OK=True
CHROMIUM_EXECUTABLE=C:\Users\Admin\AppData\Local\ms-playwright\chromium-1234\chrome-win64\chrome.exe
CHROMIUM_EXISTS=True
CHROMIUM_LAUNCH_OK=True
CHROMIUM_VERSION=151.0.7922.34
```

There is no root `design.md` and no Step 6 binding in `.viepilot/PROJECT-CONTEXT.md`; the page
will therefore follow the existing Step 2/3 page structure and shared tokens in
`frontend/static/css/style.css`, without changing the shared stylesheet.

### Proposed API contract

1. `PUT /api/projects/{project_id}/thumbnails/{thumbnail_id}/favorite`
   - No request body. Idempotently sets the target row to `is_selected=1` and every other row
     for that project to `0` in one `_write_transaction`.
   - Rejects a missing thumbnail or a thumbnail owned by another project with 404.
   - Returns the selected public thumbnail record so the client can reconcile state.
2. `PATCH /api/projects/{project_id}/thumbnails/{thumbnail_id}`
   - Accepts the complete manually editable subset: `revision`, `headline`, and the four-color
     `palette` (`primary`, `secondary`, `accent`, `text`). Headline and colors reuse the strict
     bounds/hex validation already used for Gemini output.
   - Loads the persisted sidecar, merges only those editable fields, and preserves
     `supporting_text`, `topic_keywords`, `template_name`, `variant_index`, row id, and
     `is_selected`.
   - Renders a fresh four-file revision in a new UUID directory outside the DB lock. Inside one
     `_write_transaction`, a compare-and-swap update succeeds only when the submitted
     `revision` still matches the DB row. On a stale revision it returns typed HTTP 409 and
     deletes only the newly staged revision; it never overwrites the newer edit.
   - After commit, removes the superseded revision directory and returns the updated public
     record. A DB failure removes the staged revision and leaves the previous row/files intact.

Public thumbnail records will gain a non-secret `revision` token derived from the current render
directory. Asset URLs will carry that token as a query parameter so browsers do not display a
cached pre-edit image at the otherwise stable content URL. The existing batch-generate route and
one-row-per-suggestion behavior remain unchanged.

### Layout-tweak scope decision

For Sub-task 1.8b, “layout tweaks” means:

- choose one of the five layouts/templates before batch generation;
- edit the selected variant's headline, which naturally re-wraps and shrink-fits within the
  template's approved text zone; and
- edit its primary, secondary, accent, and text colors with color inputs.

The editor will not expose free-form drag/drop, text-zone coordinates, font selection,
supporting-text/topic-keyword editing, arbitrary add/remove elements, or post-generation template
swapping. Those controls would require a new persisted layout schema and substantially expand
the renderer/API contract. The five checked-in templates remain the source of safe text zones and
composition.

### UI behavior and implementation approach

1. Add `/step6` in `app/main.py` and a new Step 6 page using the existing shared theme and page
   conventions. The page contains project context, five-template gallery, a 3-5 variant selector,
   Generate/Regenerate control, variant gallery, explicit favorite selection, aspect preview
   toggle, manual editor, save status/retry UI, and PNG/JPG download links for both 16:9 and 9:16.
2. Add all thumbnail calls to `frontend/static/js/api.js`; `step6_thumbnail.js` will never call
   `fetch()` directly and will never surface raw backend validation text in the DOM.
3. Initialization loads project, templates, and existing thumbnails. A thumbnail-list failure
   hides destructive generation controls rather than presenting a false empty state. Reload
   restores variants, selected favorite, latest edited suggestion/revision, preview, and download
   links. When rows exist, their template is reflected in the gallery; generating with a different
   selected template requires confirmation because it replaces the batch.
4. Clicking a variant/favorite control selects exactly one favorite through the idempotent route
   and opens that row in the editor. Only the persisted favorite is styled selected; controls show
   loading/disabled state during the request.
5. Headline/color edits mark the editor dirty and schedule a short debounced re-render. “Save &
   Re-render” flushes immediately. There is at most one PATCH in flight; changes made during it set
   `saveQueued` and produce one trailing save containing the latest editor state and the revision
   returned by the prior save. Failed saves retain the draft and expose a friendly Retry action.
6. Generation has a double-submit lock. Generate/favorite/card switching/download actions are
   disabled while editor changes are dirty, saving, queued, or failed, preventing state crossover.
   A `beforeunload` handler guards dirty/saving/queued/failed edits. A 409 stale-edit response is
   logged for diagnostics but shown as a friendly reload/retry message.
7. Download controls are ordinary same-origin links to the already validated content route, with
   explicit filenames and the current revision query token. No client-side canvas/image mutation
   or blob duplication is introduced.

### File-level plan and proposed `allowed_files`

- `.viepilot/phases/01-full-feature-build/tasks/task-1.8.md` — this approved plan and later raw
  implementer evidence only; no status/checkbox/PM Acceptance edits.
- `.viepilot/ARCHITECTURE.md` — add only the two proposed mutation routes under Thumbnails.
- `app/core/exceptions.py` — add a typed 409 conflict exception for stale thumbnail revisions.
- `app/models/thumbnail.py` — add the strict manual-edit request/revision contract.
- `app/services/thumbnail_service.py` — revision hydration, sidecar loading/merge, single-row
  staged re-render, optimistic DB update, exclusive favorite selection, and cleanup helpers.
- `app/api/thumbnail.py` — add thin favorite and manual-edit routes; keep Pillow/filesystem work
  outside transactions and reuse `_read_transaction`/`_write_transaction`.
- `app/main.py` — add only the `/step6` page route.
- `frontend/pages/step6_thumbnail.html` — Step 6 gallery/editor/preview/download markup and
  page-local responsive styles built from existing shared CSS variables.
- `frontend/static/js/api.js` — centralized thumbnail list/generate/favorite/edit API methods.
- `frontend/static/js/step6_thumbnail.js` — page state, rendering, validation, serialized trailing
  saves, double-submit/loading locks, friendly errors, cache-busted preview, and unload guard.
- `tests/test_thumbnail_service.py` — single-revision render/cleanup and optimistic-update tests.
- `tests/test_thumbnail_api.py` — favorite exclusivity/idempotence, edit/persistence/content,
  validation, stale revision, ownership, and rollback/cleanup coverage.
- `tests/test_thumbnail_browser.py` — real Chromium coverage for template/generate flow,
  double-submit lock, favorite/reload persistence, edit/re-render coalescing, save recovery,
  beforeunload guard, friendly-only errors, preview/aspect switching, and download targets.

No migration, shared CSS edit, prompt/Gemini change, batch-generate redesign, arbitrary layout
schema, drag/drop canvas, Step 5/7 implementation, task-state update, tracker update, commit, push,
tag, or unrelated refactor is included.

### Risks and mitigations

- **Filesystem/SQLite cannot be one physical transaction:** stage a new revision first, CAS-update
  the row under the write lock, delete staged files on failure, and delete old files only after a
  successful commit.
- **Late responses can clobber a newer edit:** server revision matching rejects stale writes with
  409; the client serializes requests and reuses the revision from each successful response.
- **Stable image URLs can show stale browser cache:** append the public revision token to preview
  and download URLs.
- **Color inputs can emit many events:** debounce plus one in-flight/one trailing-save coalescing
  bounds Pillow renders while retaining the latest values.
- **Generate replaces the whole batch:** confirm when variants already exist, and block generation
  whenever an editor save is unresolved.
- **Existing row sidecars have no explicit revision field:** derive the initial token from the
  canonical image directory, so all 1.8a output remains backward-compatible without migration.
- **Browser tests can become timing-sensitive:** await DOM/network states rather than fixed sleeps;
  use controlled route delays only to prove locking/coalescing behavior.

### Verification commands

- `venv\Scripts\python -m pytest tests/test_thumbnail_service.py -q`
- `venv\Scripts\python -m pytest tests/test_thumbnail_api.py -q`
- `venv\Scripts\python -m pytest tests/test_thumbnail_browser.py -q`
- `venv\Scripts\python -m pytest tests/ -q`
- `venv\Scripts\python -m ruff check app/ tests/ scripts/generate_thumbnail_template_assets.py`
- `node --check frontend/static/js/api.js`
- `node --check frontend/static/js/step6_thumbnail.js`
- `git diff --check`

Implementation is paused pending explicit PM approval of the route contract, layout-tweak scope,
behavior, risks, and bounded `allowed_files` above.

## PM Plan Approval (2026-09-12, Sub-task 1.8b)

APPROVED as proposed — no changes required. Notably strong points verified by reading the
actual reasoning, not just skimming: the `revision` compare-and-swap on `PATCH` correctly
prevents a stale edit from clobbering a newer one (a race I had not explicitly asked for but
is clearly necessary once concurrent/rapid edits are possible); appending `revision` as a
query token on asset URLs correctly fixes a real cache-invalidation bug (stable content URL,
changed bytes) that the 1.8a design did not need to consider since it never re-rendered a row
in place. Layout-tweak scope (headline + 4 colors only, no drag/drop/template-swap) is
explicit and reasonable. Backward compatibility for 1.8a's existing rows (deriving the initial
revision from the current canonical directory, no migration) is correct.

Proceed to implementation as planned.
