import { describe, expect, it } from "vitest";
import { episodeInputPropsSchema } from "./types";
import { crossfadeFrames, motionTransform, shotMotion, visualBackgroundForFrame, vocabCardPosition } from "./visuals";

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
    expect(vocabCardPosition("insert")).toBe("top-right");
  });

  it("selects shots, cuts through a four-frame dissolve, and scales during each line", () => {
    expect(visualBackgroundForFrame(30, 30, lines, visuals).current).toBe("one.png");
    const transition = visualBackgroundForFrame(62, 30, lines, visuals);
    expect(transition).toMatchObject({ current: "duo.png", previous: "one.png", kind: "duo_wide", opacity: 0.5 });
    expect(transition.scale).toBeGreaterThan(1);
    expect(visualBackgroundForFrame(64, 30, lines, visuals)).toMatchObject({ opacity: 1, previous: null });
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
    expect(visualBackgroundForFrame(200, 30, paused, sameThenDuo)).toMatchObject({ current: "duo.png", progress: 1 });
    expect(visualBackgroundForFrame(10, 30, paused, sameThenDuo).current).toBeNull();
  });

  it("moves continuously across lines sharing a shot and crossfades only at a shot change", () => {
    let previousProgress = 0;
    for (let frame = 15; frame < 144; frame += 1) {
      const background = visualBackgroundForFrame(frame, 30, paused, sameThenDuo);
      expect(background.progress).toBeGreaterThanOrEqual(previousProgress);
      previousProgress = background.progress;
    }
    const secondLine = visualBackgroundForFrame(76, 30, paused, sameThenDuo);
    expect(secondLine).toMatchObject({ current: "one.png", previous: null, opacity: 1 });
    const change = visualBackgroundForFrame(146, 30, paused, sameThenDuo);
    expect(change).toMatchObject({ current: "duo.png", previous: "one.png", kind: "duo_wide", opacity: 0.5 });
    expect(change.progress).toBeLessThan(0.2); // 2 of the run's 36 frames
  });

  // Task 24.6: varied, subtle, reproducible motion; softer cuts around inserts.
  it("picks one deterministic motion per shot and uses all four", () => {
    expect(shotMotion("shot-a")).toBe(shotMotion("shot-a"));
    const seen = new Set(Array.from({ length: 40 }, (_, index) => shotMotion(`shot-${index}`)));
    expect(seen).toEqual(new Set(["zoom-in", "zoom-out", "pan-left", "pan-right"]));
  });

  it("never reveals an image edge", () => {
    for (const motion of ["zoom-in", "zoom-out", "pan-left", "pan-right"] as const) {
      for (const progress of [0, 0.5, 1]) {
        const { scale, x, y } = motionTransform(motion, progress);
        expect(scale).toBeGreaterThanOrEqual(1);
        expect(Math.abs(x)).toBeLessThanOrEqual((scale - 1) / 2 + 1e-9);
        expect(y).toBe(0);
      }
    }
    expect(motionTransform("zoom-out", 0).scale).toBeCloseTo(1.05);
    expect(motionTransform("pan-left", 1).x).toBeCloseTo(-0.025);
  });

  it("cuts into and out of inserts over nine frames (owner 2026-10-07: less ghosting)", () => {
    expect(crossfadeFrames("insert", "single")).toBe(9);
    expect(crossfadeFrames("duo_wide", "insert")).toBe(9);
    expect(crossfadeFrames("duo_wide", "single")).toBe(4);
    expect(crossfadeFrames("single", "single")).toBe(4);
    const withInsert = {
      shots: { one: { url: "one.png", kind: "single" as const }, ins: { url: "ins.png", kind: "insert" as const } },
      lineShots: ["one", "ins"],
    };
    const half = visualBackgroundForFrame(60 + 4, 30, lines, withInsert);
    expect(half).toMatchObject({ current: "ins.png", previous: "one.png", opacity: 4 / 9 });
    expect(visualBackgroundForFrame(60 + 9, 30, lines, withInsert)).toMatchObject({ opacity: 1, previous: null });
    const nine = half;
    expect(nine.transform).toMatch(/^translate\(-?\d+\.\d{3}%, -?\d+\.\d{3}%\) scale\(\d\.\d{4}\)$/);
  });
});
