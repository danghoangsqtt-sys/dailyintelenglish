import React from "react";
import { Composition } from "remotion";
import { Episode } from "./Episode";
import { episodeInputPropsSchema, type EpisodeInputProps } from "./types";

const defaultProps: EpisodeInputProps = {
  episodeId: "preview",
  lines: [{ startSec: 0, endSec: 3, speaker: "Alex", text: "Preview line." }],
  audioPath: "spike-audio/preview.mp3",
  fps: 30,
  width: 1280,
  height: 720,
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Episode"
      component={Episode}
      schema={episodeInputPropsSchema}
      durationInFrames={90}
      fps={30}
      width={1280}
      height={720}
      defaultProps={defaultProps}
      calculateMetadata={async ({ props }) => {
        const lastLine = props.lines[props.lines.length - 1];
        const durationSec = lastLine ? lastLine.endSec : 3;
        return {
          durationInFrames: Math.max(1, Math.ceil(durationSec * props.fps)),
          fps: props.fps,
          width: props.width,
          height: props.height,
        };
      }}
    />
  );
};
