/**
 * Phase 96 (task 96.4): the picture-for-each-sentence Short (9:16) -- owner 2026-11-04: "tôi cởi giày thì đi kèm hình cởi giày".
 * One full-frame picture per sentence, a slow zoom so that it does not stand still, the sentence large with its key words in
 * colour and the word being read marked. One card per line, from `line.picstory` (backend/content/picture_story.py).
 */
import React from "react";
import { AbsoluteFill, Audio, Img, useCurrentFrame, useVideoConfig } from "remotion";
import { lineAt } from "./flashcardMath";
import { resolvedMedia } from "./Presenter";
import { clamp01 } from "./voxMath";
import { easeOutBack } from "./voxMotion";
import { storyWords, wordExplains } from "./wordRepeatMath";
import type { EpisodeInputProps } from "./types";

const KEY = "#7CF0A0", NOW = "#FFE14D";
const SANS = "Arial, Helvetica, sans-serif", HEAVY = "'Arial Black', Arial, Helvetica, sans-serif";

export function PictureStoryScene(props: EpisodeInputProps) {
  const frame = useCurrentFrame(), { fps, height } = useVideoConfig();
  const time = frame / fps, unit = height / 1920;
  const index = Math.max(0, lineAt(props.lines, time));
  const line = props.lines[index], card = line?.picstory;
  const since = line ? time - line.startSec : 0;
  const span = line ? Math.max(1, line.endSec - line.startSec) : 1;
  const show = wordExplains(card?.audience);
  const big = card?.beat !== "line";
  const words = storyWords(line?.text ?? "", card?.keywords ?? [], line?.words ?? [], time);
  const zoom = 1.02 + 0.07 * clamp01(since / (span + 0.5));

  return <AbsoluteFill data-short-style="picstory" style={{ overflow: "hidden", background: "linear-gradient(170deg, #0F3D2A, #1F7A4D 55%, #0B2A1E)" }}>
    {!props.soundtrackPath && props.audioPath ? <Audio src={resolvedMedia(props.audioPath)} /> : null}
    {card?.pictureUrl ? <Img data-word-picture="true" src={resolvedMedia(card.pictureUrl)} style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover",
      transform: `scale(${zoom.toFixed(4)})` }} /> : null}
    <div data-story-line="true" style={{ position: "absolute", left: 72 * unit, width: 792 * unit, top: (big ? 1040 : 1060) * unit, background: "rgba(10,20,16,0.78)", borderRadius: 24 * unit,
      padding: `${22 * unit}px ${28 * unit}px`, boxSizing: "border-box", display: "grid", gap: 12 * unit, transform: `scale(${Math.max(0, easeOutBack(since / 0.3)).toFixed(4)})` }}>
      <div style={{ fontFamily: HEAVY, fontSize: (big ? 70 : 62) * unit, lineHeight: 1.16, color: "#FFF" }}>
        {words.map((word, at) => <span key={at} data-story-word={word.now ? "now" : word.key ? "key" : undefined} style={{ color: word.now ? NOW : word.key ? KEY : "#FFF" }}>{word.text}{" "}</span>)}
      </div>
      {show.vi && card?.translation_vi ? <div data-word-vi="true" style={{ fontFamily: SANS, fontWeight: 700, fontSize: 40 * unit, lineHeight: 1.2, color: "#E9F3EE" }}>{card.translation_vi}</div> : null}
    </div>
    <div style={{ position: "absolute", left: 72 * unit, top: 170 * unit, color: "#14231C", fontFamily: SANS, fontWeight: 800, fontSize: 26 * unit,
      background: "rgba(255,255,255,0.85)", borderRadius: 10 * unit, padding: `${4 * unit}px ${12 * unit}px` }}>DAILY BEYOND ENGLISH · {props.cefrLevel}</div>
  </AbsoluteFill>;
}
