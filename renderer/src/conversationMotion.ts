import { buildKaraokeTokens, withScriptPunctuation } from "./karaoke";
import type { EpisodeLine, SpriteCharacter, SpriteLine } from "./types";

export type GestureCue = { startSec: number; endSec: number; picture: string };
type PhraseWord = { text: string; startSec: number; endSec: number };
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
    if (/[.!?;:](["')\]]*)$/.test(word.text) || group.length >= 12 || word.endSec - group[0].startSec >= 4.2) {
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

/** Long turns use brief phrase gestures and neutral rests; minimal/legacy packs retain their old fallback. */
export function buildConversationCues(line: EpisodeLine, plan: SpriteLine, character: SpriteCharacter,
  speaking: boolean): GestureCue[] | null {
  const generic = ["talk", "open"].filter((name) => paired(character, name));
  const fullPairs = ["talk", "open", "wave", "heart", "point", "think", "listen"].filter((name) => paired(character, name));
  if (plan.slot === null || line.endSec - line.startSec < 4.5 || line.words.length < 4 || !generic.length || fullPairs.length < 2) return null;
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
      const duration = name === "wave" || name === "heart" ? 1.6 : 2.3;
      const limit = Math.min(word.startSec + duration, group.at(-1)!.endSec, line.endSec);
      const ending = group.filter((candidate) => candidate.endSec <= limit + 0.01).at(-1)?.endSec ?? limit;
      if (ending - word.startSec < 0.8) return;
      cues.push({ startSec: word.startSec, endSec: ending, picture: `gesture-${name}` });
      earliest = ending + 0.9;
    } else {
      // A listener reacts near a phrase ending, then returns to the neutral listening expression.
      const start = group.at(-1)!.endSec + 0.12;
      if (start < earliest || start >= line.endSec - 0.45) return;
      const name = /\?|\b(maybe|perhaps|not sure)\b/i.test(text) && paired(character, "think") ? "think" : "listen";
      if (!paired(character, name)) return;
      const end = Math.min(start + 1.35, line.endSec);
      cues.push({ startSec: start, endSec: end, picture: `gesture-${name}` });
      earliest = end + 2.0;
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

/** Small whole-picture shifts/leans preserve anatomy and keep the mouth on its original sprite picture. */
export function conversationBody(timeSec: number, startSec: number, endSec: number, slot: number, speaking: boolean) {
  const time = Math.max(0, timeSec - startSec);
  const presence = Math.min(1, time / 0.5, Math.max(0, (endSec - timeSec) / 0.35));
  const side = slot === 0 ? 1 : -1;
  const phase = time * Math.PI * 2 / (speaking ? 5.7 : 6.4) + slot * 1.1;
  return { x: (speaking ? 1.5 : 0.7) * Math.sin(phase) * presence,
    y: -0.8 * Math.sin(phase * 1.4) * presence,
    rotation: (side * (speaking ? 0.1 : 0.06) + (speaking ? 0.2 : 0.12) * Math.sin(phase)) * presence };
}

/** Imported pictures record small head offsets; compensate for those without warping or blending the image. */
export function pictureAlignment(character: SpriteCharacter, picture: string, width: number, height: number) {
  const [dx, dy] = character.offsets[picture] ?? [0, 0];
  return { x: -(character.mirror ? -1 : 1) * dx / 1280 * width, y: -dy / 1536 * height };
}
