import React from "react";
import { Composition } from "remotion";
import { Episode } from "./Episode";
import { StillFrame } from "./StillFrame";
import { BrandSpike, type BrandSpikeProps } from "./BrandSpike";
import { episodeInputPropsSchema, type EpisodeInputProps } from "./types";

const defaultProps: EpisodeInputProps = {
  episodeId: "preview",
  lines: [{ startSec: 0, endSec: 3, speaker: "Alex", speakerId: "alex-id", text: "Preview line.", words: [] }],
  speakers: [{ id: "alex-id", name: "Alex", gender: "male" }],
  audioPath: "spike-audio/preview.mp3",
  fps: 30,
  width: 1280,
  height: 720,
  title: "Preview Episode",
  topic: "Preview topic",
  cefrLevel: "B1",
  chapters: [],
  introSec: 2.5,
  outroSec: 5.0,
  outroText: "Thanks for watching · Subscribe for more · See you next episode!",
  captionStyle: "outline",
  visuals: { shots: {}, lineShots: [] },
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
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
          const audioDurationSec = lastLine ? lastLine.endSec : 3;
          // D19.6-a: total video = intro + audio + outro (Option B, extend) -- the same
          // per-props addition Episode.tsx itself uses for its <Sequence> boundaries.
          const totalDurationSec = props.introSec + audioDurationSec + props.outroSec;
          return {
            durationInFrames: Math.max(1, Math.ceil(totalDurationSec * props.fps)),
            fps: props.fps,
            width: props.width,
            height: props.height,
          };
        }}
      />
      {/* Task 19.6 (D19.6-f): a second composition sharing the same props shape, registered
          via the same `registerRoot` (src/index.ts) -- rendered with `npx remotion still`,
          not `render`. Its own duration covers just the audio window (no intro/outro slices
          to choose a still from); the runner selects the exact frame via `--frame`. */}
      <Composition
        id="StillFrame"
        component={StillFrame}
        schema={episodeInputPropsSchema}
        durationInFrames={90}
        fps={30}
        width={1280}
        height={720}
        defaultProps={defaultProps}
        calculateMetadata={async ({ props }) => {
          const lastLine = props.lines[props.lines.length - 1];
          const audioDurationSec = lastLine ? lastLine.endSec : 3;
          return {
            durationInFrames: Math.max(1, Math.ceil(audioDurationSec * props.fps)),
            fps: props.fps,
            width: props.width,
            height: props.height,
          };
        }}
      />
      {/* Task 25.1 spike (not shipped): morph intro/outro preview for owner review. */}
      <Composition
        id="BrandSpike"
        component={BrandSpike}
        durationInFrames={90}
        fps={30}
        width={1280}
        height={720}
        defaultProps={{
          title: "Good Morning", topic: "How do you start a new day?", cefrLevel: "B1",
          speakers: ["Lan", "Minh"], wish: "Wishing you a wonderful time learning English today!",
          greetingPath: "brand-spike/greeting.mp3", farewellPath: "brand-spike/farewell.mp3",
          introSec: 7.6, gapSec: 1.5, outroSec: 7.5,
        } satisfies BrandSpikeProps}
        calculateMetadata={async ({ props }) => ({
          durationInFrames: Math.ceil((props.introSec + props.gapSec + props.outroSec) * 30),
        })}
      />
    </>
  );
};
