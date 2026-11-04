/**
 * Phase 96 (task 96.6): the Basic vs Advanced Short (9:16) -- owner 2026-11-04: nobody on screen, the content is the star. One
 * full-frame picture shows what the phrase means; a red and a blue label carry the two phrases, the advanced one grows big and
 * its meaning comes in below. One card per line, from `line.levelup` (backend/content/level_up.py).
 */
import React from "react";
import { AbsoluteFill, Audio, Img, useCurrentFrame, useVideoConfig } from "remotion";
import { lineAt } from "./flashcardMath";
import { resolvedMedia } from "./Presenter";
import { clamp01 } from "./voxMath";
import { easeOutBack } from "./voxMotion";
import { levelPhraseSize, levelSaying, wordExplains } from "./wordRepeatMath";
import type { EpisodeInputProps } from "./types";

const RED = "#E8302A", BLUE = "#1E9BE9", INK = "#14231C", YELLOW = "#FFE14D";
const SANS = "Arial, Helvetica, sans-serif", HEAVY = "'Arial Black', Arial, Helvetica, sans-serif";

export function LevelUpScene(props: EpisodeInputProps) {
  const frame = useCurrentFrame(), { fps, height } = useVideoConfig();
  const time = frame / fps, unit = height / 1920;
  const index = Math.max(0, lineAt(props.lines, time));
  const line = props.lines[index], card = line?.levelup;
  const advanced = card?.beat === "advanced";
  const since = line ? time - line.startSec : 0;
  const pairStart = props.lines.find((item) => item.levelup?.number === card?.number)?.startSec ?? 0;
  const pairEnd = [...props.lines].reverse().find((item) => item.levelup?.number === card?.number)?.endSec ?? pairStart + 1;
  const show = wordExplains(card?.audience);
  const saying = levelSaying(props.lines.slice(0, index + 1).filter((item) => item.levelup?.number === card?.number && item.levelup?.beat === "advanced").length);
  const pulse = advanced ? 1 + (saying === 2 ? 0.08 : 0.04) * Math.max(0, 1 - since / 0.3) : 1;

  return <AbsoluteFill data-short-style="levelup" style={{ overflow: "hidden", background: "linear-gradient(170deg, #0F3D2A, #1F7A4D 55%, #0B2A1E)" }}>
    {!props.soundtrackPath && props.audioPath ? <Audio src={resolvedMedia(props.audioPath)} /> : null}
    {card?.pictureUrl ? <Img data-word-picture="true" src={resolvedMedia(card.pictureUrl)} style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover",
      transform: `scale(${(1.02 + 0.06 * clamp01((time - pairStart) / Math.max(1, pairEnd - pairStart))).toFixed(4)})` }} /> : null}
    <div style={{ position: "absolute", left: 72 * unit, width: 936 * unit, top: 240 * unit, display: "grid", gap: 16 * unit, justifyItems: "start" }}>
      <div style={{ background: RED, color: "#FFF", fontFamily: HEAVY, fontSize: 30 * unit, borderRadius: 14 * unit, padding: `${6 * unit}px ${18 * unit}px` }}>BASIC</div>
      <div data-level-basic="true" style={{ background: "#FFF", color: INK, fontFamily: SANS, fontWeight: 800, fontSize: 52 * unit, lineHeight: 1.15, borderRadius: 14 * unit,
        padding: `${10 * unit}px ${22 * unit}px`, transform: `scale(${Math.max(0, advanced ? 1 : easeOutBack(since / 0.3)).toFixed(4)})`, transformOrigin: "left center",
        opacity: advanced ? 0.75 : 1 }}>{card?.basic}</div>
    </div>
    {advanced ? <div data-level-advanced="true" style={{ position: "absolute", left: 72 * unit, width: 936 * unit, top: 880 * unit, display: "grid", gap: 10 * unit, justifyItems: "start" }}>
      <div style={{ background: BLUE, color: "#FFF", fontFamily: HEAVY, fontSize: 30 * unit, borderRadius: 14 * unit, padding: `${6 * unit}px ${18 * unit}px` }}>ADVANCED</div>
      <div style={{ background: INK, color: YELLOW, fontFamily: HEAVY, fontSize: levelPhraseSize(card?.advanced ?? "") * unit, lineHeight: 1.1, borderRadius: 18 * unit,
        padding: `${14 * unit}px ${26 * unit}px`, transform: `scale(${(pulse * Math.max(0, saying === 1 ? easeOutBack(since / 0.3) : 1)).toFixed(4)})`, transformOrigin: "left center" }}>{card?.advanced}</div>
    </div> : null}
    {advanced && ((show.vi && card?.meaning_vi) || (show.en && card?.meaning_en)) ? <div data-level-meaning="true" style={{ position: "absolute", left: 72 * unit, width: 780 * unit, top: 1130 * unit,
      background: "rgba(255,255,255,0.94)", borderRadius: 20 * unit, padding: `${16 * unit}px ${24 * unit}px`, boxSizing: "border-box", display: "grid", gap: 8 * unit,
      opacity: clamp01(since / 0.25) + (saying === 2 ? 1 : 0) }}>
      {show.vi && card?.meaning_vi ? <div data-word-vi="true" style={{ fontFamily: SANS, fontWeight: 800, fontSize: 40 * unit, color: "#C2392D" }}>{card.meaning_vi}</div> : null}
      {show.en && card?.meaning_en ? <div data-word-en="true" style={{ fontFamily: SANS, fontWeight: 700, fontSize: 30 * unit, color: INK }}>{card.meaning_en}</div> : null}
    </div> : null}
    <div style={{ position: "absolute", left: 72 * unit, top: 170 * unit, color: INK, fontFamily: SANS, fontWeight: 800, fontSize: 26 * unit,
      background: "rgba(255,255,255,0.85)", borderRadius: 10 * unit, padding: `${4 * unit}px ${12 * unit}px` }}>
      DAILY BEYOND ENGLISH · {props.cefrLevel}</div>
  </AbsoluteFill>;
}
