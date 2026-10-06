import { describe, expect, it } from "vitest";
import { mix, mixColor } from "./Brand";

describe("Phase 25 brand morph helpers", () => {
  it("mixes numbers linearly", () => {
    expect(mix(150, 76, 0)).toBe(150);
    expect(mix(150, 76, 1)).toBe(76);
    expect(mix(0, 10, 0.25)).toBe(2.5);
  });

  it("mixes hex colours channel by channel", () => {
    expect(mixColor("#000000", "#FFFFFF", 0)).toBe("rgb(0,0,0)");
    expect(mixColor("#000000", "#FFFFFF", 1)).toBe("rgb(255,255,255)");
    expect(mixColor("#7C3AED", "#4F46E5", 0.5)).toBe("rgb(102,64,233)");
  });
});
