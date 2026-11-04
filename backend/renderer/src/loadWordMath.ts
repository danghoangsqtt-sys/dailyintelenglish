/** Phase 97 (D159): the opening articles and the wall of words of the "Load the word" Short. */

export const WALL_ROWS = 13;
export const WALL_COLUMNS = 3;
/** Eight article flicks, then the flash of speed lines, before the wall. */
export const ARTICLE_SEC = 0.27;
export const HOOK_SEC = 2.7;

/** A stable number in [0, 1) for a cell of the wall at a step of time. */
function noise(row: number, column: number, step: number): number {
  const value = Math.sin(row * 12.9898 + column * 78.233 + step * 37.719) * 43758.5453;
  return value - Math.floor(value);
}

/** The article on screen at this moment, and others for the blurred heading and body around it. */
export function articleAt(texts: string[], time: number): { text: string; others: string[]; step: number } {
  const step = Math.floor(Math.max(0, time) / ARTICLE_SEC);
  const at = (offset: number) => texts[(step + offset) % texts.length];
  return { text: at(0), others: [at(1), at(2), at(3), at(4)], step };
}

/** The bar: 0 at the start of the wall, 100 at the end of the loop. */
export function loadPercent(time: number, start: number, end: number): number {
  if (end <= start) return 100;
  return Math.round(Math.max(0, Math.min(1, (time - start) / (end - start))) * 100);
}

/** The steps of the wall come faster as the voice does: from 3 to 9 changes a second. */
export function wallStep(progress: number, seconds: number): number {
  return Math.floor(seconds * (3 * progress + 3 * progress * progress));
}

/** The wall builds column by column, half a second each. */
export function wallColumns(seconds: number): number {
  return Math.max(1, Math.min(WALL_COLUMNS, Math.floor(Math.max(0, seconds) / 0.5) + 1));
}

/** The wall is full at first; then cells drop out and come back; a few are lit in yellow. */
export function wallCell(row: number, column: number, step: number, progress: number): { shown: boolean; lit: boolean } {
  const shown = progress < 0.2 || noise(row, column, Math.floor(step / 4)) < 0.75;
  return { shown, lit: shown && noise(row, column, step) > 0.9 };
}

/** The meaning between two rows moves from side to side, as in a hand-made wall. */
export function wallMeaningSide(row: number): "left" | "center" | "right" {
  return (["left", "right", "center"] as const)[row % 3];
}
