import type { Chapter } from "./types";

/**
 * Task 19.6 (D19.6-d): one chapter tick, positioned as a fraction of the audio window's
 * total duration -- used by `ChapterProgressBar` to place tick marks without redoing the
 * pct math per render.
 */
export interface ChapterTick extends Chapter {
  pct: number;
}

/**
 * Task 19.6 (D19.6-d): playback progress + chapter state for a given frame within the
 * audio window's own `<Sequence>` (frame 0 == the audio window's start -- see Episode.tsx's
 * D19.6-a Sequence remapping). Pure and unit-testable; renders nothing itself.
 */
export interface ChapterProgress {
  /** 0-1, clamped -- how far through the audio window `currentFrame` is. */
  overallPct: number;
  /** The last chapter whose `startSec` has been reached, or `null` before the first one
   * (or when `chapters` is empty). */
  currentChapter: Chapter | null;
  /** Every chapter, each carrying its own tick position as a 0-1 fraction of `audioDurationSec`. */
  chapters: ChapterTick[];
}

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

export function computeProgressForFrame(
  currentFrame: number,
  fps: number,
  audioDurationSec: number,
  chapters: Chapter[]
): ChapterProgress {
  const currentTimeSec = currentFrame / fps;
  const overallPct = audioDurationSec > 0 ? clamp01(currentTimeSec / audioDurationSec) : 0;

  let currentChapter: Chapter | null = null;
  for (const chapter of chapters) {
    if (currentTimeSec >= chapter.startSec) {
      currentChapter = chapter;
    }
  }

  const chaptersWithPct: ChapterTick[] = chapters.map((chapter) => ({
    ...chapter,
    pct: audioDurationSec > 0 ? clamp01(chapter.startSec / audioDurationSec) : 0,
  }));

  return { overallPct, currentChapter, chapters: chaptersWithPct };
}
