import { describe, expect, it } from "vitest";
import { captionPage, captionPageAtTime, paginateCaptionTokens, withScriptPunctuation, type KaraokeToken } from "./karaoke";
import { VERTICAL } from "./safeZone";
import { captionLayout } from "./motionLayout";

const tokens = (words: string[]): KaraokeToken[] => words.map((text, i) => ({ text, fromMs: i * 300, toMs: i * 300 + 280 }));

const alex = "Welcome to Daily Beyond English! Today, we are attempting a notoriously difficult recipe to truly test our culinary skills in the kitchen under pressure. We need to focus on precision and timing to get everything perfect before our dinner guests arrive later this evening.";
const lina = "I am honestly so excited for this, Alex. This will be a real challenge for us, but if we stay organized, I am confident that it ends up being a total piece of cake for such a talented team like us.";

function pagesFor(all: KaraokeToken[], maxWords: number, maxCharacters: number): KaraokeToken[][] {
  const seen = new Map<number, KaraokeToken[]>();
  for (const token of all) {
    const page = captionPage(all, token.fromMs, maxWords, maxCharacters);
    seen.set(page[0].fromMs, page);
  }
  return [...seen.values()];
}

describe("BUG-041: Episode 3 subtitle continuity", () => {
  for (const layout of ["horizontal", "vertical"] as const) {
    const { maxWords, maxCharacters } = captionLayout(layout);
    it(`${layout}: keeps 'in the kitchen' together without a dangling article/preposition`, () => {
      const all = tokens(alex.split(" "));
      const pages = pagesFor(all, maxWords, maxCharacters);
      const text = pages.map(page => page.map(t => t.text).join(" "));
      expect(text.some(page => page.includes("in the kitchen"))).toBe(true);
      expect(text.some(page => page.includes("notoriously difficult recipe"))).toBe(true);
      expect(text.every(page => !/\b(in|the|a|an|our|to)$/i.test(page))).toBe(true);
      expect(pages.flat()).toEqual(all);
    });
    it(`${layout}: keeps 'piece of cake' together and avoids joining a sentence tail to the next`, () => {
      const all = tokens(lina.split(" "));
      const pages = pagesFor(all, maxWords, maxCharacters);
      const text = pages.map(page => page.map(t => t.text).join(" "));
      expect(text.some(page => page.includes("piece of cake"))).toBe(true);
      expect(text.some(page => page.includes("Alex. This"))).toBe(false);
      expect(pages.flat()).toEqual(all);
    });
  }
});

describe("BUG-041: phrase and timing safeguards", () => {
  it.each(["horizontal", "vertical"] as const)("%s: preserves the full learning idiom and original token objects", layout => {
    const all = tokens(lina.split(" "));
    const { maxWords, maxCharacters } = captionLayout(layout);
    const pages = paginateCaptionTokens(all, maxWords, maxCharacters, ["A TOTAL PIECE OF CAKE", "absent phrase"]);
    expect(pages.some(page => page.map(t => t.text).join(" ").includes("a total piece of cake"))).toBe(true);
    expect(pages.flat()).toHaveLength(all.length);
    pages.flat().forEach((token, i) => expect(token).toBe(all[i]));
    for (const page of pages) {
      expect(page.length).toBeLessThanOrEqual(maxWords);
      expect(page.map(t => t.text.trim()).join(" ").length).toBeLessThanOrEqual(maxCharacters);
    }
  });

  it("protects other learning phrases and repeated occurrences, with punctuation", () => {
    const all = tokens("Please look forward to the trip, and look forward to our next adventure together.".split(" "));
    const pages = paginateCaptionTokens(all, 6, 48, ["look forward to"]);
    expect(pages.filter(page => page.map(t => t.text).join(" ").includes("look forward to"))).toHaveLength(2);
    expect(pages.flat()).toEqual(all);
  });

  it("balances an unpunctuated sentence instead of leaving a one-word final page", () => {
    const all = tokens("bright stars light quiet roads near home tonight".split(" "));
    const pages = paginateCaptionTokens(all, 7);
    expect(pages).toHaveLength(2);
    expect(pages.every(page => page.length >= 3)).toBe(true);
    expect(pages.flat()).toEqual(all);
  });

  it("splits overlong and conflicting overlapping phrases without overflowing or dropping tokens", () => {
    const all = tokens("one two three four five six seven eight nine ten".split(" "));
    for (const phrases of [["one two three four five six"], ["one two three", "three four five"]]) {
      const pages = paginateCaptionTokens(all, 3, 18, phrases);
      expect(pages.every(page => page.length <= 3 && page.map(t => t.text).join(" ").length <= 18)).toBe(true);
      expect(pages.flat()).toEqual(all);
    }
  });

  it("shows an indivisible oversized word on its own, never loses it", () => {
    const all = tokens(["supercalifragilisticexpialidocious", "is", "long."]);
    const pages = paginateCaptionTokens(all, 4, 12);
    expect(pages[0]).toEqual([all[0]]);
    expect(pages.flat()).toEqual(all);
  });

  it("handles empty tokens and keeps short-line identity with absent learning data", () => {
    expect(paginateCaptionTokens([], 10, 54)).toEqual([]);
    expect(captionPage([], 0, 10, 54)).toEqual([]);
    const all = tokens(["Good", "morning!"]);
    expect(paginateCaptionTokens(all, 10, 54)[0]).toBe(all);
    expect(captionPage(all, -100, 10, 54)).toBe(all);
  });

  it("selects the same page at exact boundaries, gaps, pre/post roll and reverse seeks", () => {
    const all = tokens(lina.split(" "));
    const pages = paginateCaptionTokens(all, 10, 54, ["a total piece of cake"]);
    expect(captionPageAtTime(pages, -100)).toBe(pages[0]);
    expect(captionPageAtTime(pages, 999999)).toBe(pages.at(-1));
    for (let index = pages.length - 1; index > 0; index--) {
      const start = pages[index][0].fromMs;
      expect(captionPageAtTime(pages, start)).toBe(pages[index]);
      expect(captionPageAtTime(pages, start - 1)).toBe(pages[index - 1]);
      expect(captionPageAtTime(pages, pages[index - 1].at(-1)!.toMs)).toBe(pages[index - 1]);
    }
  });

  it("recognizes Unicode sentence punctuation, quoted endings and abbreviations", () => {
    const all = tokens('Dr. Smith is ready. “Everyone can start now…” Then we can cook together!'.split(" "));
    const pages = paginateCaptionTokens(all, 5, 60);
    expect(pages[0].map(t => t.text).join(" ")).toBe("Dr. Smith is ready.");
    expect(pages[1].map(t => t.text).join(" ")).toBe('“Everyone can start now…”');
    expect(pages.flat()).toEqual(all);
  });

  it("does not match a learning phrase across a real sentence ending", () => {
    const all = tokens("We have enough time. To cook fresh food together.".split(" "));
    const pages = paginateCaptionTokens(all, 6, 54, ["time to cook"]);
    expect(pages[0].map(t => t.text).join(" ")).toBe("We have enough time.");
    expect(pages.flat()).toEqual(all);
  });

  it("preserves unmatched Edge number words and their times while paging", () => {
    const spoken = tokens("It costs five dollars today and ten dollars next week".split(" "));
    const fixed = withScriptPunctuation(spoken, "It costs $5 today and $10 next week.");
    const pages = paginateCaptionTokens(fixed, 5, 30, ["five dollars"]);
    expect(pages.flat()).toEqual(fixed);
    expect(pages.flat().map(t => [t.fromMs, t.toMs])).toEqual(spoken.map(t => [t.fromMs, t.toMs]));
    expect(pages.some(page => page.map(t => t.text).join(" ").includes("five dollars"))).toBe(true);
  });
});

describe("walkthrough 2026-10-14: captions keep the script's punctuation and page in the vertical band", () => {
  it("puts the script's punctuation back on Edge's bare words", () => {
    const spoken = tokens(["It", "is", "crowded", "already", "Hoang", "The", "sun", "is", "warm"]);
    const fixed = withScriptPunctuation(spoken, "It is crowded already, Hoang! The sun is warm.");
    expect(fixed.map((t) => t.text).join(" ")).toBe("It is crowded already, Hoang! The sun is warm.");
    expect(fixed.map((t) => t.fromMs)).toEqual(spoken.map((t) => t.fromMs));
  });

  it("leaves a word it cannot match as spoken", () => {
    const fixed = withScriptPunctuation(tokens(["It", "costs", "five", "dollars"]), "It costs $5.");
    expect(fixed.map((t) => t.text)).toEqual(["It", "costs", "five", "dollars"]);
  });

  it("shows a long line a page at a time, breaking after a sentence, never more than the band holds", () => {
    const words = "I completely agree. If we want to secure the absolute best quality produce, we have to examine every single crate with a keen eye before we commit to a purchase.".split(" ");
    const all = tokens(words);
    const seen = new Set<string>();
    for (let ms = 0; ms < all.length * 300; ms += 150) {
      const page = captionPage(all, ms, VERTICAL.captionWords);
      expect(page.length).toBeLessThanOrEqual(VERTICAL.captionWords);
      seen.add(page.map((t) => t.text).join(" "));
    }
    const pages = [...seen];
    expect(pages[0]).toBe("I completely agree.");
    expect(pages.join(" ")).toBe(words.join(" ")); // every word shows, in order, once
  });

  it("keeps a short line whole", () => {
    const all = tokens(["Nice", "to", "meet", "you."]);
    expect(captionPage(all, 0, VERTICAL.captionWords)).toBe(all);
  });
});
