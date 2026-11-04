import { describe, expect, it } from "vitest";
import { BODY_LIMITS, buildConversationCues, conversationBody, conversationCues, pictureAlignment } from "./conversationMotion";
import { cameraAt, gestureAt, poseFade, poseOf, spriteFrame } from "./spriteTimeline";
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
      expect(cue.endSec - cue.startSec).toBeLessThanOrEqual(2.001);
      expect(cue.endSec - cue.startSec).toBeGreaterThanOrEqual(0.599);
      expect(character.pictures[cue.picture]).toBeDefined();
      expect(character.pictures[`${cue.picture}__open`]).toBeDefined();
      if (index) expect(cue.startSec - cues[index - 1].endSec).toBeGreaterThanOrEqual(0.29);
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
    expect(reactions.every((reaction) => reaction.endSec - reaction.startSec <= 1.101)).toBe(true);
    const reacting = spriteFrame(listener, Math.round((reactions[0].startSec + 0.4) * 30), 30, [line], sprites, 900, 1280);
    expect(reacting.picture).toBe("gesture-listen");
    expect(reacting.scale).toBe(1);
  });

  it("preserves minimal/short/no-word fallback and never chooses a missing open-mouth pair", () => {
    expect(buildConversationCues({ ...line, words: [] }, plan, character, true)).toBeNull();
    expect(buildConversationCues({ ...line, endSec: 1.1 }, plan, character, true)).toBeNull();
    expect(buildConversationCues({ ...line, words: words.slice(0, 1) }, plan, character, true)).toBeNull();
    expect(buildConversationCues(line, plan, { ...character, pictures: { calm__closed: "a", calm__open: "b" } }, true)).toBeNull();
    const pictures = { ...character.pictures };
    delete pictures["gesture-wave__open"];
    expect(buildConversationCues(line, plan, { ...character, pictures }, true)!.every((cue) => cue.picture !== "gesture-wave")).toBe(true);
    expect(buildConversationCues(line, { ...plan, slot: null }, character, true)).toBeNull();
  });

  it("bounds whole-character movement without resizing or changing the imported sprite", () => {
    for (const speaking of [true, false]) for (const slot of [0, 1]) for (let i = 0; i <= 1200; i++) {
      const body = conversationBody(i / 60, line, slot, speaking);
      expect(Math.abs(body.x)).toBeLessThanOrEqual(BODY_LIMITS.x);
      expect(Math.abs(body.y)).toBeLessThanOrEqual(BODY_LIMITS.y);
      expect(Math.abs(body.rotation)).toBeLessThanOrEqual(BODY_LIMITS.rotation);
    }
    expect(conversationBody(line.endSec + 1, line, 0, true).x).toBeCloseTo(0);
    const offset = { ...character, offsets: { "gesture-talk": [8, -3] as [number, number] } };
    expect(pictureAlignment(offset, "gesture-talk", 800, 960)).toEqual({ x: -5, y: 1.875 });
    expect(pictureAlignment({ ...offset, mirror: true }, "gesture-talk", 800, 960).x).toBe(5);
  });
});

describe("Phase 61 lively performance (ENH-043)", () => {
  const short: EpisodeLine = { startSec: 0, endSec: 2.2, text: "Really? That sounds great.", speaker: "Alex", speakerId: "a",
    words: ["Really", "That", "sounds", "great"].map((word, index) => ({ text: word, startSec: 0.1 + index * 0.5, endSec: 0.5 + index * 0.5 })) };
  const shortPlan: SpriteLine = { ...plan, mouth: [[0.1, 2.0]] };

  it("gives short lines phrase gestures too", () => {
    const cues = buildConversationCues(short, shortPlan, character, true)!;
    expect(cues.length).toBeGreaterThanOrEqual(1);
    expect(cues.every((cue) => cue.endSec <= short.endSec && cue.endSec - cue.startSec >= 0.599)).toBe(true);
  });

  it("leans the speaker toward the listener and bobs on a stressed word onset; the listener nods after a pause", () => {
    const leanLeft = conversationBody(1, line, 0, true), leanRight = conversationBody(1, line, 1, true);
    expect(leanLeft.rotation).toBeGreaterThan(0);
    expect(leanRight.rotation).toBeLessThan(0);
    const word = line.words.find((item) => item.text.length >= 6)!;
    const onset = conversationBody(word.startSec + 0.14, line, 0, true).y;
    const before = conversationBody(word.startSec - 0.02, line, 0, true).y;
    expect(onset).toBeLessThan(before - 4);
    const paused: EpisodeLine = { ...short, words: [short.words[0], { ...short.words[1], startSec: 1.4, endSec: 1.8 }] };
    expect(conversationBody(0.5 + 0.25, paused, 1, false).y).toBeGreaterThan(5);
  });

  it("cross-fades a pose change for 0.15 s and swaps the mouth directly", () => {
    const sprites: EpisodeSprites = { characters: [character], lines: [plan], backgrounds: {}, lineBackgrounds: [], cutaways: [] };
    expect(poseOf("gesture-wave__open")).toBe("gesture-wave");
    expect(poseOf("blink")).toBe("calm");
    const cue = buildConversationCues(line, plan, character, true)![0];
    const after = Math.ceil(cue.endSec * 30);
    const fade = poseFade(character, after, 30, [line], sprites, 900, 1280);
    expect(fade).not.toBeNull();
    expect(poseOf(fade!.picture)).toBe(cue.picture);
    expect(fade!.opacity).toBeGreaterThan(0);
    expect(fade!.opacity).toBeLessThan(1);
    expect(poseFade(character, after + 6, 30, [line], sprites, 900, 1280)).toBeNull();
    // inside a gesture only the mouth changes: no fade
    const inside = Math.round((cue.startSec + 0.5) * 30);
    expect(poseFade(character, inside, 30, [line], sprites, 900, 1280)).toBeNull();
  });

  it("pushes the camera in toward the speaker during a line and is back at 1 between lines", () => {
    const sprites: EpisodeSprites = { characters: [character, { ...character, slot: 1, name: "Lina" }], lines: [plan, { ...plan, slot: 1 }],
      backgrounds: {}, lineBackgrounds: [], cutaways: [] };
    const second: EpisodeLine = { ...short, startSec: line.endSec + 1, endSec: line.endSec + 3.2 };
    const middle = cameraAt(Math.round(line.endSec / 2 * 30), 30, [line, second], sprites, 1280, 720);
    expect(middle.scale).toBeGreaterThan(1.03);
    expect(middle.scale).toBeLessThanOrEqual(1.06);
    expect(middle.originX).toBeLessThan(640);
    expect(cameraAt(Math.round((line.endSec + 0.5) * 30), 30, [line, second], sprites, 1280, 720).scale).toBe(1);
    const emphatic = cameraAt(Math.round((second.startSec + 1.2) * 30), 30, [line, second], sprites, 1280, 720);
    expect(emphatic.originX).toBeGreaterThan(640);
    expect(emphatic.scale).toBeGreaterThan(middle.scale);
  });
});
