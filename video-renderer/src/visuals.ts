import type { EpisodeLine, EpisodeVisuals } from "./types";

type ShotKind = "single" | "duo_close" | "duo_wide" | "insert";

const CROSSFADE_FRAMES = 10;
/** Task 24.6: a cut into or out of an insert (a change of picture world) fades more softly. */
const INSERT_CROSSFADE_FRAMES = 18;

/** Task 24.6: with few pictures per episode, motion carries the life between cuts, kept subtle (O8). */
export type ShotMotion = "zoom-in" | "zoom-out" | "pan-left" | "pan-right";
const MOTIONS: ShotMotion[] = ["zoom-in", "zoom-out", "pan-left", "pan-right"];
const ZOOM_GAIN = 0.05;
const PAN_SCALE = 1.06;
const PAN_SHIFT = 0.025; // fraction of the frame width; stays below (PAN_SCALE - 1) / 2 so no edge shows

/** Deterministic per shot id (no randomness: Remotion frames must be reproducible). */
export function shotMotion(id: string): ShotMotion {
  let hash = 0;
  for (let index = 0; index < id.length; index += 1) hash = (hash * 31 + id.charCodeAt(index)) >>> 0;
  return MOTIONS[hash % MOTIONS.length];
}

export function motionTransform(motion: ShotMotion, progress: number): { scale: number; x: number; y: number } {
  const t = Math.min(1, Math.max(0, progress));
  if (motion === "zoom-in") return { scale: 1 + ZOOM_GAIN * t, x: 0, y: 0 };
  if (motion === "zoom-out") return { scale: 1 + ZOOM_GAIN * (1 - t), x: 0, y: 0 };
  const from = motion === "pan-left" ? PAN_SHIFT : -PAN_SHIFT;
  return { scale: PAN_SCALE, x: from - 2 * from * t, y: 0 };
}

export function crossfadeFrames(kind: ShotKind | null, previousKind: ShotKind | null): number {
  return kind === "insert" || previousKind === "insert" ? INSERT_CROSSFADE_FRAMES : CROSSFADE_FRAMES;
}

export function vocabCardPosition(kind: ShotKind | null): "top-right" | "top-center" {
  return kind === "duo_close" || kind === "duo_wide" ? "top-center" : "top-right";
}

/** Index of the last line that has started by `time`, or -1 before the first line. Holding
 * the last started line keeps the shot on screen through the 300/500 ms inter-line pauses
 * (Task 1.6b) and after the last line (review r1 F1). */
function heldLineIndex(time: number, lines: EpisodeLine[]): number {
  let held = -1;
  for (let index = 0; index < lines.length; index += 1) {
    if (lines[index].startSec <= time) held = index;
    else break;
  }
  return held;
}

/** The background for `frame`. A run is a maximal sequence of consecutive lines sharing one
 * `lineShots` id: the crossfade happens only at a run start, and the 1.00 -> 1.04 zoom spans
 * the whole run, so consecutive lines on the same shot never jump back to 1.00. */
export function visualBackgroundForFrame(
  frame: number, fps: number, lines: EpisodeLine[], visuals: EpisodeVisuals,
): {
  current: string | null; previous: string | null; kind: ShotKind | null; opacity: number; scale: number;
  progress: number; transform: string;
} {
  const time = frame / fps;
  const index = heldLineIndex(time, lines);
  if (index < 0) {
    return { current: null, previous: null, kind: null, opacity: 1, scale: 1, progress: 0, transform: "none" };
  }
  const idAt = (i: number) => visuals.lineShots[i] ?? null;
  const id = idAt(index);
  let first = index;
  while (first > 0 && idAt(first - 1) === id) first -= 1;
  let last = index;
  while (last < lines.length - 1 && idAt(last + 1) === id) last += 1;
  const runStart = lines[first].startSec;
  const runEnd = lines[last].endSec;
  const shot = id ? visuals.shots[id] ?? null : null;
  const previousId = first > 0 ? idAt(first - 1) : null;
  const previousShot = previousId ? visuals.shots[previousId] ?? null : null;
  const previous = previousShot?.url ?? null;
  const fade = crossfadeFrames(shot?.kind ?? null, previousShot?.kind ?? null);
  const elapsedFrames = Math.max(0, frame - Math.round(runStart * fps));
  const progress = Math.min(1, Math.max(0, (time - runStart) / Math.max(1 / fps, runEnd - runStart)));
  const move = motionTransform(id ? shotMotion(id) : "zoom-in", progress);
  return {
    current: shot?.url ?? null,
    previous: elapsedFrames < fade ? previous : null,
    kind: shot?.kind ?? null,
    opacity: Math.min(1, elapsedFrames / fade),
    scale: move.scale,
    progress,
    transform: `translate(${(move.x * 100).toFixed(3)}%, ${(move.y * 100).toFixed(3)}%) scale(${move.scale.toFixed(4)})`,
  };
}
