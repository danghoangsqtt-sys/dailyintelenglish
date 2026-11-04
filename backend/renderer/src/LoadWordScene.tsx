/**
 * Phase 97 (D159): the "Load the word" Short (9:16) -- a wall of the word on black while its voice loops faster and faster and a bar
 * counts up to 100%, the word in the middle with its IPA and meaning; then the word large and one example.
 * One card per line, from `line.loadword` (backend/content/load_word.py).
 */
import React from "react";
import { AbsoluteFill, Audio, useCurrentFrame, useVideoConfig } from "remotion";
import { lineAt } from "./flashcardMath";
import { loadPercent, WALL_COLUMNS, WALL_ROWS, wallCell, wallStep } from "./loadWordMath";
import { resolvedMedia } from "./Presenter";
import { clamp01 } from "./voxMath";
import { aroundWord, wordExplains, wordSize } from "./wordRepeatMath";
import type { EpisodeInputProps } from "./types";

const BLUE = "#AEBBFF", YELLOW = "#FFE14D", GREY = "#8E8E8E";
const SANS = "Arial, Helvetica, sans-serif", HEAVY = "'Arial Black', Arial, Helvetica, sans-serif";

export function LoadWordScene(props: EpisodeInputProps) {
  const frame = useCurrentFrame(), { fps, height } = useVideoConfig();
  const time = frame / fps, unit = height / 1920;
  const index = Math.max(0, lineAt(props.lines, time));
  const line = props.lines[index], card = line?.loadword;
  const loading = card?.beat === "load";
  const loop = props.lines[0];
  const percent = loop ? loadPercent(time, loop.startSec, loop.endSec) : 100;
  const progress = percent / 100;
  const step = wallStep(progress, loop ? time - loop.startSec : 0);
  const show = wordExplains(card?.audience);
  const meaning = show.vi ? card?.meaning_vi : card?.meaning_en;
  const since = line ? time - line.startSec : 0;
  const [before, word, after] = aroundWord(card?.example_en ?? "", card?.word ?? "");
  const cell = Math.min(62, Math.floor(300 / Math.max(1, (card?.word ?? "").length) / 0.62));

  return <AbsoluteFill data-short-style="loadword" style={{ overflow: "hidden", background: "#000" }}>
    {!props.soundtrackPath && props.audioPath ? <Audio src={resolvedMedia(props.audioPath)} /> : null}
    {loading ? <>
      <div data-load-wall="true" style={{ position: "absolute", left: 40 * unit, right: 40 * unit, top: 240 * unit, height: 970 * unit, display: "grid", gridTemplateColumns: `repeat(${WALL_COLUMNS}, 1fr)`, alignContent: "space-between" }}>
        {Array.from({ length: WALL_ROWS * WALL_COLUMNS }, (_, at) => {
          const row = Math.floor(at / WALL_COLUMNS), column = at % WALL_COLUMNS;
          const state = wallCell(row, column, step, progress);
          return <div key={at} style={{ textAlign: "center", fontFamily: HEAVY, fontSize: cell * unit, lineHeight: 1.1, fontStyle: "italic", whiteSpace: "nowrap",
            color: state.lit ? YELLOW : "#FFF", opacity: state.shown ? 1 : 0 }}>{card?.word}</div>;
        })}
      </div>
      <div data-load-centre="true" style={{ position: "absolute", left: 40 * unit, width: 1000 * unit, top: 590 * unit, background: "#000", borderRadius: 20 * unit, padding: `${14 * unit}px 0`,
        display: "grid", justifyItems: "center", gap: 6 * unit, textAlign: "center" }}>
        <div style={{ fontFamily: HEAVY, fontStyle: "italic", color: BLUE, fontSize: wordSize(card?.word ?? "", 740) * unit, lineHeight: 1.05 }}>{card?.word}</div>
        <div style={{ fontFamily: SANS, color: BLUE, fontSize: 40 * unit }}>{card?.ipa}</div>
        <div data-word-meaning="true" style={{ fontFamily: SANS, fontWeight: 800, color: "#FFF", fontSize: 44 * unit }}>{meaning}</div>
      </div>
      <div style={{ position: "absolute", left: 72 * unit, width: 792 * unit, top: 1240 * unit, height: 62 * unit, background: "#333", borderRadius: 10 * unit, overflow: "hidden" }}>
        <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${percent}%`, background: GREY }} />
        <div data-load-percent={percent} style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", fontFamily: SANS, fontWeight: 800, color: "#FFF", fontSize: 34 * unit }}>
          {card?.audience === "international" ? "Loading into memory" : "Nạp từ vào trí nhớ"}: {percent}%</div>
      </div>
    </> : <div data-load-final="true" style={{ position: "absolute", left: 72 * unit, width: 936 * unit, top: 470 * unit, display: "grid", justifyItems: "center", gap: 22 * unit, textAlign: "center" }}>
      <div style={{ fontFamily: HEAVY, fontStyle: "italic", color: "#FFF", fontSize: wordSize(card?.word ?? "") * unit, lineHeight: 1.05 }}>{card?.word}</div>
      <div style={{ fontFamily: SANS, color: "#DDD", fontSize: 50 * unit }}>{card?.ipa}</div>
      {show.vi && card?.meaning_vi ? <div data-word-vi="true" style={{ fontFamily: SANS, fontWeight: 800, color: "#FFF", fontSize: 54 * unit }}>({card?.part_of_speech?.slice(0, 1)}) {card.meaning_vi}</div> : null}
      {show.en && card?.meaning_en ? <div data-word-en="true" style={{ fontFamily: SANS, fontWeight: 700, color: "#DDD", fontSize: 42 * unit }}>{card.meaning_en}</div> : null}
      {card?.beat === "example" ? <div data-load-example="true" style={{ display: "grid", gap: 14 * unit, marginTop: 34 * unit, opacity: clamp01(since / 0.25) }}>
        <div style={{ fontFamily: SANS, fontStyle: "italic", fontWeight: 700, color: "#FFF", fontSize: 50 * unit, lineHeight: 1.25 }}>{before}<span style={{ color: YELLOW }}>{word}</span>{after}</div>
        {show.vi && card?.example_vi ? <div style={{ fontFamily: SANS, color: "#CCC", fontSize: 40 * unit, lineHeight: 1.25 }}>{card.example_vi}</div> : null}
      </div> : null}
    </div>}
  </AbsoluteFill>;
}
