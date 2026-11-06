/**
 * Phase 98 (D167): a Doodle story. One hand-drawn picture fills the frame and stays still; the next fades in over 0.4 s. Under
 * it, capitals in groups of 3-5 words with the spoken word in a black pill, outlined so they read on paper. D164: the first time a
 * target word is said, its card appears for 4.5 s.
 */
import React, { useMemo } from "react";
import { AbsoluteFill, Img, useCurrentFrame, useVideoConfig } from "remotion";
import { BOTTOM_SHADE_STYLE, captionStyleSpec, type CaptionStyle } from "./captionStyle";
import { CAPTION_MAX_CHARACTERS, CAPTION_MAX_WORDS, cardAt, fadeAt, termCards, type TermCard } from "./doodleMath";
import { activeTokenIndex, buildKaraokeTokens, captionPageAtTime, paginateCaptionTokens, withScriptPunctuation } from "./karaoke";
import { explains } from "./learnMath";
import { resolvedMedia } from "./Presenter";
import { voxSegmentAt } from "./voxMath";
import type { EpisodeInputProps, EpisodeLine } from "./types";
import type { SoloPayload } from "./soloTypes";

const PAPER = "#F3E7C9", INK = "#2A2418", GREEN = "#1F7A4D";
const FONT = "Arial, Helvetica, sans-serif";

function Picture({ payload, index, opacity }: { payload: SoloPayload; index: number; opacity: number }) {
  const visual = payload.plan.segments[index].visual;
  const url = visual.kind === "photo" && visual.asset ? payload.photos[`${visual.asset.asset_id}:${visual.asset.version}`] : undefined;
  if (!url) return null;
  return <Img data-doodle-picture={index} src={resolvedMedia(url)}
    style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", opacity }} />;
}

function Caption({ line, time, unit, protect, style }: { line: EpisodeLine; time: number; unit: number; protect: readonly string[]; style: CaptionStyle }) {
  const spec = captionStyleSpec(style);
  const pages = useMemo(() => paginateCaptionTokens(withScriptPunctuation(buildKaraokeTokens(line), line.text),
    CAPTION_MAX_WORDS, CAPTION_MAX_CHARACTERS, protect), [line, protect]);
  const now = time * 1000, shown = captionPageAtTime(pages, now), active = activeTokenIndex(shown, now);
  return <div data-doodle-caption="true" style={{ position: "absolute", left: "6%", right: "6%", top: "85%", textAlign: "center",
    fontFamily: FONT, fontWeight: 800, fontSize: 32 * unit, lineHeight: 1.3, textTransform: style === "pill" ? "uppercase" : undefined, letterSpacing: 0.3 * unit, color: "#FFFFFF" }}>
    {spec.bottomShade ? <div style={{ ...BOTTOM_SHADE_STYLE, height: "200%" }} /> : null}
    <span style={{ position: "relative", ...spec.text, ...spec.box }}>
    {shown.length ? shown.map((token, index) => <React.Fragment key={`${token.fromMs}-${token.text}`}>
      <span data-doodle-word={index === active ? "active" : "word"} style={{ display: "inline-block", padding: `${1 * unit}px ${7 * unit}px`, borderRadius: 8 * unit,
        background: style === "pill" && index === active ? "#0B0B0B" : "transparent" }}>{token.text.trim()}</span>{" "}
    </React.Fragment>) : line.text}
    </span>
  </div>;
}

function Card({ card, time, unit, audience }: { card: TermCard; time: number; unit: number; audience?: string }) {
  const show = explains(audience as Parameters<typeof explains>[0], Boolean(card.definitionVi));
  const age = Math.min(1, (time - card.fromSec) / 0.3), left = Math.min(1, (card.toSec - time) / 0.3);
  return <div data-doodle-card="true" style={{ position: "absolute", left: 28 * unit, top: 26 * unit, maxWidth: 440 * unit, padding: `${12 * unit}px ${20 * unit}px`,
    background: PAPER, color: INK, border: `${3 * unit}px solid ${INK}`, borderLeft: `${12 * unit}px solid ${GREEN}`, borderRadius: 6 * unit, fontFamily: FONT,
    boxShadow: `${4 * unit}px ${5 * unit}px 0 rgba(42,36,24,0.3)`, opacity: Math.min(age, left), transform: `rotate(-1deg) scale(${(0.94 + 0.06 * age).toFixed(4)})`, transformOrigin: "0 0" }}>
    <div style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: 38 * unit, fontWeight: 700, lineHeight: 1.1 }}>{card.word}</div>
    {card.ipa ? <div style={{ fontSize: 19 * unit, color: GREEN, fontWeight: 700, marginTop: 3 * unit }}>{card.ipa}</div> : null}
    {show.en ? <div style={{ fontSize: 20 * unit, lineHeight: 1.25, marginTop: 5 * unit }}>{card.definitionEn}</div> : null}
    {show.vi ? <div style={{ fontSize: 20 * unit, lineHeight: 1.25, marginTop: 5 * unit, fontWeight: 700 }}>{card.definitionVi}</div> : null}
  </div>;
}

export function DoodleScene(props: EpisodeInputProps) {
  const frame = useCurrentFrame(), { fps, width } = useVideoConfig();
  const payload = props.solo;
  if (!payload || payload.style !== "doodle") throw new Error("A Doodle story needs its reviewed payload");
  const time = frame / fps, unit = width / 1280, index = voxSegmentAt(payload, time), fade = fadeAt(payload.timeline, index, time);
  const line = props.lines.find((item) => time >= item.startSec && time < item.endSec);
  const vocab = props.learning?.vocab, terms = payload.terms;
  const cards = useMemo(() => termCards(props.lines, vocab ?? [], terms ?? []), [props.lines, vocab, terms]);
  const protect = useMemo(() => [...(props.learning?.idioms ?? []).map((item) => item.phrase), ...(vocab ?? []).map((item) => item.word)], [props.learning?.idioms, vocab]);
  const card = cardAt(cards, time);
  return <AbsoluteFill data-doodle-scene="true" style={{ background: PAPER, overflow: "hidden" }}>
    {fade < 1 ? <Picture payload={payload} index={index - 1} opacity={1} /> : null}
    <Picture payload={payload} index={index} opacity={fade} />
    {line ? <Caption line={line} time={time} unit={unit} protect={protect} style={props.captionStyle} /> : null}
    {card ? <Card card={card} time={time} unit={unit} audience={props.learning?.audience} /> : null}
  </AbsoluteFill>;
}
