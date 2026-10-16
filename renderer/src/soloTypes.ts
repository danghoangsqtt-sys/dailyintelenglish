import { z } from "zod";
import type { FrontMetrics, Rect, SegmentLayout } from "./explainerLayout";

export type Anchor = { line_id: string; token_index: number };
export type Gesture = "calm" | "talk" | "point-left" | "point-right" | "emphasize" | "count-1" | "count-2" | "count-3" | "think" | "wave";
export type Visual = { kind: "photo"; asset?: {asset_id: string; version: number} | null; prompt?: string; caption?: string; fit?: "contain" | "cover"; important_regions?: Rect[] }
  | { kind: "text_card"; title: string; bullets?: string[]; emphasis?: string }
  | { kind: "diagram"; title?: string; template: "steps" | "comparison" | "cause_effect";
      nodes: {id: string; label: string; detail?: string}[]; edges?: {source: string; target: string; label?: string}[] };
export type SoloSegment = {id: string; intent: string; line_ids: string[]; start: Anchor; end: Anchor; visual: Visual;
  gestures: {at: Anchor; gesture: Gesture}[]; layouts: Record<string, SegmentLayout>; locks: Record<string, boolean>; needs_fact_review: boolean; source_notes: string};
export type GeometrySegment = {id: string; presenter: SegmentLayout["presenter"]; protected: Rect[]; bounds: Rect; canvas: Rect; motion_bounds: Rect;
  text: {font: number; titleFont: number; padding: number; gap: number; columns: number}; transition: string};
export type SoloPayload = {plan: {project_id: string; revision: number; status: string; source_fingerprint: string; segments: SoloSegment[]; aspects: string[]};
  geometry: {rules_version: number; presenter_metrics: FrontMetrics; aspects: Record<string, {safe: Rect; caption: Rect; header: Rect; segments: GeometrySegment[]}>};
  timeline: {id: string; start_sec: number; end_sec: number; gestures?: {gesture: Gesture; at_sec: number}[]}[];
  pictures: Record<string, string>; photos: Record<string, string>};

export const soloPayloadSchema = z.custom<SoloPayload>((value) => {
  if (!value || typeof value !== "object") return false;
  const data = value as SoloPayload;
  return !!data.plan && Array.isArray(data.plan.segments) && data.plan.segments.length > 0 && data.plan.segments.length <= 60 &&
    !!data.geometry && data.geometry.rules_version === 1 && !!data.geometry.presenter_metrics &&
    Array.isArray(data.timeline) && data.timeline.length === data.plan.segments.length &&
    !!data.pictures && Object.keys(data.pictures).length === 21 && !!data.photos;
}, "Expected a bounded, backend-validated Solo payload");
