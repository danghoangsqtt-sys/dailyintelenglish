/**
 * Phase 59 (ENH-041): the VOX explainer scene -- nobody on screen; the narrator's voice over a warm paper board with
 * the segment's motion graphics, its scene plate faded behind like a collage backdrop, the brand line and captions.
 */
import React, { useMemo } from "react";
import { AbsoluteFill, Img, useCurrentFrame, useVideoConfig } from "remotion";
import { CaptionBand } from "./CaptionBand";
import { resolvedMedia } from "./Presenter";
import { sceneMotion } from "./verticalMotion";
import { INK, PAPER, VoxVisual } from "./VoxVisual";
import { easeOut, segmentProgress, voxSegmentAt } from "./voxMath";
import type { EpisodeInputProps } from "./types";
import type { SoloSegment } from "./soloTypes";

export function VoxScene(props: EpisodeInputProps) {
  const frame = useCurrentFrame(), { fps, width, height } = useVideoConfig();
  const payload = props.solo;
  if (!payload || payload.style !== "vox") throw new Error("A VOX scene needs its reviewed VOX payload");
  const time = frame / fps, aspect = props.layout === "vertical" ? "9:16" : "16:9";
  const index = voxSegmentAt(payload, time);
  const segment = payload.plan.segments[index], span = payload.timeline[index], geometry = payload.geometry.aspects[aspect];
  const board = geometry.board ?? geometry.safe, header = geometry.header, caption = geometry.caption;
  const line = props.lines.find((item) => time >= item.startSec && time < item.endSec);
  const words = useMemo(() => props.lines.flatMap((item) => item.words)
    .filter((word) => word.startSec >= span.start_sec && word.startSec < span.end_sec), [props.lines, span]);
  // progress follows the spoken words of the segment, or its time span when there are none
  const progress = words.length ? words.filter((word) => word.startSec <= time).length / words.length
    : segmentProgress(time, span.start_sec, span.end_sec);
  const photo = segment.visual.kind === "photo" && segment.visual.asset
    ? payload.photos[`${segment.visual.asset.asset_id}:${segment.visual.asset.version}`] : undefined;
  const activity = segment.visual.kind === "activity" ? payload.activities?.[segment.visual.activity_id] : undefined;
  const plate = segment.scene?.scene_id ? payload.scenes?.[segment.scene.scene_id] : undefined;
  const motion = sceneMotion(frame, fps), enter = easeOut((time - span.start_sec) / 0.35);
  const box = { left: board.x * width, top: board.y * height, width: board.width * width, height: board.height * height };
  const hook = props.hook && time >= (props.hookAtSec ?? 0) && time < (props.hookAtSec ?? 0) + 3;
  return <AbsoluteFill data-vox-scene="true" style={{ overflow: "hidden", background: PAPER, fontFamily: "Arial,sans-serif" }}>
    {plate ? <Img data-vox-plate="true" src={resolvedMedia(plate)} style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover",
      opacity: 0.11, filter: "grayscale(0.7) sepia(0.35) blur(1px)", mixBlendMode: "multiply",
      transform: `translate(${motion.x}px, ${motion.y}px) scale(${motion.scale})` }} /> : null}
    {/* paper grain and a soft vignette */}
    <div style={{ position: "absolute", inset: 0, backgroundImage: "repeating-linear-gradient(0deg, rgba(120,100,60,0.035) 0 2px, transparent 2px 5px),"
      + "radial-gradient(ellipse at 50% 45%, rgba(255,255,255,0) 55%, rgba(80,60,30,0.18) 100%)" }} />
    <div style={{ position: "absolute", left: header.x * width, top: header.y * height, width: header.width * width, height: header.height * height,
      color: INK, fontSize: aspect === "9:16" ? 26 : 20, fontWeight: 700, display: "flex", justifyContent: "space-between", alignItems: "center",
      borderBottom: `2px solid ${INK}`, overflow: "hidden" }}>
      <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{hook ? props.hook : "DAILY BEYOND ENGLISH"}</span>
      <span>{props.cefrLevel}</span>
    </div>
    <div style={{ position: "absolute", inset: 0, opacity: enter, transform: `translateY(${(1 - enter) * 14}px)` }}>
      <VoxVisual segment={{ ...segment, photoUrl: photo, activityUrl: activity } as SoloSegment & { photoUrl?: string; activityUrl?: string }}
        box={box} progress={progress} index={index} />
    </div>
    {line ? <div data-solo-caption="true" style={{ position: "absolute", left: caption.x * width, top: caption.y * height,
      width: caption.width * width, height: caption.height * height }}>
      <CaptionBand line={line} currentTimeSec={time} captionStyle={props.captionStyle} layout={props.layout}
        protectedPhrases={[...(props.learning?.idioms ?? []).map((item) => item.phrase), ...(props.learning?.vocab ?? []).map((item) => item.word)]} stationary />
    </div> : null}
  </AbsoluteFill>;
}
