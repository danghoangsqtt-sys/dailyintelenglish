import { describe, expect, it } from "vitest";
import { captionPage, withScriptPunctuation, type KaraokeToken } from "./karaoke";
import { VERTICAL } from "./safeZone";

const tokens = (words: string[]): KaraokeToken[] => words.map((text, i) => ({ text, fromMs: i * 300, toMs: i * 300 + 280 }));

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
