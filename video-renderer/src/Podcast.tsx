/**
 * Phase 30 (ENH-021): what the screen shows behind the captions in the podcast visual modes. The layout numbers live in
 * `podcastLayout.ts` (pure, tested); this file only draws them.
 */
import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { BOTTOM_SHADE_STYLE } from "./captionStyle";
import {
  CARD_GAP, CARD_HEIGHT, CARD_WIDTH, cardLayout, cardState, speakerInitial, stillScale, type PodcastLayer,
} from "./podcastLayout";
import type { EpisodeSpeaker } from "./types";

const SPEAKER_COLORS = ["#F59E0B", "#58A6FF", "#9BD13C"];
export const PODCAST_BLACK = "#000000";

function Still({ url, progress }: { url: string; progress: number }) {
  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: PODCAST_BLACK }}>
      <Img src={staticFile(url)} style={{
        position: "absolute", width: "100%", height: "100%", objectFit: "cover",
        transform: `scale(${stillScale(progress).toFixed(4)})`,
      }} />
      <div style={BOTTOM_SHADE_STYLE} />
    </AbsoluteFill>
  );
}

function CharacterCard({ speaker, color, isActive, box }: {
  speaker: EpisodeSpeaker; color: string; isActive: boolean; box: { x: number; y: number };
}) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const target = cardState(isActive);
  // A short spring, not a jump, when the speaker changes: the card eases up or down.
  const lift = spring({ frame, fps, config: { damping: 20 }, durationInFrames: 12 });
  const scale = interpolate(lift, [0, 1], [1, 1]) * target.scale;
  const picture = speaker.portraitUrl ?? speaker.avatarUrl;
  return (
    <div style={{
      position: "absolute", left: box.x, top: box.y, width: CARD_WIDTH, height: CARD_HEIGHT,
      transform: `scale(${scale})`, opacity: target.opacity, transition: "none",
      filter: `saturate(${target.saturate})`,
    }}>
      <div style={{
        width: "100%", height: "100%", borderRadius: 22, overflow: "hidden", background: "#10161a",
        boxShadow: isActive ? `0 0 0 4px ${color}, 0 0 38px ${color}88` : "0 0 0 2px rgba(255,255,255,0.18)",
      }}>
        {picture ? (
          <Img src={staticFile(picture)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "center top" }} />
        ) : (
          <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center",
            fontFamily: "'Montserrat', Arial, sans-serif", fontSize: 120, fontWeight: 800, color }}>
            {speakerInitial(speaker.name)}
          </div>
        )}
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, bottom: -44, textAlign: "center", fontFamily: "'Montserrat', Arial, sans-serif",
        fontSize: 26, fontWeight: 800, color: isActive ? color : "#E5E7EB", textShadow: "0 0 8px rgba(0,0,0,0.9)",
      }}>
        {speaker.name}
      </div>
    </div>
  );
}

export function CharacterCards({ speakers, activeId, frameWidth }: {
  speakers: EpisodeSpeaker[]; activeId: string | null; frameWidth: number;
}) {
  const boxes = cardLayout(speakers.length, frameWidth);
  return (
    <>
      {speakers.map((speaker, index) => (
        <CharacterCard key={speaker.id} speaker={speaker} color={SPEAKER_COLORS[index % SPEAKER_COLORS.length]}
          isActive={speaker.id === activeId} box={boxes[index]} />
      ))}
    </>
  );
}

export const PODCAST_CARD_GAP = CARD_GAP;

/** The layer of a podcast mode. "none" (the drawn story) draws nothing here. */
export function PodcastLayerView({ layer, stillUrl, progress, speakers, activeId, frameWidth }: {
  layer: PodcastLayer; stillUrl?: string; progress: number; speakers: EpisodeSpeaker[]; activeId: string | null;
  frameWidth: number;
}) {
  if (layer === "none") return null;
  return (
    <>
      <AbsoluteFill style={{ backgroundColor: PODCAST_BLACK }} />
      {layer === "still" && stillUrl ? <Still url={stillUrl} progress={progress} /> : null}
      {layer === "cards" ? <CharacterCards speakers={speakers} activeId={activeId} frameWidth={frameWidth} /> : null}
    </>
  );
}
