/**
 * Phase 32 (Task 32.3): the pure rules of the talking-sprite video -- which pictures each sprite shows on a frame, where it stands,
 * how it moves (turns, hop, breathing, blink, enter and leave) and which scene plate is behind them. `Sprites.tsx` only draws what
 * these functions return, so vitest pins all of it. No randomness: a frame must render the same every time.
 */
import type { EpisodeLine, EpisodeSprites, SpriteCharacter, SpriteLine } from "./types";

/** The 1280 x 1536 sprite canvas is drawn this many video heights tall (legs below the knees leave the frame, D32-g). */
export const SPRITE_HEIGHT = 1.2;
const CANVAS_RATIO = 1280 / 1536;
/** Where the highest head starts, as a fraction of the video height. */
const HEAD_MARGIN = 0.05;
/** The centre of each slot's canvas, as a fraction of the video width (slot 0 = left, the first speaker). */
export const SLOT_X = [0.27, 0.73];
export const LISTENER_BRIGHTNESS = 0.78;
export const LISTENER_SCALE = 0.97;
const TURN_FRAMES = 6;
const HOP_FRAMES = 8;
const HOP_PX = 10;
const BREATH_PX = 2.5;
const BREATH_PERIOD_SEC = 4;
const ENTER_FRAMES = 12;
const BLINK_FRAMES = 4;
export const BACKGROUND_FADE_FRAMES = 12;
/** A gesture stays a moment after its line ends. */
const GESTURE_HOLD_SEC = 0.3;

/** Index of the last line that has started by `time` (-1 before the first): faces and turns hold through the pauses. */
export function heldLineIndex(time: number, lines: Array<{ startSec: number }>): number {
  let held = -1;
  for (let index = 0; index < lines.length; index += 1) {
    if (lines[index].startSec <= time) held = index;
    else break;
  }
  return held;
}

export function isMouthOpen(time: number, intervals: Array<[number, number]>): boolean {
  return intervals.some(([start, end]) => time >= start && time < end);
}

function hash(text: string): number {
  let value = 2166136261;
  for (let index = 0; index < text.length; index += 1) value = Math.imul(value ^ text.charCodeAt(index), 16777619) >>> 0;
  return value;
}

/** A fixed pseudo-random number in [0, 1) for a key and a counter. */
function noise(key: string, counter: number): number {
  return (hash(`${key}:${counter}`) % 10000) / 10000;
}

/** True on the frames where a sprite blinks: 4 frames every 3 to 5 seconds, in a pattern fixed per character. */
export function isBlinking(frame: number, fps: number, key: string): boolean {
  let start = Math.round((1 + 2 * noise(key, 0)) * fps);
  for (let counter = 1; start <= frame; counter += 1) {
    if (frame < start + BLINK_FRAMES) return true;
    start += Math.round((3 + 2 * noise(key, counter)) * fps);
  }
  return false;
}

/** The picture to show, falling back to what the set has. */
function pick(character: SpriteCharacter, wanted: string[]): string {
  return wanted.find((name) => name in character.pictures) ?? "calm__closed";
}

export type SpriteFrame = {
  body: string;
  face: string | null;
  /** translation of the face picture (canvas pixels) so its face lands on the body's face */
  faceShift: [number, number];
  /** centre of the face mask on the face picture, fractions of the canvas */
  maskCentre: [number, number];
  speaking: boolean;
  brightness: number;
  scale: number;
  /** offsets in video pixels */
  x: number;
  y: number;
  opacity: number;
};

/** Where the canvases start vertically (fraction of the video height): the highest figure's head sits at HEAD_MARGIN. */
export function stageTop(characters: SpriteCharacter[]): number {
  const top = Math.min(...characters.map((character) => character.topFraction), 0.15);
  return HEAD_MARGIN - top * SPRITE_HEIGHT;
}

export function canvasBox(slot: number, width: number, height: number, characters: SpriteCharacter[]) {
  const boxHeight = SPRITE_HEIGHT * height;
  const boxWidth = boxHeight * CANVAS_RATIO;
  return { left: SLOT_X[slot] * width - boxWidth / 2, top: stageTop(characters) * height, width: boxWidth, height: boxHeight };
}

function turnStart(index: number, lines: SpriteLine[], timeline: EpisodeLine[]): number | null {
  // the start of the run of lines (ending at `index`) with the same speaker
  if (index < 0 || lines[index].slot === null) return null;
  let first = index;
  while (first > 0 && lines[first - 1].slot === lines[index].slot) first -= 1;
  return timeline[first].startSec;
}

export function spriteFrame(
  character: SpriteCharacter, frame: number, fps: number, timeline: EpisodeLine[], sprites: EpisodeSprites,
  totalFrames: number, width: number,
): SpriteFrame {
  const time = frame / fps;
  const index = heldLineIndex(time, timeline);
  const line = index >= 0 ? sprites.lines[index] : undefined;
  const slot = character.slot;
  const speaking = line !== undefined && line.slot === slot;
  const lineEnd = index >= 0 ? timeline[index].endSec : 0;

  const expression = !line || line.slot === null ? "calm" : speaking ? line.expression : line.listenerExpression;
  const gesture = !line || time >= lineEnd + GESTURE_HOLD_SEC ? null : speaking ? line.gesture : line.listenerGesture;
  const mouthOpen = speaking && line !== undefined && isMouthOpen(time, line.mouth);
  const blink = !mouthOpen && isBlinking(frame, fps, character.name) && "blink" in character.pictures;

  const faceName = blink ? "blink" : pick(character, [`${expression}__${mouthOpen ? "open" : "closed"}`, `calm__${mouthOpen ? "open" : "closed"}`]);
  const body = gesture ? pick(character, [`gesture-${gesture}`]) : "calm__closed";
  const face = faceName === body ? null : faceName;
  const bodyOffset = character.offsets[body] ?? [0, 0];
  const faceOffset = face ? character.offsets[face] ?? [0, 0] : [0, 0];
  const [cx, cy] = character.faceEllipse;

  // turns: the speaker brightens and grows over 6 frames, with a small hop when the turn starts
  const start = turnStart(index, sprites.lines, timeline);
  const sinceTurn = start === null ? Number.POSITIVE_INFINITY : frame - Math.round(start * fps);
  const turnMix = Math.min(1, Math.max(0, sinceTurn / TURN_FRAMES));
  const active = speaking ? turnMix : 1 - Math.min(1, turnMixForListener(index, sprites.lines, slot, sinceTurn));
  const brightness = LISTENER_BRIGHTNESS + (1 - LISTENER_BRIGHTNESS) * active;
  const scale = LISTENER_SCALE + (1 - LISTENER_SCALE) * active;
  const hop = speaking && sinceTurn >= 0 && sinceTurn < HOP_FRAMES ? -HOP_PX * Math.sin((Math.PI * sinceTurn) / HOP_FRAMES) : 0;
  const breath = BREATH_PX * Math.sin(2 * Math.PI * (time / BREATH_PERIOD_SEC + slot * 0.37));

  // enter at the start of the speech, leave at its end (slide from the own side and fade)
  const enter = Math.min(1, frame / ENTER_FRAMES);
  const leave = Math.min(1, Math.max(0, (totalFrames - frame) / ENTER_FRAMES));
  const presence = Math.min(enter, leave);
  const eased = 1 - (1 - presence) * (1 - presence);
  const side = slot === 0 ? -1 : 1;

  return {
    body, face,
    faceShift: [bodyOffset[0] - faceOffset[0], bodyOffset[1] - faceOffset[1]],
    maskCentre: [cx + faceOffset[0] / 1280, cy + faceOffset[1] / 1536],
    speaking, brightness, scale,
    x: side * (1 - eased) * 0.35 * width,
    y: hop + breath,
    opacity: eased,
  };
}

/** A listener that was the speaker of the previous line dims over the same 6 frames (no pop). */
function turnMixForListener(index: number, lines: SpriteLine[], slot: number, sinceTurn: number): number {
  if (index < 0) return 1;
  const previous = index > 0 ? lines[index - 1] : undefined;
  const wasSpeaking = previous !== undefined && previous.slot === slot && lines[index].slot !== slot;
  return wasSpeaking ? Math.min(1, Math.max(0, sinceTurn / TURN_FRAMES)) : 1;
}

/** The scene plate behind the sprites: the held line's, with a 12-frame cross-fade when it changes. */
export function spriteBackground(frame: number, fps: number, timeline: EpisodeLine[], sprites: EpisodeSprites): {
  current: string | null; previous: string | null; opacity: number;
} {
  const ids = sprites.lineBackgrounds;
  const urlOf = (id: string | null | undefined) => (id ? sprites.backgrounds[id] ?? null : null);
  const index = Math.max(0, heldLineIndex(frame / fps, timeline));
  const current = urlOf(ids[index] ?? ids.find((id) => id) ?? null);
  let first = index;
  while (first > 0 && ids[first - 1] === ids[index]) first -= 1;
  if (first === 0 || index >= timeline.length) return { current, previous: null, opacity: 1 };
  const since = frame - Math.round(timeline[first].startSec * fps);
  const previous = urlOf(ids[first - 1]);
  if (since >= BACKGROUND_FADE_FRAMES || previous === current) return { current, previous: null, opacity: 1 };
  return { current, previous, opacity: Math.max(0, since) / BACKGROUND_FADE_FRAMES };
}

/** The CSS mask that keeps only the face of a face picture (a feathered ellipse). */
export function faceMask(ellipse: [number, number, number, number], centre: [number, number]): string {
  const [, , rx, ry] = ellipse;
  const pct = (value: number) => `${(value * 100).toFixed(2)}%`;
  return `radial-gradient(ellipse ${pct(rx)} ${pct(ry)} at ${pct(centre[0])} ${pct(centre[1])}, #000 70%, transparent 100%)`;
}
