import { buildKaraokeTokens, withScriptPunctuation } from "./karaoke";
import type { EpisodeLine, SpriteCharacter, SpriteLine } from "./types";

export type GestureCue = { startSec: number; endSec: number; picture: string };
type PhraseWord = { text: string; startSec: number; endSec: number };
/** Phase 61: the shortest line that still gets phrase gestures. */
export const MIN_LINE_SEC = 1.2;
type CachedCues = { plan: SpriteLine; speaking: boolean; cues: GestureCue[] | null };
const cache = new WeakMap<SpriteCharacter, WeakMap<EpisodeLine, CachedCues>>();

const paired = (character: SpriteCharacter, name: string): boolean =>
  `gesture-${name}` in character.pictures && `gesture-${name}__open` in character.pictures;

function phrases(line: EpisodeLine): PhraseWord[][] {
  const words = withScriptPunctuation(buildKaraokeTokens(line), line.text)
    .map((word) => ({ text: word.text.trim(), startSec: word.fromMs / 1000, endSec: word.toMs / 1000 }));
  const result: PhraseWord[][] = [];
  let group: PhraseWord[] = [];
  words.forEach((word) => {
    group.push(word);
    // Phase 61 (ENH-043): shorter phrases (commas too) so the gestures change with the speech
    if (/[.!?;:](["')\]]*)$/.test(word.text) || (/,(["')\]]*)$/.test(word.text) && group.length >= 3)
      || group.length >= 8 || word.endSec - group[0].startSec >= 2.6) {
      result.push(group);
      group = [];
    }
  });
  if (group.length) result.push(group);
  return result;
}

function semanticGesture(text: string): string | null {
  if (/\b(hi|hello|hey|bye|goodbye|welcome|see you)\b/i.test(text)) return "wave";
  if (/\b(thank|thanks|grateful|appreciate)\b/i.test(text)) return "heart";
  if (/\b(look|over there|this one|that one|see that|right there)\b/i.test(text)) return "point";
  if (/\b(maybe|perhaps|not sure|don't know|do not know)\b/i.test(text)) return "open";
  if (/\?/.test(text)) return "think";
  return null;
}

/** Every turn of 1.2 s and 2 words or more uses brief phrase gestures with short neutral rests (Phase 61: lively);
 * minimal/legacy packs retain their old fallback. */
export function buildConversationCues(line: EpisodeLine, plan: SpriteLine, character: SpriteCharacter,
  speaking: boolean): GestureCue[] | null {
  const generic = ["talk", "open"].filter((name) => paired(character, name));
  const fullPairs = ["talk", "open", "wave", "heart", "point", "think", "listen"].filter((name) => paired(character, name));
  if (plan.slot === null || line.endSec - line.startSec < MIN_LINE_SEC || line.words.length < 2 || !generic.length || fullPairs.length < 2) return null;
  const groups = phrases(line);
  const cues: GestureCue[] = [];
  let earliest = line.startSec;
  groups.forEach((group, index) => {
    const text = group.map((word) => word.text).join(" ");
    if (speaking) {
      const word = group.find((candidate) => candidate.startSec >= earliest - 0.01);
      if (!word) return;
      const semantic = semanticGesture(text);
      const name = semantic && paired(character, semantic) ? semantic : generic[index % generic.length];
      const duration = name === "wave" || name === "heart" ? 1.6 : 2.0;
      const limit = Math.min(word.startSec + duration, group.at(-1)!.endSec, line.endSec);
      const ending = group.filter((candidate) => candidate.endSec <= limit + 0.01).at(-1)?.endSec ?? limit;
      if (ending - word.startSec < 0.6) return;
      cues.push({ startSec: word.startSec, endSec: ending, picture: `gesture-${name}` });
      earliest = ending + 0.3;
    } else {
      // A listener reacts near a phrase ending, then returns to the neutral listening expression.
      const start = group.at(-1)!.endSec + 0.12;
      if (start < earliest || start >= line.endSec - 0.3) return;
      const name = /\?|\b(maybe|perhaps|not sure)\b/i.test(text) && paired(character, "think") ? "think" : "listen";
      if (!paired(character, name)) return;
      const end = Math.min(start + 1.1, line.endSec);
      cues.push({ startSec: start, endSec: end, picture: `gesture-${name}` });
      earliest = end + 0.7;
    }
  });
  return cues;
}

/** Props are immutable during a render; cache cue generation per actual line/plan/character identity. */
export function conversationCues(line: EpisodeLine, plan: SpriteLine, character: SpriteCharacter,
  speaking: boolean): GestureCue[] | null {
  let byLine = cache.get(character);
  if (!byLine) { byLine = new WeakMap(); cache.set(character, byLine); }
  const saved = byLine.get(line);
  if (saved?.plan === plan && saved.speaking === speaking) return saved.cues;
  const cues = buildConversationCues(line, plan, character, speaking);
  byLine.set(line, { plan, speaking, cues });
  return cues;
}

type BodyLine = { startSec: number; endSec: number; words: Array<{ text: string; startSec: number; endSec: number }> };
/** Phase 61 bounds, in pixels of a 1280-wide video and degrees. */
export const BODY_LIMITS = { x: 11, y: 11, rotation: 1.7 };
const pulse = (age: number, length: number) => (age >= 0 && age < length ? Math.sin((Math.PI * age) / length) : 0);
/** A stressed word: a long word or one held long (the karaoke words carry no punctuation). */
const stressed = (word: { text: string; startSec: number; endSec: number }) =>
  word.text.replace(/[^\p{L}\p{N}]/gu, "").length >= 6 || word.endSec - word.startSec >= 0.38;

/** Phase 61 (ENH-043): a lively body that moves only the whole picture (no warp, nothing pasted on). The speaker leans
 * toward the listener and bobs on each word onset (more on stressed words); the listener shifts its weight, leans toward
 * the speaker and nods at the speaker's phrase ends (a pause of 0.3 s or more). Units: pixels of a 1280-wide video. */
export function conversationBody(timeSec: number, line: BodyLine, slot: number, speaking: boolean) {
  const time = Math.max(0, timeSec - line.startSec);
  const presence = Math.max(0, Math.min(1, time / 0.5, (line.endSec - timeSec) / 0.35));
  const side = slot === 0 ? 1 : -1;
  const phase = time * Math.PI * 2 / (speaking ? 5.7 : 5.2) + slot * 1.1;
  const words = line.words;
  let last = -1;
  for (let index = 0; index < words.length && words[index].startSec <= timeSec; index += 1) last = index;
  if (speaking) {
    const word = words[last];
    const bob = word ? pulse(timeSec - word.startSec, 0.28) * (stressed(word) ? 1 : 0.45) : 0;
    return { x: (side * 6 + 3 * Math.sin(phase)) * presence,
      y: (-9 * bob - 1.5 * Math.sin(phase * 1.4)) * presence,
      rotation: (side * (0.9 + 0.5 * bob) + 0.25 * Math.sin(phase)) * presence };
  }
  // the listener nods after a word that is followed by a pause (or the last word)
  let nod = 0;
  for (let index = Math.max(0, last - 1); index <= last; index += 1) {
    const word = words[index], next = words[index + 1];
    if (word && (!next || next.startSec - word.endSec >= 0.3)) nod = Math.max(nod, pulse(timeSec - word.endSec, 0.5));
  }
  return { x: (side * 2 + 5 * Math.sin(phase)) * presence,
    y: (8 * nod - 1 * Math.sin(phase * 1.4)) * presence,
    rotation: (side * (0.35 + 0.8 * nod) + 0.2 * Math.sin(phase)) * presence };
}

/** Imported pictures record small head offsets; compensate for those without warping or blending the image. */
export function pictureAlignment(character: SpriteCharacter, picture: string, width: number, height: number) {
  const [dx, dy] = character.offsets[picture] ?? [0, 0];
  return { x: -(character.mirror ? -1 : 1) * dx / 1280 * width, y: -dy / 1536 * height };
}
