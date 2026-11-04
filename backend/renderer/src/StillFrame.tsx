import React from "react";
import { AbsoluteFill } from "remotion";
import { AudioWindowContent, MIDNIGHT_BACKGROUND } from "./Episode";
import type { EpisodeInputProps } from "./types";
import { SoloScene } from "./SoloScene";
import { VoxScene } from "./VoxScene";
import { NewsScene } from "./NewsScene";
import { BlurScene } from "./BlurScene";
import { LearnScene } from "./LearnScene";
import { InteractScene } from "./InteractScene";
import { ChatScene } from "./ChatScene";

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
export const StillFrame: React.FC<EpisodeInputProps> = (props) => {
  if (props.shortStyle) return <ChatScene {...props}/>;  // Phase 65: a conversation Short
  if (props.presentationMode === "solo_explainer") {
    // Phase 63: each voice-only style has its own scene (a VOX/Short payload has no presenter for SoloScene)
    const style = props.solo?.style;
    if (style === "news") return <NewsScene {...props}/>;
    if (style === "blur") return <BlurScene {...props}/>;
    if (style === "mistakes" || style === "wordday" || style === "top5") return <LearnScene {...props}/>;
    if (style === "quiz" || style === "listen") return <InteractScene {...props}/>;
    if (style === "vox") return <VoxScene {...props}/>;
    return <SoloScene {...props}/>;
  }
  const {
  lines,
  speakers,
  learning,
  audioPath,
  fps,
  chapters,
  captionStyle,
  visualMode,
  stillUrl,
  sprites,
  } = props;
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
        visualMode={visualMode}
        stillUrl={stillUrl}
        sprites={sprites}
      />
    </AbsoluteFill>
  );
};
