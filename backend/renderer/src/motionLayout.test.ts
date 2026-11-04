import { describe, expect, it } from "vitest";
import { accentLayout, captionLayout } from "./motionLayout";

describe("shared motion in portrait and YouTube landscape", () => {
  it("uses readable page density for each frame shape", () => {
    expect(captionLayout("horizontal")).toEqual({ fontSize: 32, speakerSize: 18, maxWords: 16, maxCharacters: 96 });
    expect(captionLayout("vertical").maxCharacters).toBe(54);
    expect(captionLayout("vertical").fontSize).toBe(44);
  });
  it("anchors landscape spotlights to both character slots at either supported canvas size", () => {
    for (const [width, height] of [[1280, 720], [1920, 1080]]) {
      const geometry = accentLayout("horizontal", width, height);
      expect(geometry.centers).toEqual([width * 0.27, width * 0.73]);
      expect(geometry.top + geometry.height).toBeLessThanOrEqual(height);
    }
    expect(accentLayout("vertical", 1080, 1920).centers).toEqual([355, 725]);
  });
});
