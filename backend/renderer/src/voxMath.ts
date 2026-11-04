/** Phase 59 (ENH-041): pure timing and layout helpers for the VOX scene (unit-tested, frame-deterministic). */
import type { SoloPayload } from "./soloTypes";

export const clamp01 = (value: number) => Math.min(1, Math.max(0, value));
export const easeOut = (value: number) => 1 - (1 - clamp01(value)) ** 3;

/** The segment being narrated at `time` (before the first: the first; after the last: the last). */
export function voxSegmentAt(payload: SoloPayload, time: number): number {
  const index = payload.timeline.findIndex((span) => time >= span.start_sec && time < span.end_sec);
  if (index >= 0) return index;
  return time < (payload.timeline[0]?.start_sec ?? 0) ? 0 : payload.timeline.length - 1;
}

/** How far the narration of a segment has gone, 0..1 (its own spoken words, or its time span). */
export function segmentProgress(time: number, start: number, end: number): number {
  return clamp01((time - start) / Math.max(0.001, end - start));
}

/** Kinetic text: the words visible at `progress`; the whole text is on screen by 45 % of the segment. */
export const REVEAL_SHARE = 0.45;
export function revealedWords(text: string, progress: number): number {
  const words = text.split(/\s+/).filter(Boolean);
  return Math.min(words.length, Math.ceil(words.length * clamp01(progress / REVEAL_SHARE)));
}

/** The word indexes [from, to) of `phrase` inside `text` (case-insensitive), or null. */
export function highlightRange(text: string, phrase: string): [number, number] | null {
  const words = text.split(/\s+/).filter(Boolean), wanted = phrase.split(/\s+/).filter(Boolean);
  const norm = (word: string) => word.toLowerCase().replace(/[^\p{L}\p{N}']/gu, "");
  if (!wanted.length) return null;
  for (let i = 0; i + wanted.length <= words.length; i += 1) {
    if (wanted.every((word, j) => norm(words[i + j]) === norm(word))) return [i, i + wanted.length];
  }
  return null;
}

/** The highlighter sweeps across its phrase once the phrase is visible: 0..1. */
export function highlightSweep(progress: number, range: [number, number] | null, wordCount: number): number {
  if (!range || !wordCount) return 0;
  const shownAt = (range[1] / wordCount) * REVEAL_SHARE;
  return easeOut((progress - shownAt) / 0.15);
}

/** Bar/line chart scale from zero: each value's height 0..1 and the axis top. */
export function chartHeights(values: number[]): { heights: number[]; top: number; negative: boolean } {
  const top = Math.max(...values.map(Math.abs), 1e-9);
  return { heights: values.map((value) => Math.abs(value) / top), top, negative: values.some((value) => value < 0) };
}

/** The share 0..1 of item `index` (of `count`) that is drawn at `progress`: items grow one after another. */
export function staggered(progress: number, index: number, count: number): number {
  const slot = 0.7 / Math.max(1, count);
  return easeOut((progress - 0.08 - index * slot) / (slot * 1.6));
}

/** Evenly spaced positions 0..1 for `count` timeline events, with margins. */
export function timelinePositions(count: number): number[] {
  if (count <= 1) return [0.5];
  return Array.from({ length: count }, (_, i) => 0.08 + (0.84 * i) / (count - 1));
}

/** A small, stable tilt in degrees for a collage card (alternating sides, never random). */
export function collageTilt(index: number): number {
  return (index % 2 ? 1 : -1) * (1.2 + (index % 3) * 0.6);
}

/** Ken Burns: a slow zoom/pan across the segment. */
export function kenBurns(progress: number, index: number): { scale: number; x: number; y: number } {
  const t = clamp01(progress), direction = index % 2 ? 1 : -1;
  return { scale: 1.04 + 0.08 * t, x: direction * 2.2 * t, y: -1.2 * t };
}

/** Value labels without long decimals: 45, 2.5, 1,200. */
export function formatValue(value: number, unit = ""): string {
  const text = Math.abs(value) >= 1000 ? Math.round(value).toLocaleString("en-US") : String(Math.round(value * 10) / 10);
  return unit === "%" ? `${text}%` : unit ? `${text} ${unit}` : text;
}
