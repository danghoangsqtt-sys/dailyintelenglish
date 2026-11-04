import { describe, expect, it } from "vitest";
import { LINEART_ICONS } from "./lineartIcons";
import { fitSize, headSegments, isVietnamese, runStart, screenKey, splitProgress, underlineProgress, wheelPositions, wordSegments } from "./rootsMath";
import { sampleProps } from "./sampleShort";
import { episodeInputPropsSchema } from "./types";

const part = (text: string, role: "prefix" | "root" | "suffix") => ({ text, role, meaning: "" });

describe("Phase 87: the word-roots Short", () => {
  it("colours a word by its parts, or keeps it whole when the parts do not spell it", () => {
    expect(wordSegments("compress", [part("com", "prefix"), part("press", "root")])).toEqual(
      [{ text: "COM", role: "prefix" }, { text: "PRESS", role: "root" }]);
    expect(wordSegments("expression", [part("ex", "prefix"), part("press", "root")])).toEqual([{ text: "EXPRESSION", role: "root" }]);
    // a suffix family marks its suffix, a prefix family its prefix; an empty part is ignored
    expect(wordSegments("action", [part("act", "root"), part("ion", "suffix")], "suffix")).toEqual(
      [{ text: "ACT", role: "prefix" }, { text: "ION", role: "root" }]);
    expect(wordSegments("unhappy", [part("un-", "prefix"), part("happy", "root"), part("-", "suffix")], "prefix")).toEqual(
      [{ text: "UN", role: "root" }, { text: "HAPPY", role: "prefix" }]);
  });

  it("marks the family's head inside a word, a suffix from the end", () => {
    expect(headSegments("impress", "press")).toEqual([{ text: "IM", role: "rest" }, { text: "PRESS", role: "root" }]);
    expect(headSegments("dismiss", "mit / miss")).toEqual([{ text: "DIS", role: "rest" }, { text: "MISS", role: "root" }]);
    expect(headSegments("unhappy", "un-")).toEqual([{ text: "UN", role: "root" }, { text: "HAPPY", role: "rest" }]);
    expect(headSegments("education", "-tion / -sion")).toEqual([{ text: "EDUCA", role: "rest" }, { text: "TION", role: "root" }]);
  });

  it("animates the split and the underline from the beat start, eased and clamped", () => {
    expect(splitProgress(10, 10)).toBe(0);
    expect(splitProgress(10.65, 10)).toBeCloseTo(1);
    expect(underlineProgress(11, 10)).toBe(1);
    expect(underlineProgress(10.4, 10)).toBeGreaterThan(0.5);
  });

  it("spreads the wheel evenly from the top", () => {
    const spots = wheelPositions(4, 100);
    expect(spots).toEqual([{ x: 0, y: -100 }, { x: 100, y: 0 }, { x: 0, y: 100 }, { x: -100, y: 0 }]);
  });

  it("keeps a word on screen across its hook, whole, split and example beats", () => {
    const lines = [{ startSec: 0, roots: { beat: "wheel" } }, { startSec: 2, roots: { beat: "whole", word: "compress" } },
      { startSec: 4, roots: { beat: "split", word: "compress" } }, { startSec: 6, roots: { beat: "example", word: "compress" } },
      { startSec: 8, roots: { beat: "whole", word: "depress" } }];
    expect(runStart(lines, 3)).toBe(2);
    expect(runStart(lines, 4)).toBe(8);
    expect(screenKey({ beat: "quiz", word: "suppress" })).toBe(screenKey({ beat: "follow", word: "suppress" }));
  });

  it("fits long words and tells Vietnamese lines apart", () => {
    expect(fitSize("press", 860, 170)).toBe(170);
    expect(fitSize("infrastructure", 860, 170)).toBeLessThan(170);
    expect(isVietnamese("Bạn có biết Express là bày tỏ,")).toBe(true);
    expect(isVietnamese("Did you know Express means to show,")).toBe(false);
  });

  it("has the icons the sample uses, and a valid silent sample", () => {
    for (const name of ["device-desktop", "file-zip", "news", "lock", "mood-smile"]) expect(LINEART_ICONS[name]).toBeTruthy();
    const props = sampleProps("roots", { title: "Gốc PRESS" });
    expect(() => episodeInputPropsSchema.parse(props)).not.toThrow();
    expect(props.shortStyle).toBe("roots");
    expect(props.lines.map((line) => line.roots?.beat)).toEqual(["hook", "twins", "wheel", "whole", "split", "example", "quiz", "follow"]);
  });
});
