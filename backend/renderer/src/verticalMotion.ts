/** Frame-driven motion: deterministic during parallel renders and seeking. */
export function sceneMotion(frame: number, fps: number): { x: number; y: number; scale: number } {
  const phase = (Math.max(0, frame) / Math.max(1, fps)) * Math.PI * 2 / 20;
  return { x: 12 * Math.sin(phase), y: 6 * Math.cos(phase), scale: 1.025 + 0.015 * (1 - Math.cos(phase)) };
}

/** A page remains readable from its first frame while settling into place. */
export function captionEntrance(timeMs: number, startMs: number): { opacity: number; y: number } {
  const t = Math.min(1, Math.max(0, (timeMs - startMs) / 180));
  const eased = 1 - (1 - t) ** 3;
  return { opacity: 0.72 + 0.28 * eased, y: 8 * (1 - eased) };
}

/** Brief emphasis inside a word's real audio interval; never changes text layout. */
export function wordScale(timeMs: number, fromMs: number, toMs: number): number {
  if (timeMs < fromMs || timeMs >= toMs) return 1;
  const t = Math.min(1, (timeMs - fromMs) / Math.min(140, Math.max(1, toMs - fromMs)));
  return 1 + 0.07 * Math.sin(Math.PI * t);
}

const clamp = (value: number): number => Math.min(1, Math.max(0, value));
const ease = (value: number): number => 1 - (1 - clamp(value)) ** 3;

/** Alternate page entrances while shrinking just enough to stay inside the caption column. */
export function captionMotion(timeMs: number, startMs: number) {
  const entrance = captionEntrance(timeMs, startMs);
  const remaining = 1 - ease((timeMs - startMs) / 180);
  const direction = Math.floor(startMs / 1000) % 2 ? 1 : -1;
  return { ...entrance, x: direction * 4 * remaining, scale: 1 - 0.018 * remaining };
}

/** Progress follows the current page's audio interval, including pauses between its words. */
export function readingProgress(timeMs: number, startMs: number, endMs: number): number {
  return clamp((timeMs - startMs) / Math.max(1, endMs - startMs));
}

/** Three complementary accents retain the same yellow highlight and real word timing. */
export function wordAccent(timeMs: number, fromMs: number, toMs: number, variant: number) {
  const pulse = clamp((wordScale(timeMs, fromMs, toMs) - 1) / 0.07);
  const mode = Math.abs(Math.floor(variant)) % 3;
  return { scale: 1 + (mode === 1 ? 0.025 : mode === 2 ? 0.04 : 0.07) * pulse,
    y: mode === 1 ? -2.5 * pulse : 0, glow: 12 + (mode === 2 ? 12 : 3) * pulse };
}

/** Whole learning cards slide/pop in, then leave softly inside their own learning slot. */
export function learningMotion(timeSec: number, startSec: number, endSec: number) {
  const enter = ease((timeSec - startSec) / 0.32);
  const leave = ease((endSec - timeSec) / 0.2);
  const remaining = 1 - Math.min(enter, leave);
  return { x: 8 * remaining, y: 8 * remaining, scale: 1 - 0.04 * remaining,
    rotation: -0.5 * remaining, sweep: clamp((timeSec - startSec) / 0.7) };
}

/** An approved activity insert reveals from alternating sides and settles without moving the scene mask. */
export function insertMotion(timeSec: number, startSec: number, endSec: number, index: number) {
  const entered = ease((timeSec - startSec) / 0.42);
  const direction = index % 2 ? -1 : 1;
  const sweep = clamp((timeSec - startSec) / 0.7);
  const present = timeSec >= startSec && timeSec < endSec;
  return { x: direction * 16 * (1 - entered), scale: 1 + 0.025 * (1 - entered),
    hiddenPercent: 100 * (1 - entered), fromRight: direction < 0, sweep,
    sweepOpacity: present && sweep < 1 ? 0.12 * Math.sin(Math.PI * sweep) : 0 };
}

/** A visual speaking indicator, not an estimate of audio amplitude. */
export function speakingMeter(frame: number, fps: number, speaking: boolean): number[] {
  const time = Math.max(0, frame) / Math.max(1, fps);
  return [0, 1, 2].map((index) => speaking ? 4 + 11 * (0.5 + 0.5 * Math.sin(time * 13 + index * 2.1)) : 4);
}

export function cueEnvelope(timeSec: number, startSec: number, endSec: number): number {
  if (endSec <= startSec) return 0;
  return Math.min(ease((timeSec - startSec) / 0.25), ease((endSec - timeSec) / 0.2));
}

/** Sparse light motes stay in the decorative side gutters, behind all readable content. */
export function ambientParticles(frame: number, fps: number) {
  const time = Math.max(0, frame) / Math.max(1, fps);
  return [52, 1024, 86, 994, 40, 1042, 112, 968].map((x, index) => {
    const progress = (((index * 191 - time * (12 + index)) % 1400) + 1400) % 1400 / 1400;
    return { x, y: 280 + progress * 1400, size: 4 + index % 3 * 2,
      opacity: 0.16 * Math.sin(Math.PI * progress) };
  });
}
