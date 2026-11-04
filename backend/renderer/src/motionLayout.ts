import type { Layout } from "./types";
import { VERTICAL } from "./safeZone";

/** Motion is shared; caption density and decorative geometry follow the output canvas. */
export function captionLayout(layout: Layout) {
  return layout === "vertical"
    ? { fontSize: 44, speakerSize: 22, maxWords: VERTICAL.captionWords, maxCharacters: VERTICAL.captionCharacters }
    : { fontSize: 32, speakerSize: 18, maxWords: 16, maxCharacters: 96 };
}

export function accentLayout(layout: Layout, width: number, height: number) {
  return layout === "vertical"
    ? { centers: [...VERTICAL.slotX], top: 1000, width: 490, height: 650, particleScale: 1 }
    : { centers: [width * 0.27, width * 0.73], top: height * 0.05, width: width * 0.4,
      height: height * 0.9, particleScale: 0.7 };
}
