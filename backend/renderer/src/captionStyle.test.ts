import { describe, expect, it } from "vitest";
import { BOTTOM_SHADE_STYLE, CAPTION_STYLES, OUTLINE_SHADOW, captionStyleSpec } from "./captionStyle";
import { episodeInputPropsSchema } from "./types";

describe("captionStyleSpec (Task 20.2d)", () => {
  it("outline: hard black edge in all 8 directions plus the soft glow, no box, no shade", () => {
    const spec = captionStyleSpec("outline");
    expect(spec.text.textShadow).toBe(OUTLINE_SHADOW);
    expect(OUTLINE_SHADOW.split(", ").filter((part) => part.endsWith(" 0 #000"))).toHaveLength(8);
    expect(OUTLINE_SHADOW).toContain("0 0 6px rgba(0,0,0,0.9)");
    expect(spec.box).toBeNull();
    expect(spec.bottomShade).toBe(false);
  });

  it("box: semi-transparent dark box, glow only (no outline), no shade", () => {
    const spec = captionStyleSpec("box");
    expect(spec.box?.backgroundColor).toBe("rgba(0, 0, 0, 0.65)");
    expect(spec.text.textShadow).not.toContain(" 0 #000");
    expect(spec.bottomShade).toBe(false);
  });

  it("shade: outline plus the bottom shade", () => {
    const spec = captionStyleSpec("shade");
    expect(spec.text.textShadow).toBe(OUTLINE_SHADOW);
    expect(spec.box).toBeNull();
    expect(spec.bottomShade).toBe(true);
  });

  it("the bottom shade stays in the bottom 30% (never reaches the top-corner overlays)", () => {
    expect(BOTTOM_SHADE_STYLE.bottom).toBe(0);
    expect(BOTTOM_SHADE_STYLE.height).toBe("30%");
  });
});

describe("captionStyle prop (Task 20.2d)", () => {
  const minimal = { episodeId: "e", lines: [], audioPath: "a.mp3", fps: 30, width: 1280, height: 720 };

  it("defaults to outline when absent (older runners / props files keep rendering)", () => {
    expect(episodeInputPropsSchema.parse(minimal).captionStyle).toBe("outline");
  });

  it("accepts every declared style and rejects anything else", () => {
    for (const style of CAPTION_STYLES) {
      expect(episodeInputPropsSchema.parse({ ...minimal, captionStyle: style }).captionStyle).toBe(style);
    }
    expect(() => episodeInputPropsSchema.parse({ ...minimal, captionStyle: "neon" })).toThrow();
  });
});
