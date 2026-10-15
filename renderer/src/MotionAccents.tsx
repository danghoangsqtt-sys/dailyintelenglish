import React from "react";
import { ambientParticles } from "./verticalMotion";
import { useVideoConfig } from "remotion";
import { accentLayout } from "./motionLayout";
import type { Layout } from "./types";

/** Decorative motion is drawn behind the unmodified character pictures and all text. */
export function MotionAccents({ frame, fps, activeSlot, strength, layout = "vertical" }: {
  frame: number; fps: number; activeSlot: number | null; strength: number; layout?: Layout;
}) {
  const { width, height } = useVideoConfig();
  const geometry = accentLayout(layout, width, height);
  return (
    <>
      {geometry.centers.map((x, slot) => (
        <div key={slot} style={{ position: "absolute", left: x - geometry.width / 2, top: geometry.top,
          width: geometry.width, height: geometry.height,
          borderRadius: "50%", opacity: activeSlot === slot ? strength * 0.34 : 0,
          background: "radial-gradient(ellipse, rgba(203,198,93,0.8), rgba(75,154,89,0.25) 42%, transparent 72%)" }} />
      ))}
      {ambientParticles(frame, fps).map((particle, index) => (
        <div key={index} style={{ position: "absolute", left: particle.x / 1080 * width, top: particle.y / 1920 * height,
          width: particle.size * geometry.particleScale, height: particle.size * geometry.particleScale,
          borderRadius: "50%", opacity: particle.opacity,
          background: index % 2 ? "#A6D68B" : "#F8DB80", boxShadow: "0 0 12px rgba(241,214,112,0.3)" }} />
      ))}
    </>
  );
}
