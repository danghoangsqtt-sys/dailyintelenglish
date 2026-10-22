/**
 * Phase 65 (ENH-047): the two-character conversation Shorts (9:16), drawn from the script lines themselves --
 * chat: a generic phone chat (no brand look) with initials avatars, typing dots before each message, bubbles
 * appearing with their line and the spoken word highlighted, scrolling up as it fills;
 * would you rather: two halves (red / blue) with the options of the asking line, a timer until the answer, then
 * the chosen half growing with a check while the reason is the caption.
 */
import React from "react";
import { AbsoluteFill, Audio, useCurrentFrame, useVideoConfig } from "remotion";
import { CaptionBand } from "./CaptionBand";
import { resolvedMedia } from "./Presenter";
import { clamp01, easeOut } from "./voxMath";
import { easeOutBack } from "./voxMotion";
import { chatState, initials, roundAt, sideOf, timerShare, wyrRounds } from "./interactMath";
import type { EpisodeInputProps } from "./types";

const SANS = "Arial, Helvetica, sans-serif", HEAVY = "'Arial Black', Arial, Helvetica, sans-serif";
const YELLOW = "#FFD84D", INK = "#14231C";
const COLORS = ["#1F7A4D", "#2B6CB0"];

function Header({ label, unit, cefr }: { label: string; unit: number; cefr: string }) {
  return <div style={{ position: "absolute", left: 60 * unit, right: 60 * unit, top: 150 * unit, display: "flex", justifyContent: "space-between",
    alignItems: "center" }}>
    <span style={{ background: YELLOW, color: INK, fontFamily: HEAVY, fontSize: 30 * unit, padding: `${6 * unit}px ${16 * unit}px`, borderRadius: 10 * unit,
      whiteSpace: "nowrap" }}>{label}</span>
    <span style={{ color: "#FFF", fontWeight: 800, fontSize: 26 * unit, whiteSpace: "nowrap" }}>DAILY BEYOND ENGLISH · {cefr}</span>
  </div>;
}

function Chat({ props, time, unit }: { props: EpisodeInputProps; time: number; unit: number }) {
  const { width } = useVideoConfig();
  const lines = props.lines;
  const { shown, typing } = chatState(lines, time);
  const name = (id: string) => props.speakers.find((speaker) => speaker.id === id)?.name ?? "?";
  const top = 260 * unit, bottomLimit = 1380 * unit, bubbleGap = 22 * unit;
  // rough bubble heights to keep the newest message in view (each ~34 characters per line)
  const heights = lines.map((line) => (Math.ceil(line.text.length / 30) * 58 + 56) * unit);
  const used = heights.slice(0, shown).reduce((sum, value) => sum + value + bubbleGap, 0) + (typing ? 120 * unit : 0);
  const scroll = Math.max(0, used - (bottomLimit - top));
  const phone = { left: 70 * unit, width: width - 140 * unit };
  let y = top - scroll;
  return <>
    <div style={{ position: "absolute", left: phone.left - 20 * unit, width: phone.width + 40 * unit, top: 230 * unit, height: 1190 * unit,
      borderRadius: 40 * unit, background: "rgba(255,255,255,0.06)", border: `${3 * unit}px solid rgba(255,255,255,0.15)` }} />
    <div style={{ position: "absolute", left: 0, right: 0, top: 240 * unit, height: 1170 * unit, overflow: "hidden" }}>
      {lines.slice(0, shown).map((line, i) => {
        const left = sideOf(lines, line.speakerId) === "left";
        const at = y - 240 * unit;
        y += heights[i] + bubbleGap;
        const pop = easeOutBack((time - line.startSec) / 0.3);
        const speaking = time >= line.startSec && time < line.endSec;
        return <div key={i} data-chat-bubble={left ? "left" : "right"} style={{ position: "absolute", top: at, left: phone.left, width: phone.width,
          display: "flex", flexDirection: left ? "row" : "row-reverse", gap: 14 * unit, alignItems: "flex-end",
          transform: `scale(${Math.max(0, Math.min(1.1, pop)).toFixed(4)})`, transformOrigin: left ? "0% 100%" : "100% 100%" }}>
          <span style={{ width: 70 * unit, height: 70 * unit, borderRadius: "50%", background: COLORS[left ? 0 : 1], color: "#FFF", flexShrink: 0,
            display: "grid", placeItems: "center", fontFamily: HEAVY, fontSize: 28 * unit }}>{initials(name(line.speakerId))}</span>
          <div style={{ maxWidth: "74%", background: left ? "#FFFFFF" : "#DFF7E8", color: INK, borderRadius: 30 * unit,
            borderBottomLeftRadius: left ? 8 * unit : 30 * unit, borderBottomRightRadius: left ? 30 * unit : 8 * unit,
            padding: `${16 * unit}px ${22 * unit}px`, fontFamily: SANS, fontSize: 44 * unit, lineHeight: 1.25,
            boxShadow: speaking ? `0 0 0 ${5 * unit}px ${YELLOW}` : "0 6px 14px rgba(0,0,0,0.2)" }}>
            <div style={{ fontSize: 26 * unit, fontWeight: 800, color: COLORS[left ? 0 : 1], marginBottom: 4 * unit }}>{name(line.speakerId)}</div>
            {line.text}</div>
        </div>;
      })}
      {typing ? <div data-chat-typing="true" style={{ position: "absolute", top: y - 240 * unit, left: phone.left, width: phone.width, display: "flex",
        flexDirection: sideOf(lines, typing) === "left" ? "row" : "row-reverse", gap: 14 * unit }}>
        <span style={{ width: 70 * unit, height: 70 * unit, borderRadius: "50%", background: COLORS[sideOf(lines, typing) === "left" ? 0 : 1] }} />
        <div style={{ background: "rgba(255,255,255,0.85)", borderRadius: 30 * unit, padding: `${22 * unit}px ${26 * unit}px`, display: "flex", gap: 10 * unit }}>
          {[0, 1, 2].map((dot) => <span key={dot} style={{ width: 16 * unit, height: 16 * unit, borderRadius: "50%", background: "#6B7A72",
            opacity: 0.35 + 0.65 * Math.abs(Math.sin(time * 6 + dot)) }} />)}
        </div>
      </div> : null}
    </div>
  </>;
}

function WouldYouRather({ props, time, unit }: { props: EpisodeInputProps; time: number; unit: number }) {
  const { width } = useVideoConfig();
  const lines = props.lines, rounds = wyrRounds(lines), current = roundAt(rounds, lines, time);
  if (current < 0) return <div style={{ position: "absolute", left: 80 * unit, right: 80 * unit, top: 560 * unit, textAlign: "center", fontFamily: HEAVY,
    color: "#FFF", fontSize: 96 * unit, lineHeight: 1.1 }}>WOULD YOU RATHER…?</div>;
  const round = rounds[current];
  const question = lines[round.question], answer = round.answer !== null ? lines[round.answer] : null;
  const decided = answer !== null && time >= answer.startSec && round.chosen !== null;
  const timer = answer ? timerShare(time, question.endSec, answer.startSec) : null;
  const grow = decided ? easeOut((time - answer!.startSec) / 0.5) : 0;
  const half = (i: 0 | 1) => {
    const chosen = decided && round.chosen === i, other = decided && round.chosen !== i;
    const pop = easeOutBack((time - question.startSec - 0.6 - i * 0.5) / 0.35);
    const heightShare = 0.5 + (chosen ? 0.12 : other ? -0.12 : 0) * grow;
    return <div key={i} data-wyr-option={chosen ? "chosen" : other ? "other" : "open"} style={{ position: "relative", height: `${(heightShare * 100).toFixed(2)}%`,
      background: i === 0 ? "#D7263D" : "#1E5BD8", display: "grid", placeItems: "center", padding: `0 ${60 * unit}px`, textAlign: "center",
      opacity: other ? 1 - 0.45 * grow : 1 }}>
      <div style={{ fontFamily: HEAVY, color: "#FFF", fontSize: (round.options[i].length > 28 ? 64 : 80) * unit, lineHeight: 1.1,
        transform: `scale(${Math.max(0, Math.min(1.15, pop)).toFixed(4)})`, textShadow: "0 8px 22px rgba(0,0,0,0.3)" }}>
        {chosen ? "✅ " : ""}{round.options[i]}</div>
    </div>;
  };
  return <>
    <div style={{ position: "absolute", left: 0, right: 0, top: 230 * unit, height: 1150 * unit, display: "flex", flexDirection: "column" }}>
      {half(0)}{half(1)}
    </div>
    <div style={{ position: "absolute", left: width / 2 - 95 * unit, top: (230 + 1150 / 2 - 95) * unit, width: 190 * unit, height: 190 * unit,
      borderRadius: "50%", background: "#FFF", display: "grid", placeItems: "center", fontFamily: HEAVY, fontSize: timer !== null ? 90 * unit : 52 * unit,
      color: INK, boxShadow: "0 10px 30px rgba(0,0,0,0.35)" }} data-wyr-center={timer !== null ? "timer" : "or"}>
      {timer !== null ? Math.max(1, 3 - Math.floor(timer * 3)) : "OR"}</div>
  </>;
}

export function ChatScene(props: EpisodeInputProps) {
  const frame = useCurrentFrame(), { fps, height } = useVideoConfig();
  const time = frame / fps, unit = height / 1920, style = props.shortStyle;
  const line = props.lines.find((item) => time >= item.startSec && time < item.endSec);
  const captionTop = 1430 * unit;
  return <AbsoluteFill data-conversation-short={style} style={{ overflow: "hidden", fontFamily: SANS,
    background: style === "wyr" ? "#111827" : "linear-gradient(170deg, #0F3D2A, #1F7A4D 55%, #0B2A1E)" }}>
    {!props.soundtrackPath ? <Audio src={resolvedMedia(props.audioPath)} /> : null}
    <Header label={style === "wyr" ? "WOULD YOU RATHER" : "ENGLISH CHAT"} unit={unit} cefr={props.cefrLevel} />
    {style === "wyr" ? <WouldYouRather props={props} time={time} unit={unit} /> : <Chat props={props} time={time} unit={unit} />}
    {line && style === "wyr" ? <div data-solo-caption="true" style={{ position: "absolute", left: 120 * unit, right: 120 * unit, top: captionTop, height: 260 * unit }}>
      <CaptionBand line={line} currentTimeSec={time} captionStyle={props.captionStyle} layout={props.layout}
        protectedPhrases={[...(props.learning?.idioms ?? []).map((item) => item.phrase), ...(props.learning?.vocab ?? []).map((item) => item.word)]} stationary />
    </div> : null}
    {style === "chat" ? <div style={{ position: "absolute", left: 0, right: 0, top: 1440 * unit, textAlign: "center", color: "rgba(255,255,255,0.8)",
      fontFamily: SANS, fontWeight: 700, fontSize: 30 * unit, opacity: clamp01(time / 1) }}>Read along and learn real texting English</div> : null}
  </AbsoluteFill>;
}
