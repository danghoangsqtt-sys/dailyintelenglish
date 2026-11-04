import { describe, expect, it } from "vitest";
import { sampleProps } from "./sampleShort";
import { episodeInputPropsSchema } from "./types";
import { aroundWord, copiesAt, copyCentre, countAt, COPY_PLACES, levelPhraseSize, levelSaying, wordExplains, wordSize } from "./wordRepeatMath";

describe("Phase 96: the Word of the day Short", () => {
  it("adds one copy of the word per repetition after the first", () => {
    expect([1, 2, 6].map(copiesAt)).toEqual([0, 1, 5]);
    expect(copiesAt(99)).toBe(COPY_PLACES.length);
  });

  it("counts 1-2-3 in the silence after the question", () => {
    expect([10.5, 11.5, 12.5].map((time) => countAt(time, 10, 3))).toEqual([1, 2, 3]);
    expect(countAt(9.9, 10, 3)).toBeNull();
    expect(countAt(13.1, 10, 3)).toBeNull();
    expect(countAt(10.5, 10, 0)).toBeNull();
  });

  it("keeps an advanced phrase large and counts its sayings", () => {
    expect(levelPhraseSize("I'm beat")).toBe(84);
    expect(levelPhraseSize("up to my ears in work")).toBe(68);
    expect([0, 1, 2, 3].map(levelSaying)).toEqual([1, 1, 2, 2]);
  });

  it("keeps every copy on the frame", () => {
    expect(copyCentre(230, "meticulous", 64)).toBeGreaterThanOrEqual(24 + (10 * 64 * 0.62) / 2);
    expect(copyCentre(900, "meticulous", 92)).toBeLessThanOrEqual(1080 - 24 - (10 * 92 * 0.62) / 2);
    expect(copyCentre(540, "cozy", 76)).toBe(540);
  });

  it("marks the word in its example, an inflected form too", () => {
    expect(aroundWord("He is meticulous in his work.", "meticulous")).toEqual(["He is ", "meticulous", " in his work."]);
    expect(aroundWord("She studies at night.", "study")[1]).toBe("studies");
    expect(aroundWord("Nothing here.", "cozy")).toEqual(["Nothing here.", "", ""]);
  });

  it("follows the audience for the explanation", () => {
    expect(wordExplains("international")).toEqual({ en: true, vi: false });
    expect(wordExplains("vietnamese")).toEqual({ en: false, vi: true });
    expect(wordExplains("both")).toEqual({ en: true, vi: true });
  });

  it("keeps a long word inside the safe width", () => {
    expect(wordSize("cozy")).toBe(150);
    expect(wordSize("responsibilities") * 16 * 0.62).toBeLessThanOrEqual(936);
  });

  it("gives a valid sample: six sayings, then the example", () => {
    const props = episodeInputPropsSchema.parse(sampleProps("wordday", { title: "Word of the day: 'cozy'", brief: "warm and comfortable", vi: "ấm cúng" }));
    expect(props.shortStyle).toBe("wordday");
    expect(props.lines.map((line) => line.wordday?.beat)).toEqual([...Array(6).fill("repeat"), "example"]);
  });
});
