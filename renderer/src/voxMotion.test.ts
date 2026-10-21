import { describe, expect, it } from "vitest";
import {
  TRANSITIONS, WORLD_VIEW, arrowPaths, boardCamera, countUp, easeInOut, easeOutBack, easeOutBounce, mapViewAt, shapeAt, shapeFor,
  smoothProgress, stampAt, transitionAt, transitionFor, transitionStyles, wobblyPath, wordAppear,
} from "./voxMotion";

const timeline = [0, 6, 12, 18, 24, 30, 36, 42].map((start) => ({ start_sec: start, end_sec: start + 6 }));

describe("Phase 61 VOX transitions (ENH-043)", () => {
  it("cycles the six kinds over the boundaries and none before the first segment", () => {
    expect(transitionFor(0)).toBeNull();
    expect(Array.from({ length: 6 }, (_, i) => transitionFor(i + 1))).toEqual([...TRANSITIONS]);
    expect(transitionFor(7)).toBe("slide");
  });

  it("runs 0.5 s from the segment start with an eased share", () => {
    expect(transitionAt(timeline, 1, 5.99)).toBeNull();
    expect(transitionAt(timeline, 1, 6)).toEqual({ kind: "slide", t: 0 });
    expect(transitionAt(timeline, 1, 6.25)!.t).toBeCloseTo(0.5);
    expect(transitionAt(timeline, 1, 6.5)).toBeNull();
    expect(transitionAt([{ start_sec: 0, end_sec: 1 }, { start_sec: 1, end_sec: 1.4 }], 1, 1.19)).not.toBeNull();
    expect(transitionAt([{ start_sec: 0, end_sec: 1 }, { start_sec: 1, end_sec: 1.4 }], 1, 1.21)).toBeNull();
  });

  it("ends every kind with the new board fully in place", () => {
    for (const kind of TRANSITIONS) {
      const end = transitionStyles(kind, 1, 1280).entering;
      const transform = String(end.transform ?? "");
      expect(transform.includes("translateX(0.0px)") || transform === "" || transform.includes("scale(1.0000)")).toBe(true);
      if (end.clipPath) expect(String(end.clipPath)).toMatch(/135\.0%|circle\(75\.00%/);
      if (end.filter) expect(String(end.filter)).toMatch(/blur\(0\.0px\)|brightness\(1\.000\)/);
    }
    expect(transitionStyles("whip", 0.5, 1280).entering.filter).toBe("blur(18.0px)");
    expect(transitionStyles("flip", 0.5, 1280).top).toBe("leaving");
  });
});

describe("Phase 61 VOX morph, camera and effects", () => {
  it("morphs the decorative shape from the previous segment's to the new one's", () => {
    expect(shapeAt(timeline, 2, 12)).toMatchObject({ x: shapeFor(1).x, size: shapeFor(1).size });
    expect(shapeAt(timeline, 2, 13)).toEqual(shapeFor(2));
    const middle = shapeAt(timeline, 2, 12.25);
    expect(middle.x).toBeCloseTo((shapeFor(1).x + shapeFor(2).x) / 2);
    expect(middle.color).toMatch(/^rgba\(/);
  });

  it("flies the map from the world to the region and lands exactly", () => {
    const target = { west: 90, east: 120, south: 0, north: 20 };
    expect(mapViewAt(target, 0)).toEqual(WORLD_VIEW);
    const end = mapViewAt(target, 1);
    (["west", "east", "south", "north"] as const).forEach((key) => expect(end[key]).toBeCloseTo(target[key]));
    const middle = mapViewAt(target, 0.5);
    expect(middle.east - middle.west).toBeLessThan(WORLD_VIEW.east - WORLD_VIEW.west);
    expect(middle.east - middle.west).toBeGreaterThan(30);
  });

  it("counts chart numbers up and ends on the exact value", () => {
    expect(countUp(45, 0)).toBe(0);
    expect(countUp(45, 0.5)).toBe(23);
    expect(countUp(2.5, 0.5)).toBe(1.3);
    expect(countUp(1234.56, 1)).toBe(1234.56);
  });

  it("pushes the board camera in slowly and alternates the pan", () => {
    expect(boardCamera(0, timeline[0], 0)).toEqual({ scale: 1, x: 0, y: -0 });
    const end = boardCamera(6, timeline[0], 0);
    expect(end.scale).toBeCloseTo(1.035);
    expect(Math.sign(end.x)).toBe(-Math.sign(boardCamera(12, timeline[1], 1).x));
  });

  it("gives smooth narration progress and bouncy word entrances", () => {
    const words = [{ startSec: 0, endSec: 1 }, { startSec: 1, endSec: 2 }];
    expect(smoothProgress(words, 0.5)).toBeCloseTo(0.25);
    expect(smoothProgress(words, 2)).toBe(1);
    expect(smoothProgress([], 3)).toBe(0);
    expect(wordAppear(0.45, 9, 10, 0.45)).toBe(1);
    expect(wordAppear(0, 0, 10, 0.45)).toBe(0);
    expect(Math.max(...Array.from({ length: 50 }, (_, i) => easeOutBack(i / 49)))).toBeGreaterThan(1);
    expect(easeOutBack(1)).toBeCloseTo(1);
    expect(easeOutBounce(1)).toBeCloseTo(1);
    expect(easeInOut(0.5)).toBeCloseTo(0.5);
  });

  it("draws the same hand-drawn strokes every frame", () => {
    expect(wobblyPath(0, 0, 100, 0, 2)).toBe(wobblyPath(0, 0, 100, 0, 2));
    expect(wobblyPath(0, 0, 100, 0, 2)).toMatch(/^M0\.0,0\.0 C[-\d.]+,[-\d.]+ [-\d.]+,[-\d.]+ 100\.0,0\.0$/);
    expect(arrowPaths(0, 0, 100, 0, 1, 10).head).toMatch(/L100\.0,0\.0/);
  });

  it("stamps Subscribe when the narration says it, else at 60 % of the last segment", () => {
    const span = { start_sec: 40, end_sec: 50 };
    expect(stampAt(43.9, span, [{ text: "subscribe", startSec: 44, endSec: 44.5 }])).toBeNull();
    expect(stampAt(44.5, span, [{ text: "Subscribe", startSec: 44, endSec: 44.5 }])).toEqual({ scale: expect.closeTo(1, 5), opacity: 1 });
    expect(stampAt(45.9, span, [])).toBeNull();
    expect(stampAt(46.05, span, [])!.scale).toBeGreaterThan(1.2);
  });
});
