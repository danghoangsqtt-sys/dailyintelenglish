import React, {useMemo} from "react";
import {activeTokenIndex,buildKaraokeTokens,captionPageAtTime,paginateCaptionTokens,withScriptPunctuation} from "./karaoke";
import {captionStyleSpec,type CaptionStyle} from "./captionStyle";
import {captionLayout} from "./motionLayout";
import {captionMotion,readingProgress,wordAccent} from "./verticalMotion";
import type {EpisodeLine,Layout} from "./types";

export const CAPTION_TEXT_STYLE: React.CSSProperties = {
  fontFamily: "Arial, sans-serif",
  fontSize: 32,
  fontWeight: 700,
  color: "#FFFFFF",
  textShadow: "0 0 6px rgba(0,0,0,0.9), 0 0 2px rgba(0,0,0,0.9)",
  textAlign: "center",
};

export function CaptionBand({
  line,
  currentTimeSec,
  captionStyle,
  layout = "horizontal",
  protectedPhrases,
  stationary = false,
}: {
  line: EpisodeLine;
  currentTimeSec: number;
  captionStyle: CaptionStyle;
  layout?: Layout;
  protectedPhrases: readonly string[];
  stationary?: boolean;
}) {
  // the script's punctuation back on Edge's bare words (walkthrough 2026-10-14)
  const tokens = useMemo(() => withScriptPunctuation(buildKaraokeTokens(line), line.text), [line]);
  // Task 20.2d: the selected treatment only overrides textShadow (and optionally wraps the
  // span in a box) -- font/size/color/alignment stay the D19.3-b base style.
  const spec = captionStyleSpec(captionStyle);
  const textStyle = { ...CAPTION_TEXT_STYLE, ...spec.text, ...(spec.box ?? {}) };
  const baseDensity = captionLayout(layout);
  const density = stationary && layout !== "vertical" ? {...baseDensity,fontSize:28,speakerSize:16,maxWords:12,maxCharacters:72} : baseDensity;
  const pages = useMemo(() => paginateCaptionTokens(tokens, density.maxWords, density.maxCharacters, protectedPhrases),
    [tokens, density.maxWords, density.maxCharacters, protectedPhrases]);
    const now = currentTimeSec * 1000;
    const shown = captionPageAtTime(pages, now);
    const activeIndex = activeTokenIndex(shown, now);
    const start = shown[0]?.fromMs ?? line.startSec * 1000;
    const entrance = captionMotion(now, start);
    const progress = readingProgress(now, start, shown.at(-1)?.toMs ?? line.endSec * 1000);
    const variant = Math.floor(start / 1000) % 3;
    return (
      <div style={{ position: "relative", width: "100%", boxSizing: "border-box", padding: "14px 16px", borderRadius: 24,
        background: "linear-gradient(145deg, rgba(17,47,35,0.94), rgba(5,18,15,0.96))",
        border: "1px solid rgba(189,221,157,0.25)", boxShadow: "0 12px 32px rgba(0,0,0,0.28)",
        opacity: stationary ? 1 : entrance.opacity,
        transform: stationary ? undefined : `translate(${entrance.x.toFixed(2)}px, ${entrance.y.toFixed(2)}px) scale(${entrance.scale.toFixed(4)})`,
        textAlign: "center" }}>
        <div style={{ fontFamily: "Arial, sans-serif", fontSize: density.speakerSize, fontWeight: 700, color: "#E1C76D",
          letterSpacing: 2, marginBottom: 8 }}>{line.speaker}</div>
        <div style={{ ...textStyle, fontSize: density.fontSize, lineHeight: 1.3, fontWeight: 700 }}>
          {shown.length ? shown.map((token, index) => {
            const accent = wordAccent(now, token.fromMs, token.toMs, variant);
            return (
            <React.Fragment key={`${token.fromMs}-${token.text}`}>
              <span style={{ display: "inline-block", padding: "0 3px", borderRadius: 8,
                color: index === activeIndex ? "#102519" : "#FFFFFF",
                background: index === activeIndex ? "#FFD54A" : "transparent",
                textShadow: index === activeIndex ? "none" : textStyle.textShadow,
                maxWidth: stationary ? "100%" : undefined, overflowWrap: stationary ? "anywhere" : undefined,
                transform: stationary ? undefined : `translateY(${accent.y.toFixed(2)}px) scale(${accent.scale.toFixed(4)})`,
                boxShadow: index === activeIndex ? `0 2px ${accent.glow.toFixed(1)}px rgba(255,213,74,0.28)` : undefined }}>
                {token.text.trim()}
              </span>{index < shown.length - 1 ? " " : ""}
            </React.Fragment>
          ); }) : line.text}
        </div>
        <div style={{ position: "absolute", left: 20, right: 20, bottom: 5, height: 2, overflow: "hidden", borderRadius: 999,
          background: "rgba(229,218,153,0.08)" }}>
          <div style={{ width: "100%", height: "100%", background: "linear-gradient(90deg, #85BD73, #FFD54A)",
            transform: `scaleX(${progress.toFixed(4)})`, transformOrigin: "0 50%" }} />
        </div>
      </div>
    );
}
