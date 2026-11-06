import { describe, expect, it } from "vitest";
import { CARD_SEC, CROSSFADE_SEC, cardAt, fadeAt, termCards } from "./doodleMath";
import { soloPayloadSchema } from "./soloTypes";
import type { EpisodeLine, VocabItem } from "./types";

const line = (startSec: number, words: string[]): EpisodeLine => ({
  speaker: "N", text: words.join(" "), startSec, endSec: startSec + words.length, words: words.map((text, i) => ({ text, startSec: startSec + i, endSec: startSec + i + 1 })),
} as unknown as EpisodeLine);
const vocab = (word: string): VocabItem => ({ word, partOfSpeech: "n", ipa: "/x/", definitionEn: "en", definitionVi: "vi", exampleSentence: "" } as VocabItem);

describe("the crossfade", () => {
  const timeline = [{ start_sec: 0, end_sec: 5 }, { start_sec: 5, end_sec: 9 }];
  it("takes 0.4 s, and the first picture needs none", () => {
    expect(CROSSFADE_SEC).toBe(0.4);
    expect(fadeAt(timeline, 0, 0)).toBe(1);
    expect(fadeAt(timeline, 1, 5)).toBe(0);
    expect(fadeAt(timeline, 1, 5.2)).toBeCloseTo(0.5);
    expect(fadeAt(timeline, 1, 6)).toBe(1);
  });
});

describe("the term cards", () => {
  it("appear the first time a word is said, also in another form, and only for words of the list", () => {
    const lines = [line(0, ["He", "escaped,", "and", "escape", "was", "hard."]), line(10, ["A", "melting", "wax", "wing."])];
    const cards = termCards(lines, [vocab("escape"), vocab("wax"), vocab("wing")], ["escape", "wax"]);
    expect(cards.map((card) => [card.word, card.fromSec])).toEqual([["escape", 1], ["wax", 12]]);
    expect(cardAt(cards, 1 + CARD_SEC - 0.1)?.word).toBe("escape");
    expect(cardAt(cards, 1 + CARD_SEC + 0.1)).toBeUndefined();
  });
  it("find a phrase, skip a word with no entry or never said, and never overlap", () => {
    const lines = [line(0, ["They", "set", "off", "for", "the", "sea", "at", "dawn."])];
    const cards = termCards(lines, [vocab("set off"), vocab("sea"), vocab("gone")], ["set off", "sea", "gone", "dawn"]);
    expect(cards.map((card) => card.word)).toEqual(["set off", "sea"]);
    expect(cards[1].fromSec).toBe(cards[0].toSec);
  });
});

describe("the payload", () => {
  it("is voice-only and may hold a long plan", () => {
    const segments = Array.from({ length: 94 }, (_, i) => ({ id: `pic-${i}` }));
    const base = { style: "doodle", plan: { segments }, geometry: { rules_version: 2, style: "vox", aspects: {} }, timeline: segments, pictures: {}, photos: {} };
    expect(soloPayloadSchema.safeParse(base).success).toBe(true);
    const tooLong = Array.from({ length: 151 }, (_, i) => ({ id: `pic-${i}` }));
    expect(soloPayloadSchema.safeParse({ ...base, plan: { segments: tooLong }, timeline: tooLong }).success).toBe(false);
  });
});
