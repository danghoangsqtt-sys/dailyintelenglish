import { describe, expect, it } from "vitest";
import { activeSpeakerId } from "./speakers";
import type { EpisodeLine } from "./types";

const line = (speakerId: string, startSec: number, endSec: number): EpisodeLine => ({
  startSec,
  endSec,
  speaker: speakerId,
  speakerId,
  text: "line text",
  words: [],
});

const LINES: EpisodeLine[] = [
  line("alex", 0, 3.6),
  line("maya", 4.1, 7.0), // 0.5s gap before this line (different-speaker padding)
  line("alex", 7.3, 9.0), // 0.3s gap before this line (same-speaker padding)
];

describe("activeSpeakerId", () => {
  it("returns the speaker id inside a line", () => {
    expect(activeSpeakerId(1.0, LINES)).toBe("alex");
    expect(activeSpeakerId(5.0, LINES)).toBe("maya");
    expect(activeSpeakerId(8.0, LINES)).toBe("alex");
  });

  it("is null in a gap between lines", () => {
    expect(activeSpeakerId(3.8, LINES)).toBeNull(); // between line 0 and line 1
    expect(activeSpeakerId(7.1, LINES)).toBeNull(); // between line 1 and line 2
  });

  it("is null before line 0 and after the last line", () => {
    expect(activeSpeakerId(-1, LINES)).toBeNull();
    expect(activeSpeakerId(100, LINES)).toBeNull();
  });

  it("resolves the exact boundary as startSec-inclusive, endSec-exclusive", () => {
    expect(activeSpeakerId(0, LINES)).toBe("alex"); // exactly startSec of line 0
    expect(activeSpeakerId(3.6, LINES)).toBeNull(); // exactly endSec of line 0 -- excluded
    expect(activeSpeakerId(4.1, LINES)).toBe("maya"); // exactly startSec of line 1
  });
});
