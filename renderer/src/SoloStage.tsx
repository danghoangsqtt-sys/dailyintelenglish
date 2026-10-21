/**
 * Phase 55 (ENH-037): the Solo stage behind the presenter, built like the conversation video's `SpriteStage`: the
 * segment's Scene Library plate with the same slow camera drift, a crossfade when the place changes, and an Activity
 * Library picture revealed full-frame for an activity segment.
 */
import React from "react";
import { AbsoluteFill, Img } from "remotion";
import { resolvedMedia } from "./Presenter";
import { insertMotion, sceneMotion } from "./verticalMotion";
import type { SoloPayload } from "./soloTypes";

const FILL: React.CSSProperties = { position: "absolute", width: "100%", height: "100%", objectFit: "cover" };
export const STAGE_FALLBACK = "radial-gradient(ellipse at 50% 30%,#1B4939,#071D18 72%)";
export const SCENE_CROSSFADE_SEC = 0.6;

/** Which plate is visible at `time`: the segment's own, fading in over the previous segment's when the place changes. */
export function stagePlates(payload: SoloPayload, segmentIndex: number, time: number): { previous: string | null; current: string | null; opacity: number } {
  const plate = (index: number) => {
    const id = payload.plan.segments[index]?.scene?.scene_id;
    return id ? payload.scenes?.[id] ?? null : null;
  };
  const current = plate(segmentIndex), previous = segmentIndex > 0 ? plate(segmentIndex - 1) : null;
  const start = payload.timeline[segmentIndex]?.start_sec ?? 0;
  if (!previous || previous === current) return { previous: null, current, opacity: 1 };
  return { previous, current, opacity: Math.max(0, Math.min(1, (time - start) / SCENE_CROSSFADE_SEC)) };
}

/** Phase 61 (ENH-043): the scene plate pushes in during each segment and settles back before the next one (the cards
 * and the presenter stay where the layout proof put them). */
export function stagePush(time: number, start: number, end: number): number {
  const rise = Math.max(0, Math.min(1, (time - start) / 1.2)), fall = Math.max(0, Math.min(1, (end - time) / 0.6));
  const t = Math.min(rise, fall);
  return 1 + 0.05 * t * t * (3 - 2 * t);
}

export function SoloStage({ payload, segmentIndex, time, frame, fps }: {
  payload: SoloPayload; segmentIndex: number; time: number; frame: number; fps: number;
}) {
  const plates = stagePlates(payload, segmentIndex, time);
  const motion = sceneMotion(frame, fps);
  const segment = payload.plan.segments[segmentIndex], span = payload.timeline[segmentIndex];
  const push = span ? stagePush(time, span.start_sec, span.end_sec) : 1;
  const zoom = `translate(${motion.x.toFixed(2)}px, ${motion.y.toFixed(2)}px) scale(${(motion.scale * push).toFixed(4)})`;
  const activity = segment?.visual.kind === "activity" ? payload.activities?.[segment.visual.activity_id] : undefined;
  const reveal = activity && span ? insertMotion(time, span.start_sec, span.end_sec, segmentIndex) : null;
  return (
    <AbsoluteFill data-solo-stage="true" style={{ overflow: "hidden", background: STAGE_FALLBACK }}>
      {plates.previous ? <Img src={resolvedMedia(plates.previous)} style={{ ...FILL, transform: zoom }} /> : null}
      {plates.current ? <Img data-solo-scene-plate="true" src={resolvedMedia(plates.current)}
        style={{ ...FILL, transform: zoom, opacity: plates.opacity }} /> : null}
      {activity && reveal ? <Img data-solo-activity="true" src={resolvedMedia(activity)} style={{ ...FILL,
        transform: `${zoom} translateX(${reveal.x.toFixed(2)}px) scale(${reveal.scale.toFixed(4)})`,
        clipPath: `inset(0 ${reveal.fromRight ? 0 : reveal.hiddenPercent}% 0 ${reveal.fromRight ? reveal.hiddenPercent : 0}%)` }} /> : null}
      {/* Brand line and captions stay readable over any picture. */}
      <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: "22%",
        background: "linear-gradient(to bottom, rgba(0,0,0,0.5), rgba(0,0,0,0))" }} />
    </AbsoluteFill>
  );
}

/** Above the presenter's legs and under the captions, as in the conversation video. */
export function StageShade() {
  return <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: "34%",
    background: "linear-gradient(to top, rgba(4,16,13,0.72), rgba(4,16,13,0))" }} />;
}
