/**
 * Phase 30 (ENH-021): the pure layout rules of the podcast visual modes, kept free of React and Remotion so vitest can pin
 * them. `Podcast.tsx` draws what these functions describe.
 */

export const VISUAL_MODES = ["illustrated", "podcast_black", "podcast_still"] as const;
export type VisualMode = (typeof VISUAL_MODES)[number];
export type PodcastLayer = "none" | "black" | "still";

/** Which layer a mode draws behind the captions ("none": the drawn shots of the storyboard, as before). */
export function podcastLayer(mode: VisualMode): PodcastLayer {
  if (mode === "podcast_black") return "black";
  if (mode === "podcast_still") return "still";
  return "none";
}

/** The one still of `podcast_still` moves very slowly (a zoom of at most 5% across the whole speech). */
export const STILL_ZOOM_GAIN = 0.05;

export function stillScale(progress: number): number {
  const t = Math.min(1, Math.max(0, progress));
  return 1 + STILL_ZOOM_GAIN * t;
}
