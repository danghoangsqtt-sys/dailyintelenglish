/**
 * Phase 63 (ENH-045): the English news Short (9:16) -- a narrator's voice over news pictures that change with every
 * fact (slow zoom/pan and the Phase 61 transitions), a "BREAKING · ENGLISH NEWS" band, the headline as a lower third,
 * the key word popping up, a ticker crawling the headlines, and karaoke captions. Charts, maps, timelines and diagrams
 * are drawn as a white card over the picture.
 */
import React, { useMemo } from "react";
import { AbsoluteFill, Img, useCurrentFrame, useVideoConfig } from "remotion";
import { CaptionBand } from "./CaptionBand";
import { resolvedMedia } from "./Presenter";
import { VoxVisual } from "./VoxVisual";
import { clamp01, easeOut, kenBurns, voxSegmentAt } from "./voxMath";
import { easeOutBack, smoothProgress, transitionAt, transitionStyles } from "./voxMotion";
import { drawsCard, headlineOf, keyWordOf, newsPicture, spanWords, tickerOffset } from "./shortsMath";
import type { EpisodeInputProps } from "./types";
import type { SoloSegment } from "./soloTypes";

const RED = "#D7262E", INK = "#111418", YELLOW = "#FFD84D", SANS = "Arial, Helvetica, sans-serif";

function Picture({ url, progress, index }: { url: string | null; progress: number; index: number }) {
  const motion = kenBurns(progress, index);
  return <AbsoluteFill style={{ overflow: "hidden", background: "linear-gradient(165deg,#133b2a,#061813)" }}>
    {url ? <Img data-news-picture="true" src={resolvedMedia(url)} style={{ width: "100%", height: "100%", objectFit: "cover",
      transform: `translate(${motion.x}%, ${motion.y}%) scale(${(motion.scale * 1.04).toFixed(4)})` }} /> : null}
    {/* darken the top and the lower half so the bands and captions read on any picture */}
    <AbsoluteFill style={{ background: "linear-gradient(to bottom, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 22%, rgba(0,0,0,0) 45%, rgba(0,0,0,0.78) 100%)" }} />
  </AbsoluteFill>;
}

export function NewsScene(props: EpisodeInputProps) {
  const frame = useCurrentFrame(), { fps, width, height } = useVideoConfig();
  const payload = props.solo;
  if (!payload || payload.style !== "news") throw new Error("A news Short needs its reviewed news payload");
  const time = frame / fps, aspect = props.layout === "vertical" ? "9:16" : "16:9";
  const index = voxSegmentAt(payload, time);
  const segment = payload.plan.segments[index], span = payload.timeline[index];
  const geometry = payload.geometry.aspects[aspect] ?? Object.values(payload.geometry.aspects)[0];
  const board = geometry.board ?? geometry.safe, caption = geometry.caption, header = geometry.header;
  const line = props.lines.find((item) => time >= item.startSec && time < item.endSec);
  const words = useMemo(() => spanWords(props.lines, span.start_sec, span.end_sec), [props.lines, span]);
  const progress = words.length ? smoothProgress(words, time) : clamp01((time - span.start_sec) / Math.max(0.01, span.end_sec - span.start_sec));
  const running = transitionAt(payload.timeline, index, time);
  const layer = (at: number, style: React.CSSProperties, prog: number) => <AbsoluteFill key={at} style={style}>
    <Picture url={newsPicture(payload, at)} progress={prog} index={at} />
  </AbsoluteFill>;
  let pictures: React.ReactNode = layer(index, {}, progress);
  if (running) {
    const styles = transitionStyles(running.kind, running.t, width);
    const leaving = layer(index - 1, styles.leaving, 1), entering = layer(index, styles.entering, progress);
    pictures = styles.top === "entering" ? [leaving, entering] : [entering, leaving];
  }
  const unit = height / 1920;
  const enter = easeOutBack((time - span.start_sec) / 0.35);
  const headline = headlineOf(segment.visual), key = keyWordOf(segment.visual);
  // the headline grows upward from just above the captions; a chart/map card ends above the headline's area
  const lowerBottom = height - caption.y * height + 14 * unit;
  const cardBottom = (caption.y - 0.14) * height;
  const boxTop = board.y * height + 30 * unit;
  const box = { left: board.x * width, top: boxTop, width: board.width * width, height: Math.max(200 * unit, cardBottom - boxTop - 18 * unit) };
  const headlineSize = (text: string) => Math.max(30, (text.length > 60 ? 36 : 44) * unit);
  const ticker = payload.plan.segments.map((item) => headlineOf(item.visual)).filter(Boolean).join("   •   ") + "   •   ";
  const tickerWidth = ticker.length * 15 * unit;
  const keyPop = easeOutBack((progress - 0.25) / 0.12);
  return <AbsoluteFill data-news-scene="true" style={{ overflow: "hidden", background: INK, fontFamily: SANS }}>
    {pictures}
    {/* the news band */}
    <div style={{ position: "absolute", left: header.x * width, top: header.y * height, width: header.width * width,
      display: "flex", alignItems: "center", gap: 14 * unit }}>
      <span style={{ background: RED, color: "#FFF", fontWeight: 900, fontSize: 30 * unit, padding: `${6 * unit}px ${16 * unit}px`,
        letterSpacing: "0.04em", display: "inline-flex", alignItems: "center", gap: 10 * unit }}>
        <span style={{ width: 14 * unit, height: 14 * unit, borderRadius: "50%", background: "#FFF", opacity: 0.4 + 0.6 * Math.abs(Math.sin(time * 3)) }} />
        BREAKING</span>
      <span style={{ color: "#FFF", fontWeight: 800, fontSize: 28 * unit, textShadow: "0 2px 6px rgba(0,0,0,0.6)" }}>ENGLISH NEWS · {props.cefrLevel}</span>
    </div>
    {drawsCard(segment.visual) ? <div data-news-card="true" style={{ position: "absolute", left: box.left - 18 * unit, top: box.top - 18 * unit,
      width: box.width + 36 * unit, height: box.height + 36 * unit, background: "rgba(255,253,246,0.95)", borderRadius: 18 * unit,
      boxShadow: "0 18px 40px rgba(0,0,0,0.35)", opacity: clamp01((time - span.start_sec) / 0.3),
      transform: `scale(${(0.9 + 0.1 * easeOut((time - span.start_sec) / 0.4)).toFixed(4)})` }}>
      <VoxVisual segment={segment as SoloSegment} box={{ left: 18 * unit, top: 18 * unit, width: box.width, height: box.height }}
        progress={progress} index={index} />
    </div> : null}
    {/* the headline as a lower third */}
    {headline ? <div data-news-headline="true" style={{ position: "absolute", left: caption.x * width - 20 * unit, width: caption.width * width + 40 * unit,
      bottom: lowerBottom, transform: `translateX(${((1 - clamp01(enter)) * -60 * unit).toFixed(1)}px)`, opacity: clamp01(enter * 1.5) }}>
      <div style={{ background: "#FFF", color: INK, fontWeight: 900, fontSize: headlineSize(headline), lineHeight: 1.15,
        display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden",
        padding: `${10 * unit}px ${18 * unit}px`, borderLeft: `${12 * unit}px solid ${RED}`, boxShadow: "0 8px 20px rgba(0,0,0,0.35)" }}>
        {headline}</div>
      {key ? <span data-news-key="true" style={{ display: "inline-block", marginTop: 10 * unit, background: YELLOW, color: INK, fontWeight: 900,
        fontSize: 30 * unit, padding: `${4 * unit}px ${14 * unit}px`, transform: `scale(${Math.max(0, keyPop).toFixed(4)})`,
        transformOrigin: "0% 50%" }}>KEY WORD · {key}</span> : null}
    </div> : null}
    {line ? <div data-solo-caption="true" style={{ position: "absolute", left: caption.x * width, top: caption.y * height,
      width: caption.width * width, height: caption.height * height }}>
      <CaptionBand line={line} currentTimeSec={time} captionStyle={props.captionStyle} layout={props.layout}
        protectedPhrases={[...(props.learning?.idioms ?? []).map((item) => item.phrase), ...(props.learning?.vocab ?? []).map((item) => item.word)]} stationary />
    </div> : null}
    {/* the ticker under the captions */}
    <div data-news-ticker="true" style={{ position: "absolute", left: 0, right: 0, top: (caption.y + caption.height) * height + 16 * unit,
      height: 46 * unit, background: "rgba(10,12,16,0.85)", overflow: "hidden", display: "flex", alignItems: "center" }}>
      <span style={{ background: YELLOW, color: INK, fontWeight: 900, fontSize: 24 * unit, padding: `0 ${14 * unit}px`, height: "100%",
        display: "flex", alignItems: "center", flexShrink: 0, position: "relative", zIndex: 2, whiteSpace: "nowrap" }}>DAILY BEYOND ENGLISH</span>
      <div style={{ whiteSpace: "nowrap", color: "#FFF", fontSize: 26 * unit, fontWeight: 700, transform: `translateX(${tickerOffset(time, tickerWidth).toFixed(1)}px)` }}>
        {ticker}{ticker}</div>
    </div>
  </AbsoluteFill>;
}
