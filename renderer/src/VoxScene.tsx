/**
 * Phase 59 (ENH-041): the VOX explainer scene -- nobody on screen; the narrator's voice over a warm paper board with
 * the segment's motion graphics, its scene plate faded behind like a collage backdrop, the brand line and captions.
 * Phase 61 (ENH-043): a different transition at each segment boundary (paper slide, diagonal wipe, zoom-through, page
 * flip, iris, whip-pan), the title and a decorative shape morphing between segments, a slow push-in/pan of the board,
 * parallax paper scraps with a drifting light, and a "Subscribe" stamp at the end.
 */
import React, { useMemo } from "react";
import { AbsoluteFill, Img, useCurrentFrame, useVideoConfig } from "remotion";
import { CaptionBand } from "./CaptionBand";
import { resolvedMedia } from "./Presenter";
import { sceneMotion } from "./verticalMotion";
import { ACCENT, type Box, GREEN, INK, PAPER, VoxTitle, VoxVisual, titleOf } from "./VoxVisual";
import { voxSegmentAt } from "./voxMath";
import { boardCamera, shapeAt, smoothProgress, stampAt, transitionAt, transitionStyles } from "./voxMotion";
import type { EpisodeInputProps, EpisodeLine } from "./types";
import type { SoloPayload, SoloSegment } from "./soloTypes";

type Span = SoloPayload["timeline"][number];

/** The paper, the faded scene plate, parallax scraps, the morphing shape and a drifting light (the same in every layer). */
function Backdrop({ payload, index, time, frame, fps, width, height }: {
  payload: SoloPayload; index: number; time: number; frame: number; fps: number; width: number; height: number;
}) {
  const segment = payload.plan.segments[index];
  const plate = segment.scene?.scene_id ? payload.scenes?.[segment.scene.scene_id] : undefined;
  const motion = sceneMotion(frame, fps), shape = shapeAt(payload.timeline, index, time), unit = Math.min(width, height);
  const drift = (depth: number, k: number) =>
    `translate(${(depth * 22 * Math.sin(time * Math.PI * 2 / 14 + k)).toFixed(2)}px, ${(depth * 12 * Math.cos(time * Math.PI * 2 / 17 + k)).toFixed(2)}px)`;
  const light = 30 + 40 * (0.5 + 0.5 * Math.sin(time * Math.PI * 2 / 23));
  return <>
    <AbsoluteFill style={{ background: PAPER }} />
    {plate ? <Img data-vox-plate="true" src={resolvedMedia(plate)} style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover",
      opacity: 0.11, filter: "grayscale(0.7) sepia(0.35) blur(1px)", mixBlendMode: "multiply",
      transform: `translate(${motion.x}px, ${motion.y}px) scale(${motion.scale})` }} /> : null}
    <div data-vox-shape="true" style={{ position: "absolute", left: shape.x * width - shape.size * unit / 2, top: shape.y * height - shape.size * unit / 2,
      width: shape.size * unit, height: shape.size * unit, background: shape.color, transform: `rotate(${shape.rotation.toFixed(2)}deg) ${drift(0.5, 0)}`,
      borderRadius: shape.radius.map((r) => `${r.toFixed(1)}%`).join(" ") }} />
    {/* parallax scraps: nearer ones drift more */}
    <div style={{ position: "absolute", left: width * 0.03, top: height * 0.74, width: unit * 0.16, height: unit * 0.1, background: "#FFFDF4",
      boxShadow: "0 6px 14px rgba(30,42,38,0.12)", transform: `${drift(1.4, 1)} rotate(-7deg)`, opacity: 0.7 }} />
    <div style={{ position: "absolute", left: width * 0.88, top: height * 0.08, width: unit * 0.12, height: unit * 0.12, borderRadius: "50%",
      border: `3px dashed ${GREEN}`, transform: drift(0.8, 2), opacity: 0.3 }} />
    <div style={{ position: "absolute", left: width * 0.9, top: height * 0.8, fontFamily: "Arial", fontWeight: 800, fontSize: unit * 0.05,
      color: ACCENT, transform: drift(1.8, 3), opacity: 0.3, letterSpacing: unit * 0.02 }}>+ +</div>
    {/* paper grain, a soft vignette and the drifting light */}
    <div style={{ position: "absolute", inset: 0, backgroundImage: "repeating-linear-gradient(0deg, rgba(120,100,60,0.035) 0 2px, transparent 2px 5px),"
      + "radial-gradient(ellipse at 50% 45%, rgba(255,255,255,0) 55%, rgba(80,60,30,0.18) 100%)" }} />
    <div data-vox-light="true" style={{ position: "absolute", inset: 0,
      background: `radial-gradient(ellipse at ${light.toFixed(1)}% 30%, rgba(255,250,230,0.38), rgba(255,250,230,0) 55%)` }} />
  </>;
}

/** One segment's whole board: backdrop, title and the graphics under the board camera. */
function Layer({ payload, index, time, width, height, box, words, style, title, backdrop }: {
  payload: SoloPayload; index: number; time: number; width: number; height: number; box: Box; words: EpisodeLine["words"];
  style: React.CSSProperties; title: "show" | "ready" | "hide"; backdrop: React.ReactNode;
}) {
  const segment = payload.plan.segments[index], span = payload.timeline[index];
  const progress = words.length ? smoothProgress(words, time) : Math.min(1, Math.max(0, (time - span.start_sec) / Math.max(0.001, span.end_sec - span.start_sec)));
  const photo = segment.visual.kind === "photo" && segment.visual.asset
    ? payload.photos[`${segment.visual.asset.asset_id}:${segment.visual.asset.version}`] : undefined;
  const activity = segment.visual.kind === "activity" ? payload.activities?.[segment.visual.activity_id] : undefined;
  const camera = boardCamera(time, span, index);
  return <AbsoluteFill data-vox-layer={index} style={{ overflow: "hidden", ...style }}>
    {backdrop}
    <div style={{ position: "absolute", inset: 0, transformOrigin: `${(box.left + box.width / 2).toFixed(1)}px ${(box.top + box.height / 2).toFixed(1)}px`,
      transform: `translate(${(camera.x * width).toFixed(2)}px, ${(camera.y * height).toFixed(2)}px) scale(${camera.scale.toFixed(4)})` }}>
      <VoxVisual segment={{ ...segment, photoUrl: photo, activityUrl: activity } as SoloSegment & { photoUrl?: string; activityUrl?: string }}
        box={box} progress={progress} index={index} />
    </div>
    {title !== "hide" ? <VoxTitle text={titleOf(segment.visual)} box={box} progress={progress} ready={title === "ready"} seed={index} /> : null}
  </AbsoluteFill>;
}

/** Morph: the old title gives way to the new one in place while the underline changes its length. */
function MorphTitle({ from, to, box, t, seed }: { from: string; to: string; box: Box; t: number; seed: number }) {
  return <>
    <VoxTitle text={from} box={box} progress={1} ready seed={seed - 1}
      style={{ opacity: 1 - t, filter: `blur(${(4 * t).toFixed(1)}px)`, transform: `translateY(${(-10 * t).toFixed(1)}px)` }} />
    <VoxTitle text={to} box={box} progress={1} ready seed={seed}
      style={{ opacity: t, filter: `blur(${(4 * (1 - t)).toFixed(1)}px)`, transform: `translateY(${(10 * (1 - t)).toFixed(1)}px)` }} />
  </>;
}

function SubscribeStamp({ scale, opacity, box, vertical }: { scale: number; opacity: number; box: Box; vertical: boolean }) {
  const size = box.height * (vertical ? 0.07 : 0.085);
  return <div data-vox-stamp="true" style={{ position: "absolute", right: vertical ? undefined : box.left + box.width * 0.02,
    left: vertical ? box.left + box.width / 2 - size * 3.6 : undefined, top: box.top + box.height * (vertical ? 0.78 : 0.7),
    transform: `rotate(-8deg) scale(${scale.toFixed(4)})`, opacity, fontFamily: "Arial Black, Arial, sans-serif", fontWeight: 900,
    fontSize: size, color: ACCENT, letterSpacing: "0.06em", padding: `${size * 0.25}px ${size * 0.5}px`, border: `${Math.max(4, size * 0.12)}px solid ${ACCENT}`,
    borderRadius: size * 0.25, background: "rgba(255,253,246,0.85)", boxShadow: "0 8px 20px rgba(30,42,38,0.25)", whiteSpace: "nowrap" }}>
    SUBSCRIBE ▶
  </div>;
}

export function VoxScene(props: EpisodeInputProps) {
  const frame = useCurrentFrame(), { fps, width, height } = useVideoConfig();
  const payload = props.solo;
  if (!payload || payload.style !== "vox") throw new Error("A VOX scene needs its reviewed VOX payload");
  const time = frame / fps, aspect = props.layout === "vertical" ? "9:16" : "16:9";
  const index = voxSegmentAt(payload, time);
  const geometry = payload.geometry.aspects[aspect];
  const board = geometry.board ?? geometry.safe, header = geometry.header, caption = geometry.caption;
  const line = props.lines.find((item) => time >= item.startSec && time < item.endSec);
  const allWords = useMemo(() => props.lines.flatMap((item) => item.words), [props.lines]);
  const wordsOf = (span: Span) => allWords.filter((word) => word.startSec >= span.start_sec && word.startSec < span.end_sec);
  const box = { left: board.x * width, top: board.y * height, width: board.width * width, height: board.height * height };
  const hook = props.hook && time >= (props.hookAtSec ?? 0) && time < (props.hookAtSec ?? 0) + 3;
  const running = transitionAt(payload.timeline, index, time);
  const titles = [index > 0 ? titleOf(payload.plan.segments[index - 1].visual) : undefined, titleOf(payload.plan.segments[index].visual)];
  const morph = Boolean(titles[0] && titles[1]);
  // both boards share one backdrop (the current time and segment), so the shape morphs without a seam
  const backdrop = <Backdrop payload={payload} index={index} time={time} frame={frame} fps={fps} width={width} height={height} />;
  const layer = (at: number, style: React.CSSProperties, title: "show" | "ready" | "hide", when = time) =>
    <Layer key={at} payload={payload} index={at} time={when} width={width} height={height} box={box}
      words={wordsOf(payload.timeline[at])} style={style} title={title} backdrop={backdrop} />;
  let boards: React.ReactNode;
  if (running) {
    const styles = transitionStyles(running.kind, running.t, width);
    // the leaving board keeps its last frame while it goes
    const leaving = layer(index - 1, styles.leaving, morph ? "hide" : "show", payload.timeline[index - 1].end_sec - 1 / fps);
    const entering = layer(index, styles.entering, morph ? "hide" : "show");
    boards = <div data-vox-transition={running.kind}>{styles.top === "entering" ? [leaving, entering] : [entering, leaving]}</div>;
  } else boards = layer(index, {}, morph ? "ready" : "show");
  const last = payload.timeline.length - 1;
  const stamp = index === last ? stampAt(time, payload.timeline[last], wordsOf(payload.timeline[last])) : null;
  return <AbsoluteFill data-vox-scene="true" style={{ overflow: "hidden", background: PAPER, fontFamily: "Arial,sans-serif" }}>
    {boards}
    {running && morph ? <MorphTitle from={titles[0]!} to={titles[1]!} box={box} t={running.t} seed={index} /> : null}
    {stamp ? <SubscribeStamp {...stamp} box={box} vertical={aspect === "9:16"} /> : null}
    <div style={{ position: "absolute", left: header.x * width, top: header.y * height, width: header.width * width, height: header.height * height,
      color: INK, fontSize: aspect === "9:16" ? 26 : 20, fontWeight: 700, display: "flex", justifyContent: "space-between", alignItems: "center",
      borderBottom: `2px solid ${INK}`, overflow: "hidden" }}>
      <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{hook ? props.hook : "DAILY BEYOND ENGLISH"}</span>
      <span>{props.cefrLevel}</span>
    </div>
    {line ? <div data-solo-caption="true" style={{ position: "absolute", left: caption.x * width, top: caption.y * height,
      width: caption.width * width, height: caption.height * height }}>
      <CaptionBand line={line} currentTimeSec={time} captionStyle={props.captionStyle} layout={props.layout}
        protectedPhrases={[...(props.learning?.idioms ?? []).map((item) => item.phrase), ...(props.learning?.vocab ?? []).map((item) => item.word)]} stationary />
    </div> : null}
  </AbsoluteFill>;
}
