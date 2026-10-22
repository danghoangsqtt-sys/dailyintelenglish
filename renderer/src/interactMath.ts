/** Phase 65 (ENH-047): pure helpers of the interactive Shorts -- countdown quiz, listening challenge (one narrator),
 * chat and would you rather (two characters, drawn from the script lines). Frame-deterministic. */
import type { Visual } from "./soloTypes";

export const INTERACT_STYLES = ["quiz", "listen"] as const;
export type InteractStyle = (typeof INTERACT_STYLES)[number];
export const isInteractStyle = (style: unknown): style is InteractStyle => INTERACT_STYLES.includes(style as InteractStyle);
export const CONVERSATION_SHORTS = ["chat", "wyr"] as const;
export type ConversationShort = (typeof CONVERSATION_SHORTS)[number];

type Word = { text: string; startSec: number; endSec: number };
const clean = (text: string) => text.toLowerCase().replace(/[^\p{L}\p{N}' ]/gu, " ").replace(/\s+/g, " ").trim();
const bare = (word: string) => word.toLowerCase().replace(/[^\p{L}\p{N}']/gu, "");

/** A quiz question from its card: the question, the options without their "A " letters, and the right one. */
export function quizItem(visual: Visual): { question: string; options: string[]; answer: number } | null {
  if (visual.kind !== "text_card" || (visual.bullets ?? []).length < 2) return null;
  const options = (visual.bullets ?? []).map((option) => option.replace(/^\s*[A-Da-d][).:]?\s+/, "").trim());
  const wanted = clean((visual.emphasis ?? "").replace(/^\s*[A-Da-d][).:]?\s+/, ""));
  let answer = options.findIndex((option) => clean(option) === wanted);
  if (answer < 0) answer = options.findIndex((option) => wanted && (clean(option).includes(wanted) || wanted.includes(clean(option))));
  return { question: visual.title, options, answer };
}

/** When a word (or a two-word phrase) is first said in a span, else at `share` of it. */
export function cueAt(words: Word[], start: number, end: number, phrase: string, share: number): number {
  const parts = phrase.split(" ");
  for (let i = 0; i + parts.length <= words.length; i += 1) {
    if (parts.every((part, j) => bare(words[i + j].text) === part)) return words[i].startSec;
  }
  return start + share * (end - start);
}

/** The listening challenge's phase at `time`, from the narration itself (whatever the plan's segments are): after
 * "Listen" the sentence is heard ("listening", captions hidden), after "Here is" it is shown ("revealed", from that
 * moment); null before the first "Listen". */
export function listenPhase(words: Word[], time: number): { phase: "listening" | "revealed"; since: number } | null {
  let phase: { phase: "listening" | "revealed"; since: number } | null = null;
  for (let i = 0; i < words.length && words[i].startSec <= time; i += 1) {
    const word = bare(words[i].text), next = words[i + 1] ? bare(words[i + 1].text) : "";
    if (word === "listen") phase = { phase: "listening", since: words[i].startSec };
    else if (word === "here" && (next === "is" || next === "it's" || next === "its")) phase = { phase: "revealed", since: words[i].startSec };
  }
  return phase;
}

/** The quiz timer: from "three" to the reveal ("answer"), its share 0..1 at `time` (null outside). */
export function timerShare(time: number, from: number, to: number): number | null {
  if (time < from || time >= to || to <= from) return null;
  return (time - from) / (to - from);
}

export type ChatLine = { startSec: number; endSec: number; text: string; speakerId: string };
/** The chat messages shown at `time` (those whose line has started), and whether someone is typing the next one
 * (the 0.7 s before it starts, after the previous message). */
export function chatState(lines: ChatLine[], time: number): { shown: number; typing: string | null } {
  const shown = lines.filter((line) => line.startSec <= time).length;
  const next = lines[shown];
  const typing = next && time >= next.startSec - 0.7 ? next.speakerId : null;
  return { shown, typing };
}

/** Which side a speaker's bubbles are on: the first speaker on the left, the other on the right. */
export function sideOf(lines: ChatLine[], speakerId: string): "left" | "right" {
  return lines[0]?.speakerId === speakerId ? "left" : "right";
}

/** The two options of a "Would you rather A or B?" line, or null. */
export function wyrOptions(text: string): [string, string] | null {
  const match = text.match(/would you rather\s+(.+?)\s+or\s+(.+?)\s*\?/i);
  return match ? [match[1].trim(), match[2].trim()] : null;
}

/** The option an answer picks: the one sharing more words with it ("I'd rather ..."), or null when unclear. */
export function chosenOption(answer: string, options: [string, string]): 0 | 1 | null {
  const said = new Set(clean(answer).split(" ").filter((word) => word.length > 2));
  // the last word of an option is usually its key noun ("Tokyo", "pasta"): it counts double
  const score = options.map((option) => {
    const parts = clean(option).split(" ").filter((word) => word.length > 2);
    return parts.filter((word) => said.has(word)).length + (parts.length && said.has(parts[parts.length - 1]) ? 2 : 0);
  });
  if (score[0] === score[1]) return null;
  return score[0] > score[1] ? 0 : 1;
}

export type WyrRound = { question: number; answer: number | null; options: [string, string]; chosen: 0 | 1 | null };
/** The rounds of a would-you-rather Short: each asking line and the next line of the other speaker. */
export function wyrRounds(lines: ChatLine[]): WyrRound[] {
  const rounds: WyrRound[] = [];
  lines.forEach((line, index) => {
    const options = wyrOptions(line.text);
    if (!options) return;
    const answer = lines.findIndex((other, at) => at > index && other.speakerId !== line.speakerId);
    rounds.push({ question: index, answer: answer >= 0 ? answer : null, options,
      chosen: answer >= 0 ? chosenOption(lines[answer].text, options) : null });
  });
  return rounds;
}

/** The round on screen at `time` (the last one whose question has started), or -1. */
export function roundAt(rounds: WyrRound[], lines: ChatLine[], time: number): number {
  let current = -1;
  rounds.forEach((round, index) => { if (lines[round.question].startSec <= time) current = index; });
  return current;
}

/** Initials for a chat avatar. */
export const initials = (name: string) => name.split(/\s+/).filter(Boolean).map((part) => part[0]).join("").slice(0, 2).toUpperCase() || "?";
