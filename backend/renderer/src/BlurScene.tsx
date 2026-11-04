/**
 * Phase 63 (ENH-045): the "text on a blurred background" Short (9:16) -- the segment's picture (or the brand colours)
 * heavily blurred and darkened behind big centred words that pop in as the narrator says them, the key words in
 * yellow, a gentle drift and a soft fade between segments. The words are the captions, so no caption band is drawn.
 */
import React, { useMemo } from "react";
import { AbsoluteFill, Img, useCurrentFrame, useVideoConfig } from "remotion";
import { resolvedMedia } from "./Presenter";
import { clamp01, voxSegmentAt } from "./voxMath";
import { easeOutBack } from "./voxMotion";
import { blurGroup, fitFont, isKeyWord, keyWordOf, pictureFor, spanWords } from "./shortsMath";
import type { EpisodeInputProps } from "./types";

const YELLOW = "#FFD84D", SANS = "'Arial Black', Arial, Helvetica, sans-serif";

function Backdrop({ url, time, index }: { url: string | null; time: number; index: number }) {
  const drift = Math.sin(time * Math.PI * 2 / 16 + index) * 30, zoom = 1.25 + 0.05 * Math.sin(time * Math.PI * 2 / 20);
  const hue = (index * 23 + time * 4) % 360;
  return <AbsoluteFill style={{ overflow: "hidden" }}>
    {url ? <Img data-blur-picture="true" src={resolvedMedia(url)} style={{ width: "100%", height: "100%", objectFit: "cover",
      filter: "blur(38px) brightness(0.5) saturate(1.25)", transform: `translateX(${drift.toFixed(1)}px) scale(${zoom.toFixed(4)})` }} />
      : <AbsoluteFill data-blur-gradient="true" style={{ background: `linear-gradient(${(160 + hue / 6).toFixed(1)}deg, #0F3D2A, #1F7A4D 55%, #7A6A12)`,
        filter: `hue-rotate(${(Math.sin(time / 6) * 12).toFixed(1)}deg)` }} />}
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0.05), rgba(0,0,0,0.55) 85%)" }} />
  </AbsoluteFill>;
}

export function BlurScene(props: EpisodeInputProps) {
  const frame = useCurrentFrame(), { fps, width, height } = useVideoConfig();
  const payload = props.solo;
  if (!payload || payload.style !== "blur") throw new Error("A blur Short needs its reviewed blur payload");
  const time = frame / fps, aspect = props.layout === "vertical" ? "9:16" : "16:9";
  const index = voxSegmentAt(payload, time);
  const segment = payload.plan.segments[index], span = payload.timeline[index];
  const geometry = payload.geometry.aspects[aspect] ?? Object.values(payload.geometry.aspects)[0];
  const safe = geometry.safe, header = geometry.header;
  const words = useMemo(() => spanWords(props.lines, span.start_sec, span.end_sec), [props.lines, span]);
  const group = blurGroup(words, time);
  const key = keyWordOf(segment.visual);
  const unit = height / 1920;
  const boxWidth = safe.width * width * 0.92;
  const size = fitFont(group.map((word) => word.text).join(" ").length, boxWidth, 4, 54 * unit, 120 * unit);
  const fade = Math.min(clamp01((time - span.start_sec) / 0.3), clamp01((span.end_sec - time) / 0.25) + (index === payload.timeline.length - 1 ? 1 : 0));
  const url = pictureFor(payload, segment);
  const previous = index > 0 ? pictureFor(payload, payload.plan.segments[index - 1]) : null;
  const cross = clamp01((time - span.start_sec) / 0.6);
  return <AbsoluteFill data-blur-scene="true" style={{ overflow: "hidden", background: "#0B1F17", fontFamily: SANS }}>
    {previous && previous !== url && cross < 1 ? <Backdrop url={previous} time={time} index={index - 1} /> : null}
    <AbsoluteFill style={{ opacity: previous && previous !== url ? cross : 1 }}><Backdrop url={url} time={time} index={index} /></AbsoluteFill>
    <div style={{ position: "absolute", left: header.x * width, top: header.y * height, width: header.width * width,
      color: "rgba(255,255,255,0.85)", fontFamily: "Arial, sans-serif", fontWeight: 800, fontSize: 28 * unit, letterSpacing: "0.08em",
      display: "flex", justifyContent: "space-between" }}>
      <span>DAILY BEYOND ENGLISH</span><span>{props.cefrLevel}</span>
    </div>
    <div data-blur-words="true" style={{ position: "absolute", left: (safe.x * width) + (safe.width * width - boxWidth) / 2, width: boxWidth,
      top: (safe.y + safe.height * 0.18) * height, height: safe.height * height * 0.6, display: "flex", flexWrap: "wrap",
      alignContent: "center", justifyContent: "center", gap: `${size * 0.12}px ${size * 0.28}px`, opacity: fade,
      transform: `translateY(${(Math.sin(time * Math.PI * 2 / 9) * 6 * unit).toFixed(2)}px)` }}>
      {group.map((word, i) => {
        const lit = key && isKeyWord(word.text, key);
        return <span key={`${word.startSec}-${i}`} data-blur-word={lit ? "key" : "word"} style={{ fontSize: size, lineHeight: 1.05, color: lit ? YELLOW : "#FFF",
          fontWeight: 900, textShadow: "0 6px 24px rgba(0,0,0,0.55)", opacity: clamp01(word.pop * 2),
          transform: `translateY(${((1 - clamp01(word.pop)) * size * 0.3).toFixed(1)}px) scale(${(0.6 + 0.4 * easeOutBack(word.pop)).toFixed(4)})`,
          display: "inline-block", textTransform: lit ? "uppercase" : undefined }}>{word.text}</span>;
      })}
    </div>
  </AbsoluteFill>;
}
