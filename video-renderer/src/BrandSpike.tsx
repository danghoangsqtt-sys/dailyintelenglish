/**
 * Task 25.1 spike (not shipped): a morph-style branded intro and outro for owner review.
 *
 * "Morph" = PowerPoint-style: the same elements stay on screen and glide between layouts (position,
 * size, colour, radius) with spring easing, instead of cutting between unrelated slides.
 */
import React from "react";
import { AbsoluteFill, Audio, Easing, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

const FONT = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif";
const INK = "#F8FAFC";
const MUTED = "#C7D2FE";
const VIOLET = "#7C3AED";
const CYAN = "#22D3EE";
const AMBER = "#F59E0B";

export type BrandSpikeProps = {
  title: string;
  topic: string;
  cefrLevel: string;
  speakers: string[];
  wish: string;
  greetingPath: string;
  farewellPath: string;
  introSec: number;
  gapSec: number;
  outroSec: number;
};

const mix = (from: number, to: number, t: number) => from + (to - from) * t;

function mixColor(a: string, b: string, t: number): string {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  return `rgb(${pa.map((value, i) => Math.round(mix(value, pb[i], t))).join(",")})`;
}

/** Spring from 0 to 1 starting at `startSec`. */
function useMorph(startSec: number, damping = 18, durationSec = 1.0): number {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - Math.round(startSec * fps), fps, config: { damping, mass: 0.9 },
    durationInFrames: Math.round(durationSec * fps) });
}

function Blobs({ morph, drift }: { morph: number; drift: number }) {
  const blobs = [
    { a: [260, 180, 520], b: [1080, 160, 620], c1: VIOLET, c2: "#4F46E5" },
    { a: [1040, 560, 460], b: [220, 600, 520], c1: CYAN, c2: "#0EA5E9" },
    { a: [700, 360, 300], b: [760, 700, 360], c1: "#DB2777", c2: AMBER },
  ];
  return (
    <>
      {blobs.map((blob, index) => {
        const x = mix(blob.a[0], blob.b[0], morph) + Math.sin(drift + index * 2) * 18;
        const y = mix(blob.a[1], blob.b[1], morph) + Math.cos(drift * 0.8 + index) * 14;
        const size = mix(blob.a[2], blob.b[2], morph);
        return (
          <div key={index} style={{
            position: "absolute", left: x - size / 2, top: y - size / 2, width: size, height: size,
            borderRadius: "50%", filter: "blur(70px)", opacity: 0.55,
            background: `radial-gradient(circle, ${mixColor(blob.c1, blob.c2, morph)} 0%, transparent 70%)`,
          }} />
        );
      })}
    </>
  );
}

function Background({ morph }: { morph: number }) {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: "linear-gradient(135deg, #0B1026 0%, #151339 55%, #1E1B4B 100%)", overflow: "hidden" }}>
      <Blobs morph={morph} drift={frame / 45} />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, transparent 40%, rgba(5,6,20,0.65) 100%)" }} />
    </AbsoluteFill>
  );
}

/** The logo mark + wordmark, morphing between a centred hero layout (0) and a top-left header (1). */
function Logo({ morph, appear }: { morph: number; appear: number }) {
  const markSize = mix(150, 64, morph);
  const markX = mix(640 - 75 - 0, 72, morph);
  const markY = mix(190, 44, morph);
  const wordX = mix(640, 72 + 64 + 18, morph);
  const wordY = mix(380, 50, morph);
  const wordSize = mix(64, 28, morph);
  return (
    <>
      <div style={{
        position: "absolute", left: markX, top: markY, width: markSize, height: markSize,
        borderRadius: mix(40, 16, morph), transform: `scale(${appear})`, opacity: appear,
        background: `linear-gradient(135deg, ${VIOLET}, ${CYAN})`,
        boxShadow: `0 ${mix(24, 8, morph)}px ${mix(60, 20, morph)}px rgba(124,58,237,0.45)`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontFamily: FONT, fontWeight: 800, color: INK, fontSize: markSize * 0.42, letterSpacing: -1,
      }}>DI</div>
      <div style={{
        position: "absolute", left: wordX, top: wordY, transform: `translateX(${mix(-50, 0, morph)}%)`,
        opacity: appear, fontFamily: FONT, color: INK, whiteSpace: "nowrap", textAlign: morph < 0.5 ? "center" : "left",
      }}>
        <div style={{ fontSize: wordSize, fontWeight: 800, letterSpacing: -0.5, lineHeight: 1.05 }}>Daily Intel</div>
        <div style={{ fontSize: wordSize * 0.42, fontWeight: 600, letterSpacing: wordSize * 0.18, color: CYAN }}>ENGLISH</div>
      </div>
    </>
  );
}

function rise(progress: number) {
  return { opacity: progress, transform: `translateY(${mix(28, 0, progress)}px)` };
}

function Intro(props: BrandSpikeProps) {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const appear = useMorph(0.15, 14, 0.9);
  const morph = useMorph(1.7, 20, 1.1);
  const titleIn = useMorph(2.3, 18, 0.9);
  const metaIn = useMorph(2.6, 18, 0.9);
  const wishIn = useMorph(3.4, 18, 0.9);
  const exit = interpolate(frame, [durationInFrames - Math.round(0.6 * fps), durationInFrames], [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.ease) });
  return (
    <AbsoluteFill style={{ opacity: exit }}>
      <Background morph={morph} />
      <Logo morph={morph} appear={appear} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 230, textAlign: "center", fontFamily: FONT }}>
        <div style={{ ...rise(titleIn), fontSize: 64, fontWeight: 800, color: INK, letterSpacing: -1, padding: "0 120px" }}>
          {props.title}
        </div>
        <div style={{ ...rise(metaIn), marginTop: 22, display: "flex", justifyContent: "center", gap: 14, alignItems: "center" }}>
          <span style={{ padding: "6px 14px", borderRadius: 999, background: AMBER, color: "#1F1300", fontWeight: 800, fontSize: 22 }}>
            {props.cefrLevel}
          </span>
          <span style={{ fontSize: 26, color: MUTED, fontWeight: 600 }}>{props.topic}</span>
        </div>
        <div style={{ ...rise(metaIn), marginTop: 22, display: "flex", justifyContent: "center", gap: 12 }}>
          {props.speakers.map((name, index) => (
            <span key={name} style={{ padding: "8px 18px", borderRadius: 999, fontSize: 22, fontWeight: 700, color: INK,
              background: "rgba(255,255,255,0.08)", border: `2px solid ${index === 0 ? AMBER : "#58A6FF"}` }}>{name}</span>
          ))}
        </div>
        <div style={{ ...rise(wishIn), marginTop: 46, fontSize: 30, fontStyle: "italic", color: INK, opacity: wishIn * 0.92 }}>
          “{props.wish}”
        </div>
      </div>
      <Audio src={staticFile(props.greetingPath)} startFrom={0} />
    </AbsoluteFill>
  );
}

function Outro(props: BrandSpikeProps) {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const enter = interpolate(frame, [0, Math.round(0.6 * fps)], [0, 1], { extrapolateRight: "clamp" });
  const appear = useMorph(0.2, 14, 0.9);
  const morph = 1 - useMorph(0.2, 20, 1.1); // the header logo glides back to the centre
  const lift = useMorph(1.5, 20, 1.0);
  const chips = ["👍  Like", "🔔  Subscribe", "↗  Share"];
  const exit = interpolate(frame, [durationInFrames - Math.round(0.9 * fps), durationInFrames], [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ opacity: enter * exit }}>
      <Background morph={1 - morph} />
      <div style={{ position: "absolute", inset: 0, transform: `translateY(${mix(0, -70, lift)}px)` }}>
        <Logo morph={morph} appear={appear} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 440, textAlign: "center", fontFamily: FONT }}>
        <div style={{ ...rise(lift), fontSize: 46, fontWeight: 800, color: INK }}>Thanks for watching!</div>
        <div style={{ marginTop: 26, display: "flex", justifyContent: "center", gap: 16 }}>
          {chips.map((chip, index) => {
            const pop = spring({ frame: frame - Math.round((2.0 + index * 0.18) * fps), fps, config: { damping: 12 } });
            return (
              <span key={chip} style={{ transform: `scale(${pop})`, opacity: pop, padding: "12px 26px", borderRadius: 999,
                fontSize: 26, fontWeight: 800, color: index === 1 ? "#FFFFFF" : INK,
                background: index === 1 ? "#E11D48" : "rgba(255,255,255,0.1)", border: "2px solid rgba(255,255,255,0.18)" }}>{chip}</span>
            );
          })}
        </div>
        <div style={{ ...rise(useMorph(2.8, 18, 0.9)), marginTop: 30, fontSize: 26, color: MUTED }}>See you in the next lesson</div>
      </div>
      <Audio src={staticFile(props.farewellPath)} startFrom={0} />
    </AbsoluteFill>
  );
}

export const BrandSpike: React.FC<BrandSpikeProps> = (props) => {
  const { fps } = useVideoConfig();
  const intro = Math.round(props.introSec * fps);
  const gap = Math.round(props.gapSec * fps);
  const outro = Math.round(props.outroSec * fps);
  return (
    <AbsoluteFill style={{ backgroundColor: "#0E0F15" }}>
      <Sequence from={0} durationInFrames={intro} name="BrandIntro">
        <Intro {...props} />
      </Sequence>
      <Sequence from={intro} durationInFrames={gap} name="EpisodePlaceholder">
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", color: "#64748B", fontFamily: FONT, fontSize: 28 }}>
          … the episode plays here …
        </AbsoluteFill>
      </Sequence>
      <Sequence from={intro + gap} durationInFrames={outro} name="BrandOutro">
        <Outro {...props} />
      </Sequence>
    </AbsoluteFill>
  );
};
