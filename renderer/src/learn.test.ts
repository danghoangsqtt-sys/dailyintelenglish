import { describe, expect, it } from "vitest";
import { soloPayloadSchema } from "./soloTypes";
import { cardText, countdownNumber, isLearnStyle, learningFor, mistakePair, rightAt, templateLabel } from "./learnMath";
import { isVoiceOnly } from "./shortsMath";

const card = (title: string, bullets: string[] = [], emphasis = "") => ({ kind: "text_card", title, bullets, emphasis }) as never;
const seg = (visual: never) => ({ id: "x", visual }) as never;

describe("Phase 64 quick-learning Shorts (ENH-046)", () => {
  it("knows the three templates as voice-only Shorts", () => {
    for (const style of ["mistakes", "wordday", "top5"]) {
      expect(isLearnStyle(style) && isVoiceOnly(style)).toBe(true);
      const base = { plan: { segments: [{ id: "a" }] }, timeline: [{ id: "a", start_sec: 0, end_sec: 1 }], photos: {}, pictures: {},
        geometry: { rules_version: 2, style: "vox", aspects: {} }, style };
      expect(soloPayloadSchema.safeParse(base).success).toBe(true);
    }
    expect(isLearnStyle("news")).toBe(false);
    expect(templateLabel("top5")).toBe("TOP 5 PHRASES");
  });

  it("reads a Don't say / Say pair from a comparison diagram, by id, label or order", () => {
    const pair = { kind: "diagram", template: "comparison", nodes: [
      { id: "say", label: "Say", detail: "I am bored." }, { id: "dont", label: "Don't say", detail: "I am boring." }] } as never;
    expect(mistakePair(pair)).toEqual({ wrong: "I am boring.", right: "I am bored." });
    const plain = { kind: "diagram", template: "comparison", nodes: [{ id: "a", label: "He go" }, { id: "b", label: "He goes" }] } as never;
    expect(mistakePair(plain)).toEqual({ wrong: "He go", right: "He goes" });
    expect(mistakePair(card("Hook"))).toBeNull();
  });

  it("shows the right phrase when the narrator says 'say' the second time", () => {
    const words = [{ text: "Don't", startSec: 1 }, { text: "say", startSec: 1.2 }, { text: "boring.", startSec: 1.6 },
      { text: "Say:", startSec: 2.4 }, { text: "bored", startSec: 2.7 }];
    expect(rightAt(words, 1, 4)).toBe(2.4);
    expect(rightAt(words.slice(0, 3), 0, 10)).toBe(4.5);
  });

  it("counts the Top 5 down between the hook and the follow line", () => {
    const segments = [card("Hook"), card("a"), card("b"), card("c"), card("d"), card("e"), card("Follow")].map(seg);
    expect(segments.map((_, i) => countdownNumber(segments, i))).toEqual([null, 5, 4, 3, 2, 1, null]);
    expect(countdownNumber([seg(card("a")), seg(card("b"))], 1)).toBeNull();
  });

  it("finds the learning pack's IPA and Vietnamese meaning for a word or phrase", () => {
    const learning = { vocab: [{ word: "Resilient", partOfSpeech: "adjective", ipa: "/rɪˈzɪliənt/", definitionEn: "", definitionVi: "kiên cường", exampleSentence: "" }],
      idioms: [{ phrase: "break the ice", meaningEn: "", meaningVi: "phá vỡ sự ngại ngùng", exampleSentence: "" }] };
    expect(learningFor(learning, "resilient")).toEqual({ ipa: "/rɪˈzɪliənt/", partOfSpeech: "adjective", meaningVi: "kiên cường" });
    expect(learningFor(learning, "Break the ice!")?.meaningVi).toBe("phá vỡ sự ngại ngùng");
    expect(learningFor(learning, "other")).toBeNull();
    expect(learningFor(undefined, "x")).toBeNull();
    expect(cardText(card("Break the ice", ["start a talk"]))).toEqual({ title: "Break the ice", detail: "start a talk", emphasis: "" });
  });
});
