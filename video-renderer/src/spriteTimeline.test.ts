import { describe, expect, it } from "vitest";
import { podcastLayer } from "./podcastLayout";
import {
  SPEAKER_GESTURE_SEC, gestureAt,
  BACKGROUND_FADE_FRAMES, LISTENER_BRIGHTNESS, SPRITE_HEIGHT, canvasBox, heldLineIndex, isBlinking, isMouthOpen,
  activityCutawayAt, spriteBackground, spriteFrame, stageTop,
} from "./spriteTimeline";
import { episodeInputPropsSchema, type EpisodeLine, type EpisodeSprites, type SpriteCharacter } from "./types";

const FPS = 30;
const WIDTH = 1280;

function character(slot: number, name: string, extra: string[] = []): SpriteCharacter {
  const names = ["calm__closed", "calm__open", "smile__closed", "smile__open", "blink", ...extra];
  return {
    slot, name, faceEllipse: [0.5, 0.25, 0.08, 0.07], topFraction: slot === 0 ? 0.1 : 0.15,
    pictures: Object.fromEntries(names.map((n) => [n, `remotion-render/sprites/p/${name}/${n}.png`])),
    offsets: { "smile__open": [4, -2], "gesture-wave": [1, 1] },
  };
}

const timeline: EpisodeLine[] = [
  { startSec: 0, endSec: 2, speaker: "Alex", speakerId: "a", text: "Hello!", words: [] },
  { startSec: 2.5, endSec: 5, speaker: "Lina", speakerId: "l", text: "Hi there.", words: [] },
  { startSec: 5.5, endSec: 7, speaker: "Lina", speakerId: "l", text: "Nice day.", words: [] },
];

const sprites: EpisodeSprites = {
  characters: [character(0, "Alex", ["gesture-wave"]), character(1, "Lina", ["gesture-listen", "gesture-talk", "gesture-talk__open"])],
  lines: [
    { slot: 0, visibleSlots: [0, 1], expression: "smile", listenerExpression: "calm", gesture: "wave", listenerGesture: null, mouth: [[0.2, 0.6], [1.65, 1.9]] },
    { slot: 1, visibleSlots: [0, 1], expression: "calm", listenerExpression: "smile", gesture: null, listenerGesture: null, mouth: [[3, 4]] },
    { slot: 1, visibleSlots: [0, 1], expression: "calm", listenerExpression: "calm", gesture: "talk", listenerGesture: null, mouth: [[6.4, 6.6]] },
  ],
  backgrounds: { cafe: "remotion-render/sprites/p/bg/cafe.png", park: "remotion-render/sprites/p/bg/park.png" },
  lineBackgrounds: ["cafe", "cafe", "park"],
  cutaways: [],
};

const total = 7 * FPS;
const at = (who: number, sec: number) => spriteFrame(sprites.characters[who], Math.round(sec * FPS), FPS, timeline, sprites, total, WIDTH);

describe("Phase 32 talking sprites", () => {
  it("is a podcast mode with its own layer and accepts the sprite props", () => {
    expect(podcastLayer("podcast_sprites")).toBe("sprites");
    const parsed = episodeInputPropsSchema.parse({
      episodeId: "p", lines: [], audioPath: "a.mp3", fps: 30, width: 1280, height: 720, visualMode: "podcast_sprites", sprites,
    });
    expect(parsed.sprites?.characters[1].name).toBe("Lina");
  });

  it("rejects a cutaway longer than six seconds at the props boundary", () => {
    expect(() => episodeInputPropsSchema.parse({
      episodeId: "p", lines: [], audioPath: "a.mp3", fps: 30, width: 1280, height: 720,
      visualMode: "podcast_sprites",
      sprites: { ...sprites, cutaways: [{ startSec: 1, endSec: 7.01, url: "too-long.png" }] },
    })).toThrow();
  });

  it("holds the last started line and opens the mouth only inside its intervals", () => {
    expect(heldLineIndex(-1, timeline)).toBe(-1);
    expect(heldLineIndex(2.2, timeline)).toBe(0);
    expect(isMouthOpen(0.3, [[0.2, 0.6]])).toBe(true);
    expect(isMouthOpen(0.6, [[0.2, 0.6]])).toBe(false);
  });

  it("shows one whole picture: the expression with the mouth open or closed, nothing pasted on it", () => {
    expect(at(0, 1.7).picture).toBe("smile__open");
    expect(at(0, 1.95).picture).toBe("smile__closed");
    expect(at(1, 4.5).picture).toBe("calm__closed"); // Lina speaks with a calm face, mouth closed between the words
    expect(at(1, 3.5).picture).toBe("calm__open");
  });

  it("talks while making a gesture when the gesture has its open-mouth twin", () => {
    expect(at(1, 6).picture).toBe("gesture-talk"); // the whole line, not only the first 1.6 s
    expect(at(1, 6.5).picture).toBe("gesture-talk__open");
  });

  it("dims and shrinks the listener and brightens the speaker after a short turn change", () => {
    const listener = at(1, 1);
    expect(listener.brightness).toBeCloseTo(LISTENER_BRIGHTNESS);
    expect(listener.scale).toBe(1); // dimmed, never resized
    const turn = at(1, 2.5 + 3 / FPS);
    expect(turn.brightness).toBeGreaterThan(LISTENER_BRIGHTNESS);
    expect(turn.brightness).toBeLessThan(1);
    expect(at(1, 3.5).brightness).toBeCloseTo(1);
    expect(at(1, 2.5 + 4 / FPS).y).toBeLessThan(-5); // the hop
    expect(at(0, 3.5).picture).toBe("smile__closed"); // the listener smiles back
  });

  it("slides in at the start and out at the end", () => {
    const first = spriteFrame(sprites.characters[0], 0, FPS, timeline, sprites, total, WIDTH);
    expect(first.opacity).toBe(0);
    expect(first.x).toBeLessThan(0);
    expect(spriteFrame(sprites.characters[1], 0, FPS, timeline, sprites, total, WIDTH).x).toBeGreaterThan(0);
    expect(at(0, 3).opacity).toBe(1);
    expect(spriteFrame(sprites.characters[1], total, FPS, timeline, sprites, total, WIDTH).opacity).toBe(0);
  });

  it("blinks for 4 frames every 3 to 5 seconds, the same on every render, never with an open mouth", () => {
    const frames = Array.from({ length: 30 * FPS }, (_, frame) => isBlinking(frame, FPS, "Lina"));
    const starts = frames.flatMap((on, frame) => (on && !frames[frame - 1] ? [frame] : []));
    expect(starts.length).toBeGreaterThanOrEqual(5);
    expect(starts.length).toBeLessThanOrEqual(10);
    starts.slice(1).forEach((start, index) => {
      expect(start - starts[index]).toBeGreaterThanOrEqual(3 * FPS);
      expect(start - starts[index]).toBeLessThanOrEqual(5 * FPS);
    });
    starts.filter((start) => start + 5 <= frames.length).forEach((start) => {
      expect(frames.slice(start, start + 5)).toEqual([true, true, true, true, false]);
    });
    expect(Array.from({ length: 300 }, (_, frame) => isBlinking(frame, FPS, "Lina"))).toEqual(frames.slice(0, 300));
  });

  it("cross-fades the scene plate when the place changes", () => {
    expect(spriteBackground(30, FPS, timeline, sprites)).toEqual({ current: sprites.backgrounds.cafe, previous: null, opacity: 1 });
    const change = Math.round(5.5 * FPS);
    const middle = spriteBackground(change + BACKGROUND_FADE_FRAMES / 2, FPS, timeline, sprites);
    expect(middle.previous).toBe(sprites.backgrounds.cafe);
    expect(middle.current).toBe(sprites.backgrounds.park);
    expect(middle.opacity).toBeCloseTo(0.5);
    expect(spriteBackground(change + BACKGROUND_FADE_FRAMES, FPS, timeline, sprites).previous).toBeNull();
  });

  it("cross-fades an approved activity cutaway for its bounded interval only", () => {
    const withCutaway = { ...sprites, cutaways: [{ startSec: 2, endSec: 5, url: "activity.png" }] };
    expect(activityCutawayAt(1.99, withCutaway)).toBeNull();
    expect(activityCutawayAt(2, withCutaway)?.opacity).toBe(0);
    expect(activityCutawayAt(2.15, withCutaway)?.opacity).toBeCloseTo(0.5);
    expect(activityCutawayAt(4.85, withCutaway)?.opacity).toBeCloseTo(0.5);
    expect(activityCutawayAt(5, withCutaway)).toBeNull();
  });

  it("uses exactly nine frames for each 0.3 second cutaway fade at 30 fps", () => {
    const withCutaway = { ...sprites, cutaways: [{ startSec: 2, endSec: 6, url: "activity.png" }] };
    expect(activityCutawayAt(2 + 8 / FPS, withCutaway)?.opacity).toBeCloseTo(8 / 9);
    expect(activityCutawayAt(2 + 9 / FPS, withCutaway)?.opacity).toBeCloseTo(1);
    expect(activityCutawayAt(6 - 9 / FPS, withCutaway)?.opacity).toBeCloseTo(1);
    expect(activityCutawayAt(6 - 1 / FPS, withCutaway)?.opacity).toBeCloseTo(1 / 9);
  });

  it("keeps overlapping fades bounded for a cutaway shorter than 0.6 seconds", () => {
    const withCutaway = { ...sprites, cutaways: [{ startSec: 1, endSec: 1.3, url: "activity.png" }] };
    const middle = activityCutawayAt(1.15, withCutaway);
    expect(middle?.opacity).toBeCloseTo(0.5);
    expect(middle?.opacity).toBeGreaterThanOrEqual(0);
    expect(middle?.opacity).toBeLessThanOrEqual(1);
  });

  it("stands both canvases on the stage with the highest head near the top", () => {
    expect(stageTop(sprites.characters)).toBeCloseTo(0.05 - 0.1 * SPRITE_HEIGHT);
    const left = canvasBox(0, 1280, 720, sprites.characters);
    const right = canvasBox(1, 1280, 720, sprites.characters);
    expect(left.height).toBeCloseTo(SPRITE_HEIGHT * 720);
    expect(left.left + left.width / 2).toBeCloseTo(0.27 * 1280);
    expect(right.left).toBeGreaterThan(left.left);
  });

  it("shows the storyboard pair when a third cast member becomes active", () => {
    const trioTimeline: EpisodeLine[] = [
      { startSec: 0, endSec: 2, speaker: "Alex", speakerId: "a", text: "Hello.", words: [] },
      { startSec: 2, endSec: 4, speaker: "Rowan", speakerId: "r", text: "Hello too.", words: [] },
    ];
    const trio: EpisodeSprites = {
      ...sprites,
      characters: [...sprites.characters, character(2, "Rowan")],
      lines: [
        { slot: 0, visibleSlots: [0, 1], expression: "calm", listenerExpression: "calm", gesture: null, listenerGesture: null, mouth: [] },
        { slot: 2, visibleSlots: [0, 2], expression: "calm", listenerExpression: "calm", gesture: null, listenerGesture: null, mouth: [] },
      ],
      lineBackgrounds: ["cafe", "cafe"],
    };
    const frame = 3 * FPS;
    const alex = spriteFrame(trio.characters[0], frame, FPS, trioTimeline, trio, 4 * FPS, WIDTH);
    const lina = spriteFrame(trio.characters[1], frame, FPS, trioTimeline, trio, 4 * FPS, WIDTH);
    const rowan = spriteFrame(trio.characters[2], frame, FPS, trioTimeline, trio, 4 * FPS, WIDTH);

    expect(lina.opacity).toBe(0);
    expect(rowan.opacity).toBeGreaterThan(0);
    expect(rowan.speaking).toBe(true);
    expect(canvasBox(0, WIDTH, 720, trio.characters, [0, 2]).left)
      .toBeLessThan(canvasBox(2, WIDTH, 720, trio.characters, [0, 2]).left);
    expect(episodeInputPropsSchema.parse({
      episodeId: "p", lines: trioTimeline, audioPath: "a.mp3", fps: FPS, width: WIDTH, height: 720,
      visualMode: "podcast_sprites", sprites: trio,
    }).sprites?.characters[2].name).toBe("Rowan");
    expect(alex.opacity).toBeGreaterThan(0);
  });

  it("holds a gesture without an open-mouth twin only 1.6 s, then talks on the plain picture", () => {
    const alex = sprites.characters[0];
    const end = Math.round(SPEAKER_GESTURE_SEC * FPS);
    expect(gestureAt(alex, end - 1, FPS, timeline, sprites)).toBe("gesture-wave");
    expect(gestureAt(alex, end, FPS, timeline, sprites)).toBeNull();
    expect(at(0, 0.4).picture).toBe("gesture-wave"); // its own face, mouth as drawn
    expect(at(0, 0.4).scale).toBe(1);
  });

  it("blinks only on the calm face with the mouth closed", () => {
    const blinkFrame = Array.from({ length: 300 }, (_, frame) => frame).find((frame) => isBlinking(frame, FPS, "Lina"));
    expect(blinkFrame).toBeDefined();
  });
});
