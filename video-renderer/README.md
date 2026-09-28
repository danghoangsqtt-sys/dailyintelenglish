# video-renderer

Phase 19 (ENH-013) spike workspace — an isolated Node/TypeScript/React tree evaluating
Remotion as a replacement video renderer. **Never imported by `app/`.** Invoked only as a
subprocess, by `scripts/run_remotion_spike.py`.

See `.viepilot/phases/19-remotion/tasks/task-19.1.md` for the full design record and
`docs/operations/phase19-spike-remotion.md` for the measured results.

## Install

```
cd video-renderer
npm install
```

Requires Node `>=24.0.0` (owner's machine has v24.20.0) and npm (v11.19.0 tested). `engine-strict`
is on in `.npmrc`, so `npm install` fails loudly on an older Node instead of silently proceeding.

## Composition

One composition, `Episode` (`src/Root.tsx` / `src/Episode.tsx`): a solid-color background plus
a bottom-third subtitle band showing the active line's `speaker: text`, driven entirely by
input props (`src/types.ts`). Duration is computed from the input props' last line via
`calculateMetadata` — there is no fixed timeline.

## How it's invoked

`scripts/run_remotion_spike.py` does all of this; nothing here is meant to be run by hand
except for the typecheck below.

1. Selects a real completed project from `data/app.db` (read-only) and builds an
   `EpisodeInputProps` object.
2. Copies the project's mixed MP3 into `public/spike-audio/<episodeId>.mp3` — Remotion has no
   support for absolute filesystem paths as an asset `src`; every asset must live under
   `public/` and be loaded with `staticFile()`.
3. Writes the input props to a temp JSON file (never inline on the command line).
4. Runs, from this directory:

   ```
   npx remotion render src/index.ts Episode <outputPath> --props=<tempPropsPath>
   ```

5. Measures wall time around that subprocess call and parses Remotion's own reported render
   time and output size for the spike report.

## Typecheck

```
cd video-renderer
npm run typecheck
```
