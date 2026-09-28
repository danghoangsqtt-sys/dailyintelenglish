import { createTikTokStyleCaptions } from "@remotion/captions";
import type { EpisodeLine } from "./types";

/**
 * Task 19.3 (D19.3-b): one highlightable word within a line's karaoke band, in
 * milliseconds (matching `@remotion/captions`'s own `TikTokToken` unit).
 */
export interface KaraokeToken {
  text: string;
  fromMs: number;
  toMs: number;
}

/**
 * Builds this line's karaoke tokens by calling `createTikTokStyleCaptions` scoped to just
 * this one line's words, with `combineTokensWithinMilliseconds` set larger than the line's
 * own duration -- guaranteeing exactly one `TikTokPage` regardless of internal word-gap
 * sizes, so the helper's own auto-pagination (designed for a continuous whole-episode word
 * stream) can never split or merge across our existing per-line boundaries.
 *
 * Returns an empty array -- never throws, never returns a partial page -- when `line.words`
 * is missing or empty, so callers can use `tokens.length === 0` as the single fallback check
 * (D19.3-c).
 */
export function buildKaraokeTokens(line: EpisodeLine): KaraokeToken[] {
  if (!line.words || line.words.length === 0) {
    return [];
  }

  const lineDurationMs = (line.endSec - line.startSec) * 1000;
  const captions = line.words.map((word) => ({
    text: word.text,
    startMs: Math.round(word.startSec * 1000),
    endMs: Math.round(word.endSec * 1000),
    timestampMs: null,
    confidence: null,
  }));

  const { pages } = createTikTokStyleCaptions({
    captions,
    combineTokensWithinMilliseconds: lineDurationMs + 1,
  });

  const page = pages[0];
  if (!page) {
    return [];
  }
  return page.tokens.map((token) => ({ text: token.text, fromMs: token.fromMs, toMs: token.toMs }));
}

/**
 * Index of the token active at `currentTimeMs`, or -1 if none (before the first word starts,
 * or after the last word ends -- the surrounding gap still shows the line's other words
 * un-highlighted, matching how the plain fallback shows the whole line with no highlight).
 */
export function activeTokenIndex(tokens: KaraokeToken[], currentTimeMs: number): number {
  return tokens.findIndex((token) => currentTimeMs >= token.fromMs && currentTimeMs < token.toMs);
}
