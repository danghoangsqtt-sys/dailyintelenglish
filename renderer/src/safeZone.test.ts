import { describe, expect, it } from "vitest";
import { insideSafeZone, SAFE, VERTICAL, VERTICAL_BRAND } from "./safeZone";
import { canvasBox } from "./spriteTimeline";

describe("Phase 42 (D121): the vertical video inside the TikTok / Reels / Shorts safe zone", () => {
  it("rejects boxes under the top bar, the bottom caption area, the sides and the button column", () => {
    expect(insideSafeZone({ left: 72, top: 100, width: 300, height: 50 })).toBe(false);   // top bar
    expect(insideSafeZone({ left: 72, top: 1300, width: 300, height: 100 })).toBe(false); // bottom caption area
    expect(insideSafeZone({ left: 20, top: 400, width: 300, height: 100 })).toBe(false);  // left edge
    expect(insideSafeZone({ left: 600, top: 1000, width: 320, height: 100 })).toBe(false); // button column
    expect(insideSafeZone({ left: 600, top: 400, width: 320, height: 100 })).toBe(true);  // above the column: fine
  });

  it("keeps the chips, the vocabulary card, the hook banner and the captions inside", () => {
    for (const box of [VERTICAL.speakerChips, VERTICAL.vocabCard, VERTICAL.hookBanner, VERTICAL.captions]) {
      expect(insideSafeZone(box)).toBe(true);
    }
    expect(VERTICAL.vocabCard.top).toBeGreaterThanOrEqual(VERTICAL.speakerChips.top + VERTICAL.speakerChips.height);
    expect(VERTICAL.captions.top).toBeGreaterThanOrEqual(VERTICAL.vocabCard.top + VERTICAL.vocabCard.height);
  });

  it("keeps both characters' faces inside, under the captions", () => {
    for (const x of VERTICAL.slotX) {
      const face = { left: x - VERTICAL.faceWidth / 2, top: VERTICAL.headTop, width: VERTICAL.faceWidth,
        height: VERTICAL.facesBottom - VERTICAL.headTop };
      expect(insideSafeZone(face)).toBe(true);
    }
    expect(VERTICAL.headTop).toBeGreaterThanOrEqual(VERTICAL.captions.top + VERTICAL.captions.height);
    // the sprite canvases follow the same numbers (head top at the canvas top for a figure whose head starts at 0)
    const box = canvasBox(1, 1080, 1920, [{ topFraction: 0 } as never], "vertical");
    expect(box.top).toBeCloseTo(VERTICAL.headTop);
    expect(box.left + box.width / 2).toBeCloseTo(VERTICAL.slotX[1]);
  });

  it("balances the caption, vocabulary, speaker row and character pair on the frame centre", () => {
    for (const box of [VERTICAL.captions, VERTICAL.vocabCard, VERTICAL.speakerChips]) {
      expect(box.left + box.width / 2).toBe(540);
    }
    expect((VERTICAL.slotX[0] + VERTICAL.slotX[1]) / 2).toBe(540);
    expect(VERTICAL.captions.left + VERTICAL.captions.width).toBeLessThanOrEqual(SAFE.columnX);
  });

  it("also keeps the speech overlays and face envelopes inside the owner's 1080x1920 ads reference", () => {
    const boxes = [VERTICAL.speakerChips, VERTICAL.vocabCard, VERTICAL.hookBanner, VERTICAL.captions,
      ...VERTICAL.slotX.map((x) => ({ left: x - VERTICAL.faceWidth / 2, top: VERTICAL.headTop,
        width: VERTICAL.faceWidth, height: VERTICAL.facesBottom - VERTICAL.headTop }))];
    for (const box of boxes) {
      expect(box.left).toBeGreaterThanOrEqual(48);
      expect(box.left + box.width).toBeLessThanOrEqual(1080 - 192);
      expect(box.top).toBeGreaterThanOrEqual(288);
      expect(box.top + box.height).toBeLessThanOrEqual(1920 - 672);
    }
  });

  it("keeps the intro and outro columns inside: wide only above the button column", () => {
    expect(insideSafeZone({ left: VERTICAL_BRAND.wide.left, top: SAFE.top, width: VERTICAL_BRAND.wide.width,
      height: SAFE.columnFromY - SAFE.top })).toBe(true);
    expect(insideSafeZone({ left: VERTICAL_BRAND.narrow.left, top: SAFE.columnFromY, width: VERTICAL_BRAND.narrow.width,
      height: SAFE.bottom - SAFE.columnFromY })).toBe(true);
    expect(VERTICAL_BRAND.narrow.left + VERTICAL_BRAND.narrow.width / 2).toBe(540); // centred on the screen
  });
});
