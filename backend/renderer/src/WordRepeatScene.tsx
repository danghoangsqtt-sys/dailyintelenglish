/**
 * Phase 96 (D147-D151): the Word of the day Short (9:16) -- the word's picture fills the frame, the word with its IPA and
 * explanation stands in the middle, a copy of the word appears with every repetition, and the example sentence comes last
 * with the word marked. One card per line, from `line.wordday` (backend/content/word_repeat.py).
 */
import React from "react";
import { AbsoluteFill, Audio, Img, useCurrentFrame, useVideoConfig } from "remotion";
import { lineAt } from "./flashcardMath";
import { resolvedMedia } from "./Presenter";
import { clamp01 } from "./voxMath";
import { easeOutBack } from "./voxMotion";
import { aroundWord, copiesAt, copyCentre, COPY_PLACES, wordExplains, wordSize } from "./wordRepeatMath";
import type { EpisodeInputProps } from "./types";

const YELLOW = "#FFE14D", GREEN = "#B6F36A", RED = "#E8483B", INK = "#14231C";
const SANS = "Arial, Helvetica, sans-serif", HEAVY = "'Arial Black', Arial, Helvetica, sans-serif";
const outline = (unit: number, width = 5) => ({ WebkitTextStroke: `${width * unit}px #111`, paintOrder: "stroke fill" as const,
  textShadow: `0 ${6 * unit}px ${18 * unit}px rgba(0,0,0,0.55)` });

export function WordRepeatScene(props: EpisodeInputProps) {
  const frame = useCurrentFrame(), { fps, height } = useVideoConfig();
  const time = frame / fps, unit = height / 1920;
  const index = Math.max(0, lineAt(props.lines, time));
  const line = props.lines[index], card = line?.wordday ?? props.lines[0]?.wordday;
  const since = line ? time - line.startSec : 0;
  const show = wordExplains(card?.audience);
  const example = card?.beat === "example" && line?.wordday?.beat === "example";
  const copies = copiesAt(line?.wordday?.repeat ?? 0);
  const pulse = example ? 1 : 1 + 0.07 * Math.max(0, 1 - since / 0.25);
  const picture = card?.pictureUrl;
  const [before, word, after] = aroundWord(card?.example_en ?? "", card?.word ?? "");

  return <AbsoluteFill data-short-style="wordday" style={{ overflow: "hidden", background: "linear-gradient(170deg, #0F3D2A, #1F7A4D 55%, #0B2A1E)" }}>
    {!props.soundtrackPath && props.audioPath ? <Audio src={resolvedMedia(props.audioPath)} /> : null}
    {picture ? <Img data-word-picture="true" src={resolvedMedia(picture)} style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover",
      transform: `scale(${(1.02 + 0.05 * clamp01(time / Math.max(1, props.durationSeconds ?? 1))).toFixed(4)})` }} /> : null}
    {COPY_PLACES.slice(0, example ? 0 : copies).map(([x, y, size], at) => {
      const pop = at === copies - 1 ? easeOutBack(since / 0.3) : 1;
      const fitted = Math.min(size, wordSize(card?.word ?? "", 620));
      return <div key={at} data-word-copy={at + 1} style={{ position: "absolute", left: copyCentre(x, card?.word ?? "", fitted) * unit, top: y * unit, whiteSpace: "nowrap",
        fontFamily: HEAVY, color: "#FFF", fontSize: fitted * unit, ...outline(unit, 4),
        transform: `translate(-50%, -50%) scale(${Math.max(0, pop).toFixed(4)})` }}>{card?.word}</div>;
    })}
    <div style={{ position: "absolute", left: 72 * unit, width: 936 * unit, top: 690 * unit, height: 360 * unit, display: "grid", justifyItems: "center",
      alignContent: "center", gap: 10 * unit, textAlign: "center" }}>
      <div data-word-main="true" style={{ fontFamily: HEAVY, color: YELLOW, fontSize: wordSize(card?.word ?? "") * unit, lineHeight: 1.05,
        transform: `scale(${pulse.toFixed(4)})`, ...outline(unit, 7) }}>{card?.word}</div>
      {card?.ipa ? <div style={{ fontFamily: SANS, fontWeight: 700, color: "#FFF", fontSize: 50 * unit, ...outline(unit, 4) }}>{card.ipa}</div> : null}
      {show.en && card?.meaning_en ? <div data-word-en="true" style={{ fontFamily: SANS, fontWeight: 800, color: "#FFF", fontSize: 44 * unit, lineHeight: 1.15, ...outline(unit, 4) }}>
        {card.meaning_en}</div> : null}
      {show.vi && card?.meaning_vi ? <div data-word-vi="true" style={{ fontFamily: SANS, fontWeight: 800, color: GREEN, fontSize: 50 * unit, lineHeight: 1.15, ...outline(unit, 3) }}>
        {card.meaning_vi}</div> : null}
    </div>
    {example ? <div data-word-example="true" style={{ position: "absolute", left: 72 * unit, width: 780 * unit, top: 250 * unit, display: "grid", gap: 20 * unit,
      opacity: clamp01(since / 0.2), transform: `translateY(${((1 - clamp01(since / 0.25)) * 24 * unit).toFixed(1)}px)` }}>
      <div style={{ justifySelf: "start", background: "#FFF", color: INK, fontFamily: SANS, fontWeight: 800, fontSize: 50 * unit, lineHeight: 1.2,
        padding: `${14 * unit}px ${22 * unit}px`, borderRadius: 12 * unit }}>
        {before}<span data-word-mark="true" style={{ color: RED }}>{word}</span>{after}</div>
      {show.vi && card?.example_vi ? <div style={{ justifySelf: "start", background: "#FFF", color: INK, fontFamily: SANS, fontWeight: 700, fontSize: 44 * unit, lineHeight: 1.2,
        padding: `${12 * unit}px ${22 * unit}px`, borderRadius: 12 * unit }}>{card.example_vi}</div> : null}
    </div> : null}
    <div style={{ position: "absolute", left: 72 * unit, top: 170 * unit, color: "#FFF", fontFamily: SANS, fontWeight: 800, fontSize: 26 * unit, ...outline(unit, 3) }}>
      DAILY BEYOND ENGLISH · {props.cefrLevel}</div>
  </AbsoluteFill>;
}
