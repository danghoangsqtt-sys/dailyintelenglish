import React from "react";
import { Img, staticFile, useVideoConfig } from "remotion";
import { placementAt, presenterBoxes, type Aspect } from "./explainerLayout";
import { presenterState } from "./presenterTimeline";
import type { SoloPayload } from "./soloTypes";
import type { EpisodeLine } from "./types";

export const resolvedMedia = (src: string) => src.startsWith("/") || /^https?:\/\/(localhost|127\.0\.0\.1)(:|\/)/.test(src) ? src : staticFile(src);

export function Presenter({payload, lines, time, aspect}: {payload: SoloPayload; lines: EpisodeLine[]; time: number; aspect: Aspect}) {
  const {fps, width, height} = useVideoConfig();
  const state = presenterState(payload, lines, time, fps);
  const segment = payload.plan.segments[state.segmentIndex];
  const previous = payload.plan.segments[state.segmentIndex - 1]?.layouts[aspect]?.presenter;
  const placement = placementAt(segment.layouts[aspect], previous, time - payload.timeline[state.segmentIndex].start_sec);
  const {canvas} = presenterBoxes(placement, payload.geometry.presenter_metrics, aspect);
  // Breathing is bounded by the proof's explicit frame-relative margin.
  const breath = Math.sin(time * Math.PI * 1.1) * Math.min(2, height * .001);
  return <Img data-solo-presenter={state.picture} src={resolvedMedia(payload.pictures[state.picture])}
    style={{position:"absolute", left:canvas.x * width, top:canvas.y * height + breath,
      width:canvas.width * width, height:canvas.height * height, objectFit:"fill", opacity:1}} />;
}
