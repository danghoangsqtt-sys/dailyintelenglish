// Phase 92 (D134-D136): the short muted example clip of every kind of video, shown on the kind cards of Step 1 and the
// Shorts batch page. Templates are rendered by this renderer from the sample props (renderer/src/sampleShort.ts) in
// Vietnamese and English; the 16:9 kinds are cut with ffmpeg from the owner's own videos (renderer/samples.json).
// Usage: npm run render:samples [-- kind ...]
import {build} from "esbuild";
import {bundle} from "@remotion/bundler";
import {renderMedia, renderStill, selectComposition} from "@remotion/renderer";
import {execFileSync} from "node:child_process";
import {copyFileSync, existsSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync} from "node:fs";
import {fileURLToPath, pathToFileURL} from "node:url";
import os from "node:os";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const out = path.resolve(root, "../frontend/static/samples");
const config = JSON.parse(readFileSync(path.join(root, "samples.json"), "utf-8"));
const only = new Set(process.argv.slice(2));
const BUDGET = 8 * 1024 * 1024;
const SCALE = 0.5;  // 1080x1920 -> 540x960 (sharp card text, still about 100 KB a clip)
mkdirSync(out, {recursive: true});

// sampleShort.ts is TypeScript: bundle it to a temporary module to call sampleProps from Node
const temp = path.join(os.tmpdir(), `samples-${process.pid}.mjs`);
await build({entryPoints: [path.join(root, "src/sampleShort.ts")], bundle: true, format: "esm", platform: "node", outfile: temp,
  logLevel: "warning"});
const {sampleProps} = await import(pathToFileURL(temp).href);
rmSync(temp, {force: true});

const indexPath = path.join(out, "index.json");
const index = existsSync(indexPath) ? JSON.parse(readFileSync(indexPath, "utf-8")) : {};
const size = (file) => statSync(path.join(out, file)).size;

const templates = Object.entries(config.templates).filter(([kind]) => !only.size || only.has(kind));
if (templates.length) {
  // the sample's silent track lives in the app's static folder; the renderer reads it from its own public folder
  const silence = path.join(root, "public", "samples-silence.mp3");
  copyFileSync(path.resolve(root, "../frontend/static/media/silence.mp3"), silence);
  const serveUrl = await bundle({entryPoint: path.join(root, "src/index.ts"), publicDir: path.join(root, "public")});
  rmSync(silence, {force: true});
  for (const [kind, spec] of templates) {
    const entry = {kind, aspect: "9:16"};
    for (const lang of spec.vi_only ? ["vi"] : ["vi", "en"]) {
      const props = sampleProps(kind, spec.idea, "B1", lang === "vi" ? "vietnamese" : "international");
      props.audioPath = "samples-silence.mp3";
      const composition = await selectComposition({serveUrl, id: "Episode", inputProps: props});
      const fps = composition.fps, total = composition.durationInFrames;
      const from = Math.min(Math.round((spec.from ?? 0.4) * fps), Math.max(0, total - 1));
      const to = Math.min(total - 1, from + Math.round((spec.seconds ?? config.seconds) * fps) - 1);
      const clip = `${kind}-${lang}.mp4`, poster = `${kind}-${lang}.jpg`;
      await renderMedia({composition, serveUrl, codec: "h264", inputProps: props, outputLocation: path.join(out, clip),
        frameRange: [from, to], scale: SCALE, muted: true, crf: 30, imageFormat: "jpeg", jpegQuality: 80});
      await renderStill({composition, serveUrl, inputProps: props, output: path.join(out, poster),
        frame: Math.min(to, from + Math.round(2 * fps)), scale: SCALE, imageFormat: "jpeg", jpegQuality: 80});
      entry[lang] = clip; entry[`poster_${lang}`] = poster;
      entry.seconds = Math.round(((to - from + 1) / fps) * 10) / 10;
      console.log(`${clip}: ${(size(clip) / 1024).toFixed(0)} KB, ${entry.seconds} s (of ${(total / fps).toFixed(1)} s)`);
    }
    // most sample templates read the same for both audiences: one file is kept when the two clips are identical
    if (entry.en && readFileSync(path.join(out, entry.en)).equals(readFileSync(path.join(out, entry.vi)))) {
      rmSync(path.join(out, entry.en)); rmSync(path.join(out, entry.poster_en)); delete entry.en;
    }
    if (!entry.en) { entry.en = entry.vi; entry.poster_en = entry.poster_vi; }
    index[kind] = entry;
  }
}

// D136: the 16:9 kinds, cut from the owner's own finished videos
for (const [kind, spec] of Object.entries(config.sources).filter(([kind]) => !only.size || only.has(kind))) {
  if (!existsSync(spec.file)) { console.warn(`${kind}: ${spec.file} not found, kept as it was`); continue; }
  const clip = `${kind}.mp4`, poster = `${kind}.jpg`, seconds = spec.seconds ?? config.seconds;
  execFileSync("ffmpeg", ["-loglevel", "error", "-y", "-ss", String(spec.from ?? 0), "-t", String(seconds), "-i", spec.file,
    "-an", "-vf", "scale=640:-2", "-c:v", "libx264", "-crf", "30", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    path.join(out, clip)]);
  execFileSync("ffmpeg", ["-loglevel", "error", "-y", "-ss", String((spec.from ?? 0) + 2), "-i", spec.file, "-frames:v", "1",
    "-vf", "scale=640:-2", "-q:v", "5", path.join(out, poster)]);
  index[kind] = {kind, aspect: "16:9", vi: clip, en: clip, poster_vi: poster, poster_en: poster, seconds};
  console.log(`${clip}: ${(size(clip) / 1024).toFixed(0)} KB`);
}

for (const entry of Object.values(index)) {
  entry.bytes = [...new Set([entry.vi, entry.en, entry.poster_vi, entry.poster_en])].reduce((sum, file) => sum + size(file), 0);
}
writeFileSync(indexPath, JSON.stringify(index, null, 2) + "\n");
const total = Object.values(index).reduce((sum, entry) => sum + entry.bytes, 0);
console.log(`total ${(total / 1024 / 1024).toFixed(2)} MB for ${Object.keys(index).length} kinds`);
if (total > BUDGET) { console.error(`over the ${BUDGET / 1024 / 1024} MB budget`); process.exit(1); }
