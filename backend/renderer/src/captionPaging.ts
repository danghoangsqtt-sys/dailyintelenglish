import type { KaraokeToken } from "./karaoke";

// Small English boundary cues, not a dictionary of the example sentences. Learning
// phrases supply domain-specific units without requiring an NLP model at render time.
const ATTACHED_LEFT = new Set(("a an the this that these those my your his her its our their each every some any " +
  "in on at to of for from with by into onto over under about through between among within without " +
  "and or but nor because although if while when than as I we you he she it they " +
  "am is are was were be been being have has had do does did can could may might must shall should will would not").toLowerCase().split(" "));
const CLAUSE_START = new Set("and or but so yet nor because although if while when unless until however".split(" "));
const PHRASE_START = new Set("in on at to for from with by into onto over under about through between among within without".split(" "));
const ABBREVIATIONS = new Set("mr mrs ms dr prof st vs e.g i.e".split(" "));
const DETERMINERS = new Set("a an the my your his her its our their each every some any".split(" "));
const COMMON_MODIFIERS = new Set(("good bad great nice new old young big small long short first last next best " +
  "easy difficult important different same real total local fresh final main other little right wrong").split(" "));

function normalized(text: string): string {
  return text.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");
}

function sentenceEnd(text: string): boolean {
  const word = text.trim().replace(/["'’”\)\]]+$/u, "");
  if (!/[.!?…]$/u.test(word)) return false;
  if (word.endsWith(".") && (ABBREVIATIONS.has(word.slice(0, -1).toLowerCase()) || /^[A-Z]\.$/.test(word))) return false;
  return true;
}

function boundaryCost(tokens: KaraokeToken[], at: number): number {
  const last = tokens[at - 1].text.trim();
  const before = normalized(last);
  const after = normalized(tokens[at]?.text ?? "");
  if (/[,;:—–]["'’”\)\]]*$/u.test(last)) return 0;
  if (ATTACHED_LEFT.has(before)) return 40;
  if (DETERMINERS.has(after)) {
    // An -ing verb or a nearby infinitive normally still needs its object.
    const context = tokens.slice(Math.max(0, at - 3), at - 1).map(token => normalized(token.text));
    if (/ing$/u.test(before) || context.includes("to")) return 26;
  }
  if (after === "of") return 28; // preserve nominal units even without a learning pack
  if (CLAUSE_START.has(after)) return 1;
  if (PHRASE_START.has(after)) return 2;
  // Avoid separating an adverb/adjective from the word it modifies when a
  // grammatical alternative fits. These are soft preferences, never layout rules.
  if (COMMON_MODIFIERS.has(before) || /(ly|ous|ful|ive|able|ible|ary)$/u.test(before)) return 45;
  return 7;
}

/** Pure, frame-independent partition. Tokens are sliced, never rewritten or retimed. */
export function paginateCaptionTokens(
  tokens: KaraokeToken[], maxWords: number, maxCharacters = Number.POSITIVE_INFINITY,
  protectedPhrases: readonly string[] = [],
): KaraokeToken[][] {
  if (!tokens.length) return [];
  const wordLimit = Number.isFinite(maxWords) ? Math.max(1, Math.floor(maxWords)) : tokens.length;
  const characterLimit = Number.isFinite(maxCharacters) ? Math.max(1, maxCharacters) : Number.POSITIVE_INFINITY;
  const prefix = [0];
  for (const token of tokens) prefix.push(prefix[prefix.length - 1] + token.text.trim().length);
  const length = (from: number, to: number) => prefix[to] - prefix[from] + Math.max(0, to - from - 1);
  const fits = (from: number, to: number) => to - from <= wordLimit && length(from, to) <= characterLimit;
  if (fits(0, tokens.length)) return [tokens];

  const words = tokens.map(token => normalized(token.text));
  const protectedCuts = new Set<number>();
  for (const phrase of new Set(protectedPhrases)) {
    const parts = phrase.trim().split(/\s+/u).map(normalized).filter(Boolean);
    if (parts.length < 2 || parts.length > wordLimit) continue;
    for (let start = 0; start + parts.length <= words.length; start += 1) {
      const end = start + parts.length;
      if (!fits(start, end) || !parts.every((part, i) => part === words[start + i]) ||
        tokens.slice(start, end - 1).some(token => sentenceEnd(token.text))) continue;
      for (let at = start + 1; at < end; at += 1) protectedCuts.add(at);
    }
  }

  function partition(from: number, to: number, strict: boolean): KaraokeToken[][] | null {
    const costs = new Array<number>(to + 1).fill(Number.POSITIVE_INFINITY);
    const next = new Array<number>(to + 1).fill(-1);
    costs[to] = 0;
    for (let start = to - 1; start >= from; start -= 1) {
      for (let end = start + 1; end <= Math.min(to, start + wordLimit); end += 1) {
        // One indivisible oversized token must still be shown; never drop it or
        // allow its overflow to justify putting more words onto the same page.
        if (!fits(start, end) && end > start + 1) break;
        const protectedCut = end < to && protectedCuts.has(end);
        if (strict && protectedCut) continue;
        const count = end - start;
        const fill = Math.min(1, Math.max(count / wordLimit, length(start, end) / characterLimit));
        const tinyPage = count < 3 && to - from > 3 ? (3 - count) * 12 : 0;
        const cut = end === to ? 0 : boundaryCost(tokens, end) + (protectedCut ? 1000 : 0);
        const candidate = 12 + 8 * (1 - fill) ** 2 + tinyPage + cut + costs[end];
        if (candidate < costs[start]) {
          costs[start] = candidate;
          next[start] = end;
        }
      }
    }
    if (next[from] === -1) return null;
    const pages: KaraokeToken[][] = [];
    for (let at = from; at < to; at = next[at]) pages.push(tokens.slice(at, next[at]));
    return pages;
  }

  const pages: KaraokeToken[][] = [];
  let start = 0;
  for (let at = 1; at <= tokens.length; at += 1) {
    if (at < tokens.length && (!sentenceEnd(tokens[at - 1].text) || protectedCuts.has(at))) continue;
    // Overlapping phrases may form an impossible union. Only then allow the
    // fewest protected cuts that fit, rather than overflow or lose words.
    pages.push(...(partition(start, at, true) ?? partition(start, at, false)!));
    start = at;
  }
  return pages;
}

/** Select by absolute word start, including pre-roll, word gaps, reverse seeks and post-roll. */
export function captionPageAtTime(pages: KaraokeToken[][], currentTimeMs: number): KaraokeToken[] {
  if (!pages.length) return [];
  let current = 0;
  for (let at = 1; at < pages.length; at += 1) {
    if (pages[at][0].fromMs > currentTimeMs) break;
    current = at;
  }
  return pages[current];
}
