/**
 * Phase 32 (Task 32.3): the "Podcast: talking characters" layer -- the scene plate, an insert beat's activity picture over it
 * (Task 32.8b), then the two sprites. Each sprite is one picture
 * shown exactly as it was made (owner 2026-10-08: nothing pasted on it, never squashed); `spriteTimeline.ts` says which one.
 */
import React from "react";
import { AbsoluteFill, Img, staticFile, useVideoConfig } from "remotion";
import { BOTTOM_SHADE_STYLE } from "./captionStyle";
import { stillScale } from "./podcastLayout";
import { activityCutawayAt, canvasBox, onStage, spriteBackground, spriteFrame, spriteTransform } from "./spriteTimeline";
import type { EpisodeLine, EpisodeSprites, Layout, SpriteCharacter } from "./types";

const FILL: React.CSSProperties = { position: "absolute", width: "100%", height: "100%", objectFit: "cover" };
/** Phase 37 (D100): the picture area of the vertical video (top part); the band below it holds the captions. */
export const VERTICAL_PICTURE: React.CSSProperties = { ...FILL, height: "56%" };
const VERTICAL_FADE: React.CSSProperties = { position: "absolute", left: 0, right: 0, top: "40%", height: "22%",
  background: "linear-gradient(to bottom, rgba(0,0,0,0), rgba(0,0,0,0.92))" };

function Sprite({ character, frame, fps, lines, sprites, totalFrames, layout }: {
  character: SpriteCharacter; frame: number; fps: number; lines: EpisodeLine[]; sprites: EpisodeSprites; totalFrames: number;
  layout: Layout;
}) {
  const { width, height } = useVideoConfig();
  const box = canvasBox(character.slot, width, height, sprites.characters, layout);
  const state = spriteFrame(character, frame, fps, lines, sprites, totalFrames, width);
  return (
    <div style={{
      position: "absolute", left: box.left, top: box.top, width: box.width, height: box.height,
      transform: spriteTransform(state, character.mirror),
      transformOrigin: "50% 100%", opacity: state.opacity, filter: `brightness(${state.brightness.toFixed(3)})`,
    }}>
      <Img src={staticFile(character.pictures[state.picture])} style={{ position: "absolute", width: "100%", height: "100%" }} />
    </div>
  );
}

export function SpriteStage({ sprites, lines, fps, frame, totalFrames, progress, layout = "horizontal" }: {
  sprites: EpisodeSprites; lines: EpisodeLine[]; fps: number; frame: number; totalFrames: number; progress: number;
  layout?: Layout;
}) {
  const background = spriteBackground(frame, fps, lines, sprites);
  const cutaway = activityCutawayAt(frame / fps, sprites);
  const zoom = `scale(${stillScale(progress).toFixed(4)})`;
  const picture = layout === "vertical" ? VERTICAL_PICTURE : FILL;
  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: "#000000" }}>
      {background.previous ? <Img src={staticFile(background.previous)} style={{ ...picture, transform: zoom }} /> : null}
      {background.current ? (
        <Img src={staticFile(background.current)} style={{ ...picture, transform: zoom, opacity: background.opacity }} />
      ) : null}
      {/* Task 32.8b (ENH-028, D75): the activity picture replaces the scene behind the characters, who stay in front. */}
      {cutaway ? <Img src={staticFile(cutaway.url)} style={{ ...picture, transform: zoom, opacity: cutaway.opacity }} /> : null}
      {layout === "vertical" ? <div style={VERTICAL_FADE} /> : null}
      {sprites.characters.filter((character) => onStage(character, frame, fps)).map((character) => (
        <Sprite key={`${character.slot}-${character.name}-${character.fromSec}`} character={character} frame={frame} fps={fps}
          lines={lines} sprites={sprites} totalFrames={totalFrames} layout={layout} />
      ))}
      <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: "18%",
        background: "linear-gradient(to bottom, rgba(0,0,0,0.45), rgba(0,0,0,0))" }} />
      {layout === "vertical" ? null : <div style={BOTTOM_SHADE_STYLE} />}
    </AbsoluteFill>
  );
}
