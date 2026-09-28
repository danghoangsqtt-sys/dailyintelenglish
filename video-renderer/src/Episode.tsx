import React, { useMemo } from "react";
import { AbsoluteFill, Audio, staticFile, useCurrentFrame } from "remotion";
import { activeTokenIndex, buildKaraokeTokens } from "./karaoke";
import { activeSpeakerId } from "./speakers";
import type { EpisodeInputProps, EpisodeLine, EpisodeSpeaker } from "./types";

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

/** Task 19.4 (D19.4-a): the app's own real per-speaker palette, dark-theme variant --
 * frontend/static/css/style.css's `--speaker-a`/`--speaker-b`, already used app-wide via an
 * identical `speakerIndex % 2` alternating pattern (step2_script.js, step4_tts.js,
 * step5_video.js). The dark-theme pair is chosen over the light-theme pair because this
 * composition's background is the near-black MIDNIGHT_BACKGROUND, not a white surface. */
const SPEAKER_COLORS = ["#F59E0B", "#58A6FF"];

/** Inactive chips stay visible (persistent, never fade out) but recede at 0.6 opacity --
 * legible enough to still identify who's who, dim enough the active chip clearly wins the
 * eye (D19.4-a, within the PM-recommended 0.5-0.65 range). */
const INACTIVE_CHIP_OPACITY = 0.6;

function activeLine(lines: EpisodeInputProps["lines"], currentTimeSec: number) {
  return lines.find((line) => currentTimeSec >= line.startSec && currentTimeSec < line.endSec);
}

function SpeakerChip({ speaker, color, isActive }: { speaker: EpisodeSpeaker; color: string; isActive: boolean }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "6px 14px",
        borderRadius: 999,
        backgroundColor: isActive ? color : "rgba(255,255,255,0.08)",
        opacity: isActive ? 1 : INACTIVE_CHIP_OPACITY,
        transform: isActive ? "scale(1.08)" : "scale(1)",
      }}
    >
      {speaker.avatarUrl ? (
        <img
          src={staticFile(speaker.avatarUrl)}
          alt={speaker.name}
          style={{ width: 56, height: 56, borderRadius: "50%", objectFit: "cover" }}
        />
      ) : null}
      <span
        style={{
          fontFamily: "Arial, sans-serif",
          fontSize: 22,
          fontWeight: 700,
          color: isActive ? MIDNIGHT_BACKGROUND : "#FFFFFF",
        }}
      >
        {speaker.name}
      </span>
    </div>
  );
}

/**
 * Task 19.4: persistent per-speaker chip row, top-left -- opposite the bottom-anchored
 * caption band (D19.4-a), so it can never collide with the karaoke text even when a line
 * wraps to two lines. `flexWrap: "wrap"` lets 5-6 speakers degrade to a second row instead
 * of overflowing the canvas (D19.4-c) -- not exercised by this task's 2-speaker demo, but
 * requires no different code path at higher counts.
 */
function SpeakerChips({ speakers, activeId }: { speakers: EpisodeSpeaker[]; activeId: string | null }) {
  if (speakers.length === 0) {
    return null;
  }
  return (
    <div
      style={{
        position: "absolute",
        top: "5%",
        left: "5%",
        display: "flex",
        flexWrap: "wrap",
        gap: 8,
      }}
    >
      {speakers.map((speaker, index) => (
        <SpeakerChip
          key={speaker.id}
          speaker={speaker}
          color={SPEAKER_COLORS[index % SPEAKER_COLORS.length]}
          isActive={speaker.id === activeId}
        />
      ))}
    </div>
  );
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

export const Episode: React.FC<EpisodeInputProps> = ({ lines, speakers, audioPath, fps }) => {
  const frame = useCurrentFrame();
  const currentTimeSec = frame / fps;
  const line = activeLine(lines, currentTimeSec);
  const activeId = activeSpeakerId(currentTimeSec, lines);

  return (
    <AbsoluteFill style={{ backgroundColor: MIDNIGHT_BACKGROUND }}>
      <Audio src={staticFile(audioPath)} />
      <SpeakerChips speakers={speakers} activeId={activeId} />
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
