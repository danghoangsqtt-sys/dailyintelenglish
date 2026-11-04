/**
 * Phase 81 (owner 2026-10-28): the vocabulary flashcard Short (9:16) on beige paper -- a header pill with the deck's
 * topic and part, a "FLASHCARD TỪ VỰNG" tag, a cover card, then one card per word (N / total, the word, its part of
 * speech, IPA and a green Vietnamese meaning card) sliding in like a deck with the neighbours peeking at the sides.
 */
import React from "react";
import { AbsoluteFill, Audio, useCurrentFrame, useVideoConfig } from "remotion";
import { titleParts } from "./Brand";
import { resolvedMedia } from "./Presenter";
import { deckCards, deckEntry, lineAt, partNumber, posLabel, slideIn } from "./flashcardMath";
import { GREEN, INK, MUTED, Paper } from "./SlowPodScene";
import type { EpisodeInputProps } from "./types";

const SANS = "'Montserrat', 'Arial Black', Arial, Helvetica, sans-serif";
const CARD = { left: 150, top: 520, width: 780, height: 860 };

function Card({ unit, children, style = {} }: { unit: number; children?: React.ReactNode; style?: React.CSSProperties }) {
  return <div style={{ position: "absolute", left: CARD.left * unit, top: CARD.top * unit, width: CARD.width * unit, height: CARD.height * unit,
    boxSizing: "border-box", borderRadius: 48 * unit, background: "#FFFFFF", border: `${3 * unit}px solid rgba(31,122,77,0.35)`,
    boxShadow: "0 24px 60px rgba(60,45,20,0.18)", display: "flex", flexDirection: "column", alignItems: "center", ...style }}>{children}</div>;
}

export function FlashcardScene(props: EpisodeInputProps) {
  const frame = useCurrentFrame(), { fps, height } = useVideoConfig();
  const time = frame / fps, unit = height / 1920;
  const cards = deckCards(props.lines);
  const current = lineAt(props.lines, time);
  const cardAt = cards.findIndex((card) => card.line === current);
  const name = titleParts(props.title || "").name || props.topic;
  const topic = name.replace(/\s*\((P\s*\d+)\)\s*$/i, "").trim() || props.topic;
  const part = partNumber(name) ?? partNumber(props.topic);
  const afterDeck = cards.length > 0 && current > cards[cards.length - 1].line;
  const start = current >= 0 ? props.lines[current].startSec : 0;
  const enter = slideIn(time, start);
  return <AbsoluteFill data-short-style="flashcards" style={{ overflow: "hidden" }}>
    <Paper />
    {!props.soundtrackPath ? <Audio src={resolvedMedia(props.audioPath)} /> : null}
    <div style={{ position: "absolute", left: 70 * unit, right: 70 * unit, top: 270 * unit, display: "grid", justifyItems: "center", gap: 18 * unit }}>
      <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 56 * unit, color: INK, background: "rgba(255,255,255,0.75)",
        border: `${4 * unit}px solid ${GREEN}`, borderRadius: 999, padding: `${14 * unit}px ${40 * unit}px`, textAlign: "center" }}>
        {topic}{part ? ` (P${part})` : ""}</div>
      <span style={{ fontFamily: SANS, fontWeight: 800, fontSize: 26 * unit, letterSpacing: "0.1em", color: GREEN, background: "#FFFFFF",
        borderRadius: 999, padding: `${8 * unit}px ${22 * unit}px` }}>FLASHCARD TỪ VỰNG</span>
    </div>
    {/* the neighbours of the deck, peeking at the sides */}
    {cards.length ? [-1, 1].map((side) => <Card key={side} unit={unit} style={{ transform: `translateX(${side * 600 * unit}px) rotate(${side * 5}deg) scale(0.84)`,
      opacity: 0.7 }} />) : null}
    {cardAt >= 0 ? (() => {
      const entry = deckEntry(props.learning, cards[cardAt].word);
      return <Card unit={unit} style={{ transform: `translateX(${((1 - enter) * 700 * unit).toFixed(1)}px) rotate(${((1 - enter) * 6).toFixed(2)}deg)` }}>
        <span data-flashcard-count="true" style={{ marginTop: 56 * unit, fontFamily: SANS, fontWeight: 800, fontSize: 34 * unit, color: GREEN,
          background: "rgba(31,122,77,0.1)", borderRadius: 999, padding: `${8 * unit}px ${24 * unit}px` }}>
          {String(cardAt + 1).padStart(2, "0")} / {String(cards.length).padStart(2, "0")}</span>
        <div style={{ marginTop: 120 * unit, fontFamily: SANS, fontWeight: 800, color: INK, textAlign: "center", padding: `0 ${40 * unit}px`,
          fontSize: (entry.word.length > 14 ? 76 : 100) * unit, lineHeight: 1.1 }}>{entry.word}</div>
        {entry.partOfSpeech ? <div style={{ marginTop: 20 * unit, fontFamily: SANS, fontWeight: 800, color: GREEN, fontSize: 64 * unit }}>
          {posLabel(entry.partOfSpeech)}</div> : null}
        {entry.ipa ? <div style={{ marginTop: 14 * unit, fontFamily: "'Segoe UI', 'Arial Unicode MS', Arial, sans-serif", color: MUTED,
          fontSize: 50 * unit }}>{entry.ipa}</div> : null}
        {entry.meaningVi ? <div data-flashcard-meaning="true" style={{ position: "absolute", left: 30 * unit, right: 30 * unit, bottom: 30 * unit,
          minHeight: 190 * unit, boxSizing: "border-box", borderRadius: 36 * unit, background: "#E9F2E2", border: `${3 * unit}px solid rgba(31,122,77,0.3)`,
          display: "grid", placeItems: "center", padding: `${20 * unit}px ${30 * unit}px`, fontFamily: SANS, fontWeight: 800, color: "#3E5A1E",
          fontSize: (entry.meaningVi.length > 26 ? 50 : 62) * unit, textAlign: "center", lineHeight: 1.2 }}>{entry.meaningVi}</div> : null}
      </Card>;
    })() : <Card unit={unit} style={{ justifyContent: "center", gap: 26 * unit, textAlign: "center", padding: `0 ${50 * unit}px`, opacity: enter }}>
      <div style={{ fontFamily: SANS, fontWeight: 800, color: INK, fontSize: 56 * unit }}>{afterDeck ? "Follow for more words" : "Từ vựng chủ đề:"}</div>
      <div style={{ fontFamily: SANS, fontWeight: 800, color: GREEN, fontSize: (topic.length > 22 ? 76 : 96) * unit, lineHeight: 1.1 }}>
        {afterDeck ? "Daily Beyond English" : topic}</div>
      {!afterDeck && part ? <div style={{ fontFamily: SANS, fontWeight: 800, color: INK, fontSize: 56 * unit }}>Phần {part}</div> : null}
      {!afterDeck && cards.length ? <div style={{ fontFamily: SANS, fontWeight: 700, color: MUTED, fontSize: 38 * unit }}>{cards.length} từ</div> : null}
    </Card>}
  </AbsoluteFill>;
}
