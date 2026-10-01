import type { EpisodeLine, EpisodeVisuals } from "./types";

export function vocabCardPosition(kind: "single" | "duo_close" | "duo_wide" | null): "top-right" | "top-center" {
  return kind === "duo_close" || kind === "duo_wide" ? "top-center" : "top-right";
}

export function visualBackgroundForFrame(
  frame: number, fps: number, lines: EpisodeLine[], visuals: EpisodeVisuals,
): { current: string | null; previous: string | null; kind: "single" | "duo_close" | "duo_wide" | null;
     opacity: number; scale: number } {
  const time = frame / fps;
  const index = lines.findIndex((line) => time >= line.startSec && time < line.endSec);
  if (index < 0) return { current: null, previous: null, kind: null, opacity: 1, scale: 1 };
  const id = visuals.lineShots[index];
  const shot = id ? visuals.shots[id] : null;
  const previousId = index > 0 ? visuals.lineShots[index - 1] : null;
  const previous = previousId && visuals.shots[previousId] ? visuals.shots[previousId].url : null;
  const elapsed = Math.max(0, frame - Math.round(lines[index].startSec * fps));
  const changed = id !== previousId;
  return {
    current: shot?.url ?? null,
    previous: changed ? previous : null,
    kind: shot?.kind ?? null,
    opacity: changed ? Math.min(1, elapsed / 10) : 1,
    scale: 1 + 0.04 * Math.min(1, elapsed / Math.max(1, (lines[index].endSec - lines[index].startSec) * fps)),
  };
}
