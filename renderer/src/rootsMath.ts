/**
 * Phase 87: the pure maths of the word-roots Short (RootsScene) -- word colouring from its parts, the split, the
 * self-drawing underline, the promise wheel and the moment a word first came on screen.
 */
import type { EpisodeLine, RootsCard, RootsPart } from "./types";

export type Segment = { text: string; role: "prefix" | "root" | "suffix" | "rest" };

const clamp = (value: number) => Math.max(0, Math.min(1, value));
const ease = (value: number) => 1 - (1 - value) ** 3;

/** The word as coloured segments: its parts when they spell it, else the whole word as one root. */
export function wordSegments(word: string, parts?: RootsPart[]): Segment[] {
  const clean = (parts || []).map((part) => ({ text: part.text.replace(/-/g, "").trim(), role: part.role }));
  if (clean.length && clean.map((part) => part.text).join("").toLowerCase() === word.replace(/[^A-Za-z]/g, "").toLowerCase()) {
    return clean.map((part) => ({ text: part.text.toUpperCase(), role: part.role }));
  }
  return [{ text: word.toUpperCase(), role: "root" }];
}

/** The word with the family's head marked (for the surprise and the wheel): "EX" + "PRESS", "UN" + "HAPPY". */
export function headSegments(word: string, head: string): Segment[] {
  const upper = word.toUpperCase();
  const alternatives = head.split("/").map((alt) => alt.replace(/-/g, "").trim().toUpperCase()).filter(Boolean)
    .sort((a, b) => b.length - a.length);
  for (const alt of alternatives) {
    const at = head.trim().startsWith("-") ? upper.lastIndexOf(alt) : upper.indexOf(alt);
    if (at >= 0) {
      return [{ text: upper.slice(0, at), role: "rest" as const }, { text: alt, role: "root" as const },
        { text: upper.slice(at + alt.length), role: "rest" as const }].filter((segment) => segment.text);
    }
  }
  return [{ text: upper, role: "rest" }];
}

/** How far the parts of a split word have moved apart (0..1), from the split beat's start. */
export const splitProgress = (time: number, start: number) => ease(clamp((time - start - 0.15) / 0.5));

/** How much of the hand-drawn underline is drawn (0..1). */
export const underlineProgress = (time: number, start: number) => ease(clamp((time - start - 0.1) / 0.6));

/** A picture or icon being drawn in (0..1). */
export const drawProgress = (time: number, start: number) => clamp((time - start - 0.3) / 1.1);

/** Positions of `count` words on a circle around (0, 0), the first at the top, in pixels. */
export function wheelPositions(count: number, radius: number): { x: number; y: number }[] {
  return Array.from({ length: count }, (_, index) => {
    const angle = -Math.PI / 2 + (index * 2 * Math.PI) / Math.max(1, count);
    return { x: Math.round(radius * Math.cos(angle)), y: Math.round(radius * Math.sin(angle)) };
  });
}

const WORD_BEATS = new Set(["hook", "whole", "split", "example"]);
const HEAD_BEATS = new Set(["origin", "head", "head_logic", "head_example"]);

/** The key of what stays on screen: a word across hook/whole/split/example, the head across its beats. */
export function screenKey(card: RootsCard | undefined): string {
  if (!card) return "";
  if (WORD_BEATS.has(card.beat)) return `word:${card.word}`;
  if (HEAD_BEATS.has(card.beat)) return `head:${card.head}`;
  if (card.beat === "quiz" || card.beat === "follow") return `quiz:${card.word}`;
  return `${card.beat}`;
}

/** When the thing on screen at line `index` came on screen (the first line of its run). */
export function runStart(lines: Pick<EpisodeLine, "startSec" | "roots">[], index: number): number {
  let at = index;
  const key = screenKey(lines[index]?.roots);
  while (at > 0 && key && screenKey(lines[at - 1]?.roots) === key) at -= 1;
  return lines[at]?.startSec ?? 0;
}

/** A font size that keeps a word on one line inside `width` pixels (Bangers is about 0.5 em per letter). */
export function fitSize(text: string, width: number, max: number, min = 60): number {
  return Math.max(min, Math.min(max, Math.floor(width / Math.max(1, text.length * 0.52))));
}

/** Vietnamese or English labels, from the spoken line. */
export const isVietnamese = (text: string) => /[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]/i.test(text);
