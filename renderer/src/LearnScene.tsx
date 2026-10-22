/**
 * Phase 64 (ENH-046): the quick-learning Shorts (9:16) on the brand background --
 * Don't say / Say: a red card with the wrong phrase struck through, then a green card with the right one;
 * Word of the day: the word big, its IPA, part of speech and Vietnamese meaning (from the learning pack), examples
 * with the word highlighted; Top 5 phrases: a countdown number flipping in, the phrase and its meaning.
 * Karaoke captions in all three; a scene picture drifts faintly behind for variety.
 */
import React, { useMemo } from "react";
import { AbsoluteFill, Img, useCurrentFrame, useVideoConfig } from "remotion";
import { CaptionBand } from "./CaptionBand";
import { resolvedMedia } from "./Presenter";
import { clamp01, easeOut, voxSegmentAt } from "./voxMath";
import { easeOutBack, smoothProgress } from "./voxMotion";
import { pictureFor, spanWords } from "./shortsMath";
import { cardText, countdownNumber, explains, isLearnStyle, learningFor, mistakePair, rightAt, templateLabel } from "./learnMath";
import type { EpisodeInputProps } from "./types";

const GREEN = "#1F7A4D", RED = "#E8483B", YELLOW = "#FFD84D", CREAM = "#FFFDF4", INK = "#14231C";
const SANS = "Arial, Helvetica, sans-serif", HEAVY = "'Arial Black', Arial, Helvetica, sans-serif";

/** "VI" before a Vietnamese meaning (Windows has no flag emoji). */
function ViTag({ unit }: { unit: number }) {
  return <span style={{ display: "inline-block", background: RED, color: "#FFF", fontFamily: HEAVY, fontSize: 26 * unit, borderRadius: 8 * unit,
    padding: `${2 * unit}px ${10 * unit}px`, marginRight: 12 * unit, verticalAlign: "middle" }}>VI</span>;
}

/** Words of a text with `phrase` highlighted (case-insensitive). */
function Highlighted({ text, phrase }: { text: string; phrase: string }) {
  if (!phrase) return <>{text}</>;
  const at = text.toLowerCase().indexOf(phrase.toLowerCase());
  if (at < 0) return <>{text}</>;
  return <>{text.slice(0, at)}<span style={{ background: YELLOW, color: INK, padding: "0 0.15em", borderRadius: 6 }}>
    {text.slice(at, at + phrase.length)}</span>{text.slice(at + phrase.length)}</>;
}

export function LearnScene(props: EpisodeInputProps) {
  const frame = useCurrentFrame(), { fps, width, height } = useVideoConfig();
  const payload = props.solo;
  const style = payload?.style;
  if (!payload || !isLearnStyle(style)) throw new Error("A learning Short needs its reviewed payload");
  const time = frame / fps, aspect = props.layout === "vertical" ? "9:16" : "16:9";
  const index = voxSegmentAt(payload, time);
  const segments = payload.plan.segments, segment = segments[index], span = payload.timeline[index];
  const geometry = payload.geometry.aspects[aspect] ?? Object.values(payload.geometry.aspects)[0];
  const board = geometry.board ?? geometry.safe, caption = geometry.caption, header = geometry.header;
  const line = props.lines.find((item) => time >= item.startSec && time < item.endSec);
  const words = useMemo(() => spanWords(props.lines, span.start_sec, span.end_sec), [props.lines, span]);
  const progress = words.length ? smoothProgress(words, time) : clamp01((time - span.start_sec) / Math.max(0.01, span.end_sec - span.start_sec));
  const unit = height / 1920, since = time - span.start_sec;
  const enter = easeOutBack(since / 0.4), fade = clamp01(since / 0.25);
  const box = { left: board.x * width, top: board.y * height, width: board.width * width, height: (caption.y - board.y - 0.02) * height };
  const plate = pictureFor(payload, segment);
  const visual = segment.visual, text = cardText(visual);

  let content: React.ReactNode;
  const pair = style === "mistakes" ? mistakePair(visual) : null;
  const number = style === "top5" ? countdownNumber(segments, index) : null;
  if (pair) {
    const strike = easeOut((progress - 0.18) / 0.2);
    const showRight = time >= rightAt(words, span.start_sec, span.end_sec);
    const rightPop = easeOutBack((time - rightAt(words, span.start_sec, span.end_sec)) / 0.35);
    const card = (good: boolean, phrase: string, pop: number) => <div data-learn-card={good ? "say" : "dont"} style={{
      background: CREAM, borderRadius: 26 * unit, padding: `${26 * unit}px ${30 * unit}px`, border: `${8 * unit}px solid ${good ? GREEN : RED}`,
      boxShadow: "0 18px 40px rgba(0,0,0,0.3)", transform: `scale(${Math.max(0, pop).toFixed(4)})`, opacity: clamp01(pop * 2), width: "100%",
      boxSizing: "border-box" }}>
      <div style={{ fontFamily: HEAVY, color: good ? GREEN : RED, fontSize: 40 * unit, letterSpacing: "0.04em" }}>
        {good ? "✅ SAY" : "❌ DON'T SAY"}</div>
      <div style={{ position: "relative", display: "inline-block", marginTop: 10 * unit, fontFamily: SANS, fontWeight: 800,
        fontSize: (phrase.length > 40 ? 54 : 66) * unit, lineHeight: 1.15, color: good ? INK : "#5B3A36" }}>
        {phrase}
        {!good ? <span style={{ position: "absolute", left: 0, top: "52%", height: 8 * unit, background: RED, borderRadius: 4,
          width: `${(strike * 100).toFixed(1)}%` }} /> : null}
      </div>
    </div>;
    content = <div style={{ display: "grid", gap: 34 * unit, alignContent: "center", height: "100%" }}>
      {card(false, pair.wrong, enter)}
      {showRight ? card(true, pair.right, rightPop) : <div style={{ height: 200 * unit }} />}
    </div>;
  } else if (style === "wordday" && index === 0 && visual.kind === "text_card") {
    const extra = learningFor(props.learning, text.title);
    const part = visual.bullets?.[0] || extra?.partOfSpeech || "";
    const show = explains(props.learning?.audience, Boolean(extra?.meaningVi));  // Phase 72 (ENH-054)
    const meaning = show.en ? visual.bullets?.[1] ?? "" : "";
    content = <div data-learn-word="true" style={{ display: "grid", gap: 18 * unit, justifyItems: "center", alignContent: "center", height: "100%",
      textAlign: "center", transform: `scale(${(0.8 + 0.2 * Math.max(0, enter)).toFixed(4)})`, opacity: fade }}>
      <div style={{ fontFamily: HEAVY, color: "#FFF", fontSize: (text.title.length > 14 ? 110 : 150) * unit, lineHeight: 1,
        textShadow: "0 10px 30px rgba(0,0,0,0.35)" }}>{text.title}</div>
      {extra?.ipa ? <div style={{ fontFamily: SANS, color: YELLOW, fontSize: 52 * unit, fontWeight: 700 }}>{extra.ipa}</div> : null}
      {part ? <div style={{ fontFamily: SANS, color: "#DCEFE3", fontSize: 40 * unit, fontStyle: "italic" }}>{part}</div> : null}
      {meaning ? <div style={{ fontFamily: SANS, color: "#FFF", fontSize: 46 * unit, fontWeight: 700, maxWidth: box.width }}>{meaning}</div> : null}
      {show.vi && extra?.meaningVi ? <div data-learn-vi="true" style={{ background: CREAM, color: INK, borderRadius: 16 * unit, padding: `${10 * unit}px ${22 * unit}px`,
        fontFamily: SANS, fontWeight: 800, fontSize: 44 * unit, opacity: clamp01((progress - 0.3) / 0.15) }}><ViTag unit={unit} />{extra.meaningVi}</div> : null}
    </div>;
  } else if (number !== null) {
    const flip = easeOut(since / 0.45);
    const extra = learningFor(props.learning, text.title);
    const show = explains(props.learning?.audience, Boolean(extra?.meaningVi));  // Phase 72 (ENH-054)
    content = <div style={{ display: "grid", gap: 26 * unit, justifyItems: "center", alignContent: "center", height: "100%", textAlign: "center" }}>
      <div data-learn-number={number} style={{ width: 230 * unit, height: 230 * unit, borderRadius: "50%", background: YELLOW, color: INK,
        display: "grid", placeItems: "center", fontFamily: HEAVY, fontSize: 150 * unit, boxShadow: "0 14px 34px rgba(0,0,0,0.3)",
        transform: `perspective(${900 * unit}px) rotateX(${((1 - flip) * 90).toFixed(2)}deg)` }}>{number}</div>
      <div style={{ fontFamily: HEAVY, color: "#FFF", fontSize: (text.title.length > 22 ? 70 : 88) * unit, lineHeight: 1.1, maxWidth: box.width,
        transform: `translateY(${((1 - clamp01(enter)) * 40 * unit).toFixed(1)}px)`, opacity: fade, textShadow: "0 8px 24px rgba(0,0,0,0.35)" }}>{text.title}</div>
      {show.en && text.detail ? <div data-learn-en="true" style={{ fontFamily: SANS, color: "#DCEFE3", fontSize: 46 * unit, fontWeight: 700, maxWidth: box.width,
        opacity: clamp01((progress - 0.25) / 0.15) }}>{text.detail}</div> : null}
      {show.vi && extra?.meaningVi ? <div data-learn-vi="true" style={{ fontFamily: SANS, color: YELLOW, fontSize: 40 * unit, fontWeight: 700, opacity: clamp01((progress - 0.4) / 0.15) }}>
        <ViTag unit={unit} />{extra.meaningVi}</div> : null}
      <div style={{ display: "flex", gap: 14 * unit }}>{Array.from({ length: segments.length - 2 }, (_, i) => <span key={i} style={{
        width: 22 * unit, height: 22 * unit, borderRadius: "50%", background: i <= index - 1 ? YELLOW : "rgba(255,255,255,0.3)" }} />)}</div>
    </div>;
  } else {
    // the hook, a tip or an example, and the follow line
    const word = style === "wordday" ? cardText(segments[0].visual).title : "";
    content = <div style={{ display: "grid", gap: 24 * unit, justifyItems: "center", alignContent: "center", height: "100%", textAlign: "center",
      transform: `scale(${(0.85 + 0.15 * Math.max(0, enter)).toFixed(4)})`, opacity: fade }}>
      {style === "wordday" && index > 0 && word ? <div style={{ fontFamily: SANS, color: YELLOW, fontWeight: 800, fontSize: 36 * unit }}>
        {visual.kind === "quote" ? "EXAMPLE" : "TIP"} · {word}</div> : null}
      <div data-learn-text="true" style={{ fontFamily: visual.kind === "quote" ? "Georgia, serif" : HEAVY, color: "#FFF", maxWidth: box.width,
        fontSize: (text.title.length > 60 ? 58 : text.title.length > 30 ? 70 : 90) * unit, lineHeight: 1.15, textShadow: "0 8px 24px rgba(0,0,0,0.35)" }}>
        <Highlighted text={text.title} phrase={visual.kind === "quote" ? text.emphasis : ""} /></div>
      {text.emphasis && visual.kind !== "quote" ? <div style={{ background: YELLOW, color: INK, fontFamily: HEAVY, fontSize: 44 * unit,
        padding: `${8 * unit}px ${22 * unit}px`, borderRadius: 14 * unit, transform: `scale(${Math.max(0, easeOutBack((progress - 0.3) / 0.2)).toFixed(4)})` }}>
        {text.emphasis}</div> : null}
    </div>;
  }

  const drift = Math.sin(time * Math.PI * 2 / 18) * 24;
  return <AbsoluteFill data-learn-scene={style} style={{ overflow: "hidden", background: `linear-gradient(170deg, #0F3D2A, ${GREEN} 55%, #0B2A1E)`, fontFamily: SANS }}>
    {plate ? <Img src={resolvedMedia(plate)} style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover", opacity: 0.16,
      filter: "blur(10px) saturate(0.8)", mixBlendMode: "luminosity", transform: `translateX(${drift.toFixed(1)}px) scale(1.15)` }} /> : null}
    {/* soft shapes */}
    <div style={{ position: "absolute", left: -160 * unit, top: 260 * unit + drift, width: 520 * unit, height: 520 * unit, borderRadius: "50%", background: "rgba(255,216,77,0.12)" }} />
    <div style={{ position: "absolute", right: -140 * unit, top: 1180 * unit - drift, width: 460 * unit, height: 460 * unit, borderRadius: "42% 58% 60% 40%", background: "rgba(255,255,255,0.07)" }} />
    <div style={{ position: "absolute", left: header.x * width, top: header.y * height, width: header.width * width, display: "flex",
      justifyContent: "space-between", alignItems: "center" }}>
      <span style={{ background: YELLOW, color: INK, fontFamily: HEAVY, fontSize: 30 * unit, padding: `${6 * unit}px ${16 * unit}px`, borderRadius: 10 * unit,
        whiteSpace: "nowrap" }}>
        {templateLabel(style)}</span>
      <span style={{ color: "#FFF", fontWeight: 800, fontSize: 26 * unit, whiteSpace: "nowrap" }}>DAILY BEYOND ENGLISH · {props.cefrLevel}</span>
    </div>
    <div style={{ position: "absolute", left: box.left, top: box.top, width: box.width, height: box.height }}>{content}</div>
    {line ? <div data-solo-caption="true" style={{ position: "absolute", left: caption.x * width, top: caption.y * height,
      width: caption.width * width, height: caption.height * height }}>
      <CaptionBand line={line} currentTimeSec={time} captionStyle={props.captionStyle} layout={props.layout}
        protectedPhrases={[...(props.learning?.idioms ?? []).map((item) => item.phrase), ...(props.learning?.vocab ?? []).map((item) => item.word)]} stationary />
    </div> : null}
  </AbsoluteFill>;
}
