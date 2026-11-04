import { describe, expect, it } from "vitest";
import { activeItemForFrame, attachItemsToLines } from "./vocab";
import type { EpisodeLine, IdiomItem, VocabItem } from "./types";

const line = (startSec: number, endSec: number, text: string): EpisodeLine => ({
  startSec,
  endSec,
  speaker: "Alex",
  speakerId: "alex-id",
  text,
  words: [],
});

const vocab = (word: string): VocabItem => ({
  word,
  partOfSpeech: "verb",
  ipa: "/test/",
  definitionEn: `${word} definition`,
  definitionVi: `${word} nghĩa`,
  exampleSentence: `An example with ${word}.`,
});

const idiom = (phrase: string): IdiomItem => ({
  phrase,
  meaningEn: `${phrase} meaning`,
  meaningVi: `${phrase} ý nghĩa`,
  exampleSentence: `An example with ${phrase}.`,
});

describe("attachItemsToLines", () => {
  it("attaches a word found in exactly one line", () => {
    const lines = [line(0, 3, "Hello there, how are you?"), line(3, 6, "I am doing great, thanks.")];
    const attached = attachItemsToLines([vocab("great")], [], lines);

    expect(attached).toEqual([{ lineIndex: 1, items: [{ kind: "vocab", ...vocab("great") }] }]);
  });

  it("attaches a word found in multiple lines to the first matching line only", () => {
    const lines = [line(0, 3, "Are you an early bird?"), line(3, 6, "Yes, an early bird for sure.")];
    const attached = attachItemsToLines([], [idiom("early bird")], lines);

    expect(attached).toEqual([{ lineIndex: 0, items: [{ kind: "idiom", ...idiom("early bird") }] }]);
  });

  it("silently drops an item that matches no line", () => {
    const lines = [line(0, 3, "This line has nothing relevant.")];
    const attached = attachItemsToLines([vocab("nonexistentword")], [], lines);

    expect(attached).toEqual([]);
  });

  it("combines vocab and idiom items on the same line: vocab first, then idioms, each in source order", () => {
    const lines = [line(0, 4, "You are clever, and that's a piece of cake for you.")];
    const attached = attachItemsToLines([vocab("clever")], [idiom("piece of cake")], lines);

    expect(attached).toEqual([
      {
        lineIndex: 0,
        items: [
          { kind: "vocab", ...vocab("clever") },
          { kind: "idiom", ...idiom("piece of cake") },
        ],
      },
    ]);
  });

  it("returns an empty array for empty inputs (no learning content at all)", () => {
    expect(attachItemsToLines([], [], [line(0, 3, "Any line.")])).toEqual([]);
  });

  it("returns an empty array when there are no lines", () => {
    expect(attachItemsToLines([vocab("word")], [idiom("phrase")], [])).toEqual([]);
  });
});

describe("activeItemForFrame", () => {
  it("returns null when there is no active line (a gap)", () => {
    const lines = [line(0, 3, "First line."), line(5, 8, "Second line.")];
    expect(activeItemForFrame(4, lines, [])).toBeNull();
  });

  it("returns null when the active line has no attached items", () => {
    const lines = [line(0, 3, "No learning items here.")];
    expect(activeItemForFrame(1, lines, [])).toBeNull();
  });

  it("returns the single attached item for the line's whole duration, with slot bounds equal to the line's own bounds", () => {
    const lines = [line(0, 4, "Line with one word.")];
    const attached = [{ lineIndex: 0, items: [{ kind: "vocab" as const, ...vocab("word") }] }];

    expect(activeItemForFrame(0, lines, attached)).toEqual({
      item: { kind: "vocab", ...vocab("word") },
      slotStartSec: 0,
      slotEndSec: 4,
    });
    expect(activeItemForFrame(3.9, lines, attached)?.item).toEqual({ kind: "vocab", ...vocab("word") });
  });

  it("time-slices a line with 2 items into 2 equal halves (D19.5-c, the real line-0 case)", () => {
    const lines = [line(0, 3.6, "Hey Maya, are you an early bird or a night owl?")];
    const items: import("./vocab").LearningItem[] = [
      { kind: "idiom", ...idiom("early bird") },
      { kind: "idiom", ...idiom("night owl") },
    ];
    const attached = [{ lineIndex: 0, items }];

    // First half (0.0-1.8s): "early bird". Second half (1.8-3.6s): "night owl".
    expect(activeItemForFrame(0.5, lines, attached)).toEqual({ item: items[0], slotStartSec: 0, slotEndSec: 1.8 });
    expect(activeItemForFrame(1.79, lines, attached)?.item).toEqual(items[0]);
    expect(activeItemForFrame(1.8, lines, attached)).toEqual({ item: items[1], slotStartSec: 1.8, slotEndSec: 3.6 });
    expect(activeItemForFrame(3.5, lines, attached)?.item).toEqual(items[1]);
  });

  it("time-slices a line with 3 items into 3 equal thirds", () => {
    const lines = [line(0, 9, "Three items line.")];
    const items: import("./vocab").LearningItem[] = [
      { kind: "vocab", ...vocab("one") },
      { kind: "vocab", ...vocab("two") },
      { kind: "vocab", ...vocab("three") },
    ];
    const attached = [{ lineIndex: 0, items }];

    expect(activeItemForFrame(1, lines, attached)?.item).toEqual(items[0]);
    expect(activeItemForFrame(4, lines, attached)?.item).toEqual(items[1]);
    expect(activeItemForFrame(7, lines, attached)?.item).toEqual(items[2]);
  });
});
