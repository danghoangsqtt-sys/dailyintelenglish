import { describe, expect, it } from "vitest";
import { BRAND_NAME, BRAND_PALETTE, LOGO_PATH, mix, mixColor } from "./Brand";

function luminance(hex: string): number {
  const channel = (i: number) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5);
}
function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

describe("Phase 25 brand morph helpers", () => {
  it("mixes numbers linearly", () => {
    expect(mix(150, 76, 0)).toBe(150);
    expect(mix(150, 76, 1)).toBe(76);
    expect(mix(0, 10, 0.25)).toBe(2.5);
  });

  it("mixes hex colours channel by channel", () => {
    expect(mixColor("#000000", "#FFFFFF", 0)).toBe("rgb(0,0,0)");
    expect(mixColor("#000000", "#FFFFFF", 1)).toBe("rgb(255,255,255)");
    expect(mixColor("#3A9D3F", "#9BD13C", 0.5)).toBe("rgb(107,183,62)");
  });
});

describe("Phase 27 Daily Beyond English brand", () => {
  it("names the channel and loads the owner's logo", () => {
    expect(BRAND_NAME).toEqual({ top: "Daily Beyond", sub: "ENGLISH" });
    expect(LOGO_PATH).toBe("brand/logo.png");
  });

  it("uses the green / yellow palette and no longer the violet / cyan one", () => {
    const colours = Object.values(BRAND_PALETTE).map((value) => value.toLowerCase());
    for (const old of ["#7c3aed", "#22d3ee", "#4f46e5", "#db2777", "#0b1026", "#1e1b4b"]) {
      expect(colours).not.toContain(old);
    }
    expect(BRAND_PALETTE.green).toBe("#3A9D3F");
    expect(BRAND_PALETTE.lime).toBe("#9BD13C");
    expect(BRAND_PALETTE.yellow).toBe("#FFD60A");
  });

  it("keeps every text colour readable (AA) on the deep-green background", () => {
    for (const background of [BRAND_PALETTE.bgStart, BRAND_PALETTE.bgMid, BRAND_PALETTE.bgEnd]) {
      expect(contrast(BRAND_PALETTE.ink, background)).toBeGreaterThanOrEqual(7);
      expect(contrast(BRAND_PALETTE.muted, background)).toBeGreaterThanOrEqual(4.5);
      expect(contrast(BRAND_PALETTE.yellow, background)).toBeGreaterThanOrEqual(4.5);
    }
    expect(contrast(BRAND_PALETTE.pillInk, BRAND_PALETTE.yellow)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(BRAND_PALETTE.ink, BRAND_PALETTE.subscribe)).toBeGreaterThanOrEqual(4.5);
  });
});
