import { describe, expect, it } from "vitest";
import { STILL_ZOOM_GAIN, podcastLayer, stillScale } from "./podcastLayout";
import { episodeInputPropsSchema } from "./types";

const base = {
  episodeId: "p", lines: [], speakers: [], audioPath: "a.mp3", fps: 30, width: 1280, height: 720,
};

describe("Phase 30 podcast visual modes", () => {
  it("keeps the drawn-story behaviour by default and names a layer for every podcast mode", () => {
    expect(episodeInputPropsSchema.parse(base).visualMode).toBe("illustrated");
    expect(podcastLayer("illustrated")).toBe("none");
    expect(podcastLayer("podcast_black")).toBe("black");
    expect(podcastLayer("podcast_still")).toBe("still");
  });

  it("accepts the new props and rejects an unknown mode", () => {
    const parsed = episodeInputPropsSchema.parse({
      ...base, visualMode: "podcast_still", stillUrl: "remotion-render/visuals/p/still.png",
    });
    expect(parsed.stillUrl).toBe("remotion-render/visuals/p/still.png");
    expect(() => episodeInputPropsSchema.parse({ ...base, visualMode: "slideshow" })).toThrow();
  });

  it("zooms the still very slowly and never below 1", () => {
    expect(stillScale(0)).toBe(1);
    expect(stillScale(1)).toBeCloseTo(1 + STILL_ZOOM_GAIN);
    expect(stillScale(-3)).toBe(1);
    expect(stillScale(9)).toBeCloseTo(1 + STILL_ZOOM_GAIN);
    expect(STILL_ZOOM_GAIN).toBeLessThanOrEqual(0.06);
  });
});
