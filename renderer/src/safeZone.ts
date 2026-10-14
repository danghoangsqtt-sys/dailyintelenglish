/**
 * Phase 42 (D121, Gate B-25 review): the 1080x1920 vertical video keeps its key content inside the area that TikTok,
 * Instagram Reels and YouTube Shorts never cover.
 *
 * Source: the owner's TikTok template (1080x1920): the status bar and tabs cover the top 115 px and the
 * "Following / For You" box (x 313-762, y 133-216); the sides 46 px; the bottom from y 1545; the like / comment / share
 * column x 886-1033 from y 958. The ads spec the owner also sent covers the bottom 600 px (username, caption, music, call
 * to action). We keep a margin on both: key content (faces, captions, titles, cards, buttons) stays within
 * x 72-1008 and y 232-1320, and left of x 864 below y 900. Backgrounds and the characters' bodies may run under the UI.
 */

export const VERTICAL_SIZE = { width: 1080, height: 1920 } as const;

export const SAFE = {
  left: 72,
  right: 1008,
  top: 232,
  bottom: 1320,
  /** The platform's button column: below `columnFromY`, content stays left of `columnX`. */
  columnX: 864,
  columnFromY: 900,
} as const;

export type Box = { left: number; top: number; width: number; height: number };

/** True when `box` lies inside the safe zone (the button column included). */
export function insideSafeZone(box: Box): boolean {
  const right = box.left + box.width;
  const bottom = box.top + box.height;
  if (box.left < SAFE.left || right > SAFE.right || box.top < SAFE.top || bottom > SAFE.bottom) return false;
  if (bottom > SAFE.columnFromY && right > SAFE.columnX) return false;
  return true;
}

/** The vertical layout, in pixels of the 1080x1920 frame. Content boxes are the space each element may use. */
export const VERTICAL = {
  /** The scene / illustration (decoration: may run under the top bar). */
  picture: { top: 0, height: 790 },
  /** The dark fade from the picture into the caption band. */
  fade: { top: 570, height: 240 },
  speakerChips: { left: SAFE.left, top: 244, width: 560, height: 56 },
  /** The vocabulary card (scaled up 1.5x for a phone): left-aligned, clear of the chips. */
  vocabCard: { left: SAFE.left, top: 316, width: 792, height: 460, zoom: 1.5 },
  hookBanner: { left: SAFE.left, top: 330, width: SAFE.right - SAFE.left, height: 300 },
  /** Karaoke captions: left of the button column, above the characters. */
  captions: { left: SAFE.left, top: 790, width: SAFE.columnX - SAFE.left, height: 250 },
  /** At most this many words of a line at once: four lines of 50 px captions fit the band (long lines page). */
  captionWords: 14,
  /** Where the characters' heads start; their faces sit between here and `facesBottom`. */
  headTop: 1045,
  facesBottom: 1270,
  spriteHeight: 960,
  /** Character centres: both faces stay left of the button column. */
  slotX: [270, 640],
  /** Faces are about this wide in the sprite packs (for the safe-zone check). */
  faceWidth: 210,
} as const;

/** The intro / outro column (Phase 42.3): wide above the button column, narrower below it. */
export const VERTICAL_BRAND = {
  wide: { left: 108, width: 864 },    // above y 900
  narrow: { left: 216, width: 648 },  // below y 900: centred and still left of the button column
} as const;
