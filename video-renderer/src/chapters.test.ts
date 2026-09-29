import { describe, expect, it } from "vitest";
import { computeProgressForFrame } from "./chapters";
import type { Chapter } from "./types";

const FPS = 30;
const AUDIO_DURATION_SEC = 100;
const CHAPTERS: Chapter[] = [
  { title: "Introduction", startSec: 0 },
  { title: "Morning routine", startSec: 20 },
  { title: "Exercise", startSec: 60 },
];

describe("computeProgressForFrame", () => {
  it("returns 0 overallPct at frame 0", () => {
    const result = computeProgressForFrame(0, FPS, AUDIO_DURATION_SEC, CHAPTERS);
    expect(result.overallPct).toBe(0);
  });

  it("returns the fraction of the audio window elapsed", () => {
    const result = computeProgressForFrame(50 * FPS, FPS, AUDIO_DURATION_SEC, CHAPTERS);
    expect(result.overallPct).toBeCloseTo(0.5, 5);
  });

  it("clamps overallPct to 1 when the frame exceeds the audio duration", () => {
    const result = computeProgressForFrame(500 * FPS, FPS, AUDIO_DURATION_SEC, CHAPTERS);
    expect(result.overallPct).toBe(1);
  });

  it("does not divide by zero when audioDurationSec is 0", () => {
    const result = computeProgressForFrame(10, FPS, 0, CHAPTERS);
    expect(result.overallPct).toBe(0);
    expect(Number.isNaN(result.overallPct)).toBe(false);
  });

  it("picks the last chapter whose startSec has been reached", () => {
    expect(computeProgressForFrame(10 * FPS, FPS, AUDIO_DURATION_SEC, CHAPTERS).currentChapter?.title).toBe(
      "Introduction"
    );
    expect(computeProgressForFrame(25 * FPS, FPS, AUDIO_DURATION_SEC, CHAPTERS).currentChapter?.title).toBe(
      "Morning routine"
    );
    expect(computeProgressForFrame(90 * FPS, FPS, AUDIO_DURATION_SEC, CHAPTERS).currentChapter?.title).toBe(
      "Exercise"
    );
  });

  it("returns null currentChapter when there are no chapters", () => {
    const result = computeProgressForFrame(10 * FPS, FPS, AUDIO_DURATION_SEC, []);
    expect(result.currentChapter).toBeNull();
    expect(result.chapters).toEqual([]);
  });

  it("computes each chapter's tick position as a pct of audioDurationSec", () => {
    const result = computeProgressForFrame(0, FPS, AUDIO_DURATION_SEC, CHAPTERS);
    expect(result.chapters.map((chapter) => chapter.pct)).toEqual([0, 0.2, 0.6]);
  });
});
