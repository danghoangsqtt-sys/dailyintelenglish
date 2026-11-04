import { describe, expect, it } from "vitest";
import fixtures from "../../tests/fixtures/explainer_geometry.json";
import { envelope, insideExplainerSafeZone, intersects, placementAt, presenterBoxes, type Aspect, type Placement, type SegmentLayout } from "./explainerLayout";

describe("Solo geometry shared rules", () => {
  for (const test of fixtures.safeCases) it(`safe ${test.aspect} ${JSON.stringify(test.rect)}`, () => {
    expect(insideExplainerSafeZone(test.rect, test.aspect as Aspect)).toBe(test.valid);
  });
  it("keeps uniform pixel scaling and measured alpha height", () => {
    for (const item of fixtures.placements) {
      const { bounds, canvas } = presenterBoxes(item.placement as Placement, fixtures.metrics, item.aspect as Aspect);
      expect(bounds.height).toBeCloseTo(item.placement.height);
      const width = item.aspect === "16:9" ? 1280 : 1080, height = item.aspect === "16:9" ? 720 : 1920;
      expect(canvas.width * width / (canvas.height * height)).toBeCloseTo(1280 / 1536);
    }
  });
  it("checks the swept path even when two endpoints are clear", () => {
    const a = { x: 0.1, y: 0.3, width: 0.08, height: 0.2 }, b = { ...a, x: 0.8 };
    const text = { x: 0.4, y: 0.3, width: 0.2, height: 0.2 };
    expect(intersects(a, text)).toBe(false); expect(intersects(b, text)).toBe(false);
    expect(intersects(envelope(a, b), text)).toBe(true);
  });
  it("seeks deterministically without overshoot or disappearing", () => {
    const p: Placement = { anchor: "left", x: 0.15, y: 0.69, height: 0.22 };
    const layout: SegmentLayout = { presenter: { ...p, x: 0.85 }, illustration: { x: 0.3, y: 0.15, width: 0.6, height: 0.4 },
      transition: "ease", transition_seconds: 0.4, rules_version: 1 };
    for (const time of [0, 0.1, 0.35, 0.05, 1, -1]) {
      const point = placementAt(layout, p, time);
      expect(point.x).toBeGreaterThanOrEqual(0.15); expect(point.x).toBeLessThanOrEqual(0.85);
      expect(placementAt(layout, p, time)).toEqual(point);
    }
    expect(placementAt({ ...layout, transition: "cut" }, p, 0)).toEqual(layout.presenter);
  });
});
