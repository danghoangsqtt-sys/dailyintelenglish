/**
 * Phase 61 (ENH-043): the VOX motion rules -- the transition at each segment boundary, the title/shape morph, the board's
 * camera, the map's fly-in, counting numbers, the hand-drawn strokes and the closing "Subscribe" stamp. Pure and
 * frame-deterministic (no randomness), so vitest pins all of it and seeking renders the same frame every time.
 */
import type React from "react";
import type { MapView } from "./voxMap";
import { clamp01, easeOut } from "./voxMath";

export const TRANSITIONS = ["slide", "wipe", "zoom", "flip", "iris", "whip"] as const;
export type TransitionKind = (typeof TRANSITIONS)[number];
export const TRANSITION_SEC = 0.5;

export const easeInOut = (value: number) => {
  const t = clamp01(value);
  return t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;
};
/** Overshoots a little past 1 and settles: bouncy words and the stamp. */
export const easeOutBack = (value: number) => {
  const t = clamp01(value), c = 1.70158;
  return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2;
};
/** Drops and bounces twice: the map pins. */
export function easeOutBounce(value: number): number {
  const t = clamp01(value), n = 7.5625, d = 2.75;
  if (t < 1 / d) return n * t * t;
  if (t < 2 / d) return n * (t - 1.5 / d) ** 2 + 0.75;
  if (t < 2.5 / d) return n * (t - 2.25 / d) ** 2 + 0.9375;
  return n * (t - 2.625 / d) ** 2 + 0.984375;
}

/** The transition into segment `index` (the first segment has none); the six kinds take turns. */
export function transitionFor(index: number): TransitionKind | null {
  return index < 1 ? null : TRANSITIONS[(index - 1) % TRANSITIONS.length];
}

type Span = { start_sec: number; end_sec: number };
/** The transition running at `time` into segment `index`, with its eased share 0..1, or null. */
export function transitionAt(timeline: Span[], index: number, time: number): { kind: TransitionKind; t: number } | null {
  const kind = transitionFor(index), span = timeline[index];
  if (!kind || !span) return null;
  const length = Math.min(TRANSITION_SEC, Math.max(0.05, (span.end_sec - span.start_sec) / 2));
  const raw = (time - span.start_sec) / length;
  return raw >= 0 && raw < 1 ? { kind, t: easeInOut(raw) } : null;
}

/** The CSS of the leaving and the entering board at share `t`, and which one is drawn on top. */
export function transitionStyles(kind: TransitionKind, t: number, width: number): {
  leaving: React.CSSProperties; entering: React.CSSProperties; top: "leaving" | "entering";
} {
  const shadow = "0 0 40px rgba(30,42,38,0.35)";
  switch (kind) {
    case "slide": // a new paper sheet slides in over the old one, which is pushed back a little
      return { top: "entering",
        leaving: { transform: `translateX(${(-0.18 * t * width).toFixed(1)}px)`, filter: `brightness(${(1 - 0.12 * t).toFixed(3)})` },
        entering: { transform: `translateX(${((1 - t) * width).toFixed(1)}px) rotate(${(2.5 * (1 - t)).toFixed(2)}deg)`, boxShadow: shadow } };
    case "wipe": { // a diagonal edge sweeps across
      const x = t * 135;
      return { top: "entering", leaving: {},
        entering: { clipPath: `polygon(0% 0%, ${x.toFixed(1)}% 0%, ${(x - 35).toFixed(1)}% 100%, 0% 100%)` } };
    }
    case "zoom": // the camera flies through the old board into the new one
      return { top: "leaving",
        leaving: { transform: `scale(${(1 + 1.4 * t).toFixed(3)})`, opacity: 1 - t, filter: `blur(${(6 * t).toFixed(1)}px)` },
        entering: { transform: `scale(${(0.86 + 0.14 * t).toFixed(4)})` } };
    case "flip": // the old page turns over its left edge
      return { top: "leaving",
        leaving: { transform: `perspective(${Math.round(width * 1.6)}px) rotateY(${(100 * t).toFixed(2)}deg)`, transformOrigin: "0% 50%",
          backfaceVisibility: "hidden", boxShadow: shadow, filter: `brightness(${(1 - 0.3 * t).toFixed(3)})` },
        entering: { filter: `brightness(${(0.82 + 0.18 * t).toFixed(3)})` } };
    case "iris": // a circle opens from the centre
      return { top: "entering", leaving: {}, entering: { clipPath: `circle(${(t * 75).toFixed(2)}% at 50% 50%)` } };
    case "whip": // a fast pan with motion blur
      return { top: "entering",
        leaving: { transform: `translateX(${(-t * width).toFixed(1)}px)`, filter: `blur(${(18 * Math.sin(Math.PI * t)).toFixed(1)}px)` },
        entering: { transform: `translateX(${((1 - t) * width).toFixed(1)}px)`, filter: `blur(${(18 * Math.sin(Math.PI * t)).toFixed(1)}px)` } };
  }
}

type Word = { startSec: number; endSec: number };
/** A smooth narration share 0..1: whole words spoken plus the part of the current word (no jumps per word). */
export function smoothProgress(words: Word[], time: number): number {
  if (!words.length) return 0;
  let done = 0;
  for (const word of words) {
    if (time >= word.endSec) done += 1;
    else if (time > word.startSec) done += (time - word.startSec) / Math.max(0.01, word.endSec - word.startSec);
  }
  return clamp01(done / words.length);
}

/** The appear share 0..1 of word `index` of `count` at `progress` (the text is whole by `share` of the segment). */
export function wordAppear(progress: number, index: number, count: number, share: number): number {
  return clamp01((progress / share) * count - index);
}

/** The board's camera: a slow push-in with a pan that alternates direction per segment. */
export function boardCamera(time: number, span: Span, index: number): { scale: number; x: number; y: number } {
  const t = easeInOut((time - span.start_sec) / Math.max(0.5, span.end_sec - span.start_sec));
  const direction = index % 2 ? -1 : 1;
  return { scale: 1 + 0.035 * t, x: direction * 0.012 * t, y: -0.006 * t };
}

export type Shape = { x: number; y: number; size: number; rotation: number; radius: number[]; color: string };
const SHAPE_COLORS = ["rgba(255,216,77,0.55)", "rgba(31,122,77,0.18)", "rgba(232,72,59,0.16)", "rgba(80,140,190,0.18)"];
/** The decorative shape behind segment `index`: a soft blob with its own place, size, corners and colour. */
export function shapeFor(index: number): Shape {
  const corner = (k: number) => 30 + ((index * 37 + k * 23) % 45);
  return { x: [0.78, 0.2, 0.72, 0.28, 0.85, 0.15][index % 6], y: [0.3, 0.65, 0.72, 0.28, 0.6, 0.4][index % 6],
    size: 0.26 + ((index * 7) % 5) * 0.03, rotation: (index * 47) % 360, radius: [corner(0), corner(1), corner(2), corner(3)],
    color: SHAPE_COLORS[index % SHAPE_COLORS.length] };
}

const mix = (a: number, b: number, t: number) => a + (b - a) * t;
function mixColor(a: string, b: string, t: number): string {
  const parse = (value: string) => value.match(/[\d.]+/g)!.map(Number);
  const [x, y] = [parse(a), parse(b)];
  return `rgba(${x.slice(0, 3).map((v, i) => Math.round(mix(v, y[i], t))).join(",")},${mix(x[3], y[3], t).toFixed(3)})`;
}
/** Morph: during a transition the shape changes smoothly from the previous segment's to the new one's. */
export function shapeAt(timeline: Span[], index: number, time: number): Shape {
  const target = shapeFor(index), running = transitionAt(timeline, index, time);
  if (!running) return target;
  const from = shapeFor(index - 1), t = running.t;
  return { x: mix(from.x, target.x, t), y: mix(from.y, target.y, t), size: mix(from.size, target.size, t),
    rotation: mix(from.rotation, target.rotation, t), radius: from.radius.map((r, i) => mix(r, target.radius[i], t)),
    color: mixColor(from.color, target.color, t) };
}

/** The world view the map flies in from. */
export const WORLD_VIEW: MapView = { west: -170, east: 190, south: -58, north: 80 };
/** The map view at share `t` of the fly-in: the centre moves and the zoom changes evenly (log scale). */
export function mapViewAt(target: MapView, t: number): MapView {
  const k = easeInOut(t);
  const span = (view: MapView) => [view.east - view.west, view.north - view.south];
  const centre = (view: MapView) => [(view.west + view.east) / 2, (view.south + view.north) / 2];
  const [w0, h0] = span(WORLD_VIEW), [w1, h1] = span(target), [x0, y0] = centre(WORLD_VIEW), [x1, y1] = centre(target);
  const width = w0 * (w1 / w0) ** k, height = h0 * (h1 / h0) ** k, x = mix(x0, x1, k), y = mix(y0, y1, k);
  return { west: x - width / 2, east: x + width / 2, south: y - height / 2, north: y + height / 2 };
}

/** A chart number counting up with its bar: whole numbers stay whole and the end value is exact. */
export function countUp(value: number, t: number): number {
  if (t >= 1) return value;
  const shown = value * clamp01(t);
  return Number.isInteger(value) ? Math.round(shown) : Math.round(shown * 10) / 10;
}

/** A hand-drawn stroke from (x1, y1) to (x2, y2): a gentle fixed wobble, the same on every frame. */
export function wobblyPath(x1: number, y1: number, x2: number, y2: number, seed: number): string {
  const length = Math.hypot(x2 - x1, y2 - y1), nx = -(y2 - y1) / Math.max(1, length), ny = (x2 - x1) / Math.max(1, length);
  const [c1, c2] = [1 / 3, 2 / 3].map((share, k) => {
    const wobble = (k ? -1 : 1) * (0.6 + 0.4 * Math.sin(seed * 1.7 + k * 2.1)) * Math.min(7, length * 0.04);
    return `${(x1 + (x2 - x1) * share + nx * wobble).toFixed(1)},${(y1 + (y2 - y1) * share + ny * wobble).toFixed(1)}`;
  });
  return `M${x1.toFixed(1)},${y1.toFixed(1)} C${c1} ${c2} ${x2.toFixed(1)},${y2.toFixed(1)}`;
}

/** A hand-drawn arrow: its shaft and the two strokes of its head. */
export function arrowPaths(x1: number, y1: number, x2: number, y2: number, seed: number, head: number): { shaft: string; head: string } {
  const angle = Math.atan2(y2 - y1, x2 - x1), spread = 0.5;
  const tip = (side: number) => [x2 - head * Math.cos(angle + side * spread), y2 - head * Math.sin(angle + side * spread)];
  const [a, b] = [tip(1), tip(-1)];
  return { shaft: wobblyPath(x1, y1, x2, y2, seed),
    head: `M${a[0].toFixed(1)},${a[1].toFixed(1)} L${x2.toFixed(1)},${y2.toFixed(1)} L${b[0].toFixed(1)},${b[1].toFixed(1)}` };
}

/** The closing stamp: when the narration says "subscribe" in the last segment (else at 60 % of it), it slams in. */
export function stampAt(time: number, span: Span, words: Array<Word & { text: string }>): { scale: number; opacity: number } | null {
  const said = words.find((word) => /subscrib/i.test(word.text) && word.startSec >= span.start_sec && word.startSec < span.end_sec);
  const at = said ? said.startSec : span.start_sec + 0.6 * (span.end_sec - span.start_sec);
  const age = time - at;
  if (age < 0) return null;
  const t = clamp01(age / 0.28);
  return { scale: 2.4 - 1.4 * easeOutBack(t), opacity: easeOut(t * 2) };
}
