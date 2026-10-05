import type { EpisodeLine, EpisodeVisuals } from "./types";

type ShotKind = "single" | "duo_close" | "duo_wide" | "insert";

const CROSSFADE_FRAMES = 10;
const ZOOM_GAIN = 0.04;

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
): { current: string | null; previous: string | null; kind: ShotKind | null; opacity: number; scale: number } {
  const time = frame / fps;
  const index = heldLineIndex(time, lines);
  if (index < 0) return { current: null, previous: null, kind: null, opacity: 1, scale: 1 };
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
  const previous = previousId ? visuals.shots[previousId]?.url ?? null : null;
  const elapsedFrames = Math.max(0, frame - Math.round(runStart * fps));
  const progress = Math.min(1, Math.max(0, (time - runStart) / Math.max(1 / fps, runEnd - runStart)));
  return {
    current: shot?.url ?? null,
    previous: elapsedFrames < CROSSFADE_FRAMES ? previous : null,
    kind: shot?.kind ?? null,
    opacity: Math.min(1, elapsedFrames / CROSSFADE_FRAMES),
    scale: 1 + ZOOM_GAIN * progress,
  };
}
