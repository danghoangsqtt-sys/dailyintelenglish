import { describe, expect, it } from "vitest";
import { soloPayloadSchema } from "./soloTypes";
import { countries, countryName, countryPath, decodeArcs, project, ring, viewFor } from "./voxMap";
import {
  chartHeights, formatValue, highlightRange, highlightSweep, revealedWords, staggered, timelinePositions, voxSegmentAt,
} from "./voxMath";

const base = {
  plan: { project_id: "p", revision: 2, status: "approved", source_fingerprint: "f", aspects: ["16:9"],
    segments: [{ id: "a" }, { id: "b" }] as never[] },
  timeline: [{ id: "a", start_sec: 0, end_sec: 2 }, { id: "b", start_sec: 2, end_sec: 5 }],
  photos: {},
};

describe("the VOX payload", () => {
  it("is accepted without presenter pictures only when it is a VOX payload", () => {
    const vox = { ...base, style: "vox", pictures: {}, geometry: { rules_version: 2, style: "vox", aspects: {} } };
    expect(soloPayloadSchema.safeParse(vox).success).toBe(true);
    expect(soloPayloadSchema.safeParse({ ...vox, style: undefined }).success).toBe(false);
    const solo = { ...base, pictures: Object.fromEntries(Array.from({ length: 21 }, (_, i) => [`p${i}`, "x"])),
      geometry: { rules_version: 2, presenter_metrics: {}, aspects: {} } };
    expect(soloPayloadSchema.safeParse(solo).success).toBe(true);
    expect(soloPayloadSchema.safeParse({ ...solo, pictures: {} }).success).toBe(false);
  });

  it("finds the narrated segment", () => {
    const payload = { ...base } as never;
    expect(voxSegmentAt(payload, 0.5)).toBe(0);
    expect(voxSegmentAt(payload, 3)).toBe(1);
    expect(voxSegmentAt(payload, 9)).toBe(1);
  });
});

describe("kinetic text", () => {
  it("reveals the words and sweeps the highlighter once its phrase is shown", () => {
    const text = "Small daily steps build big habits";
    expect(revealedWords(text, 0)).toBe(0);
    expect(revealedWords(text, 0.225)).toBe(3);
    expect(revealedWords(text, 0.45)).toBe(6);
    const range = highlightRange(text, "big habits");
    expect(range).toEqual([4, 6]);
    expect(highlightRange(text, "Daily STEPS!")).toEqual([1, 3]);
    expect(highlightRange(text, "nothing here")).toBeNull();
    expect(highlightSweep(0.2, range, 6)).toBe(0);
    expect(highlightSweep(0.8, range, 6)).toBe(1);
  });
});

describe("charts and timelines", () => {
  it("scales from zero and grows the items one after another", () => {
    expect(chartHeights([45, 90]).heights).toEqual([0.5, 1]);
    expect(staggered(0, 0, 3)).toBe(0);
    expect(staggered(1, 2, 3)).toBe(1);
    expect(staggered(0.3, 0, 3)).toBeGreaterThan(staggered(0.3, 2, 3));
    timelinePositions(3).forEach((value, i) => expect(value).toBeCloseTo([0.08, 0.5, 0.92][i], 9));
    expect(formatValue(45, "%")).toBe("45%");
    expect(formatValue(1200, "people")).toBe("1,200 people");
  });
});

describe("the world map", () => {
  it("decodes quantized TopoJSON arcs and joins reversed arcs into one ring", () => {
    const topology = { transform: { scale: [1, 1] as [number, number], translate: [10, 20] as [number, number] },
      arcs: [[[0, 0], [1, 0], [0, 1]], [[1, 1], [-1, 0]]] as [number, number][][],
      objects: { countries: { geometries: [] } } };
    const arcs = decodeArcs(topology);
    expect(arcs[0]).toEqual([[10, 20], [11, 20], [11, 21]]);
    expect(ring([0, 1], arcs)).toEqual([[10, 20], [11, 20], [11, 21], [10, 21]]);  // a shared point is not repeated
    expect(ring([~1], arcs)).toEqual([[10, 21], [11, 21]]);  // ~i is arc i reversed
  });

  it("knows the Natural Earth countries and their usual names", () => {
    expect(countries().length).toBeGreaterThan(150);
    expect(countryName("Japan")).toBe("Japan");
    expect(countryName("USA")).toBe("United States of America");
    expect(countryName("Viet Nam")).toBe("Vietnam");
    expect(countryName("Atlantis")).toBeNull();
  });

  it("frames the places with the board's ratio and draws the countries inside the view", () => {
    const view = viewFor([{ lat: 21, lon: 105.8 }, { lat: 35.7, lon: 139.7 }], 16 / 9);
    expect(view.west).toBeLessThan(105.8);
    expect(view.east).toBeGreaterThan(139.7);
    expect((view.east - view.west) / (view.north - view.south)).toBeCloseTo(16 / 9, 5);
    const [x, y] = project([105.8, 21], view, 1600, 900);
    expect(x).toBeGreaterThan(0);
    expect(y).toBeLessThan(900);
    const japan = countries().find((country) => country.name === "Japan")!;
    expect(countryPath(japan, view, 1600, 900)).toMatch(/^M[\d.,L-]+Z/);
  });
});
