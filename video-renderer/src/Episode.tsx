import React, { useMemo } from "react";
import { AbsoluteFill, Audio, staticFile, useCurrentFrame } from "remotion";
import { activeTokenIndex, buildKaraokeTokens } from "./karaoke";
import type { EpisodeInputProps, EpisodeLine } from "./types";

/** Average pixel color of frontend/static/video_backgrounds/midnight.png (measured 2026-09-28
 * via PIL: Image.open(...).convert("RGB").resize((1,1)).getpixel((0,0)) == (14, 15, 21)).
 * Per PM clarification (D19.1-c), the spike uses this flat color instead of the real PNG. */
const MIDNIGHT_BACKGROUND = "#0E0F15";

/** Byte-identical to the 19.1 spike's plain-band text style -- Task 19.3 must not regress
 * font/size/shadow/position from the spike look (D19.3-b). Only the active karaoke word's
 * color deviates from this, applied as a single override per word span. */
const CAPTION_TEXT_STYLE: React.CSSProperties = {
  fontFamily: "Arial, sans-serif",
  fontSize: 32,
  fontWeight: 700,
  color: "#FFFFFF",
  textShadow: "0 0 6px rgba(0,0,0,0.9), 0 0 2px rgba(0,0,0,0.9)",
  textAlign: "center",
};

/** Warm-yellow karaoke highlight for the currently active word -- standard convention,
 * chosen as a subtle signal on top of the unchanged base style (D19.3-b). */
const ACTIVE_WORD_COLOR = "#FFD54A";

function activeLine(lines: EpisodeInputProps["lines"], currentTimeSec: number) {
  return lines.find((line) => currentTimeSec >= line.startSec && currentTimeSec < line.endSec);
}

function CaptionBand({ line, currentTimeSec }: { line: EpisodeLine; currentTimeSec: number }) {
  const tokens = useMemo(() => buildKaraokeTokens(line), [line]);

  if (tokens.length === 0) {
    // D19.3-c fallback: the exact, unmodified 19.1 plain-span render -- untouched by this task.
    return (
      <span style={CAPTION_TEXT_STYLE}>
        {line.speaker}: {line.text}
      </span>
    );
  }

  const activeIndex = activeTokenIndex(tokens, currentTimeSec * 1000);
  return (
    <span style={CAPTION_TEXT_STYLE}>
      {line.speaker}:{" "}
      {tokens.map((token, index) => (
        <span key={`${token.fromMs}-${token.text}`} style={index === activeIndex ? { color: ACTIVE_WORD_COLOR } : undefined}>
          {token.text}
          {index < tokens.length - 1 ? " " : ""}
        </span>
      ))}
    </span>
  );
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
          <CaptionBand line={line} currentTimeSec={currentTimeSec} />
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
