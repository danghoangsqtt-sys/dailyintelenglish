import type { EpisodeLine, IdiomItem, VocabItem } from "./types";

/** One learning item, tagged with its own kind so the card renderer knows which fields to
 * show (vocab has partOfSpeech/ipa, idioms don't). */
export type LearningItem = ({ kind: "vocab" } & VocabItem) | ({ kind: "idiom" } & IdiomItem);

export interface AttachedLineItems {
  lineIndex: number;
  items: LearningItem[];
}

function normalizeWhitespace(text: string): string {
  return text.toLowerCase().replace(/\s+/g, " ").trim();
}

/** D19.5-a: case-insensitive substring match on the raw line text. */
function lineMatchesWord(line: EpisodeLine, word: string): boolean {
  return line.text.toLowerCase().includes(word.toLowerCase());
}

/** D19.5-b: normalized substring match -- lowercase + collapsed whitespace on both sides. */
function lineMatchesPhrase(line: EpisodeLine, phrase: string): boolean {
  return normalizeWhitespace(line.text).includes(normalizeWhitespace(phrase));
}

/**
 * Task 19.5 (D19.5-a/b/c): attaches each vocab word / idiom phrase to the first line (by
 * array index, matching every other composition function's positional convention -- there is
 * no line-level id on `EpisodeLine`) whose text contains it. An item matching zero lines is
 * silently dropped (real Learning Content sometimes references concepts more abstract than
 * verbatim script words) -- not fabricated a home. An item matching multiple lines attaches
 * to the earliest one only (first-matching-line tie-break, D19.5-a/b).
 *
 * Combined ordering when a line ends up with both vocab and idiom items (not exercised by
 * the demo episode -- no real line there has both -- but the function must still be
 * deterministic for a future project that does): vocab items first, in the vocab array's own
 * order, then idiom items, in the idioms array's own order. A deliberate default, not
 * accidental, per PM review.
 */
export function attachItemsToLines(
  vocab: VocabItem[],
  idioms: IdiomItem[],
  lines: EpisodeLine[]
): AttachedLineItems[] {
  const itemsByLineIndex = new Map<number, LearningItem[]>();

  const attach = (lineIndex: number, item: LearningItem) => {
    const existing = itemsByLineIndex.get(lineIndex);
    if (existing) {
      existing.push(item);
    } else {
      itemsByLineIndex.set(lineIndex, [item]);
    }
  };

  for (const word of vocab) {
    const lineIndex = lines.findIndex((line) => lineMatchesWord(line, word.word));
    if (lineIndex !== -1) {
      attach(lineIndex, { kind: "vocab", ...word });
    }
  }
  for (const idiom of idioms) {
    const lineIndex = lines.findIndex((line) => lineMatchesPhrase(line, idiom.phrase));
    if (lineIndex !== -1) {
      attach(lineIndex, { kind: "idiom", ...idiom });
    }
  }

  return Array.from(itemsByLineIndex.entries())
    .map(([lineIndex, items]) => ({ lineIndex, items }))
    .sort((a, b) => a.lineIndex - b.lineIndex);
}

export interface ActiveLearningItem {
  item: LearningItem;
  /** The active item's own time slot (not the whole line's duration) -- needed by the
   * renderer to fade the card in/out relative to *this item's* window, not the line's. */
  slotStartSec: number;
  slotEndSec: number;
}

/**
 * Task 19.5 (D19.5-c): the active learning item (plus its own time-slot bounds, for the
 * renderer's fade animation) at `currentTimeSec`, or `null` if the active line has no
 * attached items (or there's no active line at all -- a gap between lines). When a line has
 * N attached items, its own duration is divided into N equal time slots, one item per slot,
 * in `items`' own array order (option (i): simple, deterministic, robust to missing
 * word-level timing).
 */
export function activeItemForFrame(
  currentTimeSec: number,
  lines: EpisodeLine[],
  attached: AttachedLineItems[]
): ActiveLearningItem | null {
  const lineIndex = lines.findIndex(
    (line) => currentTimeSec >= line.startSec && currentTimeSec < line.endSec
  );
  if (lineIndex === -1) {
    return null;
  }
  const entry = attached.find((a) => a.lineIndex === lineIndex);
  if (!entry || entry.items.length === 0) {
    return null;
  }

  const line = lines[lineIndex];
  const slotDuration = (line.endSec - line.startSec) / entry.items.length;
  const slotIndex = Math.min(
    entry.items.length - 1,
    Math.floor((currentTimeSec - line.startSec) / slotDuration)
  );
  const slotStartSec = line.startSec + slotIndex * slotDuration;
  return {
    item: entry.items[slotIndex],
    slotStartSec,
    slotEndSec: slotStartSec + slotDuration,
  };
}
