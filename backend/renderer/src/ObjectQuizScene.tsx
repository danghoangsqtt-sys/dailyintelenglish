/**
 * Phase 96 (task 96.5): the "What is this called?" Short (9:16) -- one object on a plain colour, the question above it, a
 * circle counting 1-2-3 in the silence after the question, then the name with its IPA and explanation.
 * One card per line, from `line.whatis` (backend/content/object_quiz.py).
 */
import React from "react";
import { AbsoluteFill, Audio, Img, useCurrentFrame, useVideoConfig } from "remotion";
import { lineAt } from "./flashcardMath";
import { resolvedMedia } from "./Presenter";
import { clamp01 } from "./voxMath";
import { easeOutBack } from "./voxMotion";
import { countAt, wordExplains } from "./wordRepeatMath";
import type { EpisodeInputProps } from "./types";

const INK = "#14231C", SKY = "#BFE8F6", GREEN = "#1F7A4D";
const SANS = "Arial, Helvetica, sans-serif", HEAVY = "'Arial Black', Arial, Helvetica, sans-serif";

export function ObjectQuizScene(props: EpisodeInputProps) {
  const frame = useCurrentFrame(), { fps, height } = useVideoConfig();
  const time = frame / fps, unit = height / 1920;
  const index = Math.max(0, lineAt(props.lines, time));
  const line = props.lines[index], card = line?.whatis;
  const answer = card?.beat === "answer";
  const count = !answer && line ? countAt(time, line.endSec, (card?.pause_after_ms ?? 0) / 1000) : null;
  const since = line ? time - line.startSec : 0;
  const show = wordExplains(card?.audience);
  const askStart = answer ? props.lines[index - 1]?.startSec ?? time : line?.startSec ?? time;
  const pop = easeOutBack((time - askStart) / 0.35);

  return <AbsoluteFill data-short-style="whatis" style={{ overflow: "hidden", background: SKY }}>
    {!props.soundtrackPath && props.audioPath ? <Audio src={resolvedMedia(props.audioPath)} /> : null}
    {card?.pictureUrl ? <Img data-word-picture="true" src={resolvedMedia(card.pictureUrl)} style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover",
      transform: `scale(${(0.9 + 0.1 * Math.max(0, pop)).toFixed(4)})` }} /> : null}
    <div style={{ position: "absolute", left: 72 * unit, width: 936 * unit, top: 250 * unit, textAlign: "center", fontFamily: HEAVY, color: INK, fontSize: 66 * unit,
      lineHeight: 1.1 }}>What is this called?</div>
    {count !== null ? <div data-quiz-count={count} style={{ position: "absolute", left: 415 * unit, top: 1040 * unit, width: 250 * unit, height: 250 * unit, borderRadius: "50%",
      display: "grid", placeItems: "center", background: "rgba(255,255,255,0.72)", border: `${10 * unit}px solid ${GREEN}`, fontFamily: HEAVY, color: GREEN, fontSize: 130 * unit,
      transform: `scale(${(1.12 - 0.12 * clamp01((time - (line?.endSec ?? 0)) % 1 / 0.3)).toFixed(4)})` }}>{count}</div> : null}
    {answer ? <div data-quiz-answer="true" style={{ position: "absolute", left: 72 * unit, width: 780 * unit, top: 980 * unit, display: "grid", justifyItems: "center",
      gap: 8 * unit, textAlign: "center", marginLeft: 78 * unit, background: "rgba(255,255,255,0.9)", borderRadius: 28 * unit, padding: `${20 * unit}px ${24 * unit}px`,
      boxSizing: "border-box", boxShadow: "0 12px 30px rgba(20,35,28,0.18)", transform: `scale(${Math.max(0, easeOutBack(since / 0.3)).toFixed(4)})` }}>
      <div style={{ fontFamily: HEAVY, fontSize: 84 * unit, lineHeight: 1.05, color: GREEN }}>{card?.word}</div>
      {card?.ipa ? <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 46 * unit, color: INK }}>{card.ipa}</div> : null}
      {show.vi && card?.meaning_vi ? <div data-word-vi="true" style={{ fontFamily: SANS, fontWeight: 800, fontSize: 46 * unit, color: "#C2392D" }}>{card.meaning_vi}</div> : null}
      {show.en && card?.meaning_en ? <div data-word-en="true" style={{ fontFamily: SANS, fontWeight: 700, fontSize: 38 * unit, color: INK }}>{card.meaning_en}</div> : null}
    </div> : null}
    <div style={{ position: "absolute", left: 72 * unit, top: 170 * unit, color: INK, fontFamily: SANS, fontWeight: 800, fontSize: 26 * unit }}>
      DAILY BEYOND ENGLISH · {props.cefrLevel} · {card?.number ?? 1}/{props.lines.length / 2}</div>
  </AbsoluteFill>;
}
