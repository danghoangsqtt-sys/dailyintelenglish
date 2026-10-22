/** Phase 64 (ENH-046): pure helpers of the quick-learning Shorts -- Don't say / Say, Word of the day, Top 5 phrases. */
import type { SoloSegment, Visual } from "./soloTypes";
import type { EpisodeLearning } from "./types";

export const LEARN_STYLES = ["mistakes", "wordday", "top5"] as const;
export type LearnStyle = (typeof LEARN_STYLES)[number];
export const isLearnStyle = (style: unknown): style is LearnStyle => LEARN_STYLES.includes(style as LearnStyle);

/** The band label of a template. */
export function templateLabel(style: LearnStyle): string {
  return style === "mistakes" ? "DON'T SAY · SAY" : style === "wordday" ? "WORD OF THE DAY" : "TOP 5 PHRASES";
}

/** A Don't say / Say pair: a comparison diagram's two nodes (by id or label, else the first two). */
export function mistakePair(visual: Visual): { wrong: string; right: string } | null {
  if (visual.kind !== "diagram" || visual.nodes.length < 2) return null;
  const text = (node: { label: string; detail?: string }) => (node.detail || node.label).trim();
  const wrong = visual.nodes.find((node) => node.id === "dont" || /don'?t|wrong|avoid|not/i.test(node.label)) ?? visual.nodes[0];
  const right = visual.nodes.find((node) => node !== wrong && (node.id === "say" || /^say|right|better|correct/i.test(node.label)))
    ?? visual.nodes.find((node) => node !== wrong)!;
  return { wrong: text(wrong), right: text(right) };
}

/** When the right phrase pops in: from the moment the narration says "say" a second time, else at 45 %. */
export function rightAt(words: Array<{ text: string; startSec: number }>, start: number, end: number): number {
  const says = words.filter((word) => /^say[.,:!]?$/i.test(word.text.trim()));
  return says.length >= 2 ? says[1].startSec : start + 0.45 * (end - start);
}

/** The countdown number of a Top 5 item: the segments between the hook (first) and the follow line (last) count down
 * from their number to 1; null for the hook and the last segment. */
export function countdownNumber(segments: SoloSegment[], index: number): number | null {
  if (segments.length < 3 || index <= 0 || index >= segments.length - 1) return null;
  const items = segments.length - 2;
  return Math.max(1, items - (index - 1));
}

const norm = (text: string) => text.toLowerCase().replace(/[^\p{L}\p{N}' ]/gu, "").replace(/\s+/g, " ").trim();
/** The learning pack's entry for a word or phrase (vocabulary first, then idioms), for its IPA and Vietnamese meaning. */
export function learningFor(learning: EpisodeLearning | undefined, phrase: string):
  { ipa: string; partOfSpeech: string; meaningVi: string } | null {
  if (!learning || !phrase) return null;
  const wanted = norm(phrase);
  const vocab = learning.vocab.find((item) => norm(item.word) === wanted);
  if (vocab) return { ipa: vocab.ipa, partOfSpeech: vocab.partOfSpeech, meaningVi: vocab.definitionVi };
  const idiom = learning.idioms.find((item) => norm(item.phrase) === wanted);
  return idiom ? { ipa: "", partOfSpeech: "", meaningVi: idiom.meaningVi } : null;
}

/** The title and the first bullet of a card (the phrase and its meaning). */
export function cardText(visual: Visual): { title: string; detail: string; emphasis: string } {
  if (visual.kind === "text_card") return { title: visual.title, detail: visual.bullets?.[0] ?? "", emphasis: visual.emphasis ?? "" };
  if (visual.kind === "quote") return { title: visual.text, detail: "", emphasis: visual.highlight ?? "" };
  return { title: "title" in visual && visual.title ? visual.title : "", detail: "", emphasis: "" };
}
