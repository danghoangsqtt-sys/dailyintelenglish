import React from "react";
import { AbsoluteFill, Audio, staticFile, useCurrentFrame } from "remotion";
import type { EpisodeInputProps } from "./types";

/** Average pixel color of frontend/static/video_backgrounds/midnight.png (measured 2026-09-28
 * via PIL: Image.open(...).convert("RGB").resize((1,1)).getpixel((0,0)) == (14, 15, 21)).
 * Per PM clarification (D19.1-c), the spike uses this flat color instead of the real PNG. */
const MIDNIGHT_BACKGROUND = "#0E0F15";

function activeLine(lines: EpisodeInputProps["lines"], currentTimeSec: number) {
  return lines.find((line) => currentTimeSec >= line.startSec && currentTimeSec < line.endSec);
}

export const Episode: React.FC<EpisodeInputProps> = ({ lines, audioPath, fps }) => {
  const frame = useCurrentFrame();
  const currentTimeSec = frame / fps;
  const line = activeLine(lines, currentTimeSec);

  return (
    <AbsoluteFill style={{ backgroundColor: MIDNIGHT_BACKGROUND }}>
      <Audio src={staticFile(audioPath)} />
      {line ? (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: "10%",
            display: "flex",
            justifyContent: "center",
            padding: "0 5%",
          }}
        >
          <span
            style={{
              fontFamily: "Arial, sans-serif",
              fontSize: 32,
              fontWeight: 700,
              color: "#FFFFFF",
              textShadow: "0 0 6px rgba(0,0,0,0.9), 0 0 2px rgba(0,0,0,0.9)",
              textAlign: "center",
            }}
          >
            {line.speaker}: {line.text}
          </span>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
