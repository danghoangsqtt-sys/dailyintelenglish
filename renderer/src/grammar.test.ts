import { describe, expect, it } from "vitest";
import { cardsSeen, chipColour, countdown, markedPieces, pillColour, pillText, rowsBefore, sceneStart, stackScale } from "./grammarMath";
import { sampleProps } from "./sampleShort";
import { episodeInputPropsSchema } from "./types";

import type { GrammarCard } from "./types";

const line = (startSec: number, grammar: Partial<GrammarCard>) =>
  ({ startSec, grammar: { beat: "scene", scene: 0, label: "", title: "", cards: [], ...grammar } as GrammarCard });

describe("Phase 88: the easy-grammar Short", () => {
  it("keeps one colour per grammar role", () => {
    expect(chipColour("be").fill).toBe("#2F6FD6");
    expect(chipColour("v3")).toEqual({ fill: "#F2C230", text: "#151515" });
    expect(chipColour("unknown")).toEqual(chipColour("plain"));
    expect(pillColour("hook", 0)).toBe("#D64545");
    expect(pillColour("scene", 1)).not.toBe(pillColour("scene", 2));
    expect(pillText("scene", 2, "BẺ KHOÁ V3", true)).toBe("PHÂN CẢNH 2 • BẺ KHOÁ V3");
    expect(pillText("scene", 2, "THE V3 STICKER", false)).toBe("SCENE 2 • THE V3 STICKER");
    expect(pillText("summary", 4, "TỔNG KẾT BẢN CHẤT", true)).toBe("TỔNG KẾT BẢN CHẤT");
  });

  it("animates only the cards and rows that are new on a line", () => {
    const a = { kind: "compare", left_en: "A", right_en: "B" }, b = { kind: "formula", chips: [] };
    const table = (rows: string[][]) => ({ kind: "table", columns: ["x", "y"], rows });
    const lines = [line(0, { beat: "scene", scene: 1, title: "T", cards: [a] }), line(2, { beat: "scene", scene: 1, title: "T", cards: [a, b] }),
      line(4, { beat: "scene", scene: 2, title: "U", cards: [b] }),
      line(6, { beat: "summary", scene: 3, title: "S", cards: [table([["1", "2"]])] }),
      line(8, { beat: "summary", scene: 3, title: "S", cards: [table([["1", "2"], ["3", "4"]])] })];
    expect(cardsSeen(lines, 1)).toEqual([true, false]);
    expect(cardsSeen(lines, 2)).toEqual([false]);  // a new scene shows its cards anew
    expect(cardsSeen(lines, 4)).toEqual([true]);   // the same table, one row more
    expect(rowsBefore(lines, 4)).toBe(1);
    expect(rowsBefore(lines, 3)).toBe(0);
    expect(sceneStart(lines, 1)).toBe(0);
    expect(sceneStart(lines, 4)).toBe(6);
  });

  it("colours the marked words of an example and counts the quiz down", () => {
    expect(markedPieces("The room was cleaned yesterday.", [{ text: "was", role: "be" }, { text: "cleaned", role: "v3" }])).toEqual([
      { text: "The room " }, { text: "was", role: "be" }, { text: " " }, { text: "cleaned", role: "v3" }, { text: " yesterday." }]);
    expect(markedPieces("It has been done.", [])).toEqual([{ text: "It has been done." }]);
    expect(markedPieces("Washing was easy.", [{ text: "was", role: "be" }]).filter((piece) => piece.role)).toHaveLength(1);
    expect([countdown(10, 10), countdown(11.2, 10), countdown(12.5, 10), countdown(20, 10)]).toEqual([3, 2, 1, 1]);
    expect(stackScale(2)).toBe(1);
    expect(stackScale(4)).toBeLessThan(stackScale(3));
  });

  it("has a valid silent sample", () => {
    const props = sampleProps("grammar", { title: "Câu bị động" });
    expect(() => episodeInputPropsSchema.parse(props)).not.toThrow();
    expect(props.shortStyle).toBe("grammar");
    expect(props.lines.map((item) => item.grammar?.beat)).toEqual(
      ["hook", "hook", "hook", "scene", "scene", "scene", "scene", "summary", "summary", "quiz", "follow"]);
  });
});
