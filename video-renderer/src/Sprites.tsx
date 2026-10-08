/**
 * Phase 32 (Task 32.3): the "Podcast: talking characters" layer -- the scene plate, then the two sprites. Each sprite is one body
 * picture (the calm picture or a gesture) with the face of the current expression and mouth laid over it inside a feathered ellipse,
 * so the body never shimmers when the mouth moves. All numbers come from `spriteTimeline.ts`.
 */
import React from "react";
import { AbsoluteFill, Img, staticFile, useVideoConfig } from "remotion";
import { BOTTOM_SHADE_STYLE } from "./captionStyle";
import { stillScale } from "./podcastLayout";
import { canvasBox, faceMask, spriteBackground, spriteFrame } from "./spriteTimeline";
import type { EpisodeLine, EpisodeSprites, SpriteCharacter } from "./types";

const FILL: React.CSSProperties = { position: "absolute", width: "100%", height: "100%", objectFit: "cover" };

function Sprite({ character, frame, fps, lines, sprites, totalFrames }: {
  character: SpriteCharacter; frame: number; fps: number; lines: EpisodeLine[]; sprites: EpisodeSprites; totalFrames: number;
}) {
  const { width, height } = useVideoConfig();
  const box = canvasBox(character.slot, width, height, sprites.characters);
  const state = spriteFrame(character, frame, fps, lines, sprites, totalFrames, width);
  const pixel = box.height / 1536;
  const mask = state.face ? faceMask(character.faceEllipse, state.maskCentre) : undefined;
  return (
    <div style={{
      position: "absolute", left: box.left, top: box.top, width: box.width, height: box.height,
      transform: `translate(${state.x.toFixed(1)}px, ${state.y.toFixed(2)}px) scale(${(state.scale * state.flip).toFixed(4)}, ${state.scale.toFixed(4)})`,
      transformOrigin: "50% 100%", opacity: state.opacity, filter: `brightness(${state.brightness.toFixed(3)})`,
    }}>
      <Img src={staticFile(character.pictures[state.body])} style={{ position: "absolute", width: "100%", height: "100%" }} />
      {state.face ? (
        <Img src={staticFile(character.pictures[state.face])} style={{
          position: "absolute", width: "100%", height: "100%",
          transform: `translate(${(state.faceShift[0] * pixel).toFixed(2)}px, ${(state.faceShift[1] * pixel).toFixed(2)}px)`,
          WebkitMaskImage: mask, maskImage: mask,
        }} />
      ) : null}
    </div>
  );
}

export function SpriteStage({ sprites, lines, fps, frame, totalFrames, progress }: {
  sprites: EpisodeSprites; lines: EpisodeLine[]; fps: number; frame: number; totalFrames: number; progress: number;
}) {
  const background = spriteBackground(frame, fps, lines, sprites);
  const zoom = `scale(${stillScale(progress).toFixed(4)})`;
  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: "#000000" }}>
      {background.previous ? <Img src={staticFile(background.previous)} style={{ ...FILL, transform: zoom }} /> : null}
      {background.current ? (
        <Img src={staticFile(background.current)} style={{ ...FILL, transform: zoom, opacity: background.opacity }} />
      ) : null}
      {sprites.characters.map((character) => (
        <Sprite key={character.slot} character={character} frame={frame} fps={fps} lines={lines} sprites={sprites}
          totalFrames={totalFrames} />
      ))}
      <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: "18%",
        background: "linear-gradient(to bottom, rgba(0,0,0,0.45), rgba(0,0,0,0))" }} />
      <div style={BOTTOM_SHADE_STYLE} />
    </AbsoluteFill>
  );
}
