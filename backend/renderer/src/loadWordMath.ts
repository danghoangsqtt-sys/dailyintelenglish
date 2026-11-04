/** Phase 97 (D159): the wall of words of the "Load the word" Short. */

export const WALL_ROWS = 12;
export const WALL_COLUMNS = 3;

/** A stable number in [0, 1) for a cell of the wall at a step of time. */
function noise(row: number, column: number, step: number): number {
  const value = Math.sin(row * 12.9898 + column * 78.233 + step * 37.719) * 43758.5453;
  return value - Math.floor(value);
}

/** The bar: 0 at the start of the loop, 100 at its end. */
export function loadPercent(time: number, start: number, end: number): number {
  if (end <= start) return 100;
  return Math.round(Math.max(0, Math.min(1, (time - start) / (end - start))) * 100);
}

/** The steps of the wall come faster as the voice does: from 3 to 9 changes a second. */
export function wallStep(progress: number, seconds: number): number {
  return Math.floor(seconds * (3 * progress + 3 * progress * progress));
}

/** More of the wall fills in as the word loads; a few cells are lit in yellow. */
export function wallCell(row: number, column: number, step: number, progress: number): { shown: boolean; lit: boolean } {
  const shown = noise(row, column, Math.floor(step / 4)) < 0.35 + 0.6 * progress;
  return { shown, lit: shown && noise(row, column, step) > 0.9 };
}
