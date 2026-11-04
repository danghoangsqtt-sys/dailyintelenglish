import type React from "react";

/**
 * Task 20.2d: user-selectable caption treatment. Each keeps the caption band legible on any
 * background (including detailed AI scenes) without shrinking the picture -- the owner
 * rejected a framed "window" layout as wasted space. `outline` (film/streaming-subtitle
 * convention) is the default by the owner's explicit preference.
 */
export const CAPTION_STYLES = ["outline", "box", "shade"] as const;
export type CaptionStyle = (typeof CAPTION_STYLES)[number];

/** The pre-20.2d soft glow, kept in every style (D19.3-b's look is the base layer). */
const GLOW_SHADOW = "0 0 6px rgba(0,0,0,0.9), 0 0 2px rgba(0,0,0,0.9)";

const OUTLINE_PX = 2;

/** 8-direction hard black edge, then the soft glow. `text-shadow` rather than
 * `-webkit-text-stroke`: the stroke is centered on the glyph edge and eats into the fill. */
export const OUTLINE_SHADOW = [
  [-1, -1],
  [0, -1],
  [1, -1],
  [-1, 0],
  [1, 0],
  [-1, 1],
  [0, 1],
  [1, 1],
]
  .map(([x, y]) => `${x * OUTLINE_PX}px ${y * OUTLINE_PX}px 0 #000`)
  .concat(GLOW_SHADOW)
  .join(", ");

export interface CaptionStyleSpec {
  /** Merged over the base caption text style (font/size/color stay the base's). */
  text: React.CSSProperties;
  /** Wraps the caption span when set (the `box` style). */
  box: React.CSSProperties | null;
  /** Draw the bottom gradient shade behind the caption band. */
  bottomShade: boolean;
}

const BOX_STYLE: React.CSSProperties = {
  backgroundColor: "rgba(0, 0, 0, 0.65)",
  borderRadius: 8,
  padding: "6px 14px",
  boxDecorationBreak: "clone",
  WebkitBoxDecorationBreak: "clone",
};

export function captionStyleSpec(style: CaptionStyle): CaptionStyleSpec {
  switch (style) {
    case "box":
      return { text: { textShadow: GLOW_SHADOW }, box: BOX_STYLE, bottomShade: false };
    case "shade":
      return { text: { textShadow: OUTLINE_SHADOW }, box: null, bottomShade: true };
    case "outline":
    default:
      return { text: { textShadow: OUTLINE_SHADOW }, box: null, bottomShade: false };
  }
}

/** Bottom ~30% of the frame, transparent -> near-black (the composition background color),
 * so it never reaches the speaker chips (top-left) or the vocab card (top-right). */
export const BOTTOM_SHADE_STYLE: React.CSSProperties = {
  position: "absolute",
  left: 0,
  right: 0,
  bottom: 0,
  height: "30%",
  background: "linear-gradient(to bottom, rgba(14, 15, 21, 0) 0%, rgba(14, 15, 21, 0.75) 100%)",
  pointerEvents: "none",
};
