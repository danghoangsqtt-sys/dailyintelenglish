import type { EpisodeLine } from "./types";
import type { Gesture, SoloPayload } from "./soloTypes";

export function mediaUrl(value: string): string {
  // Absolute same-origin preview URLs and staged render paths use one explicit resolver.
  if (value.startsWith("/") || value.startsWith("http://127.0.0.1:") || value.startsWith("http://localhost:")) return value;
  return value;
}

type Word = {text: string; startSec: number; endSec: number};
/** Phase 61 (ENH-043): the presenter's own rhythm between planned cues -- talk, rest, talk, emphasize, rest, one per phrase. */
export const PHRASE_GESTURES: Gesture[] = ["talk", "calm", "talk", "emphasize", "calm"];
const PHRASE_HOLD_SEC = 2.0;

/** The spoken phrases of a segment: words split at a pause of 0.25 s or after 2.2 s. */
export function segmentPhrases(lines: EpisodeLine[], start: number, end: number): Word[][] {
  const words = lines.flatMap(line => line.words).filter(word => word.startSec >= start && word.startSec < end);
  const phrases: Word[][] = [];
  words.forEach(word => {
    const group = phrases.at(-1), last = group?.at(-1);
    if (!group || !last || word.startSec - last.endSec >= .25 || word.endSec - group[0].startSec > 2.2) phrases.push([word]);
    else group.push(word);
  });
  return phrases;
}

/** The phrase gesture at `time` (from the phrase start for up to 2 s), "calm" outside phrases or for a missing pose. */
export function phraseGesture(lines: EpisodeLine[], span: {start_sec: number; end_sec: number}, time: number,
  pictures: Record<string, string>): Gesture {
  const phrases = segmentPhrases(lines, span.start_sec, span.end_sec);
  const index = phrases.findIndex(group => time >= group[0].startSec && time < Math.min(group.at(-1)!.endSec, group[0].startSec + PHRASE_HOLD_SEC));
  if (index < 0) return "calm";
  const gesture = PHRASE_GESTURES[index % PHRASE_GESTURES.length];
  return gesture === "calm" || (pictures[`gesture-${gesture}`] && pictures[`gesture-${gesture}__open`]) ? gesture : "calm";
}

/** Phase 61: a bob on each word onset (more on a stressed word) and a slow sway, as fractions of the frame. Kept inside
 * the layout proof's motion margin (0.006) together with the breathing, so no card or caption is ever touched. */
export const PRESENTER_SWAY = {x: .003, y: .0035};
export function presenterBody(lines: EpisodeLine[], time: number): {x: number; y: number} {
  let last: Word | undefined;
  for (const line of lines) for (const word of line.words) if (word.startSec <= time && (!last || word.startSec > last.startSec)) last = word;
  const age = last ? time - last.startSec : -1;
  const strong = last && (last.text.replace(/[^\p{L}\p{N}]/gu, "").length >= 6 || last.endSec - last.startSec >= .38) ? 1 : .45;
  const bob = age >= 0 && age < .28 ? Math.sin(Math.PI * age / .28) * strong : 0;
  return {x: PRESENTER_SWAY.x * Math.sin(time * Math.PI * 2 / 6.3), y: -PRESENTER_SWAY.y * (.8 * bob + .2 * Math.sin(time * Math.PI * 2 / 4.4))};
}

/** Phase 61: the pose of a picture without the mouth state (the blink has the calm face). */
export const presenterPose = (picture: string) => picture === "blink" ? "calm" : picture.replace(/__(open|closed)$/, "");

/** Phase 61: the previous pose fading out over the new one for 0.15 s after a pose change (mouth swaps stay direct). */
export function presenterFade(payload: SoloPayload, lines: EpisodeLine[], time: number, fps: number): {picture: string; opacity: number} | null {
  const frames = Math.max(1, Math.round(.15 * fps)), frame = Math.round(time * fps);
  let newer = presenterState(payload, lines, frame / fps, fps).picture;
  for (let back = 1; back <= frames && frame - back >= 0; back += 1) {
    const older = presenterState(payload, lines, (frame - back) / fps, fps).picture;
    if (presenterPose(older) !== presenterPose(newer)) return {picture: older, opacity: 1 - back / (frames + 1)};
    newer = older;
  }
  return null;
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
  else gesture = phraseGesture(lines, span, time, payload.pictures);
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
