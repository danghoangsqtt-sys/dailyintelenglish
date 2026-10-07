import { describe, expect, it } from "vitest";
import {
  ACTIVE_CARD_SCALE,
  CARD_HEIGHT,
  CARD_TOP,
  CARD_WIDTH,
  INACTIVE_CARD_OPACITY,
  STILL_ZOOM_GAIN,
  cardLayout,
  cardState,
  podcastLayer,
  speakerInitial,
  stillScale,
} from "./podcastLayout";
import { episodeInputPropsSchema } from "./types";

const FRAME = { width: 1280, height: 720 };
const base = {
  episodeId: "p", lines: [], speakers: [], audioPath: "a.mp3", fps: 30, width: 1280, height: 720,
};

describe("Phase 30 podcast visual modes", () => {
  it("keeps the drawn-story behaviour by default and names a layer for every podcast mode", () => {
    expect(episodeInputPropsSchema.parse(base).visualMode).toBe("illustrated");
    expect(podcastLayer("illustrated")).toBe("none");
    expect(podcastLayer("podcast_black")).toBe("black");
    expect(podcastLayer("podcast_characters")).toBe("cards");
    expect(podcastLayer("podcast_still")).toBe("still");
  });

  it("accepts the new props and rejects an unknown mode", () => {
    const parsed = episodeInputPropsSchema.parse({
      ...base, visualMode: "podcast_still", stillUrl: "remotion-render/visuals/p/still.png",
      speakers: [{ id: "a", name: "Lan", gender: "female", portraitUrl: "remotion-render/avatars/a_portrait.png" }],
    });
    expect(parsed.stillUrl).toBe("remotion-render/visuals/p/still.png");
    expect(parsed.speakers[0].portraitUrl).toBe("remotion-render/avatars/a_portrait.png");
    expect(() => episodeInputPropsSchema.parse({ ...base, visualMode: "slideshow" })).toThrow();
  });

  it("lays two or three portrait cards out centred, inside the frame and below the vocabulary card", () => {
    for (const count of [1, 2, 3]) {
      const cards = cardLayout(count, FRAME.width);
      expect(cards).toHaveLength(count);
      cards.forEach((card) => {
        expect(card.width).toBe(CARD_WIDTH);
        expect(card.height).toBe(CARD_HEIGHT);
        expect(card.x).toBeGreaterThanOrEqual(0);
        expect(card.x + card.width).toBeLessThanOrEqual(FRAME.width);
        expect(card.y).toBe(CARD_TOP);
        expect(card.y + card.height).toBeLessThan(FRAME.height * 0.8); // the captions keep the bottom
      });
      const left = cards[0].x;
      const right = FRAME.width - (cards[count - 1].x + CARD_WIDTH);
      expect(Math.abs(left - right)).toBeLessThan(1); // centred
    }
    expect(CARD_TOP).toBeGreaterThanOrEqual(190); // under the vocabulary card (top 20..170)
  });

  it("lights the active card and dims the others", () => {
    expect(cardState(true)).toEqual({ scale: ACTIVE_CARD_SCALE, opacity: 1, saturate: 1 });
    const dim = cardState(false);
    expect(dim.scale).toBe(1);
    expect(dim.opacity).toBe(INACTIVE_CARD_OPACITY);
    expect(dim.saturate).toBeLessThan(1);
    expect(ACTIVE_CARD_SCALE).toBeGreaterThan(1);
    expect(INACTIVE_CARD_OPACITY).toBeGreaterThan(0.4);
  });

  it("zooms the still very slowly and never below 1", () => {
    expect(stillScale(0)).toBe(1);
    expect(stillScale(1)).toBeCloseTo(1 + STILL_ZOOM_GAIN);
    expect(stillScale(-3)).toBe(1);
    expect(stillScale(9)).toBeCloseTo(1 + STILL_ZOOM_GAIN);
    expect(STILL_ZOOM_GAIN).toBeLessThanOrEqual(0.06);
  });

  it("falls back to a name initial for a speaker without a picture", () => {
    expect(speakerInitial("lan")).toBe("L");
    expect(speakerInitial("  minh ")).toBe("M");
    expect(speakerInitial("")).toBe("?");
  });
});
