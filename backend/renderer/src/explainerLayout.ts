import rules from "../../frontend/static/explainer-layout-rules.json";

export const EXPLAINER_RULES = rules;
export type Aspect = "16:9" | "9:16";
export type Rect = { x: number; y: number; width: number; height: number };
export type Placement = { anchor: "left" | "right" | "center"; x: number; y: number; height: number };
export type FrontMetrics = { canvasWidth: number; canvasHeight: number; alpha: Rect };
export type SegmentLayout = { presenter: Placement; illustration: Rect; transition: "cut" | "ease" | "slide";
  motion_from?: Placement | null; transition_seconds: number; rules_version: number };
const EPSILON = 1e-8;

export function intersects(a: Rect, b: Rect): boolean {
  return a.x < b.x + b.width - EPSILON && b.x < a.x + a.width - EPSILON &&
    a.y < b.y + b.height - EPSILON && b.y < a.y + a.height - EPSILON;
}
export function contains(outer: Rect, inner: Rect): boolean {
  return Object.values(inner).every(Number.isFinite) && inner.width > 0 && inner.height > 0 &&
    inner.x >= outer.x - EPSILON && inner.y >= outer.y - EPSILON &&
    inner.x + inner.width <= outer.x + outer.width + EPSILON && inner.y + inner.height <= outer.y + outer.height + EPSILON;
}
export function insideExplainerSafeZone(rect: Rect, aspect: Aspect): boolean {
  const spec = rules.aspects[aspect];
  const column = "column" in spec ? spec.column : undefined;
  return contains(spec.safe, rect) && !(column && rect.y + rect.height > column.fromY + EPSILON && rect.x + rect.width > column.x + EPSILON);
}
export function envelope(a: Rect, b: Rect, margin = 0): Rect {
  const x = Math.min(a.x, b.x) - margin, y = Math.min(a.y, b.y) - margin;
  return { x, y, width: Math.max(a.x + a.width, b.x + b.width) + margin - x,
    height: Math.max(a.y + a.height, b.y + b.height) + margin - y };
}
export function presenterBoxes(p: Placement, metrics: FrontMetrics, aspect: Aspect): { bounds: Rect; canvas: Rect } {
  const spec = rules.aspects[aspect], alpha = metrics.alpha;
  const h = p.height / alpha.height;
  const w = h * spec.height / spec.width * metrics.canvasWidth / metrics.canvasHeight;
  const canvas = { x: p.x - (alpha.x + alpha.width / 2) * w, y: p.y - (alpha.y + alpha.height) * h, width: w, height: h };
  return { bounds: { x: canvas.x + alpha.x * w, y: canvas.y + alpha.y * h, width: alpha.width * w, height: p.height }, canvas };
}
/** Smoothstep is monotonic: the server's endpoint union bounds the entire path. */
export function placementAt(layout: SegmentLayout, previous: Placement | undefined, elapsed: number): Placement {
  const start = layout.motion_from ?? previous;
  if (!start || layout.transition === "cut" || layout.transition_seconds <= 0) return layout.presenter;
  const t = Math.max(0, Math.min(1, elapsed / layout.transition_seconds)), k = t * t * (3 - 2 * t);
  return { ...layout.presenter, x: start.x + (layout.presenter.x - start.x) * k,
    y: start.y + (layout.presenter.y - start.y) * k, height: start.height + (layout.presenter.height - start.height) * k };
}
