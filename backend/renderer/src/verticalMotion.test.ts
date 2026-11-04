import { describe, expect, it } from "vitest";
import { ambientParticles, captionEntrance, captionMotion, cueEnvelope, insertMotion, learningMotion,
  readingProgress, sceneMotion, speakingMeter, wordAccent, wordScale } from "./verticalMotion";

describe("vertical visual motion", () => {
  it("stays bounded and reproducible across the entire episode at different frame rates", () => {
    for (const fps of [24, 30, 60]) {
      for (let frame = 0; frame <= fps * 300; frame += 13) {
        const motion = sceneMotion(frame, fps);
        expect(Math.abs(motion.x)).toBeLessThanOrEqual(12);
        expect(Math.abs(motion.y)).toBeLessThanOrEqual(6);
        expect(motion.scale).toBeGreaterThanOrEqual(1.025);
        expect(motion.scale).toBeLessThanOrEqual(1.055);
        expect(sceneMotion(frame, fps)).toEqual(motion);
      }
    }
    expect(sceneMotion(300, 30)).toEqual(sceneMotion(600, 60));
  });

  it("keeps a caption readable during its entrance and settles in 180 milliseconds", () => {
    expect(captionEntrance(900, 1000)).toEqual({ opacity: 0.72, y: 8 });
    expect(captionEntrance(1180, 1000)).toEqual({ opacity: 1, y: 0 });
    expect(captionEntrance(2000, 1000)).toEqual({ opacity: 1, y: 0 });
    expect(captionEntrance(1090, 1000).opacity).toBeGreaterThan(0.9);
  });

  it("emphasizes only the currently spoken word and settles before its interval ends", () => {
    expect(wordScale(999, 1000, 1500)).toBe(1);
    expect(wordScale(1070, 1000, 1500)).toBeCloseTo(1.07);
    expect(wordScale(1200, 1000, 1500)).toBeCloseTo(1);
    expect(wordScale(1500, 1000, 1500)).toBe(1);
    expect(wordScale(1025, 1000, 1050)).toBeCloseTo(1.07);
    expect(wordScale(1000, 1000, 1000)).toBe(1);
  });
});

describe("expanded vertical motion cues", () => {
  it("keeps alternating caption entrances within the existing horizontal safe column", () => {
    for (const start of [1000, 2000, 3010]) {
      for (let elapsed = -30; elapsed <= 300; elapsed += 3) {
        const motion = captionMotion(start + elapsed, start);
        const left = 216 + 324 * (1 - motion.scale) + motion.x;
        expect(left).toBeGreaterThanOrEqual(216);
        expect(left + 648 * motion.scale).toBeLessThanOrEqual(864.001);
      }
      const settled = captionMotion(start + 180, start);
      expect(settled.x).toBeCloseTo(0);
      expect(settled).toMatchObject({ y: 0, scale: 1, opacity: 1 });
    }
  });

  it("finishes an activity reveal and light sweep while the insert is still fully visible", () => {
    expect(insertMotion(10, 10, 16, 0).hiddenPercent).toBe(100);
    expect(insertMotion(10.5, 10, 16, 0)).toMatchObject({ hiddenPercent: 0, x: 0, scale: 1 });
    expect(insertMotion(11, 10, 16, 0).sweepOpacity).toBe(0);
    expect(insertMotion(10.1, 10, 16, 0).x).toBeGreaterThan(0);
    expect(insertMotion(10.1, 10, 16, 1).x).toBeLessThan(0);
    expect(insertMotion(16, 10, 16, 1).sweepOpacity).toBe(0);
  });

  it("bounds learning-card motion, speech cues and decorative particles across the episode", () => {
    for (let frame = 0; frame < 30 * 300; frame += 11) {
      const card = learningMotion(frame / 30, 10, 18);
      expect(card.scale).toBeGreaterThanOrEqual(0.96);
      expect(card.scale).toBeLessThanOrEqual(1);
      expect(card.x).toBeLessThanOrEqual(8);
      expect(Math.abs(card.rotation)).toBeLessThanOrEqual(0.5);
      for (const particle of ambientParticles(frame, 30)) {
        expect(particle.x < 120 || particle.x > 960).toBe(true);
        expect(particle.y).toBeGreaterThanOrEqual(280);
        expect(particle.y).toBeLessThanOrEqual(1680);
        expect(particle.opacity).toBeGreaterThanOrEqual(0);
        expect(particle.opacity).toBeLessThanOrEqual(0.16);
      }
      for (const bar of speakingMeter(frame, 30, true)) {
        expect(bar).toBeGreaterThanOrEqual(4);
        expect(bar).toBeLessThanOrEqual(15);
      }
      expect(ambientParticles(frame, 30)).toEqual(ambientParticles(frame * 2, 60));
    }
    expect(learningMotion(11, 10, 18)).toMatchObject({ x: 0, y: 0, scale: 1 });
    expect(learningMotion(11, 10, 18).rotation).toBeCloseTo(0);
    expect(cueEnvelope(9, 10, 18)).toBe(0);
    expect(cueEnvelope(11, 10, 18)).toBe(1);
    expect(cueEnvelope(19, 10, 18)).toBe(0);
    expect(cueEnvelope(10, 10, 10)).toBe(0);
    expect(speakingMeter(300, 30, false)).toEqual([4, 4, 4]);
  });

  it("keeps progress and word effects tied to the original audio intervals", () => {
    expect(readingProgress(900, 1000, 2000)).toBe(0);
    expect(readingProgress(1500, 1000, 2000)).toBe(0.5);
    expect(readingProgress(2200, 1000, 2000)).toBe(1);
    for (const variant of [0, 1, 2]) {
      const idle = wordAccent(900, 1000, 1500, variant);
      const active = wordAccent(1070, 1000, 1500, variant);
      expect(idle.scale).toBe(1);
      expect(idle.y).toBeCloseTo(0);
      expect(active.scale).toBeGreaterThan(1);
      expect(active.scale).toBeLessThanOrEqual(1.07);
      expect(active.y).toBeGreaterThanOrEqual(-2.5);
      expect(active.glow).toBeLessThanOrEqual(24.001);
      expect(wordAccent(1600, 1000, 1500, variant)).toEqual(idle);
    }
  });
});
