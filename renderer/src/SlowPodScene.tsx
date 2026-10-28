/**
 * Phase 81 (owner 2026-10-28): the slow English podcast Short (9:16) -- one sentence per screen on beige paper: the
 * English line large and bold with the spoken word marked in brand green, its Vietnamese translation underneath.
 */
import React, { useMemo } from "react";
import { AbsoluteFill, Audio, useCurrentFrame, useVideoConfig } from "remotion";
import { activeTokenIndex, buildKaraokeTokens, withScriptPunctuation } from "./karaoke";
import { resolvedMedia } from "./Presenter";
import { lineAt, slideIn } from "./flashcardMath";
import type { EpisodeInputProps } from "./types";

export const PAPER = "#F1E9D8", INK = "#151515", GREEN = "#1F7A4D", MUTED = "#4B463D";
const SANS = "'Montserrat', 'Arial Black', Arial, Helvetica, sans-serif";

/** Beige paper: a warm base, a soft vignette and a faint fibre grain (CSS only). */
export function Paper({ children }: { children?: React.ReactNode }) {
  return <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, #F7F1E3, ${PAPER} 60%, #E2D6BD)` }}>
    <AbsoluteFill style={{ opacity: 0.35, backgroundImage:
      "repeating-linear-gradient(17deg, rgba(120,100,70,0.05) 0 2px, transparent 2px 7px), repeating-linear-gradient(103deg, rgba(120,100,70,0.04) 0 1px, transparent 1px 9px)" }} />
    {children}
  </AbsoluteFill>;
}

function Sentence({ props, index, time, unit }: { props: EpisodeInputProps; index: number; time: number; unit: number }) {
  const line = props.lines[index];
  const tokens = useMemo(() => withScriptPunctuation(buildKaraokeTokens(line), line.text), [line]);
  const active = activeTokenIndex(tokens, time * 1000);
  const enter = slideIn(time, line.startSec, 0.4);
  const size = line.text.length > 70 ? 64 : line.text.length > 40 ? 74 : 84;
  return <div data-slowpod-line={index} style={{ position: "absolute", left: 90 * unit, right: 90 * unit, top: 560 * unit, display: "grid",
    gap: 46 * unit, textAlign: "center", opacity: enter, transform: `translateY(${((1 - enter) * 30 * unit).toFixed(1)}px)` }}>
    <div style={{ fontFamily: SANS, fontWeight: 800, color: INK, fontSize: size * unit, lineHeight: 1.22 }}>
      {tokens.length ? tokens.map((token, at) => <React.Fragment key={`${token.fromMs}-${at}`}>
        <span style={{ color: at === active ? GREEN : INK, textDecoration: at === active ? `underline ${6 * unit}px ${GREEN}` : "none",
          textUnderlineOffset: `${10 * unit}px` }}>{token.text.trim()}</span>{at < tokens.length - 1 ? " " : ""}
      </React.Fragment>) : line.text}
    </div>
    {line.translation ? <div data-slowpod-translation="true" style={{ fontFamily: SANS, fontWeight: 600, color: MUTED, fontSize: 46 * unit,
      lineHeight: 1.35 }}>{line.translation}</div> : null}
  </div>;
}

export function SlowPodScene(props: EpisodeInputProps) {
  const frame = useCurrentFrame(), { fps, height } = useVideoConfig();
  const time = frame / fps, unit = height / 1920;
  const index = lineAt(props.lines, time);
  return <AbsoluteFill data-short-style="slowpod" style={{ overflow: "hidden" }}>
    <Paper />
    {!props.soundtrackPath ? <Audio src={resolvedMedia(props.audioPath)} /> : null}
    <div style={{ position: "absolute", left: 0, right: 0, top: 250 * unit, display: "flex", justifyContent: "center" }}>
      <span style={{ fontFamily: SANS, fontWeight: 800, fontSize: 30 * unit, letterSpacing: "0.12em", color: GREEN, border: `${3 * unit}px solid ${GREEN}`,
        borderRadius: 999, padding: `${10 * unit}px ${30 * unit}px`, background: "rgba(255,255,255,0.55)" }}>SLOW ENGLISH PODCAST</span>
    </div>
    {index >= 0 ? <Sentence props={props} index={index} time={time} unit={unit} /> : null}
    <div style={{ position: "absolute", left: 0, right: 0, top: 1240 * unit, display: "flex", justifyContent: "center", gap: 12 * unit }}>
      {props.lines.map((_, at) => <span key={at} style={{ width: (at === index ? 34 : 12) * unit, height: 12 * unit, borderRadius: 999,
        background: at <= index ? GREEN : "rgba(31,122,77,0.25)" }} />)}
    </div>
  </AbsoluteFill>;
}
