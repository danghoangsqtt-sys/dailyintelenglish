/**
 * Phase 30 (ENH-021): the pure layout rules of the podcast visual modes, kept free of React and Remotion so vitest can pin
 * them. `Podcast.tsx` draws what these functions describe.
 */

export const VISUAL_MODES = ["illustrated", "podcast_black", "podcast_characters", "podcast_still"] as const;
export type VisualMode = (typeof VISUAL_MODES)[number];
export type PodcastLayer = "none" | "black" | "cards" | "still";

/** Which layer a mode draws behind the captions ("none": the drawn shots of the storyboard, as before). */
export function podcastLayer(mode: VisualMode): PodcastLayer {
  if (mode === "podcast_black") return "black";
  if (mode === "podcast_characters") return "cards";
  if (mode === "podcast_still") return "still";
  return "none";
}

/** The portrait cards: 3:4, centred, starting below the vocabulary card (top 20..170) and above the caption band. */
export const CARD_WIDTH = 280;
export const CARD_HEIGHT = 373;
export const CARD_GAP = 48;
export const CARD_TOP = 190;
export const ACTIVE_CARD_SCALE = 1.06;
export const INACTIVE_CARD_OPACITY = 0.55;

export type CardBox = { x: number; y: number; width: number; height: number };

export function cardLayout(count: number, frameWidth: number): CardBox[] {
  const total = count * CARD_WIDTH + Math.max(0, count - 1) * CARD_GAP;
  const left = (frameWidth - total) / 2;
  return Array.from({ length: count }, (_, index) => ({
    x: left + index * (CARD_WIDTH + CARD_GAP), y: CARD_TOP, width: CARD_WIDTH, height: CARD_HEIGHT,
  }));
}

/** The active speaker's card is lit and a little larger; the others recede and lose some colour. */
export function cardState(isActive: boolean): { scale: number; opacity: number; saturate: number } {
  return isActive
    ? { scale: ACTIVE_CARD_SCALE, opacity: 1, saturate: 1 }
    : { scale: 1, opacity: INACTIVE_CARD_OPACITY, saturate: 0.6 };
}

/** The one still of `podcast_still` moves very slowly (a zoom of at most 5% across the whole speech). */
export const STILL_ZOOM_GAIN = 0.05;

export function stillScale(progress: number): number {
  const t = Math.min(1, Math.max(0, progress));
  return 1 + STILL_ZOOM_GAIN * t;
}

/** A speaker without a picture gets a card with the first letter of the name. */
export function speakerInitial(name: string): string {
  const trimmed = name.trim();
  return trimmed ? trimmed[0].toUpperCase() : "?";
}
