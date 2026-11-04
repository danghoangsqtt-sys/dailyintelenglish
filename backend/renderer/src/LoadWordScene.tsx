/**
 * Phase 97 (D159): the "Load the word" Short (9:16). Owner 2026-11-04, on the first version: "đoạn đầu phải có kiểu như 1 bài báo tua nhanh
 * có từ vựng cần nạp vào não xuất hiện". So it opens on news articles flicking past with the word marked in yellow at the same place, then a
 * flash of speed lines; then the wall of the word with its meaning while the voice loops faster and a bar counts up to 100%; then the word
 * large with one example. One card per line, from `line.loadword` (backend/content/load_word.py).
 */
import React from "react";
import { AbsoluteFill, Audio, useCurrentFrame, useVideoConfig } from "remotion";
import { lineAt } from "./flashcardMath";
import { ARTICLE_SEC, articleAt, HOOK_SEC, loadPercent, wallCell, wallColumns, wallMeaningSide, WALL_COLUMNS, WALL_ROWS, wallStep } from "./loadWordMath";
import { resolvedMedia } from "./Presenter";
import { clamp01 } from "./voxMath";
import { aroundWord, wordExplains, wordSize } from "./wordRepeatMath";
import type { EpisodeInputProps, WordCard } from "./types";

const BLUE = "#AEBBFF", YELLOW = "#FFE14D", GREY = "#8E8E8E", MARKER = "#E9EC4A", RED = "#C8352B", INK = "#1C1C1C";
const SANS = "Arial, Helvetica, sans-serif", HEAVY = "'Arial Black', Arial, Helvetica, sans-serif", SERIF = "Georgia, 'Times New Roman', serif";

/** Articles flicking past: the word stays marked at the same place, the text around it changes. */
function Articles({ card, time, unit }: { card: WordCard; time: number; unit: number }) {
  const texts = card.articles?.length ? card.articles : [card.example_en ?? ""];
  const { text, others, step } = articleAt(texts, time);
  const [before, word, after] = aroundWord(text, card.word ?? "");
  const marked = word || card.word || "";
  const size = Math.min(92, Math.floor(620 / Math.max(1, marked.length) / 0.6));
  const drift = ((time % ARTICLE_SEC) / ARTICLE_SEC) * 24 - 12;
  const gap = (marked.length * size * 0.3 + 26) * unit;
  const blurred = (line: string, at: number) => <div key={at} style={{ fontFamily: at === 0 ? HEAVY : SERIF, fontSize: (at === 0 ? 58 : 46) * unit, color: at === 0 ? "#6A6A6A" : "#555", whiteSpace: "nowrap",
    filter: `blur(${(at === 0 ? 2.5 : 3.5) * unit}px)`, opacity: 0.8 }}>{line}</div>;
  return <AbsoluteFill data-load-article={step} style={{ background: "repeating-linear-gradient(178deg, #E9E9E6 0 7px, #EEEEEB 7px 15px)" }}>
    {/* a scrap of small print behind the word */}
    <div style={{ position: "absolute", left: 620 * unit, top: 660 * unit, width: 360 * unit, height: 200 * unit, background: "repeating-linear-gradient(180deg, #BDBDBA 0 3px, transparent 3px 9px)", opacity: 0.55, filter: `blur(${unit}px)` }} />
    <div style={{ position: "absolute", left: -60 * unit, right: -60 * unit, top: (120 + drift) * unit, display: "grid", gap: 44 * unit, overflow: "hidden" }}>{[others[1], others[2], others[3], others[0]].map((line, at) => blurred(line, at === 3 ? 0 : at + 1))}</div>
    <div style={{ position: "absolute", left: -60 * unit, right: -60 * unit, top: (860 - drift) * unit, display: "grid", gap: 44 * unit, overflow: "hidden" }}>{[...others, ...others, ...others].slice(1, 12).map((line, at) => blurred(line, at + 1))}</div>
    <div style={{ position: "absolute", left: 0, right: 0, top: 690 * unit, height: 120 * unit, fontSize: size * unit, lineHeight: `${120 * unit}px`, whiteSpace: "nowrap" }}>
      <div style={{ position: "absolute", right: `calc(50% + ${gap}px)`, fontFamily: SERIF, color: "#3A3A3A", filter: `blur(${0.8 * unit}px)` }}>{before.trim()}</div>
      <div style={{ position: "absolute", left: `calc(50% + ${gap}px)`, fontFamily: SERIF, color: "#3A3A3A", filter: `blur(${0.8 * unit}px)` }}>{after.trim()}</div>
      <div data-load-marked="true" style={{ position: "absolute", left: "50%", transform: "translateX(-50%) rotate(-0.8deg)", background: MARKER, color: INK, fontFamily: HEAVY, padding: `0 ${20 * unit}px` }}>
        {marked}
        <span style={{ position: "absolute", right: -30 * unit, top: -66 * unit, fontFamily: HEAVY, fontSize: 104 * unit, lineHeight: 1, color: RED }}>?</span>
      </div>
    </div>
  </AbsoluteFill>;
}

/** The flash of speed lines between the articles and the wall. */
function Warp({ card, progress, unit }: { card: WordCard; progress: number; unit: number }) {
  return <AbsoluteFill data-load-warp="true" style={{ background: "#3C4C9C", overflow: "hidden" }}>
    <div style={{ position: "absolute", left: "-50%", top: "-50%", width: "200%", height: "200%",
      background: "repeating-conic-gradient(from 0deg at 50% 50%, #E6ECFF 0deg 0.7deg, transparent 0.7deg 3.1deg, #AEBBFF 3.1deg 3.5deg, transparent 3.5deg 7deg)",
      transform: `rotate(${(progress * 14).toFixed(2)}deg) scale(${(1 + progress * 0.5).toFixed(3)})` }} />
    <div style={{ position: "absolute", inset: 0, background: `radial-gradient(circle, rgba(255,255,255,${(0.75 + progress * 0.25).toFixed(2)}) 0%, rgba(255,255,255,${(progress * 0.6).toFixed(2)}) 45%, transparent 75%)` }} />
    <div style={{ position: "absolute", left: 0, right: 0, top: 880 * unit, textAlign: "center", fontFamily: HEAVY, fontSize: 90 * unit, color: "#2A2F55", opacity: 1 - progress,
      filter: `blur(${(2 + progress * 14) * unit}px)`, transform: `scale(${(1 - progress * 0.5).toFixed(3)})` }}>{card.word}</div>
  </AbsoluteFill>;
}

export function LoadWordScene(props: EpisodeInputProps) {
  const frame = useCurrentFrame(), { fps, height } = useVideoConfig();
  const time = frame / fps, unit = height / 1920;
  const index = Math.max(0, lineAt(props.lines, time));
  const line = props.lines[index], card = line?.loadword;
  const loading = card?.beat === "load";
  const loop = props.lines[0];
  const start = loop?.startSec ?? 0;
  const hookLeft = HOOK_SEC - (time - start);
  const wallStart = start + HOOK_SEC;
  const flicks = ARTICLE_SEC * 8;
  const percent = loop ? loadPercent(time, wallStart, loop.endSec) : 100;
  const progress = percent / 100;
  const step = wallStep(progress, Math.max(0, time - wallStart));
  const columns = wallColumns(time - wallStart);
  const show = wordExplains(card?.audience);
  const meaning = show.vi ? card?.meaning_vi : card?.meaning_en;
  const short = `(${(card?.part_of_speech ?? "").slice(0, 1) || "n"}) ${meaning ?? ""}`;
  const since = line ? time - line.startSec : 0;
  const [before, word, after] = aroundWord(card?.example_en ?? "", card?.word ?? "");
  const cell = Math.min(60, Math.floor(310 / Math.max(1, (card?.word ?? "").length) / 0.58));

  return <AbsoluteFill data-short-style="loadword" style={{ overflow: "hidden", background: "#000" }}>
    {!props.soundtrackPath && props.audioPath ? <Audio src={resolvedMedia(props.audioPath)} /> : null}
    {loading && card && hookLeft > 0 ? (time - start < flicks
      ? <Articles card={card} time={time - start} unit={unit} />
      : <Warp card={card} progress={clamp01((time - start - flicks) / Math.max(0.01, HOOK_SEC - flicks))} unit={unit} />) : null}
    {loading && hookLeft <= 0 ? <>
      <div data-load-wall="true" style={{ position: "absolute", left: 30 * unit, right: 30 * unit, top: 40 * unit, height: 1840 * unit, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
        {Array.from({ length: WALL_ROWS }, (_, row) => <React.Fragment key={row}>
          <div style={{ display: "grid", gridTemplateColumns: `repeat(${WALL_COLUMNS}, 1fr)` }}>
            {Array.from({ length: WALL_COLUMNS }, (_, column) => {
              const state = wallCell(row, column, step, progress);
              return <div key={column} style={{ textAlign: "center", fontFamily: SANS, fontWeight: 800, fontStyle: "italic", fontSize: cell * unit, lineHeight: 1.05, whiteSpace: "nowrap",
                color: state.lit ? YELLOW : "#FFF", opacity: column < columns && state.shown ? 1 : 0 }}>{card?.word}</div>;
            })}
          </div>
          {row < WALL_ROWS - 1 ? <div style={{ textAlign: wallMeaningSide(row), padding: `0 ${40 * unit}px`, fontFamily: SANS, fontWeight: 700, color: "#FFF", fontSize: 30 * unit, lineHeight: 1,
            opacity: columns > 1 ? 1 : 0 }}>{short}</div> : null}
        </React.Fragment>)}
      </div>
      <div data-load-centre="true" style={{ position: "absolute", left: 190 * unit, width: 700 * unit, top: 610 * unit, background: "#000", borderRadius: 20 * unit, padding: `${10 * unit}px 0`,
        display: "grid", justifyItems: "center", gap: 4 * unit, textAlign: "center" }}>
        <div style={{ fontFamily: SANS, fontWeight: 800, fontStyle: "italic", color: BLUE, fontSize: wordSize(card?.word ?? "", 660) * unit, lineHeight: 1.05 }}>{card?.word}</div>
        <div style={{ fontFamily: SERIF, fontStyle: "italic", color: BLUE, fontSize: 40 * unit }}>{card?.ipa}</div>
        <div data-word-meaning="true" style={{ fontFamily: SANS, fontWeight: 800, color: BLUE, fontSize: 42 * unit }}>{meaning}</div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 1240 * unit, height: 66 * unit, background: "#333" }}>
        <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${percent}%`, background: GREY }} />
        <div data-load-percent={percent} style={{ position: "absolute", left: 72 * unit, top: 0, bottom: 0, display: "flex", alignItems: "center", fontFamily: SANS, fontWeight: 800, color: "#FFF", fontSize: 36 * unit }}>
          {card?.audience === "international" ? "Loading into memory" : "Nạp từ vào trí nhớ"}: {percent}%</div>
      </div>
    </> : null}
    {!loading ? <div data-load-final="true" style={{ position: "absolute", left: 72 * unit, width: 936 * unit, top: 470 * unit, display: "grid", justifyItems: "center", gap: 22 * unit, textAlign: "center" }}>
      <div style={{ fontFamily: HEAVY, fontStyle: "italic", color: "#FFF", fontSize: wordSize(card?.word ?? "") * unit, lineHeight: 1.05 }}>{card?.word}</div>
      <div style={{ fontFamily: SERIF, fontStyle: "italic", color: "#DDD", fontSize: 50 * unit }}>{card?.ipa}</div>
      {show.vi && card?.meaning_vi ? <div data-word-vi="true" style={{ fontFamily: SANS, fontWeight: 800, color: "#FFF", fontSize: 54 * unit }}>({card?.part_of_speech?.slice(0, 1)}) {card.meaning_vi}</div> : null}
      {show.en && card?.meaning_en ? <div data-word-en="true" style={{ fontFamily: SANS, fontWeight: 700, color: "#DDD", fontSize: 42 * unit }}>{card.meaning_en}</div> : null}
      {card?.beat === "example" ? <div data-load-example="true" style={{ display: "grid", gap: 14 * unit, marginTop: 34 * unit, opacity: clamp01(since / 0.25) }}>
        <div style={{ fontFamily: SANS, fontStyle: "italic", fontWeight: 700, color: "#FFF", fontSize: 50 * unit, lineHeight: 1.25 }}>{before}<span style={{ color: YELLOW }}>{word}</span>{after}</div>
        {show.vi && card?.example_vi ? <div style={{ fontFamily: SANS, color: "#CCC", fontSize: 40 * unit, lineHeight: 1.25 }}>{card.example_vi}</div> : null}
      </div> : null}
    </div> : null}
  </AbsoluteFill>;
}
