import React, {useMemo} from "react";
import {AbsoluteFill, Audio, Img, useCurrentFrame, useVideoConfig} from "remotion";
import {resolvedMedia} from "./Presenter";
import type {EpisodeInputProps, EpisodeLine} from "./types";

const FONT = "Arial, Helvetica, sans-serif";
const LEADING = 1.38;
const PASSAGE_WIDTH = 910;
const keyOf = (word: string) => word.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");

export function readingWords(line: EpisodeLine) {
  const timings = line.words ?? [];
  let cursor = 0;
  return line.text.trim().split(/\s+/u).filter(Boolean).map((text) => {
    const key = keyOf(text);
    const offset = key ? timings.slice(cursor, cursor + 4).findIndex((item) => keyOf(item.text) === key) : -1;
    const timing = offset < 0 ? undefined : timings[cursor + offset];
    if (timing) cursor += offset + 1;
    return {text, timing};
  });
}

function passageFont(words: string[]): number {
  const canvas = typeof document === "undefined" ? null : document.createElement("canvas").getContext("2d");
  for (let size = 60; size >= 30; size -= 2) {
    if (canvas) canvas.font = `700 ${size}px ${FONT}`;
    const measure = (text: string) => canvas?.measureText(text).width ?? text.length * size * 0.57;
    const space = measure(" ");
    let rows = 1, occupied = 0;
    for (const word of words) {
      const width = measure(word);
      if (occupied > 0 && occupied + space + width > PASSAGE_WIDTH) {
        rows += 1;
        occupied = width;
      } else {
        occupied += (occupied > 0 ? space : 0) + width;
      }
    }
    if (rows * size * LEADING <= 1130 && words.every((word) => measure(word) <= PASSAGE_WIDTH)) return size;
  }
  return 28;
}

type ReadAlongProps = Pick<EpisodeInputProps, "lines" | "title" | "audioPath" | "soundtrackPath">;

export function ReadAlongScene({lines, title, audioPath, soundtrackPath}: ReadAlongProps) {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const unit = width / 1080;
  const time = frame / fps;
  const passage = useMemo(() => lines.map(readingWords), [lines]);
  const font = useMemo(() => passageFont(passage.flat().map((word) => word.text)), [passage]);
  const currentLine = lines.findIndex((line) => time >= line.startSec && time < line.endSec);
  const card = lines.find((line) => line.readalong?.title || line.readalong?.pictureUrl)?.readalong;

  return <AbsoluteFill data-short-style="readalong" style={{
    overflow: "hidden", background: "#F8F4EB", color: "#172031", fontFamily: FONT,
  }}>
    {!soundtrackPath && audioPath ? <Audio src={resolvedMedia(audioPath)} /> : null}
    <div style={{height: 510 * unit, flexShrink: 0, position: "relative", background: "linear-gradient(150deg,#E5F0DA,#B5D6C5)"}}>
      {card?.pictureUrl ? <Img src={resolvedMedia(card.pictureUrl)}
        style={{width: "100%", height: "100%", objectFit: "cover"}} /> : null}
    </div>
    <div style={{
      padding: `${23 * unit}px ${(1080 - PASSAGE_WIDTH) / 2 * unit}px 0`,
      backgroundImage: "linear-gradient(140deg, rgba(255,255,255,.60), transparent 45%), linear-gradient(25deg,#F0EADF,#FBF8EF 72%)",
      flex: 1,
    }}>
      <div style={{
        height: 137 * unit, display: "grid", alignContent: "center", textAlign: "center", fontWeight: 900,
        fontSize: (card?.title && card.title.length > 36 ? 49 : 65) * unit, lineHeight: 1.04, overflowWrap: "anywhere",
      }}>{card?.title || title || "Read Along"}</div>
      <div data-reading-passage="true" style={{
        fontWeight: 700, fontSize: font * unit, lineHeight: LEADING, textAlign: "justify", overflowWrap: "anywhere",
      }}>
        {passage.map((words, index) => <React.Fragment key={index}>
          <span data-reading-sentence={index === currentLine ? "active" : undefined} style={{
            backgroundColor: index === currentLine ? "#DEDEFC" : undefined,
            borderRadius: 7 * unit, boxDecorationBreak: "clone", WebkitBoxDecorationBreak: "clone",
          }}>
            {words.map(({text, timing}, offset) => {
              const active = index === currentLine && timing && time >= timing.startSec && time < timing.endSec;
              return <React.Fragment key={offset}>
                {offset > 0 ? " " : null}
                <span data-reading-word={active ? "active" : undefined} style={{
                  backgroundColor: active ? "#5752BC" : undefined,
                  color: active ? "#FFFFFF" : undefined, borderRadius: 6 * unit,
                }}>{text}</span>
              </React.Fragment>;
            })}
          </span>{index < passage.length - 1 ? " " : null}
        </React.Fragment>)}
      </div>
    </div>
  </AbsoluteFill>;
}
