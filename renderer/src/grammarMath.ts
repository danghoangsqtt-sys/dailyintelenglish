/**
 * Phase 88: the pure helpers of the easy-grammar Short (GrammarScene) -- the fixed colour code, which cards and table
 * rows are new on a line (only those animate in), when a scene came on screen and how much the card stack shrinks.
 */
import type { EpisodeLine, GrammarItem } from "./types";

/** The fixed colour code shared by every lesson (D127 brand green for the subject). Text colour on top of each. */
export const CHIP_COLOURS: Record<string, { fill: string; text: string }> = {
  s: { fill: "#1F7A4D", text: "#FFFFFF" },
  v: { fill: "#D64545", text: "#FFFFFF" },
  o: { fill: "#8B5E34", text: "#FFFFFF" },
  be: { fill: "#2F6FD6", text: "#FFFFFF" },
  ing: { fill: "#E8822A", text: "#FFFFFF" },
  v3: { fill: "#F2C230", text: "#151515" },
  modal: { fill: "#8A4FC8", text: "#FFFFFF" },
  have: { fill: "#0E8A8A", text: "#FFFFFF" },
  adj: { fill: "#D9467A", text: "#FFFFFF" },
  plain: { fill: "#E6DFD0", text: "#151515" },
};

export const chipColour = (role?: string) => CHIP_COLOURS[role || "plain"] || CHIP_COLOURS.plain;

/** The scene pill's colour: red for the hook, brand green for the summary, a rotating colour per scene. */
const PILLS = ["#1F7A4D", "#2F6FD6", "#E8822A", "#8A4FC8", "#D9467A", "#0E8A8A"];
export function pillColour(beat: string, scene: number): string {
  if (beat === "hook") return "#D64545";
  if (beat === "summary" || beat === "core" || beat === "follow") return "#1F7A4D";
  if (beat === "quiz") return "#2F6FD6";
  return PILLS[(Math.max(1, scene) - 1) % PILLS.length];
}

/** "PHÂN CẢNH 2 • BẢN CHẤT CỐT LÕI" for a scene, the label alone for the hook / summary / quiz. */
export function pillText(beat: string, scene: number, label: string, vietnamese: boolean): string {
  return beat === "scene" ? `${vietnamese ? "PHÂN CẢNH" : "SCENE"} ${scene} • ${label}` : label;
}

type GrammarLine = Pick<EpisodeLine, "startSec" | "grammar">;
const sameScreen = (a?: GrammarLine["grammar"], b?: GrammarLine["grammar"]) =>
  !!a && !!b && a.scene === b.scene && a.title === b.title && a.label === b.label;
const key = (item: GrammarItem) => JSON.stringify({ ...item, rows: undefined });

/** Whether each card of line `index` was already on screen on the line before (same scene, same card). */
export function cardsSeen(lines: GrammarLine[], index: number): boolean[] {
  const now = lines[index]?.grammar, before = lines[index - 1]?.grammar;
  const old = new Set(sameScreen(now, before) ? (before!.cards || []).map(key) : []);
  return (now?.cards || []).map((item) => old.has(key(item)));
}

/** How many rows of a table the line before already showed (the new ones fill in). */
export function rowsBefore(lines: GrammarLine[], index: number): number {
  const now = lines[index]?.grammar, before = lines[index - 1]?.grammar;
  if (!sameScreen(now, before)) return 0;
  const table = (before!.cards || []).find((item) => item.kind === "table");
  return table?.rows?.length || 0;
}

/** When the scene on screen at line `index` came on screen (its header animates in once). */
export function sceneStart(lines: GrammarLine[], index: number): number {
  let at = index;
  while (at > 0 && sameScreen(lines[at - 1]?.grammar, lines[index]?.grammar)) at -= 1;
  return lines[at]?.startSec ?? 0;
}

/** The card stack's scale so up to four cards fit between the title and the caption. */
export const stackScale = (count: number) => (count <= 2 ? 1 : count === 3 ? 0.9 : 0.8);

/** The quiz countdown on the follow line: 3, 2, 1 then stays at 1. */
export const countdown = (time: number, start: number) => Math.max(1, 3 - Math.floor(Math.max(0, time - start)));

/** An example sentence cut into pieces, the marked words carrying their colour role ("was" -> be). */
export function markedPieces(sentence: string, marks: { text: string; role?: string }[] = []): { text: string; role?: string }[] {
  const wanted = marks.filter((mark) => mark.text.trim()).sort((a, b) => b.text.length - a.text.length);
  if (!wanted.length) return [{ text: sentence }];
  const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pattern = new RegExp(`\\b(${wanted.map((mark) => escape(mark.text.trim())).join("|")})\\b`, "gi");
  const pieces: { text: string; role?: string }[] = [];
  let last = 0;
  for (const match of sentence.matchAll(pattern)) {
    const at = match.index ?? 0;
    if (at > last) pieces.push({ text: sentence.slice(last, at) });
    const mark = wanted.find((item) => item.text.trim().toLowerCase() === match[0].toLowerCase());
    pieces.push({ text: match[0], role: mark?.role || "plain" });
    last = at + match[0].length;
  }
  if (last < sentence.length) pieces.push({ text: sentence.slice(last) });
  return pieces;
}
