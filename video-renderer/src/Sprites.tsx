/**
 * Phase 32 (Task 32.3): the "Podcast: talking characters" layer -- the scene plate, then the two sprites. Each sprite is one picture
 * shown exactly as it was made (owner 2026-10-08: nothing pasted on it, never squashed); `spriteTimeline.ts` says which one.
 */
import React from "react";
import { AbsoluteFill, Img, staticFile, useVideoConfig } from "remotion";
import { BOTTOM_SHADE_STYLE } from "./captionStyle";
import { stillScale } from "./podcastLayout";
import { activityCutawayAt, canvasBox, spriteBackground, spriteFrame, visibleSlotsAt } from "./spriteTimeline";
import type { EpisodeLine, EpisodeSprites, SpriteCharacter } from "./types";

const FILL: React.CSSProperties = { position: "absolute", width: "100%", height: "100%", objectFit: "cover" };

function Sprite({ character, frame, fps, lines, sprites, totalFrames }: {
  character: SpriteCharacter; frame: number; fps: number; lines: EpisodeLine[]; sprites: EpisodeSprites; totalFrames: number;
}) {
  const { width, height } = useVideoConfig();
  const visibleSlots = visibleSlotsAt(frame, fps, lines, sprites);
  const box = canvasBox(character.slot, width, height, sprites.characters, visibleSlots);
  const state = spriteFrame(character, frame, fps, lines, sprites, totalFrames, width);
  return (
    <div style={{
      position: "absolute", left: box.left, top: box.top, width: box.width, height: box.height,
      transform: `translate(${state.x.toFixed(1)}px, ${state.y.toFixed(2)}px) scale(${state.scale.toFixed(4)})`,
      transformOrigin: "50% 100%", opacity: state.opacity, filter: `brightness(${state.brightness.toFixed(3)})`,
    }}>
      <Img src={staticFile(character.pictures[state.picture])} style={{ position: "absolute", width: "100%", height: "100%" }} />
    </div>
  );
}

export function SpriteStage({ sprites, lines, fps, frame, totalFrames, progress }: {
  sprites: EpisodeSprites; lines: EpisodeLine[]; fps: number; frame: number; totalFrames: number; progress: number;
}) {
  const background = spriteBackground(frame, fps, lines, sprites);
  const cutaway = activityCutawayAt(frame / fps, sprites);
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
      {cutaway ? <Img src={staticFile(cutaway.url)} style={{ ...FILL, opacity: cutaway.opacity }} /> : null}
      <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: "18%",
        background: "linear-gradient(to bottom, rgba(0,0,0,0.45), rgba(0,0,0,0))" }} />
      <div style={BOTTOM_SHADE_STYLE} />
    </AbsoluteFill>
  );
}
