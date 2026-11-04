/**
 * Phase 81 (owner 2026-10-28): pure helpers of the slow English podcast and vocabulary flashcard Shorts.
 * A flashcard script is a deck name line, one line per card that says the word twice ("wash up. wash up."), and a
 * follow line; the card's part of speech, IPA and Vietnamese meaning come from the lesson (learning vocab).
 */
import type { EpisodeLine } from "./types";

export type DeckEntry = { word: string; partOfSpeech: string; ipa: string; meaningVi: string };
export type LearningLike = { vocab?: { word: string; partOfSpeech: string; ipa: string; definitionVi: string }[];
  idioms?: { phrase: string; meaningVi: string }[] } | undefined;

/** The word of a card line ("wash up. wash up." -> "wash up"), else null. Same rule as learning_pipeline.flashcard_words. */
export function cardWord(text: string): string | null {
  const match = text.trim().match(/^\s*(.{1,60}?)[.!?]\s+(.{1,60}?)[.!?]?\s*$/);
  return match && match[1].trim().toLowerCase() === match[2].trim().toLowerCase() ? match[1].trim() : null;
}

/** The card lines of a deck, in order: their line index and word. */
export function deckCards(lines: Pick<EpisodeLine, "text">[]): { line: number; word: string }[] {
  return lines.flatMap((line, index) => {
    const word = cardWord(line.text);
    return word ? [{ line: index, word }] : [];
  });
}

const norm = (value: string) => value.toLowerCase().replace(/^to\s+/, "").replace(/[^\p{L}\p{N}' ]/gu, " ").replace(/\s+/g, " ").trim();

/** What the card shows for a word, from the lesson (an idiom when no vocabulary item matches). */
export function deckEntry(learning: LearningLike, word: string): DeckEntry {
  const key = norm(word);
  const vocab = learning?.vocab?.find((item) => norm(item.word) === key);
  if (vocab) return { word, partOfSpeech: vocab.partOfSpeech, ipa: vocab.ipa, meaningVi: vocab.definitionVi };
  const idiom = learning?.idioms?.find((item) => norm(item.phrase) === key);
  return { word, partOfSpeech: idiom ? "phrase" : "", ipa: "", meaningVi: idiom?.meaningVi ?? "" };
}

/** A short part-of-speech label like the sample cards ("verb" -> "v."). */
export function posLabel(partOfSpeech: string): string {
  const value = partOfSpeech.trim().toLowerCase();
  const short: Record<string, string> = { verb: "v.", noun: "n.", adjective: "adj.", adverb: "adv.", "phrasal verb": "phr. v.",
    preposition: "prep.", pronoun: "pron.", conjunction: "conj.", phrase: "phr.", idiom: "idiom" };
  return short[value] ?? value;
}

/** The index of the line playing at `time` (the last started one between lines), -1 before the first. */
export function lineAt(lines: Pick<EpisodeLine, "startSec" | "endSec">[], time: number): number {
  let current = -1;
  lines.forEach((line, index) => { if (time >= line.startSec) current = index; });
  return current;
}

/** "Sinh hoạt hằng ngày (P1)" / "Daily routines, part 2" -> 1 / 2; null without a part number. */
export function partNumber(title: string): number | null {
  const match = title.match(/\(P\s*(\d+)\)|\bpart\s+(\d+)\b|\bphần\s+(\d+)\b/i);
  return match ? Number(match[1] ?? match[2] ?? match[3]) : null;
}

/** How far a new card has slid in, 0..1, over its first `seconds`. */
export function slideIn(time: number, start: number, seconds = 0.35): number {
  const t = Math.min(1, Math.max(0, (time - start) / seconds));
  return 1 - Math.pow(1 - t, 3);
}
