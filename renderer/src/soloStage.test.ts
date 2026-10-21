import { describe, expect, it } from "vitest";
import { SCENE_CROSSFADE_SEC, stagePlates } from "./SoloStage";
import type { SoloPayload } from "./soloTypes";

function payload(scenes: (string | null)[]): SoloPayload {
  return {
    plan: { project_id: "p", revision: 1, status: "approved", source_fingerprint: "a", aspects: ["16:9"],
      segments: scenes.map((scene, i) => ({ id: `s${i}`, scene: scene ? { scene_id: scene } : null, visual: { kind: "text_card", title: "T" } })) },
    timeline: scenes.map((_, i) => ({ id: `s${i}`, start_sec: i * 10, end_sec: i * 10 + 10 })),
    scenes: { office: "plates/office.png", park: "plates/park.png" }, pictures: {}, photos: {},
  } as unknown as SoloPayload;
}

describe("Solo stage plates (Phase 55)", () => {
  it("shows the segment's plate and keeps it steady while the place stays the same", () => {
    const data = payload(["office", "office"]);
    expect(stagePlates(data, 0, 3)).toEqual({ previous: null, current: "plates/office.png", opacity: 1 });
    expect(stagePlates(data, 1, 10.1)).toEqual({ previous: null, current: "plates/office.png", opacity: 1 });
  });
  it("crossfades into a new place and seeks deterministically", () => {
    const data = payload(["office", "park"]);
    expect(stagePlates(data, 1, 10).opacity).toBe(0);
    expect(stagePlates(data, 1, 10 + SCENE_CROSSFADE_SEC / 2).opacity).toBeCloseTo(0.5);
    expect(stagePlates(data, 1, 15)).toEqual({ previous: "plates/office.png", current: "plates/park.png", opacity: 1 });
  });
  it("falls back to no plate when a segment has no scene", () => {
    expect(stagePlates(payload([null]), 0, 1)).toEqual({ previous: null, current: null, opacity: 1 });
  });
});
