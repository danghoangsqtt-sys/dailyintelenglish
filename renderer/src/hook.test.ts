import { describe, expect, it } from "vitest";
import { chipsOpacity, hookOpacity } from "./Episode";

describe("hookOpacity (Phase 37 clip hook banner)", () => {
  it("is hidden before the clip, full for the hook's seconds, then fades out", () => {
    expect(hookOpacity(0, 2)).toBe(0);
    expect(hookOpacity(2, 2)).toBe(1);
    expect(hookOpacity(4.8, 2)).toBe(1);
    expect(hookOpacity(5.5, 2)).toBe(0);
    expect(hookOpacity(5.3, 2)).toBeGreaterThan(0);
  });
});

describe("chipsOpacity (Phase 78: the hook banner covers the speaker chips' row)", () => {
  it("hides the chips while the hook shows and brings them back as it fades", () => {
    expect(chipsOpacity(hookOpacity(2, 2))).toBe(0);
    expect(chipsOpacity(hookOpacity(0, 2))).toBe(1);
    expect(chipsOpacity(hookOpacity(5.3, 2))).toBeGreaterThan(0);
    expect(chipsOpacity(hookOpacity(5.3, 2))).toBeLessThan(1);
    expect(chipsOpacity(0)).toBe(1);
  });
});
