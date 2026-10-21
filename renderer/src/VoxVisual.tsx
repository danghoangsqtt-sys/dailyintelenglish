/**
 * Phase 59 (ENH-041): the VOX motion graphics -- one board per segment, driven by the segment's narration progress:
 * kinetic text with a highlighter, cut-out quotes, collage pictures with slow zoom and a drawn marker, animated
 * diagrams, bar/line charts, timelines and a world map.
 * Phase 61 (ENH-043): bouncy words, hand-drawn underlines and arrows, numbers counting up, pins dropping in and a map
 * that flies in from the whole world; the title is drawn by the scene (`VoxTitle`) so it can morph between segments.
 */
import React from "react";
import { Img } from "remotion";
import { resolvedMedia } from "./Presenter";
import type { Rect } from "./explainerLayout";
import type { SoloSegment, Visual } from "./soloTypes";
import {
  REVEAL_SHARE, chartHeights, clamp01, collageTilt, easeOut, formatValue, highlightRange, highlightSweep, kenBurns,
  staggered, timelinePositions,
} from "./voxMath";
import { arrowPaths, countUp, easeOutBack, easeOutBounce, mapViewAt, wobblyPath, wordAppear } from "./voxMotion";
import { countries, countryName, countryPath, project, viewFor } from "./voxMap";

export const INK = "#1E2A26", PAPER = "#F6EFDF", ACCENT = "#E8483B", HIGHLIGHT = "#FFD84D", GREEN = "#1F7A4D";
const SERIF = "Georgia, 'Times New Roman', serif", SANS = "Arial, Helvetica, sans-serif";

export type Box = { left: number; top: number; width: number; height: number };
type Props = { segment: SoloSegment & { photoUrl?: string; activityUrl?: string }; box: Box; progress: number; index: number };

/** The title of a visual, if it has one (drawn by `VoxTitle`). */
export function titleOf(visual: Visual): string | undefined {
  return "title" in visual && visual.title ? visual.title : undefined;
}
/** The share of the board the title takes. */
export const TITLE_SHARE = 0.2;

/** Words of a text that pop in one after another, with the highlighter sweeping behind `phrase` once it is on screen. */
function KineticText({ text, phrase, progress, size, font, color = INK }: {
  text: string; phrase?: string; progress: number; size: number; font: string; color?: string;
}) {
  const words = text.split(/\s+/).filter(Boolean);
  const range = phrase ? highlightRange(text, phrase) : null, sweep = highlightSweep(progress, range, words.length);
  return <span style={{ fontFamily: font, fontSize: size, lineHeight: 1.22, color }}>
    {words.map((word, i) => {
      const lit = range && i >= range[0] && i < range[1];
      const appear = wordAppear(progress, i, words.length, REVEAL_SHARE);
      return <span key={i} data-vox-word={lit ? "highlight" : "word"} style={{
        opacity: clamp01(appear * 2.5), display: "inline-block", marginRight: size * 0.26,
        transform: `translateY(${((1 - easeOut(appear)) * size * 0.35).toFixed(2)}px) scale(${(0.55 + 0.45 * easeOutBack(appear)).toFixed(4)})`,
        transformOrigin: "50% 80%",
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
  const enter = easeOutBack(progress / 0.12), draw = easeOut((progress - 0.25) / 0.35), arrowDraw = easeOut((progress - 0.5) / 0.25);
  const r = { cx: (marker.x + marker.width / 2) * width, cy: (marker.y + marker.height / 2) * height,
    rx: marker.width * width * 0.62, ry: marker.height * height * 0.62 };
  // a hand-drawn arrow from outside the picture to the marker
  const fromRight = r.cx < width / 2 ? -1 : 1;
  const arrow = arrowPaths(fromRight > 0 ? width * 1.1 : -width * 0.1, height * 0.12,
    r.cx + fromRight * r.rx * 0.8, r.cy - r.ry * 0.6, index, Math.max(12, width * 0.03));
  const stroke = Math.max(3, width * 0.006);
  return <>
    <div data-vox-visual="collage" style={{ position: "absolute", left, top, width, height, padding: width * 0.018, background: "#FFFFFF",
      boxShadow: "0 18px 38px rgba(30,42,38,0.32)", transform: `rotate(${tilt}deg) scale(${(0.8 + 0.2 * enter).toFixed(4)})`,
      opacity: clamp01(progress / 0.05), boxSizing: "border-box" }}>
      <div style={{ width: "100%", height: "100%", overflow: "hidden", position: "relative", background: "#D9CDB3" }}>
        {url ? <Img src={resolvedMedia(url)} style={{ width: "100%", height: "100%", objectFit: "cover",
          transform: `translate(${motion.x}%, ${motion.y}%) scale(${motion.scale})`, filter: "saturate(0.92) contrast(1.04)" }} />
          : <div style={{ display: "grid", placeItems: "center", height: "100%", fontFamily: SANS, color: INK, fontSize: height * 0.07 }}>
            Add the picture for this segment</div>}
        <svg width={width} height={height} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
          <ellipse {...r} fill="none" stroke={ACCENT} strokeWidth={stroke} strokeLinecap="round"
            pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} />
        </svg>
      </div>
      <svg data-vox-arrow="true" width={width} height={height} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
        <path d={arrow.shaft} fill="none" stroke={ACCENT} strokeWidth={stroke} strokeLinecap="round" pathLength={1}
          strokeDasharray={1} strokeDashoffset={1 - arrowDraw} />
        <path d={arrow.head} fill="none" stroke={ACCENT} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round"
          opacity={arrowDraw >= 0.95 ? 1 : 0} />
      </svg>
      {/* a strip of tape holds the cut-out on the paper */}
      <div style={{ position: "absolute", left: width * 0.42, top: -height * 0.05, width: width * 0.16, height: height * 0.1,
        background: "rgba(255,240,180,0.75)", transform: "rotate(-3deg)" }} />
    </div>
    {caption ? <div style={{ position: "absolute", left: box.left, width: box.width, top: top + height + box.height * 0.04,
      textAlign: "center", fontFamily: SANS, fontWeight: 700, fontSize: box.height * 0.07, color: INK,
      opacity: easeOut((progress - 0.1) / 0.15), transform: `translateY(${((1 - easeOut((progress - 0.1) / 0.15)) * 16).toFixed(1)}px)` }}>
      <span style={{ background: PAPER, padding: "0.1em 0.4em", boxShadow: "0 4px 10px rgba(0,0,0,0.12)" }}>{caption}</span>
    </div> : null}
  </>;
}

/** The board title with a hand-drawn underline; `ready` shows it whole (it arrived by morphing from the last title). */
export function VoxTitle({ text, box, progress, ready = false, seed = 0, style }: {
  text?: string; box: Box; progress: number; ready?: boolean; seed?: number; style?: React.CSSProperties;
}) {
  if (!text) return null;
  const enter = ready ? 1 : easeOut(progress / 0.12), draw = ready ? 1 : easeOut((progress - 0.05) / 0.2);
  const size = box.height * 0.085, width = Math.min(box.width, text.length * size * 0.56);
  return <div data-vox-title="true" style={{ position: "absolute", left: box.left, top: box.top, width: box.width, fontFamily: SANS, fontWeight: 800,
    fontSize: size, color: INK, letterSpacing: "-0.01em", opacity: enter, transform: `translateY(${(1 - enter) * 12}px)`, ...style }}>
    {text}
    <svg width={width} height={size * 0.4} style={{ display: "block", overflow: "visible" }}>
      <path d={wobblyPath(2, size * 0.18, width * 0.98, size * 0.12, seed)} fill="none" stroke={ACCENT}
        strokeWidth={Math.max(4, size * 0.1)} strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} />
    </svg>
  </div>;
}

function Chart({ visual, box, progress }: { visual: Extract<Visual, { kind: "chart" }>; box: Box; progress: number }) {
  const top = box.height * (visual.title ? TITLE_SHARE : 0.06), height = box.height - top - box.height * 0.16, width = box.width;
  const { heights } = chartHeights(visual.items.map((item) => item.value));
  const n = visual.items.length, slot = width / n, barWidth = slot * 0.56, font = Math.max(14, box.height * 0.055);
  const points = visual.items.map((_, i) => [slot * (i + 0.5), height * (1 - heights[i])] as [number, number]);
  const lineDraw = easeOut((progress - 0.08) / 0.6);
  return <svg data-vox-visual="chart" style={{ position: "absolute", left: box.left, top: box.top + top, overflow: "visible" }} width={width} height={height}>
    <path d={wobblyPath(0, height, width * easeOut(progress / 0.1), height, 3)} fill="none" stroke={INK} strokeWidth={3} strokeLinecap="round" />
    {visual.chart_type === "line" ? <>
      <polyline points={points.map((point) => point.join(",")).join(" ")} fill="none" stroke={ACCENT} strokeWidth={Math.max(3, height * 0.018)}
        strokeLinejoin="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - lineDraw} />
      {points.map(([x, y], i) => {
        const shown = staggered(progress, i, n);
        return <g key={i} opacity={clamp01(shown * 3)}>
          <circle cx={x} cy={y} r={Math.max(5, height * 0.025) * easeOutBack(shown)} fill={ACCENT} />
          <text data-vox-value={i} x={x} y={y - font * 0.7} textAnchor="middle" fontFamily={SANS} fontWeight={800} fontSize={font} fill={INK}>
            {formatValue(countUp(visual.items[i].value, shown), visual.unit)}</text>
        </g>;
      })}
    </> : visual.items.map((item, i) => {
      const grow = staggered(progress, i, n), barHeight = height * heights[i] * easeOutBack(grow);
      return <g key={i}>
        <rect x={slot * i + (slot - barWidth) / 2} y={height - barHeight} width={barWidth} height={Math.max(0, barHeight)}
          fill={i === n - 1 ? ACCENT : GREEN} rx={4} />
        <text data-vox-value={i} x={slot * (i + 0.5)} y={height - barHeight - font * 0.4} textAnchor="middle" fontFamily={SANS} fontWeight={800}
          fontSize={font} fill={INK} opacity={clamp01(grow * 3)}>{formatValue(countUp(item.value, grow), visual.unit)}</text>
      </g>;
    })}
    {visual.items.map((item, i) => <text key={`l${i}`} x={slot * (i + 0.5)} y={height + font * 1.3} textAnchor="middle"
      fontFamily={SANS} fontSize={font * 0.9} fill={INK} opacity={clamp01(staggered(progress, i, n) * 3)}>{item.label}</text>)}
  </svg>;
}

function Timeline({ visual, box, progress }: { visual: Extract<Visual, { kind: "timeline" }>; box: Box; progress: number }) {
  const positions = timelinePositions(visual.events.length), y = box.height * 0.55, font = Math.max(14, box.height * 0.055);
  const draw = easeOut((progress - 0.05) / 0.5);
  return <svg data-vox-visual="timeline" style={{ position: "absolute", left: box.left, top: box.top, overflow: "visible" }} width={box.width} height={box.height}>
    <path d={wobblyPath(box.width * 0.04, y, box.width * 0.96, y, 5)} fill="none" stroke={INK} strokeWidth={Math.max(3, box.height * 0.012)}
      strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} />
    {visual.events.map((event, i) => {
      const x = positions[i] * box.width, shown = staggered(progress, i, visual.events.length), up = i % 2 === 0;
      return <g key={i} opacity={clamp01(shown * 3)} transform={`translate(0, ${((1 - easeOut(shown)) * (up ? -14 : 14)).toFixed(2)})`}>
        <circle cx={x} cy={y} r={Math.max(7, box.height * 0.028) * easeOutBack(shown)} fill={i === visual.events.length - 1 ? ACCENT : GREEN}
          stroke={PAPER} strokeWidth={3} />
        <text x={x} y={up ? y - font * 1.6 : y + font * 2.1} textAnchor="middle" fontFamily={SANS} fontWeight={800} fontSize={font * 1.05} fill={ACCENT}>{event.when}</text>
        <text x={x} y={up ? y - font * 0.6 : y + font * 3.2} textAnchor="middle" fontFamily={SANS} fontSize={font * 0.85} fill={INK}>{event.label}</text>
      </g>;
    })}
  </svg>;
}

/** The map flies in from the whole world to its region over the first 30 % of the segment. */
export const MAP_FLY_SHARE = 0.3;

function WorldMap({ visual, box, progress }: { visual: Extract<Visual, { kind: "map" }>; box: Box; progress: number }) {
  const top = visual.title ? box.height * 0.18 : 0, width = box.width, height = box.height - top;
  const view = mapViewAt(viewFor(visual.places, width / height), progress / MAP_FLY_SHARE);
  const lit = new Set((visual.highlight_countries ?? []).map(countryName).filter(Boolean));
  const appear = easeOut((progress - MAP_FLY_SHARE * 0.6) / 0.2), font = Math.max(13, box.height * 0.05);
  const pins = visual.places.map((place) => project([place.lon, place.lat], view, width, height));
  const route = visual.route && visual.route.length === 2 ? [pins[visual.route[0]], pins[visual.route[1]]] : null;
  const draw = easeOut((progress - MAP_FLY_SHARE - 0.1) / 0.35);
  const arc = route ? (() => {
    const [[x1, y1], [x2, y2]] = route, mx = (x1 + x2) / 2, my = Math.min(y1, y2) - Math.hypot(x2 - x1, y2 - y1) * 0.28;
    return `M${x1},${y1} Q${mx},${my} ${x2},${y2}`;
  })() : null;
  // pins drop in one after another once the map has landed
  const pinShare = (i: number) => staggered(clamp01((progress - MAP_FLY_SHARE * 0.8) / (1 - MAP_FLY_SHARE * 0.8)), i, pins.length);
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
      const shown = pinShare(i), drop = easeOutBounce(shown), label = easeOut((shown - 0.6) / 0.4);
      return <g key={i} data-vox-pin={i} opacity={shown > 0 ? 1 : 0}>
        <g transform={`translate(0, ${(-(1 - drop) * height * 0.15).toFixed(2)})`}>
          <circle cx={x} cy={y} r={Math.max(6, height * 0.022)} fill={ACCENT} stroke="#FFFFFF" strokeWidth={3} />
        </g>
        <ellipse cx={x} cy={y + Math.max(6, height * 0.022) * 0.9} rx={Math.max(6, height * 0.022) * drop} ry={3 * drop} fill="rgba(0,0,0,0.25)" />
        <text x={x} y={y - font * 0.9} textAnchor="middle" fontFamily={SANS} fontWeight={800} fontSize={font} fill={INK}
          stroke={PAPER} strokeWidth={4} paintOrder="stroke" opacity={label}>{visual.places[i].name}</text>
      </g>;
    })}
  </svg>;
}

function Diagram({ visual, box, progress }: { visual: Extract<Visual, { kind: "diagram" }>; box: Box; progress: number }) {
  const top = visual.title ? box.height * TITLE_SHARE : 0, n = visual.nodes.length, comparison = visual.template === "comparison";
  const columns = comparison ? 2 : Math.min(n, 4), rows = Math.ceil(n / columns), gap = box.width * 0.025;
  const cellWidth = (box.width - gap * (columns - 1)) / columns, cellHeight = Math.min((box.height - top - gap * (rows - 1)) / rows, box.height * 0.62);
  const font = Math.max(14, Math.min(cellHeight * 0.16, box.height * 0.06));
  return <div data-vox-visual="diagram" style={{ position: "absolute", left: box.left, top: box.top + top, width: box.width }}>
    {visual.nodes.map((node, i) => {
      const shown = staggered(progress, i, n), column = i % columns, row = Math.floor(i / columns);
      const arrow = easeOut((staggered(progress, i + 1, n) - 0.1) / 0.5);
      return <div key={node.id} style={{ position: "absolute", left: column * (cellWidth + gap), top: row * (cellHeight + gap),
        width: cellWidth, height: cellHeight, boxSizing: "border-box", padding: font * 0.7, background: "#FFFFFF",
        border: `3px solid ${INK}`, borderRadius: 10, boxShadow: `6px 6px 0 ${i % 2 ? GREEN : ACCENT}`,
        opacity: clamp01(shown * 3), transform: `scale(${(0.7 + 0.3 * easeOutBack(shown)).toFixed(4)}) rotate(${((1 - shown) * (i % 2 ? 3 : -3)).toFixed(2)}deg)`,
        fontFamily: SANS, color: INK }}>
        <div style={{ height: "100%", overflow: "hidden" }}>
          <div style={{ fontWeight: 800, fontSize: font * 1.05 }}>{visual.template === "steps" ? `${i + 1}. ` : ""}{node.label}</div>
          {node.detail ? <div style={{ fontSize: font * 0.85, marginTop: font * 0.3 }}>{node.detail}</div> : null}
        </div>
        {!comparison && column < columns - 1 && i < n - 1 ? <svg width={gap * 1.6} height={font * 1.4}
          style={{ position: "absolute", right: -gap * 1.3, top: "42%", overflow: "visible" }}>
          {(() => {
            const paths = arrowPaths(0, font * 0.7, gap * 1.2, font * 0.7, i, font * 0.45);
            return <>
              <path d={paths.shaft} fill="none" stroke={ACCENT} strokeWidth={4} strokeLinecap="round" pathLength={1} strokeDasharray={1}
                strokeDashoffset={1 - arrow} />
              <path d={paths.head} fill="none" stroke={ACCENT} strokeWidth={4} strokeLinecap="round" opacity={arrow >= 0.95 ? 1 : 0} />
            </>;
          })()}
        </svg> : null}
      </div>;
    })}
  </div>;
}

/** The segment's graphics without its title (the scene draws the title, see `VoxTitle`). */
export function VoxVisual({ segment, box, progress, index }: Props) {
  const visual = segment.visual;
  const title = titleOf(visual);
  const inner = (offset: number): Box => ({ ...box, top: box.top + offset, height: box.height - offset });
  if (visual.kind === "photo" || visual.kind === "activity") {
    const url = visual.kind === "photo" ? segment.photoUrl : segment.activityUrl;
    const region = visual.kind === "photo" ? visual.important_regions?.[0] : undefined;
    return <Collage url={url} caption={visual.caption} progress={progress} index={index} box={box} region={region} />;
  }
  if (visual.kind === "quote") {
    // as large as the board allows: short quotes get big type, long ones wrap smaller
    const size = Math.max(22, Math.min(box.height * 0.12, (box.width * 0.85) / Math.sqrt(Math.max(16, visual.text.length))));
    const tilt = collageTilt(index) * 0.5, enter = easeOutBack(progress / 0.1);
    return <div data-vox-visual="quote" style={{ position: "absolute", left: box.left + box.width * 0.06, top: box.top + box.height * 0.08,
      width: box.width * 0.88, padding: `${size * 0.7}px ${size * 0.9}px`, boxSizing: "border-box", background: "#FFFDF6",
      boxShadow: "0 16px 34px rgba(30,42,38,0.25)", transform: `rotate(${(tilt * enter).toFixed(3)}deg) scale(${(0.85 + 0.15 * enter).toFixed(4)})`,
      opacity: clamp01(progress / 0.04),
      clipPath: "polygon(0 2%, 3% 0, 97% 1%, 100% 3%, 99% 97%, 96% 100%, 2% 99%, 0 96%)" }}>
      <div style={{ fontFamily: SERIF, fontSize: size * 2.2, color: ACCENT, lineHeight: 0.6, height: size * 0.9 }}>“</div>
      <KineticText text={visual.text} phrase={visual.highlight} progress={progress} size={size} font={SERIF} />
      {visual.attribution ? <div style={{ marginTop: size * 0.5, fontFamily: SANS, fontSize: size * 0.55, color: INK, opacity: clamp01(progress * 2) }}>
        — {visual.attribution}</div> : null}
    </div>;
  }
  const offset = title ? box.height * TITLE_SHARE : 0;
  return <>
    {visual.kind === "text_card" ? <div data-vox-visual="text_card" style={{ position: "absolute", left: box.left, top: box.top + offset + box.height * 0.04, width: box.width }}>
      {(visual.bullets ?? []).map((bullet, i) => {
        const shown = staggered(progress, i, (visual.bullets ?? []).length + (visual.emphasis ? 1 : 0));
        return <div key={i} style={{ display: "flex", gap: 14, marginBottom: box.height * 0.035, opacity: clamp01(shown * 2.5),
          transform: `translateX(${((1 - easeOutBack(shown)) * -40).toFixed(2)}px)`, fontFamily: SANS, fontSize: Math.max(18, box.height * 0.07), color: INK }}>
          <span style={{ color: ACCENT, fontWeight: 800, display: "inline-block", transform: `scale(${easeOutBack(shown).toFixed(4)}) rotate(${((1 - shown) * 90).toFixed(1)}deg)` }}>■</span>
          <span>{bullet}</span></div>;
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
