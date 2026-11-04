/** Phase 63 (ENH-045): pure helpers of the two vertical Shorts -- English news and text on a blurred background.
 * Frame-deterministic (no randomness), so vitest pins them. */
import type { SoloPayload, SoloSegment, Visual } from "./soloTypes";
import { clamp01 } from "./voxMath";

export const VOICE_ONLY_STYLES = ["vox", "news", "blur", "mistakes", "wordday", "top5", "quiz", "listen"] as const;  // Phase 64: + learning Shorts
export type VoiceOnlyStyle = (typeof VOICE_ONLY_STYLES)[number];
export const isVoiceOnly = (style: unknown): style is VoiceOnlyStyle => VOICE_ONLY_STYLES.includes(style as VoiceOnlyStyle);

/** The picture behind a segment: the owner's photo, the activity picture, else the scene plate, else none. */
export function pictureFor(payload: SoloPayload, segment: SoloSegment): string | null {
  const visual = segment.visual;
  if (visual.kind === "photo" && visual.asset) {
    const url = payload.photos[`${visual.asset.asset_id}:${visual.asset.version}`];
    if (url) return url;
  }
  if (visual.kind === "activity" && payload.activities?.[visual.activity_id]) return payload.activities[visual.activity_id];
  const scene = segment.scene?.scene_id ? payload.scenes?.[segment.scene.scene_id] : undefined;
  return scene ?? null;
}

/** The picture of a segment, or the nearest earlier segment's (news pictures never go blank between facts). */
export function newsPicture(payload: SoloPayload, index: number): string | null {
  for (let at = index; at >= 0; at -= 1) {
    const url = pictureFor(payload, payload.plan.segments[at]);
    if (url) return url;
  }
  for (let at = index + 1; at < payload.plan.segments.length; at += 1) {
    const url = pictureFor(payload, payload.plan.segments[at]);
    if (url) return url;
  }
  return null;
}

/** The headline of a segment: its title, else its quote, else its emphasis (short). */
export function headlineOf(visual: Visual): string {
  const title = "title" in visual && visual.title ? visual.title : "";
  const text = title || (visual.kind === "quote" ? visual.text : "") || ("emphasis" in visual && visual.emphasis ? visual.emphasis : "")
    || ("caption" in visual && visual.caption ? visual.caption : "");
  return text.length > 90 ? `${text.slice(0, 87).trimEnd()}…` : text;
}

/** The key word(s) of a segment to pop up: the highlight of a quote or the emphasis of a card. */
export function keyWordOf(visual: Visual): string {
  if (visual.kind === "quote" && visual.highlight) return visual.highlight;
  if ("emphasis" in visual && visual.emphasis && visual.emphasis.split(/\s+/).length <= 4) return visual.emphasis;
  return "";
}

/** Whether the news Short draws the visual as a card over the picture (charts, maps, timelines, diagrams). */
export const drawsCard = (visual: Visual) => ["chart", "map", "timeline", "diagram"].includes(visual.kind);

/** The ticker's horizontal offset in pixels: a steady leftward crawl, looping over the text's width. */
export function tickerOffset(time: number, textWidth: number, speed = 90): number {
  const width = Math.max(1, textWidth);
  return -((Math.max(0, time) * speed) % width);
}

type Word = { text: string; startSec: number; endSec: number };
/** The spoken words of a span, in order. */
export function spanWords(lines: Array<{ words: Word[] }>, start: number, end: number): Word[] {
  return lines.flatMap((line) => line.words).filter((word) => word.startSec >= start && word.startSec < end);
}

/** The words shown on a blur Short at `time`: the current group of at most `size` words (the group of the word being
 * spoken), each with how far it has popped in (0..1, over 0.18 s from its start). */
export function blurGroup(words: Word[], time: number, size = 7): Array<Word & { pop: number }> {
  if (!words.length) return [];
  let current = 0;
  words.forEach((word, index) => { if (word.startSec <= time) current = index; });
  const first = Math.floor(current / size) * size;
  return words.slice(first, first + size).map((word) => ({ ...word, pop: clamp01((time - word.startSec) / 0.18) }));
}

/** A font size that fits `count` characters on `lines` lines of a box `width` wide (between min and max). */
export function fitFont(characters: number, width: number, lines: number, min: number, max: number): number {
  const perLine = Math.max(1, characters / Math.max(1, lines));
  return Math.max(min, Math.min(max, (width / perLine) * 1.75));
}

const norm = (word: string) => word.toLowerCase().replace(/[^\p{L}\p{N}']/gu, "");
/** Whether a spoken word is one of the key words (highlighted on a blur Short). */
export function isKeyWord(word: string, key: string): boolean {
  const wanted = key.split(/\s+/).map(norm).filter(Boolean);
  return wanted.includes(norm(word));
}
