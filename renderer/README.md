# Studio video renderer

Production React/TypeScript/Remotion workspace for Daily Beyond English Studio.
The Python backend invokes this Node workspace as a subprocess through
`backend/media/video_renderer_remotion.py`. Remotion has been the sole video
renderer since Phase35; FFmpeg still handles audio, probes and media validation.

The private package version is independent of the application release version.
Published Windows trial:1.4.0-rc.1; source target:1.5.0 unreleased. Solo layout,
embedded Player and render/integrations are implemented and technically verified.
Real owner front21 pictures and V49 acceptance remain pending. The published ZIP
and the locally installed development trial are separate artifacts.

## Install

From the repository root in PowerShell:

```powershell
Set-Location renderer
npm.cmd ci
npx.cmd remotion browser ensure
npm.cmd run build:preview
```

Requires Node.js>=24.0.0; `.npmrc` enforces the engine requirement. FFmpeg/ffprobe
must be available to the backend. The Windows application links to this external
runtime; it does not bundle the full renderer/browser in its Python EXE.
`build:preview` generates `frontend/static/solo-preview/player.js` (ignored by Git).
Run it before packaging; `scripts/build_exe.ps1` installs dependencies, checks
types, builds Player and prepares the Remotion browser before PyInstaller.

## Compositions and inputs

`src/index.ts` registers `src/Root.tsx`, which defines two compositions:

- `Episode`: production video. `src/Episode.tsx` composes the selected podcast
  visuals, talking sprites, captions, learning accents and intro/outro. Input
  width/height/layout select horizontal or vertical output.
- `StillFrame`: a still image from the same episode input contract, used through
  Remotion's still-image path.

`src/types.ts` defines `EpisodeInputProps` and its runtime schema.
`calculateMetadata` derives dimensions, fps and duration from the inputs;
Episode includes intro and outro around the spoken-audio window. Word timings
come from actual project audio; the renderer does not synthesize replacement TTS.

## Backend invocation

The backend builds project props, stages required media under `public/` for
`staticFile()` access and writes a temporary JSON props file. It runs Remotion
from this directory with a bounded render deadline and diagnostics. It verifies
and publishes the attempt output through the backend media revision guards;
failed/stale attempts do not replace the previous valid project output.

The production command shape is:

```powershell
npx.cmd remotion render src/index.ts Episode <outputPath> --props=<propsJsonPath>
```

The backend owns extra browser/compositor/codec options, cleanup and retries; use
the app's Video step for production rendering. The old Phase19 spike runner was
removed and is not a runtime dependency.

## Development checks

From `renderer/`:

```powershell
npm.cmd test
npm.cmd run typecheck
```

Tests cover caption paging, karaoke, layout/safe zones, sprite timing, motion and
other deterministic helpers. Passing them does not replace real render checks or
owner visual acceptance. `@remotion/player` powers the embedded Solo editor bundle.
Player, Episode and StillFrame share `SoloScene` and real word timings; the preview
shows the content window while production also includes the branded intro/outro.
