/**
 * Phase 32 (Task 32.3): the "Podcast: talking characters" layer -- the scene plate, an insert beat's activity picture over it
 * (Task 32.8b), then the two sprites. Each sprite is one picture
 * shown exactly as it was made (owner 2026-10-08: nothing pasted on it, never squashed); `spriteTimeline.ts` says which one.
 */
import React from "react";
import { AbsoluteFill, Img, staticFile, useVideoConfig } from "remotion";
import { BOTTOM_SHADE_STYLE } from "./captionStyle";
import { activityCutawayAt, cameraAt, canvasBox, onStage, poseFade, spriteBackground, spriteFrame, spriteTransform } from "./spriteTimeline";
import { VERTICAL } from "./safeZone";
import { cueEnvelope, insertMotion, sceneMotion } from "./verticalMotion";
import { MotionAccents } from "./MotionAccents";
import { pictureAlignment } from "./conversationMotion";
import type { EpisodeLine, EpisodeSprites, Layout, SpriteCharacter } from "./types";

const FILL: React.CSSProperties = { position: "absolute", width: "100%", height: "100%", objectFit: "cover" };
/** Phase 37 (D100) / 42 (D121): the picture area of the vertical video (top part, decoration that may run under the
 * platform's top bar); the band below it holds the captions, then the characters (`safeZone.ts`). */
export const VERTICAL_PICTURE: React.CSSProperties = { ...FILL, height: VERTICAL.picture.height };

/** The scene's colors carry through the lower stage rather than ending in a black strip. */
function AmbientScene({ previous, current, opacity }: { previous: string | null; current: string | null; opacity: number }) {
  return (
    <>
      <AbsoluteFill style={{ background: "linear-gradient(165deg, #133b2a, #061813 65%, #071317)" }} />
      <div style={{ position: "absolute", inset: -40, filter: "blur(28px) saturate(0.8)", opacity: 0.28 }}>
        {previous ? <Img src={staticFile(previous)} style={FILL} /> : null}
        {current ? <Img src={staticFile(current)} style={{ ...FILL, opacity }} /> : null}
      </div>
      <AbsoluteFill style={{ background: "linear-gradient(to bottom, rgba(6,24,19,0.1), rgba(6,24,19,0.78) 48%, #061813)" }} />
    </>
  );
}

function Sprite({ character, frame, fps, lines, sprites, totalFrames, layout }: {
  character: SpriteCharacter; frame: number; fps: number; lines: EpisodeLine[]; sprites: EpisodeSprites; totalFrames: number;
  layout: Layout;
}) {
  const { width, height } = useVideoConfig();
  const box = canvasBox(character.slot, width, height, sprites.characters, layout);
  const state = spriteFrame(character, frame, fps, lines, sprites, totalFrames, width);
  const fade = poseFade(character, frame, fps, lines, sprites, totalFrames, width);
  // Phase 61: each picture keeps its own head alignment; the previous pose fades out over the new one
  const layer = (picture: string, opacity: number) => {
    const alignment = pictureAlignment(character, picture, box.width, box.height);
    return (
      <div key={picture} data-sprite-picture={picture} style={{
        position: "absolute", left: box.left, top: box.top, width: box.width, height: box.height,
        transform: spriteTransform({ ...state, x: state.x + alignment.x, y: state.y + alignment.y }, character.mirror),
        transformOrigin: "50% 85%", opacity, filter: `brightness(${state.brightness.toFixed(3)})`,
      }}>
        <Img src={staticFile(character.pictures[picture])} style={{ position: "absolute", width: "100%", height: "100%" }} />
      </div>
    );
  };
  return (
    <>
      {layer(state.picture, state.opacity)}
      {fade && fade.picture !== state.picture ? layer(fade.picture, state.opacity * fade.opacity) : null}
    </>
  );
}

export function SpriteStage({ sprites, lines, fps, frame, totalFrames, progress, layout = "horizontal" }: {
  sprites: EpisodeSprites; lines: EpisodeLine[]; fps: number; frame: number; totalFrames: number; progress: number;
  layout?: Layout;
}) {
  const background = spriteBackground(frame, fps, lines, sprites);
  const { width, height } = useVideoConfig();
  const camera = cameraAt(frame, fps, lines, sprites, width, height, layout);
  const cutaway = activityCutawayAt(frame / fps, sprites);
  const insertIndex = sprites.cutaways.findIndex((item) => frame / fps >= item.startSec && frame / fps < item.endSec);
  const insert = sprites.cutaways[insertIndex];
  const reveal = insert ? insertMotion(frame / fps, insert.startSec, insert.endSec, insertIndex) : null;
  const lineIndex = lines.findIndex((line) => frame / fps >= line.startSec && frame / fps < line.endSec);
  const spoken = lines[lineIndex];
  const motion = sceneMotion(frame, fps);
  const zoom = `translate(${motion.x.toFixed(2)}px, ${motion.y.toFixed(2)}px) scale(${motion.scale.toFixed(4)})`;
  const picture = layout === "vertical" ? VERTICAL_PICTURE : FILL;
  const scene = (
    <>
      {background.previous ? <Img src={staticFile(background.previous)} style={{ ...picture, transform: zoom }} /> : null}
      {background.current ? (
        <Img src={staticFile(background.current)} style={{ ...picture, transform: zoom, opacity: background.opacity }} />
      ) : null}
      {/* Composite the insert over the scene before fading the whole picture into the ambient stage. */}
      {cutaway ? <Img src={staticFile(cutaway.url)} style={{ ...picture,
        transform: reveal ? `${zoom} translateX(${reveal.x.toFixed(2)}px) scale(${reveal.scale.toFixed(4)})` : zoom,
        clipPath: reveal
          ? `inset(0 ${reveal.fromRight ? 0 : reveal.hiddenPercent}% 0 ${reveal.fromRight ? reveal.hiddenPercent : 0}%)` : undefined,
        opacity: cutaway.opacity }} /> : null}
      {reveal && reveal.sweepOpacity > 0 ? (
        <div style={{ position: "absolute", top: -100, height: height + 200, width: 180,
          left: -260 + reveal.sweep * 1600, transform: "rotate(-18deg)", opacity: reveal.sweepOpacity,
          background: "linear-gradient(90deg, transparent, #FFF1BE, transparent)" }} />
      ) : null}
    </>
  );
  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: "#000000" }}>
      {/* Phase 61: the camera pushes in toward the speaker; the shades stay put */}
      <AbsoluteFill data-sprite-camera={camera.scale.toFixed(3)} style={{ transform: `scale(${camera.scale.toFixed(4)})`,
        transformOrigin: `${camera.originX.toFixed(1)}px ${camera.originY.toFixed(1)}px` }}>
      {layout === "vertical" ? <AmbientScene {...background} /> : null}
      {layout === "vertical" ? (
        <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: VERTICAL.picture.height, overflow: "hidden",
          maskImage: `linear-gradient(to bottom, #000 ${VERTICAL.fade.top}px, transparent ${VERTICAL.picture.height}px)` }}>
          {scene}
        </div>
      ) : scene}
      {layout === "vertical" ? (
        <div style={{ position: "absolute", left: 0, right: 0, top: 900, height: 850,
          background: "radial-gradient(ellipse at 50% 40%, rgba(90,155,82,0.24), transparent 68%)",
          opacity: 0.8 + 0.12 * Math.sin(frame / fps * Math.PI / 4) }} />
      ) : null}
      <MotionAccents frame={frame} fps={fps} layout={layout}
        activeSlot={sprites.lines[lineIndex]?.slot ?? null}
        strength={spoken ? cueEnvelope(frame / fps, spoken.startSec, spoken.endSec) : 0} />
      {sprites.characters.filter((character) => onStage(character, frame, fps)).map((character) => (
        <Sprite key={`${character.slot}-${character.name}-${character.fromSec}`} character={character} frame={frame} fps={fps}
          lines={lines} sprites={sprites} totalFrames={totalFrames} layout={layout} />
      ))}
      </AbsoluteFill>
      <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: "18%",
        background: "linear-gradient(to bottom, rgba(0,0,0,0.45), rgba(0,0,0,0))" }} />
      {layout === "vertical" ? null : <div style={BOTTOM_SHADE_STYLE} />}
    </AbsoluteFill>
  );
}
