import { describe, expect, it } from "vitest";
import { podcastLayer } from "./podcastLayout";
import {
  FLIP_SQUASH, bodyAt, flipAt,
  BACKGROUND_FADE_FRAMES, LISTENER_BRIGHTNESS, SPRITE_HEIGHT, canvasBox, faceMask, heldLineIndex, isBlinking, isMouthOpen,
  spriteBackground, spriteFrame, stageTop,
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
  characters: [character(0, "Alex", ["gesture-wave"]), character(1, "Lina")],
  lines: [
    { slot: 0, expression: "smile", listenerExpression: "calm", gesture: "wave", listenerGesture: null, mouth: [[0.2, 0.6]] },
    { slot: 1, expression: "calm", listenerExpression: "smile", gesture: null, listenerGesture: null, mouth: [[3, 4]] },
    { slot: 1, expression: "calm", listenerExpression: "calm", gesture: "talk", listenerGesture: null, mouth: [] },
  ],
  backgrounds: { cafe: "remotion-render/sprites/p/bg/cafe.png", park: "remotion-render/sprites/p/bg/park.png" },
  lineBackgrounds: ["cafe", "cafe", "park"],
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

  it("holds the last started line and opens the mouth only inside its intervals", () => {
    expect(heldLineIndex(-1, timeline)).toBe(-1);
    expect(heldLineIndex(2.2, timeline)).toBe(0);
    expect(isMouthOpen(0.3, [[0.2, 0.6]])).toBe(true);
    expect(isMouthOpen(0.6, [[0.2, 0.6]])).toBe(false);
  });

  it("puts the speaker's face for the mouth on the body, and the gesture body while the line lasts", () => {
    const open = at(0, 0.4);
    expect(open.speaking).toBe(true);
    expect(open.body).toBe("gesture-wave");
    expect(open.face).toBe("smile__open");
    expect(open.faceShift).toEqual([1 - 4, 1 + 2]);
    expect(at(0, 1.0).face).toBe("smile__closed");
    expect(at(0, 2.4).body).toBe("calm__closed"); // the gesture ends just after the line
  });

  it("uses only pictures that exist: Lina has no talking gesture, the plain body stays", () => {
    const state = at(1, 6);
    expect(state.body).toBe("calm__closed");
    expect(state.face).toBeNull(); // calm and closed on the calm body: one picture is enough
  });

  it("dims and shrinks the listener and brightens the speaker after a short turn change", () => {
    const listener = at(1, 1);
    expect(listener.brightness).toBeCloseTo(LISTENER_BRIGHTNESS);
    expect(listener.scale).toBe(1); // dimmed, never resized
    expect(listener.face).toBe("calm__closed" === listener.body ? null : listener.face);
    const turn = at(1, 2.5 + 3 / FPS);
    expect(turn.brightness).toBeGreaterThan(LISTENER_BRIGHTNESS);
    expect(turn.brightness).toBeLessThan(1);
    expect(at(1, 3.5).brightness).toBeCloseTo(1);
    expect(at(1, 2.5 + 4 / FPS).y).toBeLessThan(-5); // the hop
    expect(at(0, 3.5).face).toBe("smile__closed"); // the listener smiles back
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

  it("stands both canvases on the stage with the highest head near the top", () => {
    expect(stageTop(sprites.characters)).toBeCloseTo(0.05 - 0.1 * SPRITE_HEIGHT);
    const left = canvasBox(0, 1280, 720, sprites.characters);
    const right = canvasBox(1, 1280, 720, sprites.characters);
    expect(left.height).toBeCloseTo(SPRITE_HEIGHT * 720);
    expect(left.left + left.width / 2).toBeCloseTo(0.27 * 1280);
    expect(right.left).toBeGreaterThan(left.left);
    expect(faceMask([0.5, 0.25, 0.08, 0.07], [0.5, 0.25])).toBe(
      "radial-gradient(ellipse 8.00% 7.00% at 50.00% 25.00%, #000 70%, transparent 100%)");
  });

  it("changes the pose with a quick paper-doll flip, never a blend", () => {
    const alex = sprites.characters[0];
    // Alex waves during line 0 (0 to 2 s) and keeps the wave 0.3 s: the calm body comes back at 2.3 s
    const change = Math.round(2.3 * FPS);
    expect(bodyAt(alex, change - 1, FPS, timeline, sprites)).toBe("gesture-wave");
    expect(bodyAt(alex, change, FPS, timeline, sprites)).toBe("calm__closed");
    const squash = [-3, -2, -1, 0, 1, 2, 3].map((offset) => flipAt(alex, change + offset, FPS, timeline, sprites));
    expect(squash[0]).toBe(1);
    expect(squash[1]).toBeLessThan(1);
    expect(squash[2]).toBeCloseTo(FLIP_SQUASH);
    expect(squash[3]).toBeCloseTo(FLIP_SQUASH);
    expect(squash[4]).toBeGreaterThan(FLIP_SQUASH);
    expect(squash[6]).toBe(1);
    expect(at(0, 1).flip).toBe(1); // no change near: no squash
  });
});
