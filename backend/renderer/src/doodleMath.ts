/** Phase 98 (D164, D167): the pure rules of a Doodle story's screen: its crossfade and its term cards. */
import type { EpisodeLine, VocabItem } from "./types";

export const CROSSFADE_SEC = 0.4;
export const CARD_SEC = 4.5;
export const CAPTION_MAX_WORDS = 5;
export const CAPTION_MAX_CHARACTERS = 30;

type Span = { start_sec: number; end_sec: number };

/** How far the picture of segment `index` has faded in, 0..1; the first picture needs no fade. */
export function fadeAt(timeline: Span[], index: number, time: number): number {
  if (index <= 0) return 1;
  return Math.min(1, Math.max(0, (time - timeline[index].start_sec) / CROSSFADE_SEC));
}

const plain = (text: string) => text.toLowerCase().replace(/[^\p{L}\p{N}']/gu, "");

/** A word and its simple inflections, as the script check counts them (plural, -ed, -ing, the e-drop, y to i). */
function formsOf(word: string): RegExp {
  const safe = word.replace(/[^\p{L}\p{N}']/gu, "");
  if (safe.endsWith("e")) return new RegExp(`^${safe.slice(0, -1)}(e|es|ed|ing)$`, "u");
  if (safe.endsWith("y") && safe.length > 2) return new RegExp(`^${safe.slice(0, -1)}(y|ies|ied|ying)$`, "u");
  return new RegExp(`^${safe}(s|es|ed|ing)?$`, "u");
}

export type TermCard = { word: string; ipa: string; definitionEn: string; definitionVi: string; fromSec: number; toSec: number };

/** One card per target word, from the first time it is said, for as long as the word has a learning-pack entry. Two cards
 * never overlap: the later one waits. A word never said has no card. */
export function termCards(lines: EpisodeLine[], vocab: VocabItem[], terms: readonly string[]): TermCard[] {
  const words = lines.flatMap((line) => line.words ?? []);
  const said = words.map((word) => plain(word.text));
  const cards: TermCard[] = [];
  for (const term of terms) {
    const item = vocab.find((entry) => entry.word.toLowerCase() === term.toLowerCase());
    const parts = term.trim().split(/\s+/u).map((part) => plain(part)).filter(Boolean);
    if (!item || !parts.length) continue;
    const forms = parts.map((part, index) => (index === parts.length - 1 || parts.length === 1 ? formsOf(part) : new RegExp(`^${part}$`, "u")));
    const at = said.findIndex((_, start) => forms.every((form, offset) => form.test(said[start + offset] ?? "")));
    if (at < 0) continue;
    cards.push({ word: item.word, ipa: item.ipa, definitionEn: item.definitionEn, definitionVi: item.definitionVi,
      fromSec: words[at].startSec, toSec: words[at].startSec + CARD_SEC });
  }
  cards.sort((a, b) => a.fromSec - b.fromSec);
  for (let index = 1; index < cards.length; index += 1) {
    const before = cards[index - 1];
    if (cards[index].fromSec < before.toSec) {
      cards[index].fromSec = before.toSec;
      cards[index].toSec = before.toSec + CARD_SEC;
    }
  }
  return cards;
}

export const cardAt = (cards: TermCard[], time: number) => cards.find((card) => time >= card.fromSec && time < card.toSec);
