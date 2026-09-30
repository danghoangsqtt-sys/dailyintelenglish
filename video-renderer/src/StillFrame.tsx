import React from "react";
import { AbsoluteFill } from "remotion";
import { AudioWindowContent, MIDNIGHT_BACKGROUND } from "./Episode";
import type { EpisodeInputProps } from "./types";

/**
 * Task 19.6 (D19.6-f): a separate composition that renders the exact same audio-window
 * visuals as `Episode` (karaoke caption band, speaker chips, vocab card, chapter progress
 * bar), via the shared `AudioWindowContent`. Registered with no intro/outro `<Sequence>`
 * wrapping -- its own frame 0 is already the audio window's start, so the runner selects the
 * still's timestamp (50% of audio duration, owner decision) with `remotion still`'s real
 * `--frame` CLI override rather than anything computed inside this file (confirmed via
 * `npx remotion still --help`: frame selection is a CLI concern, not a `calculateMetadata`
 * one -- see task-19.6.md's D19.6-f finding).
 */
export const StillFrame: React.FC<EpisodeInputProps> = ({
  lines,
  speakers,
  learning,
  audioPath,
  fps,
  chapters,
  captionStyle,
}) => {
  const audioDurationSec = lines.length > 0 ? lines[lines.length - 1].endSec : 0;

  return (
    <AbsoluteFill style={{ backgroundColor: MIDNIGHT_BACKGROUND }}>
      <AudioWindowContent
        lines={lines}
        speakers={speakers}
        learning={learning}
        audioPath={audioPath}
        fps={fps}
        audioDurationSec={audioDurationSec}
        chapters={chapters}
        captionStyle={captionStyle}
      />
    </AbsoluteFill>
  );
};
