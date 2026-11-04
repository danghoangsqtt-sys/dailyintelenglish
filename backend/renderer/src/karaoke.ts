import { createTikTokStyleCaptions } from "@remotion/captions";
import type { EpisodeLine } from "./types";
import { captionPageAtTime, paginateCaptionTokens } from "./captionPaging";
export { captionPageAtTime, paginateCaptionTokens } from "./captionPaging";

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

/** Letters and digits only, lower-cased: how a spoken word and a script word are compared. */
function bare(word: string): string {
  return word.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");
}

/**
 * Walkthrough 2026-10-14: Edge TTS reports each spoken word without its punctuation ("already" "Hoang" "The"), so the
 * captions read "crowded already Hoang The morning". Give each token back the script's spelling ("already," "Hoang!")
 * by walking the line's words in order; a token that matches no nearby script word keeps its own text.
 */
export function withScriptPunctuation(tokens: KaraokeToken[], text: string): KaraokeToken[] {
  const words = text.split(/\s+/).filter(Boolean);
  let next = 0;
  return tokens.map((token) => {
    const spoken = bare(token.text);
    if (!spoken) return token;
    for (let look = next; look < Math.min(words.length, next + 4); look += 1) {
      if (bare(words[look]) === spoken) {
        next = look + 1;
        const lead = token.text.match(/^\s*/)?.[0] ?? "";
        return { ...token, text: lead + words[look] };
      }
    }
    return token;
  });
}

/**
 * Compatibility helper for callers needing one page. The composition memoizes
 * paginateCaptionTokens and selects with captionPageAtTime on each frame instead.
 */
export function captionPage(tokens: KaraokeToken[], currentTimeMs: number, maxWords: number,
  maxCharacters = Number.POSITIVE_INFINITY, protectedPhrases: readonly string[] = []): KaraokeToken[] {
  return captionPageAtTime(paginateCaptionTokens(tokens, maxWords, maxCharacters, protectedPhrases), currentTimeMs);
}
