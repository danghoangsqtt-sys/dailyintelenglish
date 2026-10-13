/**
 * Phase 30 (ENH-021): what the screen shows behind the captions in the two podcast visual modes (a black screen, or one
 * still scene picture). The numbers live in `podcastLayout.ts` (pure, tested); this file only draws them.
 */
import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { BOTTOM_SHADE_STYLE } from "./captionStyle";
import { stillScale, type PodcastLayer } from "./podcastLayout";

export const PODCAST_BLACK = "#000000";

function Still({ url, progress }: { url: string; progress: number }) {
  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: PODCAST_BLACK }}>
      <Img src={staticFile(url)} style={{
        position: "absolute", width: "100%", height: "100%", objectFit: "cover",
        transform: `scale(${stillScale(progress).toFixed(4)})`,
      }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: "22%",
        background: "linear-gradient(to bottom, rgba(0,0,0,0.55), rgba(0,0,0,0))" }} />
      <div style={BOTTOM_SHADE_STYLE} />
    </AbsoluteFill>
  );
}

/** The layer of a podcast mode. "none" (the drawn story) draws nothing here. */
export function PodcastLayerView({ layer, stillUrl, progress }: {
  layer: PodcastLayer; stillUrl?: string; progress: number;
}) {
  if (layer === "none") return null;
  return (
    <>
      <AbsoluteFill style={{ backgroundColor: PODCAST_BLACK }} />
      {layer === "still" && stillUrl ? <Still url={stillUrl} progress={progress} /> : null}
    </>
  );
}
