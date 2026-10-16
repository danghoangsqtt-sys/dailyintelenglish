# Phase49 — implementation and verification,2026-10-16

Owner authorized vp-auto to finish49.6–49.10 and confirmed no real front21 images exist. Owner additionally requested explicit per-action upload cards and strict external-AI prompts in the character profile. Real-art demonstration and owner V49 sign-off remain pending. Fixture evidence is technical verification only; published trial1.4.0-rc.1 and target1.5.0 are distinct.

## Implementation

- Shared versioned JSON rules define16:9/9:16 safe regions, reserved captions/header, portrait platform button column, readable card budgets and anchor candidates. Python proves all21 alpha extents and the full swept motion envelope. TypeScript uses the same dimensions and monotonic interpolation; unsafe moves fall back to cuts. Owner layout locks are preserved.
- Read-only `/explainer-plan/layout` suggestions require revision/source CAS. PATCH explicitly saves/locks edits; approval pins actual geometry, immutable front21/illustrations, real audio hashes and token timing. `/explainer-plan/preview` returns scoped browser URLs, with no internal file paths.
- Vanilla Step5 editor embeds a built Remotion Player widget. It serializes/trails autosave, flushes before operations, locks double submissions and active-operation fields, retains local drafts on409, and guards dirty navigation. Photo protected regions, diagrams/cards, gestures, factual review and locks are editable.
- Shared SoloScene, Presenter, ExplainerVisual and CaptionBand render both preview and production. Mouth follows actual word events; bounded gestures/rests/blinks/breathing are deterministic under seek. StillFrame uses SoloScene. Zero-length branded sequences are omitted for content preview. `durationSeconds` preserves the real audio tail rather than ending at the last spoken word.
- Production stages checked image bytes into an isolated attempt folder. Media publication fingerprints include plan revision/status and live source so concurrent layout/front changes cannot promote stale video or Shorts. Classic props remain on the existing branch.
- Additive029 migration stores series mode/structure, defaultclassic. Solo series creates one-presenter projects with independent IDs. Copy settings preserves current voice/cast identity pins while creating a fresh draft with no inherited plan approval/media. Solo thumbnail uses one front presenter without mirroring; YouTube and Shorts copy distinguish a knowledge monologue. Export adds portable plan/revision metadata and approved image files.
- Build installs locked renderer dependencies and builds the static Player before PyInstaller; the spec refuses a missing bundle. Generated widget files remain ignored and are included in frozen resources through frontend/.
- Actual frozen production trials exposed a Windows cp1252 decoder failure on Remotion Unicode logs and a Player font URL reaching `/fonts/` instead of `/static/fonts/`. The renderer explicitly decodes UTF-8 with replacement for malformed diagnostics; the preview build supplies its static asset base before imported font loaders run.

## Commands and evidence

Focused checks executed during implementation:24 layout/bridge/channel/editor checks and12 integration/editor/front-browser checks passed. Renderer124 tests passed after correcting deterministic frame quantization. Final combined results, actual media comparison, staged EXE and limitations appear below.

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
npm --prefix renderer test -- --run
npm --prefix renderer run typecheck
npm --prefix renderer run build:preview
.venv\Scripts\python.exe scripts/verify_solo_media.py
powershell -File scripts/build_exe.ps1 -OutputRoot data/tmp/phase49-exe-stage
```

`scripts/verify_solo_media.py` installs the test suite's owner-DB/cloud guards, creates a unique disposable database, synthetic front images and encoded silent audio, then renders baseline/landscape/portrait/Short using the real renderer. It probes/fully decodes outputs and compares actual Player seek screenshots to StillFrame at the same frames for all three visual types. Evidence lives under `data/tmp/phase49-20261016/`; no real owner image is fabricated or marked accepted.

## Measured fixture media

Final content-window evidence: `data/tmp/phase49-20261016/run-1792146554329808400/` and `report.json` in its parent. Real Chromium Player screenshots and Remotion StillFrame were compared at frames15/78/110 for both aspects, covering text card/diagram/photo. Mean RGB absolute differences were0.326–0.522 on a255-level channel scale; the same geometry/timing/pose/caption was used. Browser transport was excluded from composition comparison.

| Fixture | Frames | Encoded duration | Audio/video stream duration difference | Render wall time |
|---|---:|---:|---:|---:|
| Classic baseline1280×720 |135|4.544s|0.044s|6.259s|
| Solo1280×720 |135|4.544s|0.044s|6.047s|
| Solo1080×1920 |135|4.544s|0.044s|7.295s|
| Solo short frame window1080×1920 |84|2.859s|0.059s|7.626s|

All four MP4 files were fully decoded by FFmpeg without errors. These are tiny synthetic/silent fixtures; the2.8s Short checks frame-window mechanics, while the existing user-facing Short length policy remains30–90s. These measurements do not establish full-episode speed or real speaker/art quality.

The first frozen production API trial also successfully generated/downloaded both branded outputs and an SRT with both source lines plus intro offset. Each output lasted21.227s, with0.060s stream duration difference and complete FFmpeg decode. Landscape105.24s included cold runtime/browser preparation and brand setup; portrait21.19s reused cache. They are not comparable speed baselines. The Windows decoder/font-base fixes found during this trial passed in the rebuilt stage. Because npm ci clears the browser inside node_modules, the build now explicitly ensures the Remotion browser before packaging.

## Remaining owner evidence

Owner needs to generate/import/review the21 Hoang front images using Character Library → Presenter21, review the knowledge content, and visually accept a real landscape/portrait/Short demonstration. B-25/B-26/B-27/B-28 and Phase47 review remain separately pending. No installed owner EXE is replaced, no new release published, and no V49 acceptance claimed by this implementation.

## Final quality and frozen evidence

Feature full pytest 1867 passed in779.20s. Post-Windows-UTF8 full run:1862 passed,5 legacy subprocess mock-signature failures; all40 video/bridge checks passed in7.95s after updating those5 mocks, with no further application-code change.124 renderer tests, TypeScript/Ruff/JS/diff clean. Actual Player/StillFrame6 comparisons, four decoded fixture MP4s, two frozen restarts and production landscape/portrait/SRT verified. Real owner art/V49 acceptance pending.

Latest full log: `data/tmp/phase49-pytest-final.log`. First combined run also passed1867 in779.20s. Final frozen stage EXE SHA-256: `09d2ea4f7b5b4d6047598c15266f90f6149c76e968e136eaf194c8d08458fafe`. Both latest launches read the bundled1030320-byte widget, played/paused/sought actual content, preserved approved revision3/front21, and opened/reloaded a fresh no-audio Solo editor. Fresh desktop log segments contain zero Unicode decoder exceptions and zero unscoped font requests.

Final frozen production API timing: landscape104.88s, portrait22.31s, including download/decode checks; landscape includes Chrome download after npm ci. Both durations21.227s, drift0.060s. Both Solo composed thumbnail sizes1280×720 and720×1280 rendered with one pinned front presenter.

Hardware/runtime: Windows11, Intel Core i7-12700, RTX3060 12288MiB, Node24.20.0, Python3.14.7. The staged build was made from the source worktree with build-info source_dirty=true; it is an implementation trial, not a new release. Build browser-ensure step additionally executed successfully and PowerShell syntax validated. Git checkpoint/tags are recorded after verification.

## Git persistence

Implementation commit `c517eca6181578329af690fe7470c90682a329bf` pushed to `origin/owner-runs/20261001-r9`; branch and all four annotated technical tags49.6/49.7/49.8/49.9 were independently verified via ls-remote. Source branch divergence was0/0 and worktree clean before this documentation checkpoint. No49.10 done, phase-complete or release tag was created. Owner V49 is still pending.
