/**
 * Phase 25 (D52-D55): the branded intro and outro, owner-approved in spike 25.1.
 *
 * "Morph" = PowerPoint-style: the same elements stay on screen and glide between layouts
 * (position, size, colour, radius) with spring easing instead of cutting between unrelated slides.
 * The intro opens on the logo, morphs it into a header, then brings in the episode; the outro
 * mirrors it. Jenny's greeting / farewell play here unless the full-video soundtrack already
 * carries them (Phase 22.4 + 25.2), so the music can duck under her.
 */
import React from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  Sequence,
  continueRender,
  delayRender,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type { EpisodeBrand, EpisodeSpeaker } from "./types";

export const BRAND_FONT = "'Montserrat', 'Segoe UI', Arial, sans-serif";
const INK = "#F8FAFC";
const MUTED = "#C7D2FE";
const VIOLET = "#7C3AED";
const CYAN = "#22D3EE";
const AMBER = "#F59E0B";
const SPEAKER_RING = ["#F59E0B", "#58A6FF"];
export const DEFAULT_WISH = "Wishing you a wonderful time learning English today!";

// Bundled SIL OFL font (video-renderer/public/fonts/OFL.txt); the render waits until it is loaded.
if (typeof document !== "undefined" && typeof FontFace !== "undefined") {
  const handle = delayRender("Loading Montserrat");
  const font = new FontFace("Montserrat", `url('${staticFile("fonts/Montserrat-Variable.ttf")}') format('truetype')`,
    { weight: "100 900" });
  font.load()
    .then((loaded) => {
      (document.fonts as unknown as { add: (face: FontFace) => void }).add(loaded);
      continueRender(handle);
    })
    .catch((error) => {
      console.warn("Montserrat failed to load; using the fallback font", error);
      continueRender(handle);
    });
}

export const mix = (from: number, to: number, t: number): number => from + (to - from) * t;

export function mixColor(a: string, b: string, t: number): string {
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

/** The logo mark + wordmark, morphing between a centred hero layout (0) and a top-left header (1).
 * The mark and the wordmark have their own progress: the mark leads into the header and the
 * wordmark follows (reversed in the outro), so the moving text never slides under the mark. */
function Logo({ markMorph, wordMorph, appear }: { markMorph: number; wordMorph: number; appear: number }) {
  const morph = markMorph;
  const markSize = mix(150, 76, morph);
  const markX = mix(640 - 75, 56, morph);
  const markY = mix(190, 36, morph);
  const wordX = mix(640, 56 + 76 + 26, wordMorph);
  const wordY = mix(380, 40, wordMorph);
  const wordSize = mix(64, 34, wordMorph);
  return (
    <>
      <div style={{
        position: "absolute", left: markX, top: markY, width: markSize, height: markSize,
        borderRadius: mix(40, 20, morph), transform: `scale(${appear})`, opacity: appear,
        background: `linear-gradient(135deg, ${VIOLET}, ${CYAN})`,
        boxShadow: `0 ${mix(24, 10, morph)}px ${mix(60, 24, morph)}px rgba(124,58,237,0.45)`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontFamily: BRAND_FONT, fontWeight: 800, color: INK, fontSize: markSize * 0.42, letterSpacing: -1,
      }}>DI</div>
      <div style={{
        // The centring shift finishes early, so the moving wordmark never slides under the mark.
        position: "absolute", left: wordX, top: wordY, transform: `translateX(${mix(-50, 0, Math.min(1, wordMorph * 1.6))}%)`,
        opacity: appear, fontFamily: BRAND_FONT, color: INK, whiteSpace: "nowrap",
        textAlign: wordMorph < 0.5 ? "center" : "left",
      }}>
        <div style={{ fontSize: wordSize, fontWeight: 800, letterSpacing: -0.5, lineHeight: 1.05 }}>Daily Intel</div>
        <div style={{ fontSize: Math.max(14, wordSize * 0.42), fontWeight: 700, letterSpacing: wordSize * 0.16,
          color: CYAN, marginTop: 2 }}>ENGLISH</div>
      </div>
    </>
  );
}

function rise(progress: number) {
  return { opacity: progress, transform: `translateY(${mix(28, 0, progress)}px)` };
}

function BrandVoice({ path, startSec }: { path?: string; startSec?: number }) {
  const { fps } = useVideoConfig();
  if (!path) return null;
  // A Sequence shifts the Audio's own timeline, so the voice starts from its first sample here.
  return (
    <Sequence from={Math.round((startSec ?? 0) * fps)} name="BrandVoice">
      <Audio src={staticFile(path)} />
    </Sequence>
  );
}

export function BrandIntro({ title, topic, cefrLevel, speakers, brand }: {
  title: string; topic: string; cefrLevel: string; speakers: EpisodeSpeaker[]; brand?: EpisodeBrand;
}) {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const appear = useMorph(0.15, 14, 0.9);
  const markMorph = useMorph(1.55, 20, 0.85);
  const morph = useMorph(1.75, 20, 1.1);
  const titleIn = useMorph(2.3, 18, 0.9);
  const metaIn = useMorph(2.6, 18, 0.9);
  const wishIn = useMorph(3.4, 18, 0.9);
  const exit = interpolate(frame, [durationInFrames - Math.round(0.6 * fps), durationInFrames], [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.ease) });
  const playVoice = brand && !brand.voicesInSoundtrack;
  return (
    <AbsoluteFill style={{ opacity: exit }}>
      <Background morph={morph} />
      <Logo markMorph={markMorph} wordMorph={morph} appear={appear} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 230, textAlign: "center", fontFamily: BRAND_FONT }}>
        <div style={{ ...rise(titleIn), fontSize: 62, fontWeight: 800, color: INK, letterSpacing: -1, padding: "0 120px" }}>
          {title}
        </div>
        <div style={{ ...rise(metaIn), marginTop: 22, display: "flex", justifyContent: "center", gap: 14, alignItems: "center" }}>
          {cefrLevel ? (
            <span style={{ padding: "6px 14px", borderRadius: 999, background: AMBER, color: "#1F1300", fontWeight: 800, fontSize: 22 }}>
              {cefrLevel}
            </span>
          ) : null}
          <span style={{ fontSize: 26, color: MUTED, fontWeight: 600 }}>{topic}</span>
        </div>
        <div style={{ ...rise(metaIn), marginTop: 22, display: "flex", justifyContent: "center", gap: 12 }}>
          {speakers.map((speaker, index) => (
            <span key={speaker.id} style={{ padding: "8px 18px", borderRadius: 999, fontSize: 22, fontWeight: 700, color: INK,
              background: "rgba(255,255,255,0.08)", border: `2px solid ${SPEAKER_RING[index % SPEAKER_RING.length]}` }}>
              {speaker.name}
            </span>
          ))}
        </div>
        <div style={{ ...rise(wishIn), marginTop: 46, fontSize: 30, fontStyle: "italic", fontWeight: 500, color: INK,
          opacity: wishIn * 0.92, padding: "0 140px" }}>
          “{brand?.wish ?? DEFAULT_WISH}”
        </div>
      </div>
      {playVoice ? <BrandVoice path={brand.greetingPath} startSec={brand.greetingStartSec} /> : null}
    </AbsoluteFill>
  );
}

export function BrandOutro({ brand }: { brand?: EpisodeBrand }) {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const enter = interpolate(frame, [0, Math.round(0.6 * fps)], [0, 1], { extrapolateRight: "clamp" });
  const appear = useMorph(0.2, 14, 0.9);
  // The header logo glides back to the centre: the wordmark leaves first, the mark follows.
  const morph = 1 - useMorph(0.2, 20, 1.1);
  const markMorph = 1 - useMorph(0.4, 20, 1.0);
  const lift = useMorph(1.5, 20, 1.0);
  const lineIn = useMorph(2.8, 18, 0.9);
  const chips = ["👍  Like", "🔔  Subscribe", "↗  Share"];
  const exit = interpolate(frame, [durationInFrames - Math.round(0.9 * fps), durationInFrames], [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const playVoice = brand && !brand.voicesInSoundtrack;
  return (
    <AbsoluteFill style={{ opacity: enter * exit }}>
      <Background morph={1 - morph} />
      <div style={{ position: "absolute", inset: 0, transform: `translateY(${mix(0, -70, lift)}px)` }}>
        <Logo markMorph={markMorph} wordMorph={morph} appear={appear} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 440, textAlign: "center", fontFamily: BRAND_FONT }}>
        <div style={{ ...rise(lift), fontSize: 46, fontWeight: 800, color: INK }}>Thanks for watching!</div>
        <div style={{ marginTop: 26, display: "flex", justifyContent: "center", gap: 16 }}>
          {chips.map((chip, index) => {
            const pop = spring({ frame: frame - Math.round((2.0 + index * 0.18) * fps), fps, config: { damping: 12 } });
            return (
              <span key={chip} style={{ transform: `scale(${pop})`, opacity: pop, padding: "12px 26px", borderRadius: 999,
                fontSize: 26, fontWeight: 800, color: INK,
                background: index === 1 ? "#E11D48" : "rgba(255,255,255,0.1)", border: "2px solid rgba(255,255,255,0.18)" }}>
                {chip}
              </span>
            );
          })}
        </div>
        <div style={{ ...rise(lineIn), marginTop: 30, fontSize: 26, fontWeight: 500, color: MUTED, padding: "0 140px" }}>
          {brand?.farewellLine ?? "See you in the next lesson"}
        </div>
      </div>
      {playVoice ? <BrandVoice path={brand.farewellPath} startSec={brand.farewellStartSec} /> : null}
    </AbsoluteFill>
  );
}
