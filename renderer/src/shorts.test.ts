import { describe, expect, it } from "vitest";
import { soloPayloadSchema, type SoloPayload } from "./soloTypes";
import {
  blurGroup, drawsCard, fitFont, headlineOf, isKeyWord, isVoiceOnly, keyWordOf, newsPicture, pictureFor, spanWords, tickerOffset,
} from "./shortsMath";

const segment = (id: string, visual: object, scene?: string) => ({ id, visual, scene: scene ? { scene_id: scene } : null }) as never;
const payload = {
  plan: { segments: [
    segment("a", { kind: "text_card", title: "Big storm hits the coast", bullets: [], emphasis: "storm" }, "beach"),
    segment("b", { kind: "photo", asset: { asset_id: "p", version: 1 }, caption: "" }),
    segment("c", { kind: "chart", title: "Rain in mm", items: [{ label: "Mon", value: 20 }] }),
    segment("d", { kind: "quote", text: "Stay safe and stay inside.", highlight: "stay inside", attribution: "" }),
  ] },
  photos: { "p:1": "/photo.png" }, scenes: { beach: "/beach.png" }, activities: {},
} as unknown as SoloPayload;

describe("Phase 63 Shorts (ENH-045)", () => {
  it("accepts the news and blur payloads as voice-only (no presenter pictures)", () => {
    const base = { plan: { segments: [{ id: "a" }] }, timeline: [{ id: "a", start_sec: 0, end_sec: 1 }], photos: {}, pictures: {},
      geometry: { rules_version: 2, style: "vox", aspects: {} } };
    for (const style of ["news", "blur", "vox"]) expect(soloPayloadSchema.safeParse({ ...base, style }).success).toBe(true);
    expect(soloPayloadSchema.safeParse({ ...base, style: "presenter" }).success).toBe(false);
    expect(isVoiceOnly("news") && isVoiceOnly("blur") && !isVoiceOnly("presenter")).toBe(true);
  });

  it("chooses each segment's picture and never leaves a news fact without one", () => {
    expect(pictureFor(payload, payload.plan.segments[0])).toBe("/beach.png");
    expect(pictureFor(payload, payload.plan.segments[1])).toBe("/photo.png");
    expect(pictureFor(payload, payload.plan.segments[2])).toBeNull();
    expect(newsPicture(payload, 2)).toBe("/photo.png");
    expect(newsPicture({ ...payload, scenes: {}, photos: {} } as SoloPayload, 0)).toBeNull();
  });

  it("finds the headline, the key word and which visuals are drawn as a card", () => {
    expect(headlineOf(payload.plan.segments[0].visual)).toBe("Big storm hits the coast");
    expect(headlineOf(payload.plan.segments[3].visual)).toBe("Stay safe and stay inside.");
    expect(headlineOf({ kind: "quote", text: "x".repeat(120), highlight: "", attribution: "" } as never).length).toBe(88);
    expect(keyWordOf(payload.plan.segments[3].visual)).toBe("stay inside");
    expect(keyWordOf(payload.plan.segments[0].visual)).toBe("storm");
    expect([0, 1, 2, 3].map((i) => drawsCard(payload.plan.segments[i].visual))).toEqual([false, false, true, false]);
  });

  it("crawls the ticker steadily and loops", () => {
    expect(tickerOffset(0, 1000)).toBeCloseTo(0);
    expect(tickerOffset(2, 1000)).toBe(-180);
    expect(tickerOffset(12, 1000)).toBe(-80);
  });

  it("pops the words of the current group in as they are spoken", () => {
    const words = Array.from({ length: 10 }, (_, i) => ({ text: `w${i}`, startSec: i * 0.5, endSec: i * 0.5 + 0.4 }));
    const lines = [{ words }];
    expect(spanWords(lines, 1, 3).map((word) => word.text)).toEqual(["w2", "w3", "w4", "w5"]);
    const early = blurGroup(words, 0.09);
    expect(early.map((word) => word.text)).toEqual(["w0", "w1", "w2", "w3", "w4", "w5", "w6"]);
    expect(early[0].pop).toBeCloseTo(0.5);
    expect(early[1].pop).toBe(0);
    expect(blurGroup(words, 4.0).map((word) => word.text)).toEqual(["w7", "w8", "w9"]);
    expect(blurGroup([], 1)).toEqual([]);
  });

  it("fits the font and matches key words without punctuation", () => {
    expect(fitFont(20, 900, 4, 50, 120)).toBe(120);
    expect(fitFont(400, 900, 4, 50, 120)).toBe(50);
    expect(isKeyWord("Inside!", "stay inside")).toBe(true);
    expect(isKeyWord("outside", "stay inside")).toBe(false);
  });
});
