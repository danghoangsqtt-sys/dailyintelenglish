import type { EpisodeLine } from "./types";

/**
 * Task 19.4 (D19.4-d): the speaker id of the line active at `currentTimeSec`, or `null` in a
 * gap (before line 0, between lines -- the 300ms/500ms silence padding from Task 1.6b -- or
 * after the last line). Tie rule: `startSec` inclusive, `endSec` exclusive -- identical
 * convention to `karaoke.ts`'s `activeTokenIndex` and to this project's SRT export format.
 */
export function activeSpeakerId(currentTimeSec: number, lines: EpisodeLine[]): string | null {
  const line = lines.find((candidate) => currentTimeSec >= candidate.startSec && currentTimeSec < candidate.endSec);
  return line ? line.speakerId : null;
}
