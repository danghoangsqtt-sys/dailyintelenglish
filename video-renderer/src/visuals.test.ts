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
    expect(visualBackgroundForFrame(75, 30, lines, visuals).previous).toBeNull();
    expect(visualBackgroundForFrame(30, 30, lines, { shots: {}, lineShots: [] }).current).toBeNull();
  });

  // Review r1 F1: real audio has 300/500 ms pauses between lines (Task 1.6b).
  const paused = [
    { startSec: 0.5, endSec: 2, speaker: "Nova", speakerId: "a", text: "One.", words: [] },
    { startSec: 2.5, endSec: 4.5, speaker: "Mira", speakerId: "b", text: "Two.", words: [] },
    { startSec: 4.8, endSec: 6, speaker: "Nova", speakerId: "a", text: "Three.", words: [] },
  ];
  const sameThenDuo = { ...visuals, lineShots: ["one", "one", "duo"] };

  it("holds the shot through inter-line pauses and after the last line, never midnight", () => {
    for (let frame = 15; frame < 400; frame += 1) {
      expect(visualBackgroundForFrame(frame, 30, paused, sameThenDuo).current).not.toBeNull();
    }
    expect(visualBackgroundForFrame(68, 30, paused, sameThenDuo).current).toBe("one.png");
    expect(visualBackgroundForFrame(200, 30, paused, sameThenDuo)).toMatchObject({ current: "duo.png", scale: 1.04 });
    expect(visualBackgroundForFrame(10, 30, paused, sameThenDuo).current).toBeNull();
  });

  it("zooms continuously across lines sharing a shot and crossfades only at a shot change", () => {
    let previousScale = 0;
    for (let frame = 15; frame < 144; frame += 1) {
      const background = visualBackgroundForFrame(frame, 30, paused, sameThenDuo);
      expect(background.scale).toBeGreaterThanOrEqual(previousScale);
      previousScale = background.scale;
    }
    const secondLine = visualBackgroundForFrame(76, 30, paused, sameThenDuo);
    expect(secondLine).toMatchObject({ current: "one.png", previous: null, opacity: 1 });
    const change = visualBackgroundForFrame(149, 30, paused, sameThenDuo);
    expect(change).toMatchObject({ current: "duo.png", previous: "one.png", kind: "duo_wide", opacity: 0.5 });
    expect(change.scale).toBeLessThan(1.01);
  });
});
