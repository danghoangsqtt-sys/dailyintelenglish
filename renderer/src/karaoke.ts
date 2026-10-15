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
 * Phase 42 (D121, Gate B-25 review): a long line does not fit the vertical caption band (it ran over the characters'
 * faces). Split the tokens into pages of at most `maxWords`, breaking after a sentence end -- or a comma -- once a page is
 * at least half full, and return the page being spoken at `currentTimeMs` (between words: the page of the last word
 * said; before the first word: the first page).
 */
export function captionPage(tokens: KaraokeToken[], currentTimeMs: number, maxWords: number,
  maxCharacters = Number.POSITIVE_INFINITY): KaraokeToken[] {
  if (tokens.length <= maxWords && tokens.map((token) => token.text.trim()).join(" ").length <= maxCharacters) return tokens;
  const pages: KaraokeToken[][] = [];
  let page: KaraokeToken[] = [];
  let characters = 0;
  tokens.forEach((token, index) => {
    const length = token.text.trim().length;
    if (page.length && characters + 1 + length > maxCharacters) {
      pages.push(page);
      page = [];
      characters = 0;
    }
    characters += length + (page.length ? 1 : 0);
    page.push(token);
    const remaining = tokens.length - index - 1;
    const sentenceEnd = /[.!?â€¦]["')\]]?$/.test(token.text.trim());
    const pause = sentenceEnd || /[,;:â€”]$/.test(token.text.trim());
    const halfFull = page.length >= Math.ceil(maxWords / 2);
    if (page.length >= maxWords || (halfFull && pause && remaining >= 3) || (sentenceEnd && page.length >= 3 && remaining >= 3)) {
      pages.push(page);
      page = [];
      characters = 0;
    }
  });
  if (page.length) pages.push(page);
  let current = 0;
  pages.forEach((candidate, index) => {
    if (candidate[0].fromMs <= currentTimeMs) current = index;
  });
  return pages[current];
}
