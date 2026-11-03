/**
 * Phase 88 (D127): the easy-grammar Short (9:16) on paper -- a coloured scene pill ("PHÂN CẢNH 2 • …"), a bold title
 * and subtitle, rounded cards that stack down as the narration reaches them (fixed colour code: BE blue, -ing orange,
 * V3 a yellow sticker, modal purple, S/V/O), the red "forget them" stamp over the rote formulas, a summary table that
 * fills row by row, and the spoken line as a karaoke caption. One beat per line, from `line.grammar`
 * (backend/content/grammar_lesson.py); the Bangers / Patrick Hand fonts are loaded by RootsScene.
 */
import React, { useMemo } from "react";
import { AbsoluteFill, Audio, useCurrentFrame, useVideoConfig } from "remotion";
import { activeTokenIndex, buildKaraokeTokens, withScriptPunctuation } from "./karaoke";
import { lineAt, slideIn } from "./flashcardMath";
import { cardsSeen, chipColour, countdown, fitScale, markedPieces, pillColour, pillText, rowsBefore, sceneStart } from "./grammarMath";
import { resolvedMedia } from "./Presenter";
import { isVietnamese } from "./rootsMath";
import { GREEN, INK, MUTED, Paper } from "./SlowPodScene";
import type { EpisodeInputProps, EpisodeLine, GrammarChip, GrammarItem } from "./types";

const LETTERS = "'Bangers', 'Montserrat', 'Arial Black', sans-serif";
const HAND = "'Patrick Hand', 'Segoe Print', 'Comic Sans MS', sans-serif";
const SANS = "'Montserrat', 'Arial Black', Arial, Helvetica, sans-serif";
const YELLOW = "#F2C230", RED = "#D64545", PINK = "#D9467A";

const cardBox = (unit: number, extra: React.CSSProperties = {}): React.CSSProperties => ({
  background: "#FFFFFF", borderRadius: 30 * unit, padding: `${26 * unit}px ${34 * unit}px`,
  boxShadow: `0 ${10 * unit}px ${28 * unit}px rgba(60, 45, 20, 0.16)`, ...extra,
});

function ChipView({ chip, unit, size = 52 }: { chip: GrammarChip; unit: number; size?: number }) {
  const colour = chipColour(chip.role);
  return <span data-grammar-chip={chip.role} style={{ display: "inline-block", background: colour.fill, color: colour.text, fontFamily: SANS,
    fontWeight: 900, fontSize: size * unit, lineHeight: 1.1, padding: `${10 * unit}px ${22 * unit}px`, borderRadius: 18 * unit,
    boxShadow: chip.role === "v3" ? `0 ${4 * unit}px 0 #C99A12` : "none", whiteSpace: "nowrap" }}>{chip.text}</span>;
}

function Joined({ chips, unit, sign = "+", result }: { chips: GrammarChip[]; unit: number; sign?: string; result?: GrammarChip }) {
  const symbol = (text: string) => <span style={{ fontFamily: SANS, fontWeight: 900, color: INK, fontSize: 48 * unit }}>{text}</span>;
  return <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", alignItems: "center", gap: 16 * unit }}>
    {chips.map((chip, at) => <React.Fragment key={at}>{at > 0 ? symbol(sign) : null}<ChipView chip={chip} unit={unit} /></React.Fragment>)}
    {result ? <span style={{ display: "inline-flex", alignItems: "center", gap: 16 * unit }}>{symbol("=")}<ChipView chip={result} unit={unit} size={62} /></span> : null}
  </div>;
}

function Table({ item, unit, shownRows, time, since }: { item: GrammarItem; unit: number; shownRows: number; time: number; since: number }) {
  const columns = item.columns || [], rows = item.rows || [];
  const cell = (text: string, head: boolean, at: number): React.CSSProperties => ({
    fontFamily: SANS, fontWeight: head ? 800 : 700, fontSize: (head ? 34 : 38) * unit, color: head ? "#FFFFFF" : at === 0 ? INK : "#1D4F91",
    padding: `${14 * unit}px ${16 * unit}px`, textAlign: "center", lineHeight: 1.2 });
  return <div data-grammar-table={rows.length} style={cardBox(unit, { padding: 0, overflow: "hidden" })}>
    <div style={{ display: "grid", gridTemplateColumns: `repeat(${columns.length}, 1fr)`, background: GREEN }}>
      {columns.map((column, at) => <div key={at} style={cell(column, true, at)}>{column}</div>)}
    </div>
    {rows.map((row, index) => {
      const show = index < shownRows ? 1 : slideIn(time, since + 0.05, 0.35);
      return <div key={index} style={{ display: "grid", gridTemplateColumns: `repeat(${columns.length}, 1fr)`, opacity: show,
        transform: `translateX(${((1 - show) * -40 * unit).toFixed(1)}px)`, background: index % 2 ? "#F7F2E7" : "#FFFFFF",
        borderTop: "1px solid #E6DFD0" }}>
        {row.map((text, at) => <div key={at} style={cell(text, false, at)}>{text}</div>)}
      </div>;
    })}
  </div>;
}

function Example({ item, unit }: { item: GrammarItem; unit: number }) {
  const pieces = markedPieces(item.en || "", item.marks || []);
  return <div style={cardBox(unit, { display: "grid", gap: 10 * unit, textAlign: "center" })}>
    <div style={{ fontFamily: SANS, fontWeight: 800, color: INK, fontSize: 48 * unit, lineHeight: 1.3 }}>
      {pieces.map((piece, at) => piece.role
        // a "plain" mark is ink (sandbox run 2026-11-03: its beige chip fill made "really" invisible on the card)
        ? <span key={at} style={{ color: piece.role === "v3" || piece.role === "plain" ? "#151515" : chipColour(piece.role).fill,
          background: piece.role === "v3" ? YELLOW : "transparent", borderRadius: 10 * unit, padding: piece.role === "v3" ? `0 ${8 * unit}px` : 0,
          textDecoration: piece.role === "v3" ? "none" : `underline ${5 * unit}px`, textUnderlineOffset: `${8 * unit}px`,
          textDecorationColor: piece.role === "plain" ? YELLOW : undefined }}>{piece.text}</span>
        : <span key={at}>{piece.text}</span>)}
    </div>
    {item.vi ? <div style={{ fontFamily: HAND, color: MUTED, fontSize: 40 * unit, lineHeight: 1.2 }}>{item.vi}</div> : null}
  </div>;
}

function Card({ item, unit, shownRows, time, since, stamped }: { item: GrammarItem; unit: number; shownRows: number; time: number;
  since: number; stamped: boolean }) {
  const text = (size: number, colour = INK, weight = 800) => ({ fontFamily: SANS, fontWeight: weight, fontSize: size * unit, color: colour,
    lineHeight: 1.25, textAlign: "center" as const });
  switch (item.kind) {
    case "formulas":
      return <div style={cardBox(unit, { position: "relative", display: "grid", gap: 14 * unit })}>
        {(item.items || []).map((formula, at) => <div key={at} style={{ ...text(42, stamped ? "#9A9388" : INK, 700),
          textDecoration: stamped ? `line-through ${4 * unit}px ${RED}` : "none" }}>{formula}</div>)}
      </div>;
    case "promise":
      return <div style={cardBox(unit, { background: YELLOW })}><div style={text(54)}>{item.text}</div></div>;
    case "core":
      return <div style={cardBox(unit, { background: GREEN })}><div style={text(50, "#FFFFFF")}>{item.text}</div></div>;
    case "rule":
      return <div style={cardBox(unit, { background: "#FDE7EF", border: `${4 * unit}px solid ${PINK}` })}><div style={text(46, "#8E1E4A")}>{item.text}</div></div>;
    case "stamp":
      return <div style={{ display: "flex", justifyContent: "center" }}>
        <div style={{ border: `${8 * unit}px solid ${RED}`, color: RED, fontFamily: LETTERS, fontSize: 84 * unit, lineHeight: 1,
          padding: `${12 * unit}px ${30 * unit}px`, borderRadius: 20 * unit, transform: "rotate(-5deg)", background: "rgba(255,255,255,0.7)" }}>✕ {item.text}</div>
      </div>;
    case "sticker":
      return <div style={{ display: "flex", justifyContent: "center" }}>
        <div data-grammar-sticker="true" style={{ background: YELLOW, color: INK, fontFamily: LETTERS, fontSize: 104 * unit, lineHeight: 1,
          padding: `${18 * unit}px ${44 * unit}px`, borderRadius: 22 * unit, transform: "rotate(-3deg)",
          boxShadow: `0 ${8 * unit}px 0 #C99A12, 0 ${14 * unit}px ${26 * unit}px rgba(60,45,20,0.2)` }}>[{item.text}]</div>
      </div>;
    case "formula":
      return <div style={cardBox(unit, { display: "grid", gap: 14 * unit })}>
        <Joined chips={item.chips || []} unit={unit} />
        {item.text ? <div style={{ fontFamily: HAND, color: MUTED, fontSize: 40 * unit, textAlign: "center" }}>{item.text}</div> : null}
      </div>;
    case "lego":
      return <div style={cardBox(unit)}><Joined chips={item.chips || []} unit={unit} result={item.result} /></div>;
    case "compare":
      return <div style={{ display: "grid", gap: 14 * unit }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 * unit }}>
          {[[item.left_en, item.left_vi], [item.right_en, item.right_vi]].map(([en, vi], at) => <div key={at} style={cardBox(unit, { display: "grid", gap: 8 * unit })}>
            <div style={text(42)}>{en}</div>
            {vi ? <div style={{ fontFamily: HAND, color: MUTED, fontSize: 36 * unit, textAlign: "center" }}>{vi}</div> : null}
          </div>)}
        </div>
        {item.text ? <div style={{ ...text(40, GREEN), fontFamily: HAND }}>{item.text}</div> : null}
      </div>;
    case "table":
      return <Table item={item} unit={unit} shownRows={shownRows} time={time} since={since} />;
    case "example":
      return <Example item={item} unit={unit} />;
    case "quiz":
      return <div style={cardBox(unit, { display: "grid", gap: 22 * unit })}>
        <div style={text(52)}>{item.text}</div>
        <div style={{ display: "flex", justifyContent: "center", gap: 22 * unit, flexWrap: "wrap" }}>
          {(item.options || []).map((option, at) => <div key={at} style={{ ...text(44, "#FFFFFF"), background: "#2F6FD6",
            borderRadius: 999, padding: `${12 * unit}px ${30 * unit}px` }}>{String.fromCharCode(65 + at)}. {option}</div>)}
        </div>
      </div>;
    default:
      return item.text ? <div style={cardBox(unit)}><div style={text(46)}>{item.text}</div></div> : null;
  }
}

function Stamp({ text, show, unit }: { text: string; show: number; unit: number }) {
  return <div data-grammar-stamp="true" style={{ position: "absolute", left: 0, right: 0, top: 560 * unit, display: "flex", justifyContent: "center",
    opacity: show, transform: `rotate(-9deg) scale(${(1.6 - 0.6 * show).toFixed(3)})` }}>
    <div style={{ border: `${10 * unit}px solid ${RED}`, color: RED, fontFamily: LETTERS, fontSize: 130 * unit, lineHeight: 1,
      padding: `${16 * unit}px ${40 * unit}px`, borderRadius: 24 * unit, background: "rgba(255,255,255,0.85)" }}>✕ {text}</div>
  </div>;
}

function Caption({ line, time, unit }: { line: EpisodeLine; time: number; unit: number }) {
  const tokens = useMemo(() => withScriptPunctuation(buildKaraokeTokens(line), line.text), [line]);
  const active = activeTokenIndex(tokens, time * 1000);
  const size = line.text.length > 120 ? 38 : line.text.length > 80 ? 42 : 48;
  return <div data-grammar-caption="true" style={{ position: "absolute", left: 90 * unit, right: 170 * unit, top: 1500 * unit, textAlign: "center",
    fontFamily: SANS, fontWeight: 700, color: INK, fontSize: size * unit, lineHeight: 1.3 }}>
    {tokens.length ? tokens.map((token, at) => <React.Fragment key={`${token.fromMs}-${at}`}>
      <span style={{ color: at === active ? GREEN : INK, textDecoration: at === active ? `underline ${5 * unit}px ${YELLOW}` : "none",
        textUnderlineOffset: `${8 * unit}px` }}>{token.text.trim()}</span>{at < tokens.length - 1 ? " " : ""}
    </React.Fragment>) : line.text}
  </div>;
}

function Beat({ props, index, time, unit }: { props: EpisodeInputProps; index: number; time: number; unit: number }) {
  const line = props.lines[index];
  const card = line.grammar || { beat: "", scene: 0, label: "", title: "", cards: [] };
  const vi = isVietnamese(`${line.text} ${card.title} ${card.label}`);
  const since = sceneStart(props.lines, index);
  const head = slideIn(time, since, 0.35);
  const seen = cardsSeen(props.lines, index);
  const shownRows = rowsBefore(props.lines, index);
  // the hook's stamp lands over the rote formulas; in a scene it is one more card (sandbox run 2026-11-03: drawn over the
  // scene's example sentence it hid it)
  const stamp = card.beat === "hook" ? card.cards.find((item) => item.kind === "stamp") : undefined;
  const stack = card.cards.filter((item) => item !== stamp);
  // the stack is laid out narrower and scaled up, so its cards fill the 940 px column (stills 2026-11-03: too small)
  const top = card.subtitle ? 470 : 420;
  const scale = fitScale(stack, 1470 - top);
  const width = 940 / scale;
  const quiz = card.cards.find((item) => item.kind === "quiz");
  return <>
    <div style={{ position: "absolute", left: 60 * unit, right: 60 * unit, top: 170 * unit, display: "grid", justifyItems: "center",
      gap: 14 * unit, opacity: head, transform: `translateY(${((1 - head) * -20 * unit).toFixed(1)}px)` }}>
      <div data-grammar-pill="true" style={{ background: pillColour(card.beat, card.scene), color: "#FFFFFF", fontFamily: SANS, fontWeight: 800,
        // kept clear of the channel logo in the top-right corner (sandbox run 2026-11-03: a long label ran under it)
        fontSize: (pillText(card.beat, card.scene, card.label, vi).length > 30 ? 26 : 32) * unit, letterSpacing: "0.04em",
        padding: `${10 * unit}px ${30 * unit}px`, borderRadius: 999, maxWidth: 760 * unit, textAlign: "center" }}>
        {pillText(card.beat, card.scene, card.label, vi)}</div>
      <div style={{ fontFamily: LETTERS, color: INK, fontSize: (card.title.length > 48 ? 54 : card.title.length > 34 ? 66 : 80) * unit, lineHeight: 1.05, textAlign: "center",
        letterSpacing: "0.01em" }}>{card.title}</div>
      {card.subtitle ? <div style={{ fontFamily: HAND, color: MUTED, fontSize: 44 * unit, textAlign: "center" }}>{card.subtitle}</div> : null}
    </div>
    <div data-grammar-stack={stack.length} style={{ position: "absolute", left: (1080 - width) / 2 * unit, width: width * unit,
      top: top * unit, display: "grid", gap: 26 * unit, transform: `scale(${scale.toFixed(3)})`, transformOrigin: "top center" }}>
      {stack.map((item, at) => {
        const old = seen[card.cards.indexOf(item)];
        const show = old ? 1 : slideIn(time, line.startSec + 0.05, 0.35);
        return <div key={at} style={{ opacity: show, transform: `translateY(${((1 - show) * 40 * unit).toFixed(1)}px)` }}>
          <Card item={item} unit={unit} shownRows={shownRows} time={time} since={line.startSec} stamped={!!stamp} />
        </div>;
      })}
    </div>
    {stamp ? <Stamp text={stamp.text || ""} show={seen[card.cards.indexOf(stamp)] ? 1 : slideIn(time, line.startSec, 0.25)} unit={unit} /> : null}
    {quiz && card.beat === "follow" ? <div data-grammar-countdown="true" style={{ position: "absolute", left: 0, right: 0, top: 1180 * unit,
      display: "flex", justifyContent: "center" }}>
      <div style={{ width: 170 * unit, height: 170 * unit, borderRadius: "50%", border: `${10 * unit}px solid #2F6FD6`, display: "flex",
        alignItems: "center", justifyContent: "center", fontFamily: LETTERS, fontSize: 110 * unit, color: "#2F6FD6", background: "#FFFFFF" }}>
        {countdown(time, line.startSec)}</div>
    </div> : null}
    <Caption line={line} time={time} unit={unit} />
  </>;
}

export function GrammarScene(props: EpisodeInputProps) {
  const frame = useCurrentFrame(), { fps, height } = useVideoConfig();
  const time = frame / fps, unit = height / 1920;
  const index = lineAt(props.lines, time);
  return <AbsoluteFill data-short-style="grammar" style={{ overflow: "hidden" }}>
    <Paper />
    {!props.soundtrackPath ? <Audio src={resolvedMedia(props.audioPath)} /> : null}
    {index >= 0 ? <Beat props={props} index={index} time={time} unit={unit} /> : null}
  </AbsoluteFill>;
}
