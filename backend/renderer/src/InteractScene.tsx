/**
 * Phase 65 (ENH-047): the one-narrator interactive Shorts (9:16) on the brand background --
 * countdown quiz: the question card, options A/B/C popping in, a ring timer from "three" to "the answer is", then
 * the right option turning green with a check and the others fading;
 * listening challenge: an ear and a moving sound wave while the sentence is heard (captions hidden, so the viewer
 * really listens), then the sentence revealed at "here is the sentence" with its hardest words highlighted.
 */
import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { CaptionBand } from "./CaptionBand";
import { clamp01, voxSegmentAt } from "./voxMath";
import { easeOutBack } from "./voxMotion";
import { spanWords } from "./shortsMath";
import { cardText } from "./learnMath";
import { cueAt, isInteractStyle, listenPhase, quizItem, timerShare } from "./interactMath";
import type { EpisodeInputProps } from "./types";

const GREEN = "#1F7A4D", YELLOW = "#FFD84D", CREAM = "#FFFDF4", INK = "#14231C", RED = "#E8483B";
const SANS = "Arial, Helvetica, sans-serif", HEAVY = "'Arial Black', Arial, Helvetica, sans-serif";

export function InteractScene(props: EpisodeInputProps) {
  const frame = useCurrentFrame(), { fps, width, height } = useVideoConfig();
  const payload = props.solo, style = payload?.style;
  if (!payload || !isInteractStyle(style)) throw new Error("An interactive Short needs its reviewed payload");
  const time = frame / fps, aspect = props.layout === "vertical" ? "9:16" : "16:9";
  const index = voxSegmentAt(payload, time);
  const segment = payload.plan.segments[index], span = payload.timeline[index];
  const geometry = payload.geometry.aspects[aspect] ?? Object.values(payload.geometry.aspects)[0];
  const board = geometry.board ?? geometry.safe, caption = geometry.caption, header = geometry.header;
  const line = props.lines.find((item) => time >= item.startSec && time < item.endSec);
  const words = useMemo(() => spanWords(props.lines, span.start_sec, span.end_sec), [props.lines, span]);
  const allWords = useMemo(() => props.lines.flatMap((item) => item.words), [props.lines]);
  const unit = height / 1920, since = time - span.start_sec;
  const box = { left: board.x * width, top: board.y * height, width: board.width * width, height: (caption.y - board.y - 0.02) * height };
  const enter = easeOutBack(since / 0.4), fade = clamp01(since / 0.25);
  const visual = segment.visual;
  let content: React.ReactNode;
  let hideCaptions = false;
  const quiz = style === "quiz" ? quizItem(visual) : null;
  if (quiz) {
    const reveal = cueAt(words, span.start_sec, span.end_sec, "answer", 0.7);
    const timer = timerShare(time, cueAt(words, span.start_sec, span.end_sec, "three", 0.55), reveal);
    const revealed = time >= reveal;
    const radius = 70 * unit, circumference = 2 * Math.PI * radius;
    content = <div style={{ display: "grid", gap: 22 * unit, alignContent: "center", height: "100%" }}>
      <div data-quiz-question="true" style={{ background: CREAM, color: INK, borderRadius: 24 * unit, padding: `${24 * unit}px ${28 * unit}px`,
        fontFamily: HEAVY, fontSize: (quiz.question.length > 70 ? 46 : 56) * unit, lineHeight: 1.15, boxShadow: "0 16px 36px rgba(0,0,0,0.3)",
        transform: `scale(${Math.max(0, enter).toFixed(4)})` }}>{quiz.question}</div>
      {quiz.options.map((option, i) => {
        const pop = easeOutBack((since - 0.5 - i * 0.35) / 0.35);
        const right = revealed && i === quiz.answer, wrong = revealed && i !== quiz.answer;
        return <div key={i} data-quiz-option={right ? "right" : wrong ? "wrong" : "open"} style={{ display: "flex", alignItems: "center", gap: 18 * unit,
          background: right ? GREEN : "rgba(255,255,255,0.12)", border: `${4 * unit}px solid ${right ? "#7BE0A4" : "rgba(255,255,255,0.35)"}`,
          borderRadius: 18 * unit, padding: `${14 * unit}px ${20 * unit}px`, color: "#FFF", fontFamily: SANS, fontWeight: 800,
          fontSize: 46 * unit, opacity: wrong ? 0.35 : clamp01(pop * 2), transform: `scale(${(right ? 1.04 : 1) * Math.max(0, Math.min(1.2, pop))})` }}>
          <span style={{ width: 66 * unit, height: 66 * unit, borderRadius: "50%", background: right ? "#FFF" : YELLOW, color: right ? GREEN : INK,
            display: "grid", placeItems: "center", fontFamily: HEAVY, flexShrink: 0 }}>{right ? "✓" : "ABCD"[i]}</span>{option}</div>;
      })}
      {timer !== null ? <svg data-quiz-timer="true" width={radius * 2 + 20 * unit} height={radius * 2 + 20 * unit} style={{ justifySelf: "center" }}>
        <circle cx={radius + 10 * unit} cy={radius + 10 * unit} r={radius} fill="rgba(0,0,0,0.25)" stroke="rgba(255,255,255,0.25)" strokeWidth={12 * unit} />
        <circle cx={radius + 10 * unit} cy={radius + 10 * unit} r={radius} fill="none" stroke={timer > 0.66 ? RED : YELLOW} strokeWidth={12 * unit}
          strokeDasharray={circumference} strokeDashoffset={circumference * timer} transform={`rotate(-90 ${radius + 10 * unit} ${radius + 10 * unit})`} strokeLinecap="round" />
        <text x={radius + 10 * unit} y={radius + 10 * unit + 26 * unit} textAnchor="middle" fill="#FFF" fontFamily={HEAVY} fontSize={74 * unit}>
          {Math.max(1, 3 - Math.floor(timer * 3))}</text>
      </svg> : null}
    </div>;
  } else if (style === "listen" && visual.kind === "quote") {
    // the narration decides: hidden from "Listen" until "Here is the sentence", whatever the segments are
    const state = listenPhase(allWords, time);
    const revealed = state?.phase !== "listening";
    const reveal = state?.phase === "revealed" ? state.since : span.start_sec;
    hideCaptions = !revealed;
    const bars = Array.from({ length: 13 }, (_, i) => 0.25 + 0.75 * Math.abs(Math.sin(time * 7 + i * 0.9)) * (line ? 1 : 0.2));
    const pop = easeOutBack((time - reveal) / 0.4);
    content = revealed ? <div data-listen-reveal="true" style={{ display: "grid", alignContent: "center", height: "100%", textAlign: "center",
      transform: `scale(${Math.max(0, pop).toFixed(4)})` }}>
      {state?.phase === "revealed" && state.since >= span.start_sec ? <div style={{ fontFamily: SANS, color: YELLOW, fontWeight: 800,
        fontSize: 38 * unit, marginBottom: 18 * unit }}>YOU HEARD:</div> : null}
      <div style={{ background: CREAM, color: INK, borderRadius: 24 * unit, padding: `${26 * unit}px ${30 * unit}px`, fontFamily: "Georgia, serif",
        fontSize: (visual.text.length > 60 ? 54 : 66) * unit, lineHeight: 1.2, boxShadow: "0 16px 36px rgba(0,0,0,0.3)" }}>
        {(() => {
          const at = visual.highlight ? visual.text.toLowerCase().indexOf(visual.highlight.toLowerCase()) : -1;
          if (at < 0) return visual.text;
          return <>{visual.text.slice(0, at)}<span style={{ background: YELLOW, borderRadius: 8 * unit, padding: "0 0.12em" }}>
            {visual.text.slice(at, at + visual.highlight!.length)}</span>{visual.text.slice(at + visual.highlight!.length)}</>;
        })()}</div>
    </div> : <div data-listen-wave="true" style={{ display: "grid", gap: 30 * unit, justifyItems: "center", alignContent: "center", height: "100%", opacity: fade }}>
      <div style={{ fontSize: 170 * unit, lineHeight: 1 }}>👂</div>
      <div style={{ display: "flex", gap: 12 * unit, alignItems: "center", height: 160 * unit }}>
        {bars.map((bar, i) => <span key={i} style={{ width: 18 * unit, height: `${(bar * 100).toFixed(1)}%`, borderRadius: 9 * unit, background: i % 2 ? YELLOW : "#FFF" }} />)}
      </div>
      <div style={{ fontFamily: HEAVY, color: "#FFF", fontSize: 54 * unit }}>Listen carefully…</div>
    </div>;
  } else {
    const text = cardText(visual);
    content = <div style={{ display: "grid", gap: 24 * unit, justifyItems: "center", alignContent: "center", height: "100%", textAlign: "center",
      transform: `scale(${(0.85 + 0.15 * Math.max(0, enter)).toFixed(4)})`, opacity: fade }}>
      <div style={{ fontFamily: HEAVY, color: "#FFF", fontSize: (text.title.length > 40 ? 70 : 88) * unit, lineHeight: 1.12, maxWidth: box.width,
        textShadow: "0 8px 24px rgba(0,0,0,0.35)" }}>{text.title}</div>
      {text.emphasis ? <div style={{ background: YELLOW, color: INK, fontFamily: HEAVY, fontSize: 44 * unit, padding: `${8 * unit}px ${22 * unit}px`,
        borderRadius: 14 * unit }}>{text.emphasis}</div> : null}
    </div>;
  }
  return <AbsoluteFill data-interact-scene={style} style={{ overflow: "hidden", fontFamily: SANS,
    background: style === "quiz" ? "linear-gradient(170deg, #1B2A6B, #3B2C8F 55%, #14143A)" : "linear-gradient(170deg, #0F3D2A, #1F7A4D 55%, #0B2A1E)" }}>
    <div style={{ position: "absolute", left: -150 * unit, top: 240 * unit, width: 500 * unit, height: 500 * unit, borderRadius: "50%", background: "rgba(255,216,77,0.10)" }} />
    <div style={{ position: "absolute", left: header.x * width, top: header.y * height, width: header.width * width, display: "flex",
      justifyContent: "space-between", alignItems: "center" }}>
      <span style={{ background: YELLOW, color: INK, fontFamily: HEAVY, fontSize: 30 * unit, padding: `${6 * unit}px ${16 * unit}px`, borderRadius: 10 * unit,
        whiteSpace: "nowrap" }}>{style === "quiz" ? "QUIZ TIME" : "LISTENING CHALLENGE"}</span>
      <span style={{ color: "#FFF", fontWeight: 800, fontSize: 26 * unit, whiteSpace: "nowrap" }}>DAILY BEYOND ENGLISH · {props.cefrLevel}</span>
    </div>
    <div style={{ position: "absolute", left: box.left, top: box.top, width: box.width, height: box.height }}>{content}</div>
    {line && !hideCaptions ? <div data-solo-caption="true" style={{ position: "absolute", left: caption.x * width, top: caption.y * height,
      width: caption.width * width, height: caption.height * height }}>
      <CaptionBand line={line} currentTimeSec={time} captionStyle={props.captionStyle} layout={props.layout}
        protectedPhrases={[...(props.learning?.idioms ?? []).map((item) => item.phrase), ...(props.learning?.vocab ?? []).map((item) => item.word)]} stationary />
    </div> : null}
  </AbsoluteFill>;
}
