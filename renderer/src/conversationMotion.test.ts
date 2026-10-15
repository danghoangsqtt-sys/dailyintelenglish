import { describe, expect, it } from "vitest";
import { buildConversationCues, conversationBody, conversationCues, pictureAlignment } from "./conversationMotion";
import { gestureAt, spriteFrame } from "./spriteTimeline";
import type { EpisodeLine, EpisodeSprites, SpriteCharacter, SpriteLine } from "./types";

const text = "Hello everyone. Today we are exploring this busy local market together. Look over there at those beautiful fresh vegetables. Thank you for coming with us today.";
const words = text.split(" ").map((word, index) => ({ text: word.replace(/[.!?]/g, ""), startSec: index * 0.55, endSec: index * 0.55 + 0.4 }));
const line: EpisodeLine = { startSec: 0, endSec: words.at(-1)!.endSec, text, words, speaker: "Alex", speakerId: "a" };
const names = ["calm__closed", "calm__open", "blink", ...["talk", "open", "wave", "heart", "point", "think", "listen"].flatMap((name) => [`gesture-${name}`, `gesture-${name}__open`])];
const character: SpriteCharacter = { slot: 0, name: "Alex", pictures: Object.fromEntries(names.map((name) => [name, `${name}.png`])),
  faceEllipse: [0.5, 0.2, 0.1, 0.1], topFraction: 0.1, offsets: {}, mirror: false, fromSec: 0, toSec: null };
const plan: SpriteLine = { slot: 0, expression: "calm", listenerExpression: "calm", gesture: "wave", listenerGesture: "listen", mouth: [[0, line.endSec]] };

describe("phrase-level conversation performance", () => {
  it("uses several semantic gestures within one long turn, with neutral rests and no invented poses", () => {
    const cues = buildConversationCues(line, plan, character, true)!;
    expect(cues.length).toBeGreaterThanOrEqual(3);
    expect(cues[0].picture).toBe("gesture-wave");
    expect(cues[0].endSec).toBeLessThan(2);
    expect(cues.some((cue) => cue.picture === "gesture-point")).toBe(true);
    expect(cues.some((cue) => cue.picture === "gesture-heart")).toBe(true);
    cues.forEach((cue, index) => {
      expect(cue.startSec).toBeGreaterThanOrEqual(line.startSec);
      expect(cue.endSec).toBeLessThanOrEqual(line.endSec);
      expect(cue.endSec - cue.startSec).toBeLessThanOrEqual(2.301);
      expect(cue.endSec - cue.startSec).toBeGreaterThanOrEqual(0.799);
      expect(character.pictures[cue.picture]).toBeDefined();
      expect(character.pictures[`${cue.picture}__open`]).toBeDefined();
      if (index) expect(cue.startSec - cues[index - 1].endSec).toBeGreaterThanOrEqual(0.89);
    });
    expect(conversationCues(line, plan, character, true)).toEqual(cues);
    expect(conversationCues(line, plan, character, true)).toBe(conversationCues(line, plan, character, true));
  });

  it("keeps the original mouth timing through gestures and neutral rests; listeners never inherit the open mouth", () => {
    const sprites: EpisodeSprites = { characters: [character], lines: [plan], backgrounds: {}, lineBackgrounds: [], cutaways: [] };
    const cues = buildConversationCues(line, plan, character, true)!;
    const cue = cues[0];
    const within = Math.round((cue.startSec + 0.25) * 30);
    expect(spriteFrame(character, within, 30, [line], sprites, 900, 1280).picture).toBe(`${cue.picture}__open`);
    const rest = Math.round((cue.endSec + 0.3) * 30);
    expect(gestureAt(character, rest, 30, [line], sprites)).toBeNull();
    expect(spriteFrame(character, rest, 30, [line], sprites, 900, 1280).picture).toBe("calm__open");
    const listener = { ...character, slot: 1 };
    const reactions = buildConversationCues(line, plan, listener, false)!;
    expect(reactions.length).toBeGreaterThan(1);
    expect(reactions.every((reaction) => reaction.endSec - reaction.startSec <= 1.351)).toBe(true);
    const reacting = spriteFrame(listener, Math.round((reactions[0].startSec + 0.4) * 30), 30, [line], sprites, 900, 1280);
    expect(reacting.picture).toBe("gesture-listen");
    expect(reacting.scale).toBe(1);
  });

  it("preserves minimal/short/no-word fallback and never chooses a missing open-mouth pair", () => {
    expect(buildConversationCues({ ...line, words: [] }, plan, character, true)).toBeNull();
    expect(buildConversationCues({ ...line, endSec: 3 }, plan, character, true)).toBeNull();
    expect(buildConversationCues(line, plan, { ...character, pictures: { calm__closed: "a", calm__open: "b" } }, true)).toBeNull();
    const pictures = { ...character.pictures };
    delete pictures["gesture-wave__open"];
    expect(buildConversationCues(line, plan, { ...character, pictures }, true)!.every((cue) => cue.picture !== "gesture-wave")).toBe(true);
    expect(buildConversationCues(line, { ...plan, slot: null }, character, true)).toBeNull();
  });

  it("bounds whole-character movement without resizing or changing the imported sprite", () => {
    for (const speaking of [true, false]) for (const slot of [0, 1]) for (let i = 0; i <= 1200; i++) {
      const body = conversationBody(i / 60, 0, 18, slot, speaking);
      expect(Math.abs(body.x)).toBeLessThanOrEqual(1.5);
      expect(Math.abs(body.y)).toBeLessThanOrEqual(0.8);
      expect(Math.abs(body.rotation)).toBeLessThanOrEqual(0.301);
    }
    expect(conversationBody(19, 0, 18, 0, true).x).toBeCloseTo(0);
    const offset = { ...character, offsets: { "gesture-talk": [8, -3] as [number, number] } };
    expect(pictureAlignment(offset, "gesture-talk", 800, 960)).toEqual({ x: -5, y: 1.875 });
    expect(pictureAlignment({ ...offset, mirror: true }, "gesture-talk", 800, 960).x).toBe(5);
  });
});
