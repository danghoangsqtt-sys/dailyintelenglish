import type { EpisodeLine } from "./types";
import type { Gesture, SoloPayload } from "./soloTypes";

export function mediaUrl(value: string): string {
  // Absolute same-origin preview URLs and staged render paths use one explicit resolver.
  if (value.startsWith("/") || value.startsWith("http://127.0.0.1:") || value.startsWith("http://localhost:")) return value;
  return value;
}

/** Pure seed/frame selection; no mutable animation state, random calls or per-frame IO. */
export function presenterState(payload: SoloPayload, lines: EpisodeLine[], time: number, fps: number): {picture: string; segmentIndex: number} {
  let index = payload.timeline.findIndex((span) => time >= span.start_sec && time < span.end_sec);
  if (index < 0) index = time < payload.timeline[0].start_sec ? 0 : payload.timeline.length - 1;
  const span = payload.timeline[index], segment = payload.plan.segments[index];
  let gesture: Gesture = "calm";
  // Timeline cues already carry actual word-event seconds computed by the backend.
  const cues = span.gestures ?? [];
  const cue = [...cues].reverse().find((item) => item.at_sec <= time);
  if (cue && time - cue.at_sec < 1.8) gesture = cue.gesture;
  else if (time >= span.start_sec + .2 && time - span.start_sec < 1.5) gesture = "talk";
  const speaking = lines.some(line => line.words.some(word => time >= word.startSec && time < word.endSec));
  const frame = Math.floor(time * fps + 1e-7);
  const blink = gesture === "calm" && !speaking && (frame + index * 17) % Math.round(fps * 4.1) < Math.max(2, Math.round(fps * .12));
  const open = speaking && frame % 9 < 5;
  const closed = gesture === "calm" ? "calm__closed" : `gesture-${gesture}`;
  const picture = blink ? "blink" : open ? gesture === "calm" ? "calm__open" : `${closed}__open` : closed;
  if (!payload.pictures[picture]) throw new Error(`The pinned front pack has no ${picture}`);
  // Referencing the segment prevents accidentally selecting a cue from another plan revision.
  if (!segment || segment.id !== span.id) throw new Error("Solo timeline/segment identity mismatch");
  return {picture, segmentIndex: index};
}
