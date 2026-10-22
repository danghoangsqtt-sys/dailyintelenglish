import { z } from "zod";
import type { FrontMetrics, Rect, SegmentLayout } from "./explainerLayout";

export type Anchor = { line_id: string; token_index: number };
export type Gesture = "calm" | "talk" | "point-left" | "point-right" | "emphasize" | "count-1" | "count-2" | "count-3" | "think" | "wave";
export type Visual = { kind: "photo"; asset?: {asset_id: string; version: number} | null; prompt?: string; caption?: string; fit?: "contain" | "cover"; important_regions?: Rect[] }
  | { kind: "text_card"; title: string; bullets?: string[]; emphasis?: string }
  | { kind: "diagram"; title?: string; template: "steps" | "comparison" | "cause_effect";
      nodes: {id: string; label: string; detail?: string}[]; edges?: {source: string; target: string; label?: string}[] }
  | { kind: "activity"; activity_id: string; caption?: string }
  // Phase 59 (ENH-041): the VOX kinds
  | { kind: "quote"; text: string; highlight?: string; attribution?: string }
  | { kind: "chart"; chart_type?: "bar" | "line"; title?: string; unit?: string; items: {label: string; value: number}[] }
  | { kind: "timeline"; title?: string; events: {when: string; label: string}[] }
  | { kind: "map"; title?: string; places: {name: string; lat: number; lon: number}[]; highlight_countries?: string[]; route?: number[] };
export type SoloSegment = {id: string; intent: string; line_ids: string[]; start: Anchor; end: Anchor; visual: Visual; scene?: {scene_id: string} | null;
  gestures: {at: Anchor; gesture: Gesture}[]; layouts: Record<string, SegmentLayout>; locks: Record<string, boolean>; needs_fact_review: boolean; source_notes: string};
export type GeometrySegment = {id: string; presenter: SegmentLayout["presenter"]; protected: Rect[]; bounds: Rect; canvas: Rect; motion_bounds: Rect;
  text: {font: number; titleFont: number; padding: number; gap: number; columns: number}; transition: string};
export type SoloPayload = {plan: {project_id: string; revision: number; status: string; source_fingerprint: string; segments: SoloSegment[]; aspects: string[]};
  /** Phase 59: "vox" = voice-over with motion graphics (no presenter); absent for the presenter video. */
  style?: "vox" | "news" | "blur" | "mistakes" | "wordday" | "top5" | "quiz" | "listen";  // Phase 63: the news and blur Shorts are voice-only too, on the VOX proof
  geometry: {rules_version: number; style?: "vox"; presenter_metrics: FrontMetrics;
    aspects: Record<string, {safe: Rect; caption: Rect; header: Rect; board?: Rect; segments: GeometrySegment[]}>};
  timeline: {id: string; start_sec: number; end_sec: number; gestures?: {gesture: Gesture; at_sec: number}[]}[];
  pictures: Record<string, string>; photos: Record<string, string>;
  /** Phase 55: Scene Library plates and Activity Library pictures, keyed by their IDs. */
  scenes?: Record<string, string>; activities?: Record<string, string>};

export const soloPayloadSchema = z.custom<SoloPayload>((value) => {
  if (!value || typeof value !== "object") return false;
  const data = value as SoloPayload;
  const vox = ["vox", "news", "blur", "mistakes", "wordday", "top5", "quiz", "listen"].includes(data.style ?? "");  // Phase 59: nobody on screen -- no presenter metrics, no front pictures
  return !!data.plan && Array.isArray(data.plan.segments) && data.plan.segments.length > 0 && data.plan.segments.length <= 60 &&
    !!data.geometry && [1, 2].includes(data.geometry.rules_version) && (vox ? data.geometry.style === "vox" : !!data.geometry.presenter_metrics) &&
    Array.isArray(data.timeline) && data.timeline.length === data.plan.segments.length &&
    !!data.pictures && Object.keys(data.pictures).length === (vox ? 0 : 21) && !!data.photos;
}, "Expected a bounded, backend-validated Solo payload");
