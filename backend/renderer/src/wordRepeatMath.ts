/** Phase 96 (D147-D151): where the copies of the word appear in the Word of the day Short, and the word inside its example. */

/** One copy per repetition, away from the word block in the middle: [x, y, size] on the 1080x1920 frame (centre of the text). */
export const COPY_PLACES: readonly (readonly [number, number, number])[] = [
  [300, 330, 76], [760, 420, 92], [230, 560, 64], [790, 1090, 84], [300, 1200, 104], [620, 1320, 72],
];

/** How many copies are on screen at this repetition: the first saying is the word itself. */
export function copiesAt(repeat: number): number {
  return Math.max(0, Math.min(COPY_PLACES.length, repeat - 1));
}

/** Font size of the word so that a long one still fits the safe width. */
export function wordSize(word: string, width = 936): number {
  return Math.min(150, Math.floor(width / (Math.max(1, word.length) * 0.62)));
}

/** The centre of a copy, moved in so that the whole word stays on the frame. */
export function copyCentre(x: number, word: string, size: number, frame = 1080, margin = 24): number {
  const half = Math.min(frame / 2 - margin, (word.length * size * 0.62) / 2);
  return Math.max(margin + half, Math.min(frame - margin - half, x));
}

/** The example split around the word, an inflected form too ("studies" for "study"): [before, the word, after]. */
export function aroundWord(text: string, word: string): [string, string, string] {
  const stem = word.toLowerCase().replace(/[^a-z]/g, "");
  const head = stem.slice(0, Math.max(3, stem.length - 3));
  const found = head ? new RegExp(`\\b${head}[a-z'-]*`, "i").exec(text) : null;
  if (!found) return [text, "", ""];
  return [text.slice(0, found.index), found[0], text.slice(found.index + found[0].length)];
}

/** The number counted in the silence after a line (1, 2, 3), or null outside it. */
export function countAt(time: number, lineEnd: number, pause: number): number | null {
  if (pause <= 0 || time < lineEnd || time >= lineEnd + pause) return null;
  return Math.min(3, Math.floor(((time - lineEnd) / pause) * 3) + 1);
}

/** Font size of an advanced phrase so that it stays large and inside the safe width on up to two lines. */
export function levelPhraseSize(phrase: string): number {
  return phrase.length > 22 ? 58 : phrase.length > 14 ? 68 : 84;
}

/** First or second saying of the advanced phrase, from how many have started. */
export function levelSaying(started: number): number {
  return Math.max(1, Math.min(2, started));
}

/** Which explanations the audience setting shows (D150). */
export function wordExplains(audience: string | undefined): { en: boolean; vi: boolean } {
  if (audience === "international") return { en: true, vi: false };
  if (audience === "vietnamese") return { en: false, vi: true };
  return { en: true, vi: true };
}
