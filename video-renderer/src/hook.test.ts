import { describe, expect, it } from "vitest";
import { hookOpacity } from "./Episode";

describe("hookOpacity (Phase 37 clip hook banner)", () => {
  it("is hidden before the clip, full for the hook's seconds, then fades out", () => {
    expect(hookOpacity(0, 2)).toBe(0);
    expect(hookOpacity(2, 2)).toBe(1);
    expect(hookOpacity(4.8, 2)).toBe(1);
    expect(hookOpacity(5.5, 2)).toBe(0);
    expect(hookOpacity(5.3, 2)).toBeGreaterThan(0);
  });
});
