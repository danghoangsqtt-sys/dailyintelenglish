/**
 * Phase 59 (ENH-041): the VOX motion graphics -- one board per segment, driven by the segment's narration progress:
 * kinetic text with a highlighter, cut-out quotes, collage pictures with slow zoom and a drawn marker, animated
 * diagrams, bar/line charts, timelines and a world map.
 */
import React from "react";
import { Img } from "remotion";
import { resolvedMedia } from "./Presenter";
import type { Rect } from "./explainerLayout";
import type { SoloSegment, Visual } from "./soloTypes";
import {
  chartHeights, clamp01, collageTilt, easeOut, formatValue, highlightRange, highlightSweep, kenBurns, revealedWords,
  staggered, timelinePositions,
} from "./voxMath";
import { countries, countryName, countryPath, project, viewFor } from "./voxMap";

export const INK = "#1E2A26", PAPER = "#F6EFDF", ACCENT = "#E8483B", HIGHLIGHT = "#FFD84D", GREEN = "#1F7A4D";
const SERIF = "Georgia, 'Times New Roman', serif", SANS = "Arial, Helvetica, sans-serif";

type Box = { left: number; top: number; width: number; height: number };
type Props = { segment: SoloSegment & { photoUrl?: string; activityUrl?: string }; box: Box; progress: number; index: number };

/** Words of a text with the highlighter sweeping behind `phrase` once it is on screen. */
function KineticText({ text, phrase, progress, size, font, color = INK }: {
  text: string; phrase?: string; progress: number; size: number; font: string; color?: string;
}) {
  const words = text.split(/\s+/).filter(Boolean), shown = revealedWords(text, progress);
  const range = phrase ? highlightRange(text, phrase) : null, sweep = highlightSweep(progress, range, words.length);
  return <span style={{ fontFamily: font, fontSize: size, lineHeight: 1.22, color }}>
    {words.map((word, i) => {
      const lit = range && i >= range[0] && i < range[1];
      const appear = i < shown ? 1 : 0;
      return <span key={i} data-vox-word={lit ? "highlight" : "word"} style={{
        opacity: appear, display: "inline-block", marginRight: size * 0.26,
        transform: `translateY(${(1 - appear) * size * 0.3}px)`,
        backgroundImage: lit ? `linear-gradient(transparent 52%, ${HIGHLIGHT} 52%, ${HIGHLIGHT} 92%, transparent 92%)` : undefined,
        backgroundRepeat: "no-repeat", backgroundSize: lit ? `${Math.round(sweep * 100)}% 100%` : undefined,
      }}>{word}</span>;
    })}
  </span>;
}

function Collage({ url, caption, progress, index, box, region }: {
  url?: string; caption?: string; progress: number; index: number; box: Box; region?: Rect;
}) {
  const motion = kenBurns(progress, index), tilt = collageTilt(index);
  const width = Math.min(box.width * 0.72, box.height * 1.55), height = width / (16 / 9);
  const left = box.left + (box.width - width) / 2, top = box.top + (box.height - height - (caption ? box.height * 0.12 : 0)) / 2;
  const marker = region ?? { x: 0.58, y: 0.3, width: 0.26, height: 0.4 };
  const draw = easeOut((progress - 0.25) / 0.35);
  const r = { cx: (marker.x + marker.width / 2) * width, cy: (marker.y + marker.height / 2) * height,
    rx: marker.width * width * 0.62, ry: marker.height * height * 0.62 };
  return <>
    <div data-vox-visual="collage" style={{ position: "absolute", left, top, width, height, padding: width * 0.018, background: "#FFFFFF",
      boxShadow: "0 18px 38px rgba(30,42,38,0.32)", transform: `rotate(${tilt}deg)`, boxSizing: "border-box" }}>
      <div style={{ width: "100%", height: "100%", overflow: "hidden", position: "relative", background: "#D9CDB3" }}>
        {url ? <Img src={resolvedMedia(url)} style={{ width: "100%", height: "100%", objectFit: "cover",
          transform: `translate(${motion.x}%, ${motion.y}%) scale(${motion.scale})`, filter: "saturate(0.92) contrast(1.04)" }} />
          : <div style={{ display: "grid", placeItems: "center", height: "100%", fontFamily: SANS, color: INK, fontSize: height * 0.07 }}>
            Add the picture for this segment</div>}
        <svg width={width} height={height} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
          <ellipse {...r} fill="none" stroke={ACCENT} strokeWidth={Math.max(3, width * 0.006)} strokeLinecap="round"
            pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} />
        </svg>
      </div>
      {/* a strip of tape holds the cut-out on the paper */}
      <div style={{ position: "absolute", left: width * 0.42, top: -height * 0.05, width: width * 0.16, height: height * 0.1,
        background: "rgba(255,240,180,0.75)", transform: "rotate(-3deg)" }} />
    </div>
    {caption ? <div style={{ position: "absolute", left: box.left, width: box.width, top: top + height + box.height * 0.04,
      textAlign: "center", fontFamily: SANS, fontWeight: 700, fontSize: box.height * 0.07, color: INK }}>
      <span style={{ background: PAPER, padding: "0.1em 0.4em", boxShadow: "0 4px 10px rgba(0,0,0,0.12)" }}>{caption}</span>
    </div> : null}
  </>;
}

function Title({ text, box, progress }: { text?: string; box: Box; progress: number }) {
  if (!text) return null;
  const enter = easeOut(progress / 0.12);
  return <div style={{ position: "absolute", left: box.left, top: box.top, width: box.width, fontFamily: SANS, fontWeight: 800,
    fontSize: box.height * 0.085, color: INK, letterSpacing: "-0.01em", opacity: enter, transform: `translateY(${(1 - enter) * 12}px)` }}>
    {text}<div style={{ width: `${Math.round(enter * 14)}%`, height: box.height * 0.012, background: ACCENT, marginTop: box.height * 0.012 }} />
  </div>;
}

function Chart({ visual, box, progress }: { visual: Extract<Visual, { kind: "chart" }>; box: Box; progress: number }) {
  const top = box.height * (visual.title ? 0.2 : 0.06), height = box.height - top - box.height * 0.16, width = box.width;
  const { heights } = chartHeights(visual.items.map((item) => item.value));
  const n = visual.items.length, slot = width / n, barWidth = slot * 0.56, font = Math.max(14, box.height * 0.055);
  const points = visual.items.map((_, i) => [slot * (i + 0.5), height * (1 - heights[i])] as [number, number]);
  const lineDraw = easeOut((progress - 0.08) / 0.6);
  return <svg data-vox-visual="chart" style={{ position: "absolute", left: box.left, top: box.top + top, overflow: "visible" }} width={width} height={height}>
    <line x1={0} x2={width} y1={height} y2={height} stroke={INK} strokeWidth={2} />
    {visual.chart_type === "line" ? <>
      <polyline points={points.map((point) => point.join(",")).join(" ")} fill="none" stroke={ACCENT} strokeWidth={Math.max(3, height * 0.018)}
        strokeLinejoin="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - lineDraw} />
      {points.map(([x, y], i) => {
        const shown = staggered(progress, i, n);
        return <g key={i} opacity={shown}>
          <circle cx={x} cy={y} r={Math.max(5, height * 0.025)} fill={ACCENT} />
          <text x={x} y={y - font * 0.7} textAnchor="middle" fontFamily={SANS} fontWeight={800} fontSize={font} fill={INK}>
            {formatValue(visual.items[i].value, visual.unit)}</text>
        </g>;
      })}
    </> : visual.items.map((item, i) => {
      const grow = staggered(progress, i, n), barHeight = height * heights[i] * grow;
      return <g key={i}>
        <rect x={slot * i + (slot - barWidth) / 2} y={height - barHeight} width={barWidth} height={barHeight}
          fill={i === n - 1 ? ACCENT : GREEN} rx={4} />
        <text x={slot * (i + 0.5)} y={height - barHeight - font * 0.4} textAnchor="middle" fontFamily={SANS} fontWeight={800}
          fontSize={font} fill={INK} opacity={grow}>{formatValue(item.value, visual.unit)}</text>
      </g>;
    })}
    {visual.items.map((item, i) => <text key={`l${i}`} x={slot * (i + 0.5)} y={height + font * 1.3} textAnchor="middle"
      fontFamily={SANS} fontSize={font * 0.9} fill={INK}>{item.label}</text>)}
  </svg>;
}

function Timeline({ visual, box, progress }: { visual: Extract<Visual, { kind: "timeline" }>; box: Box; progress: number }) {
  const positions = timelinePositions(visual.events.length), y = box.height * 0.55, font = Math.max(14, box.height * 0.055);
  const draw = easeOut((progress - 0.05) / 0.5);
  return <svg data-vox-visual="timeline" style={{ position: "absolute", left: box.left, top: box.top, overflow: "visible" }} width={box.width} height={box.height}>
    <line x1={box.width * 0.04} x2={box.width * (0.04 + 0.92 * draw)} y1={y} y2={y} stroke={INK} strokeWidth={Math.max(3, box.height * 0.012)} strokeLinecap="round" />
    {visual.events.map((event, i) => {
      const x = positions[i] * box.width, shown = staggered(progress, i, visual.events.length), up = i % 2 === 0;
      return <g key={i} opacity={shown} transform={`translate(0, ${(1 - shown) * 10})`}>
        <circle cx={x} cy={y} r={Math.max(7, box.height * 0.028)} fill={i === visual.events.length - 1 ? ACCENT : GREEN} stroke={PAPER} strokeWidth={3} />
        <text x={x} y={up ? y - font * 1.6 : y + font * 2.1} textAnchor="middle" fontFamily={SANS} fontWeight={800} fontSize={font * 1.05} fill={ACCENT}>{event.when}</text>
        <text x={x} y={up ? y - font * 0.6 : y + font * 3.2} textAnchor="middle" fontFamily={SANS} fontSize={font * 0.85} fill={INK}>{event.label}</text>
      </g>;
    })}
  </svg>;
}

function WorldMap({ visual, box, progress }: { visual: Extract<Visual, { kind: "map" }>; box: Box; progress: number }) {
  const top = visual.title ? box.height * 0.18 : 0, width = box.width, height = box.height - top;
  const view = viewFor(visual.places, width / height);
  const lit = new Set((visual.highlight_countries ?? []).map(countryName).filter(Boolean));
  const appear = easeOut(progress / 0.25), font = Math.max(13, box.height * 0.05);
  const pins = visual.places.map((place) => project([place.lon, place.lat], view, width, height));
  const route = visual.route && visual.route.length === 2 ? [pins[visual.route[0]], pins[visual.route[1]]] : null;
  const draw = easeOut((progress - 0.3) / 0.45);
  const arc = route ? (() => {
    const [[x1, y1], [x2, y2]] = route, mx = (x1 + x2) / 2, my = Math.min(y1, y2) - Math.hypot(x2 - x1, y2 - y1) * 0.28;
    return `M${x1},${y1} Q${mx},${my} ${x2},${y2}`;
  })() : null;
  return <svg data-vox-visual="map" style={{ position: "absolute", left: box.left, top: box.top + top, overflow: "hidden", borderRadius: 14 }}
    width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
    <rect width={width} height={height} fill="#CFE3E6" />
    {countries().map((country) => {
      const path = countryPath(country, view, width, height);
      return path ? <path key={country.name} d={path} fill={lit.has(country.name) ? HIGHLIGHT : "#EAE0C8"} stroke="#9C9077"
        strokeWidth={0.8} opacity={lit.has(country.name) ? appear : 1} /> : null;
    })}
    {arc ? <path d={arc} fill="none" stroke={ACCENT} strokeWidth={Math.max(3, height * 0.012)} strokeDasharray="1" pathLength={1}
      strokeDashoffset={1 - draw} strokeLinecap="round" /> : null}
    {pins.map(([x, y], i) => {
      const shown = staggered(progress, i, pins.length);
      return <g key={i} opacity={shown}>
        <circle cx={x} cy={y} r={Math.max(6, height * 0.022)} fill={ACCENT} stroke="#FFFFFF" strokeWidth={3} />
        <text x={x} y={y - font * 0.9} textAnchor="middle" fontFamily={SANS} fontWeight={800} fontSize={font} fill={INK}
          stroke={PAPER} strokeWidth={4} paintOrder="stroke">{visual.places[i].name}</text>
      </g>;
    })}
  </svg>;
}

function Diagram({ visual, box, progress }: { visual: Extract<Visual, { kind: "diagram" }>; box: Box; progress: number }) {
  const top = visual.title ? box.height * 0.2 : 0, n = visual.nodes.length, comparison = visual.template === "comparison";
  const columns = comparison ? 2 : Math.min(n, 4), rows = Math.ceil(n / columns), gap = box.width * 0.025;
  const cellWidth = (box.width - gap * (columns - 1)) / columns, cellHeight = Math.min((box.height - top - gap * (rows - 1)) / rows, box.height * 0.62);
  const font = Math.max(14, Math.min(cellHeight * 0.16, box.height * 0.06));
  return <div data-vox-visual="diagram" style={{ position: "absolute", left: box.left, top: box.top + top, width: box.width }}>
    {visual.nodes.map((node, i) => {
      const shown = staggered(progress, i, n), column = i % columns, row = Math.floor(i / columns);
      return <div key={node.id} style={{ position: "absolute", left: column * (cellWidth + gap), top: row * (cellHeight + gap),
        width: cellWidth, height: cellHeight, boxSizing: "border-box", padding: font * 0.7, background: "#FFFFFF",
        border: `3px solid ${INK}`, borderRadius: 10, boxShadow: `6px 6px 0 ${i % 2 ? GREEN : ACCENT}`,
        opacity: shown, transform: `scale(${0.92 + 0.08 * shown})`, fontFamily: SANS, color: INK, overflow: "hidden" }}>
        <div style={{ fontWeight: 800, fontSize: font * 1.05 }}>{visual.template === "steps" ? `${i + 1}. ` : ""}{node.label}</div>
        {node.detail ? <div style={{ fontSize: font * 0.85, marginTop: font * 0.3 }}>{node.detail}</div> : null}
        {!comparison && column < columns - 1 && i < n - 1 ? <div style={{ position: "absolute", right: -gap * 0.9, top: "45%",
          fontSize: font * 1.4, color: ACCENT, fontWeight: 800 }}>→</div> : null}
      </div>;
    })}
  </div>;
}

export function VoxVisual({ segment, box, progress, index }: Props) {
  const visual = segment.visual;
  const title = "title" in visual ? visual.title : undefined;
  const inner = (offset: number): Box => ({ ...box, top: box.top + offset, height: box.height - offset });
  if (visual.kind === "photo" || visual.kind === "activity") {
    const url = visual.kind === "photo" ? segment.photoUrl : segment.activityUrl;
    const region = visual.kind === "photo" ? visual.important_regions?.[0] : undefined;
    return <Collage url={url} caption={visual.caption} progress={progress} index={index} box={box} region={region} />;
  }
  if (visual.kind === "quote") {
    // as large as the board allows: short quotes get big type, long ones wrap smaller
    const size = Math.max(22, Math.min(box.height * 0.12, (box.width * 0.85) / Math.sqrt(Math.max(16, visual.text.length))));
    const tilt = collageTilt(index) * 0.5;
    return <div data-vox-visual="quote" style={{ position: "absolute", left: box.left + box.width * 0.06, top: box.top + box.height * 0.08,
      width: box.width * 0.88, padding: `${size * 0.7}px ${size * 0.9}px`, boxSizing: "border-box", background: "#FFFDF6",
      boxShadow: "0 16px 34px rgba(30,42,38,0.25)", transform: `rotate(${tilt}deg)`, clipPath: "polygon(0 2%, 3% 0, 97% 1%, 100% 3%, 99% 97%, 96% 100%, 2% 99%, 0 96%)" }}>
      <div style={{ fontFamily: SERIF, fontSize: size * 2.2, color: ACCENT, lineHeight: 0.6, height: size * 0.9 }}>“</div>
      <KineticText text={visual.text} phrase={visual.highlight} progress={progress} size={size} font={SERIF} />
      {visual.attribution ? <div style={{ marginTop: size * 0.5, fontFamily: SANS, fontSize: size * 0.55, color: INK, opacity: clamp01(progress * 2) }}>
        — {visual.attribution}</div> : null}
    </div>;
  }
  const offset = title ? box.height * 0.2 : 0;
  return <>
    <Title text={title} box={box} progress={progress} />
    {visual.kind === "text_card" ? <div data-vox-visual="text_card" style={{ position: "absolute", left: box.left, top: box.top + offset + box.height * 0.04, width: box.width }}>
      {(visual.bullets ?? []).map((bullet, i) => {
        const shown = staggered(progress, i, (visual.bullets ?? []).length + (visual.emphasis ? 1 : 0));
        return <div key={i} style={{ display: "flex", gap: 14, marginBottom: box.height * 0.035, opacity: shown,
          transform: `translateX(${(1 - shown) * -18}px)`, fontFamily: SANS, fontSize: Math.max(18, box.height * 0.07), color: INK }}>
          <span style={{ color: ACCENT, fontWeight: 800 }}>■</span><span>{bullet}</span></div>;
      })}
      {visual.emphasis ? <div style={{ marginTop: box.height * ((visual.bullets ?? []).length ? 0.04 : 0.12) }}>
        {/* a card without bullets makes its emphasis the big kinetic line of the board */}
        <KineticText text={visual.emphasis} phrase={visual.emphasis} progress={clamp01((progress - 0.08) / 0.5)}
          size={Math.max(20, box.height * ((visual.bullets ?? []).length ? 0.085 : 0.16))} font={SANS} /></div> : null}
    </div> : null}
    {visual.kind === "chart" ? <Chart visual={visual} box={box} progress={progress} /> : null}
    {visual.kind === "timeline" ? <Timeline visual={visual} box={inner(offset)} progress={progress} /> : null}
    {visual.kind === "map" ? <WorldMap visual={visual} box={box} progress={progress} /> : null}
    {visual.kind === "diagram" ? <Diagram visual={visual} box={box} progress={progress} /> : null}
  </>;
}
