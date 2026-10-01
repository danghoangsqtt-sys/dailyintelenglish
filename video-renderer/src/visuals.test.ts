import { describe, expect, it } from "vitest";
import { episodeInputPropsSchema } from "./types";
import { visualBackgroundForFrame, vocabCardPosition } from "./visuals";

const lines = [
  { startSec: 0, endSec: 2, speaker: "Nova", speakerId: "a", text: "Hello.", words: [] },
  { startSec: 2, endSec: 4, speaker: "Mira", speakerId: "b", text: "Hello!", words: [] },
];
const visuals = {
  shots: {
    one: { url: "one.png", kind: "single" as const },
    duo: { url: "duo.png", kind: "duo_wide" as const },
  },
  lineShots: ["one", "duo"],
};

describe("AI visual props", () => {
  it("defaults to no shots for older input props", () => {
    const result = episodeInputPropsSchema.parse({
      episodeId: "preview", lines, speakers: [], audioPath: "audio.mp3", fps: 30, width: 1280, height: 720,
    });
    expect(result.visuals).toEqual({ shots: {}, lineShots: [] });
  });

  it("places vocabulary above duo people and retains top-right for singles or midnight", () => {
    expect(vocabCardPosition("duo_close")).toBe("top-center");
    expect(vocabCardPosition("duo_wide")).toBe("top-center");
    expect(vocabCardPosition("single")).toBe("top-right");
    expect(vocabCardPosition(null)).toBe("top-right");
  });

  it("selects shots, crossfades over ten frames, and scales during each line", () => {
    expect(visualBackgroundForFrame(30, 30, lines, visuals).current).toBe("one.png");
    const transition = visualBackgroundForFrame(65, 30, lines, visuals);
    expect(transition).toMatchObject({ current: "duo.png", previous: "one.png", kind: "duo_wide", opacity: 0.5 });
    expect(transition.scale).toBeGreaterThan(1);
    expect(visualBackgroundForFrame(75, 30, lines, visuals).opacity).toBe(1);
    expect(visualBackgroundForFrame(125, 30, lines, visuals).current).toBeNull();
    expect(visualBackgroundForFrame(30, 30, lines, { shots: {}, lineShots: [] }).current).toBeNull();
  });
});
