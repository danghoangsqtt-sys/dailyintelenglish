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
/** The centre of each visible canvas, as a fraction of the video width. */
export const SLOT_X = [0.27, 0.73];
export const LISTENER_BRIGHTNESS = 0.78;
/** 1: the listener is only dimmed, never resized (a resize resamples the picture: owner 2026-10-08, no blur). */
export const LISTENER_SCALE = 1;
const TURN_FRAMES = 6;
const HOP_FRAMES = 8;
const HOP_PX = 10;
const BREATH_PX = 2.5;
const BREATH_PERIOD_SEC = 4;
const ENTER_FRAMES = 12;
const BLINK_FRAMES = 4;
export const BACKGROUND_FADE_FRAMES = 12;
export const CUTAWAY_FADE_SEC = 0.3;
/** A listener's gesture stays a moment after the line ends. */
const GESTURE_HOLD_SEC = 0.3;
/** Owner 2026-10-08: every picture is shown exactly as it was made -- nothing is pasted on it, it is never squashed or blended.
 * The mouth moves by swapping a picture with its open-mouth twin (the same picture with only the mouth edited), and a pose is
 * swapped in on one frame, like a game character. A gesture without its open-mouth twin cannot talk, so the speaker holds it
 * only for the first 1.6 s of the line and then talks on the plain picture. */
export const SPEAKER_GESTURE_SEC = 1.6;

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
  /** the one picture shown (a name of `character.pictures`) */
  picture: string;
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

export function visibleSlotsAt(frame: number, fps: number, timeline: EpisodeLine[], sprites: EpisodeSprites): number[] {
  const index = Math.max(0, heldLineIndex(frame / fps, timeline));
  const requested = sprites.lines[index]?.visibleSlots ?? [];
  const known = new Set(sprites.characters.map((character) => character.slot));
  // Storyboard speakers may be stored in click order or speaker order. Stage order must be stable so the same
  // pair never exchanges sides between beats: lower cast slot stands left, higher cast slot stands right.
  const visible = [...new Set(requested.filter((slot) => known.has(slot)))].sort((a, b) => a - b).slice(0, 2);
  return visible.length > 0
    ? visible
    : sprites.characters.map((character) => character.slot).sort((a, b) => a - b).slice(0, 2);
}

export function canvasBox(slot: number, width: number, height: number, characters: SpriteCharacter[], visibleSlots?: number[]) {
  const boxHeight = SPRITE_HEIGHT * height;
  const boxWidth = boxHeight * CANVAS_RATIO;
  const visible = visibleSlots?.length ? visibleSlots : characters.slice(0, 2).map((character) => character.slot);
  const position = visible.indexOf(slot);
  const center = visible.length === 1 ? 0.5 : SLOT_X[Math.max(0, position)] ?? SLOT_X[0];
  const stageCharacters = characters.filter((character) => visible.includes(character.slot));
  return {
    left: center * width - boxWidth / 2,
    top: stageTop(stageCharacters.length ? stageCharacters : characters) * height,
    width: boxWidth,
    height: boxHeight,
  };
}

function turnStart(index: number, lines: SpriteLine[], timeline: EpisodeLine[]): number | null {
  // the start of the run of lines (ending at `index`) with the same speaker
  if (index < 0 || lines[index].slot === null) return null;
  let first = index;
  while (first > 0 && lines[first - 1].slot === lines[index].slot) first -= 1;
  return timeline[first].startSec;
}

/** The gesture picture a sprite shows on a frame, or null (the plain body that talks). */
export function gestureAt(character: SpriteCharacter, frame: number, fps: number, timeline: EpisodeLine[], sprites: EpisodeSprites): string | null {
  const time = frame / fps;
  const index = heldLineIndex(time, timeline);
  const line = index >= 0 ? sprites.lines[index] : undefined;
  if (!line) return null;
  const speaking = line.slot === character.slot;
  const gesture = speaking ? line.gesture : line.listenerGesture;
  const name = gesture ? `gesture-${gesture}` : null;
  if (!name || !(name in character.pictures)) return null;
  const talks = `${name}__open` in character.pictures;
  const until = speaking
    ? (talks ? timeline[index].endSec : Math.min(timeline[index].startSec + SPEAKER_GESTURE_SEC, timeline[index].endSec))
    : timeline[index].endSec + GESTURE_HOLD_SEC;
  return time < until ? name : null;
}

export function spriteFrame(
  character: SpriteCharacter, frame: number, fps: number, timeline: EpisodeLine[], sprites: EpisodeSprites,
  totalFrames: number, width: number,
): SpriteFrame {
  const time = frame / fps;
  const index = heldLineIndex(time, timeline);
  const line = index >= 0 ? sprites.lines[index] : undefined;
  const slot = character.slot;
  const visibleSlots = visibleSlotsAt(frame, fps, timeline, sprites);
  const visiblePosition = visibleSlots.indexOf(slot);
  const visible = visiblePosition >= 0;
  const speaking = line !== undefined && line.slot === slot;

  const expression = !line || line.slot === null ? "calm" : speaking ? line.expression : line.listenerExpression;
  const mouthOpen = speaking && line !== undefined && isMouthOpen(time, line.mouth);
  const gesture = gestureAt(character, frame, fps, timeline, sprites);
  // the blink picture has the calm face: it is used only on the calm face, with the mouth closed and no gesture
  const blink = !gesture && !mouthOpen && expression === "calm" && isBlinking(frame, fps, character.name) && "blink" in character.pictures;
  const mouth = mouthOpen ? "open" : "closed";
  const picture = gesture
    ? (mouthOpen && `${gesture}__open` in character.pictures ? `${gesture}__open` : gesture)
    : blink ? "blink" : pick(character, [`${expression}__${mouth}`, `calm__${mouth}`]);

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
  const side = visibleSlots.length === 1 ? 0 : visiblePosition === 0 ? -1 : 1;

  return {
    picture,
    speaking, brightness, scale,
    x: side * (1 - eased) * 0.35 * width,
    y: hop + breath,
    opacity: visible ? eased : 0,
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

export function activityCutawayAt(time: number, sprites: EpisodeSprites): { url: string; opacity: number } | null {
  const cutaway = sprites.cutaways.find((item) => time >= item.startSec && time < item.endSec);
  if (!cutaway) return null;
  const entering = Math.min(1, (time - cutaway.startSec) / CUTAWAY_FADE_SEC);
  const leaving = Math.min(1, (cutaway.endSec - time) / CUTAWAY_FADE_SEC);
  return { url: cutaway.url, opacity: Math.max(0, Math.min(entering, leaving)) };
}
