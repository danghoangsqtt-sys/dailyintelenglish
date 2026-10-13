import { describe, expect, it } from "vitest";
import { activeTokenIndex, buildKaraokeTokens } from "./karaoke";
import type { EpisodeLine } from "./types";

const LINE_WITH_WORDS: EpisodeLine = {
  startSec: 10,
  endSec: 12,
  speaker: "Alex",
  speakerId: "alex-id",
  text: "Hi there friend",
  words: [
    { text: "Hi", startSec: 10.0, endSec: 10.4 },
    { text: "there", startSec: 10.5, endSec: 10.9 },
    { text: "friend", startSec: 11.0, endSec: 11.6 },
  ],
};

const LINE_WITHOUT_WORDS: EpisodeLine = {
  startSec: 20,
  endSec: 21,
  speaker: "Sam",
  speakerId: "sam-id",
  text: "No captured words here",
  words: [],
};

describe("buildKaraokeTokens", () => {
  it("returns one token per captured word, in milliseconds", () => {
    const tokens = buildKaraokeTokens(LINE_WITH_WORDS);

    expect(tokens).toEqual([
      { text: "Hi", fromMs: 10000, toMs: 10400 },
      { text: "there", fromMs: 10500, toMs: 10900 },
      { text: "friend", fromMs: 11000, toMs: 11600 },
    ]);
  });

  it("returns an empty array for a line with no captured words (D19.3-c fallback)", () => {
    expect(buildKaraokeTokens(LINE_WITHOUT_WORDS)).toEqual([]);
  });

  it("does not split a line's words into multiple pages even with an internal gap", () => {
    // The gap between "there" (ends 10900ms) and "friend" (starts 11000ms) is only 100ms,
    // but the real risk this guards against is createTikTokStyleCaptions's own
    // auto-pagination splitting on ANY gap once combineTokensWithinMilliseconds is too small
    // -- scoping the call per-line with a large threshold (D19.3-b) must always yield one page.
    const tokens = buildKaraokeTokens(LINE_WITH_WORDS);
    expect(tokens).toHaveLength(3);
  });
});

describe("activeTokenIndex", () => {
  const tokens = buildKaraokeTokens(LINE_WITH_WORDS);

  it("finds the token active at a given time", () => {
    expect(activeTokenIndex(tokens, 10200)).toBe(0); // inside "Hi"
    expect(activeTokenIndex(tokens, 10600)).toBe(1); // inside "there"
    expect(activeTokenIndex(tokens, 11300)).toBe(2); // inside "friend"
  });

  it("returns -1 in a gap between words", () => {
    expect(activeTokenIndex(tokens, 10450)).toBe(-1); // between "Hi" and "there"
  });

  it("returns -1 before the first word and after the last", () => {
    expect(activeTokenIndex(tokens, 0)).toBe(-1);
    expect(activeTokenIndex(tokens, 20000)).toBe(-1);
  });
});
