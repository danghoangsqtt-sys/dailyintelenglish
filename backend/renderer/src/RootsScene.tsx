/**
 * Phase 87 (D127): the word-roots Short (9:16) on cream paper -- the word in big hand-lettered capitals (root in brand
 * green, prefix / suffix in ink), a yellow underline that draws itself, the meaning in handwriting, the split
 * "COM + PRESS" with its one-line breakdown, a line-art picture (Qwen) or the word's line icons drawn stroke by stroke,
 * and the spoken line as a karaoke caption. One beat per line, from `line.roots` (backend/content/word_family.py).
 */
import React, { useMemo } from "react";
import { AbsoluteFill, Audio, continueRender, delayRender, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { activeTokenIndex, buildKaraokeTokens, withScriptPunctuation } from "./karaoke";
import { lineAt, slideIn } from "./flashcardMath";
import { LINEART_ICONS } from "./lineartIcons";
import { resolvedMedia } from "./Presenter";
import {
  drawProgress, fitSize, headSegments, isVietnamese, runStart, Segment, splitProgress, underlineProgress, wheelPositions,
  wordSegments,
} from "./rootsMath";
import { GREEN, INK, Paper } from "./SlowPodScene";
import type { EpisodeInputProps, EpisodeLine, RootsCard } from "./types";

const LETTERS = "'Bangers', 'Montserrat', 'Arial Black', sans-serif";
const HAND = "'Patrick Hand', 'Segoe Print', 'Comic Sans MS', sans-serif";
const YELLOW = "#F2C230", DARK_GREEN = "#2E5E3E", BROWN = "#4A3B2A", FADED = "#A79C8A";

// Bundled SIL OFL fonts with Vietnamese glyphs (renderer/public/fonts/OFL-*.txt); the render waits until they load.
if (typeof document !== "undefined" && typeof FontFace !== "undefined") {
  for (const [family, file] of [["Bangers", "Bangers-Regular.ttf"], ["Patrick Hand", "PatrickHand-Regular.ttf"]]) {
    const handle = delayRender(`Loading ${family}`);
    new FontFace(family, `url('${staticFile(`fonts/${file}`)}') format('truetype')`).load()
      .then((loaded) => { (document.fonts as unknown as { add: (face: FontFace) => void }).add(loaded); continueRender(handle); })
      .catch((error) => { console.warn(`${family} failed to load; using the fallback font`, error); continueRender(handle); });
  }
}

const colour = (segment: Segment) => (segment.role === "root" ? GREEN : segment.role === "rest" ? FADED : INK);

/** The word in hand-lettered capitals; when `split` > 0 the parts move apart and a "+" appears between them. */
function Lettering({ segments, size, split = 0, unit }: { segments: Segment[]; size: number; split?: number; unit: number }) {
  return <div style={{ display: "flex", justifyContent: "center", alignItems: "baseline", fontFamily: LETTERS, fontSize: size * unit,
    lineHeight: 1, transform: "skewX(-6deg)", letterSpacing: "0.01em" }}>
    {segments.map((segment, at) => <React.Fragment key={at}>
      {at > 0 && split > 0 ? <span style={{ fontFamily: HAND, color: INK, fontSize: size * 0.42 * unit, opacity: split,
        margin: `0 ${split * 18 * unit}px`, transform: `translateY(${-size * 0.18 * unit}px)` }}>+</span> : null}
      <span style={{ color: colour(segment) }}>{segment.text}</span>
    </React.Fragment>)}
  </div>;
}

function Underline({ progress, width, unit }: { progress: number; width: number; unit: number }) {
  return <svg width={width * unit} height={30 * unit} viewBox="0 0 300 30" style={{ display: "block", margin: "0 auto" }}>
    <path d="M6 18 C 70 10, 150 24, 294 12" fill="none" stroke={YELLOW} strokeWidth={7} strokeLinecap="round"
      pathLength={1} strokeDasharray={1} strokeDashoffset={1 - progress} />
    <path d="M30 24 C 110 18, 190 26, 270 20" fill="none" stroke={YELLOW} strokeWidth={3} strokeLinecap="round" opacity={0.7}
      pathLength={1} strokeDasharray={1} strokeDashoffset={1 - Math.max(0, progress * 1.3 - 0.3)} />
  </svg>;
}

/** The word's picture: Qwen line art wiped in from the left, or its line icons drawn stroke by stroke. */
function Picture({ card, progress, unit }: { card: RootsCard; progress: number; unit: number }) {
  const box: React.CSSProperties = { position: "absolute", left: 140 * unit, width: 800 * unit, top: 760 * unit, height: 380 * unit,
    display: "flex", justifyContent: "center", alignItems: "center", gap: 60 * unit };
  if (card.pictureUrl) {
    return <div data-roots-picture="art" style={{ ...box, clipPath: `inset(0 ${((1 - progress) * 100).toFixed(1)}% 0 0)` }}>
      <Img src={resolvedMedia(card.pictureUrl)} style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain", mixBlendMode: "multiply" }} />
    </div>;
  }
  const icons = (card.icons || []).filter((name) => LINEART_ICONS[name]).slice(0, 2);
  if (!icons.length) return null;
  const drawn = (svg: string) => svg.replace(/<(path|circle|rect|line|polyline|polygon|ellipse)\b/g,
    `<$1 pathLength="1" stroke-dasharray="1" stroke-dashoffset="${(1 - progress).toFixed(3)}"`);
  return <div data-roots-picture="icons" style={box}>
    {icons.map((name, at) => <svg key={name} viewBox="0 0 24 24" width={(icons.length > 1 ? 300 : 360) * unit} height={(icons.length > 1 ? 300 : 360) * unit}
      fill="none" stroke={at === 0 ? BROWN : DARK_GREEN} strokeWidth={1.1} strokeLinecap="round" strokeLinejoin="round"
      dangerouslySetInnerHTML={{ __html: drawn(LINEART_ICONS[name]) }} />)}
  </div>;
}

function Caption({ line, time, unit, gloss }: { line: EpisodeLine; time: number; unit: number; gloss?: string }) {
  const tokens = useMemo(() => withScriptPunctuation(buildKaraokeTokens(line), line.text), [line]);
  const active = activeTokenIndex(tokens, time * 1000);
  const size = line.text.length > 110 ? 40 : line.text.length > 70 ? 46 : 52;
  return <div data-roots-caption="true" style={{ position: "absolute", left: 100 * unit, right: 216 * unit, top: 1160 * unit,
    textAlign: "center", display: "grid", gap: 10 * unit }}>
    <div style={{ fontFamily: HAND, color: INK, fontSize: size * unit, lineHeight: 1.25 }}>
      {tokens.length ? tokens.map((token, at) => <React.Fragment key={`${token.fromMs}-${at}`}>
        <span style={{ color: at === active ? DARK_GREEN : INK, textDecoration: at === active ? `underline ${4 * unit}px ${YELLOW}` : "none",
          textUnderlineOffset: `${8 * unit}px` }}>{token.text.trim()}</span>{at < tokens.length - 1 ? " " : ""}
      </React.Fragment>) : line.text}
    </div>
    {gloss ? <div style={{ fontFamily: HAND, color: FADED, fontSize: 34 * unit }}>{gloss}</div> : null}
  </div>;
}

/** Phase 97 (D158): a sentence of the word's true story: its line drawing large, wiped in from the left. */
function StoryPicture({ card, progress, unit }: { card: RootsCard; progress: number; unit: number }) {
  if (!card.pictureUrl) return null;
  return <div data-roots-picture="story" style={{ position: "absolute", left: 72 * unit, width: 792 * unit, top: 300 * unit, height: 820 * unit, display: "grid", placeItems: "center",
    clipPath: `inset(0 ${((1 - progress) * 100).toFixed(1)}% 0 0)` }}>
    <Img src={resolvedMedia(card.pictureUrl)} style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain", mixBlendMode: "multiply" }} />
  </div>;
}

function Label({ text, unit }: { text: string; unit: number }) {
  return <div style={{ position: "absolute", left: 0, right: 0, top: 250 * unit, textAlign: "center", fontFamily: HAND, color: INK,
    fontSize: 46 * unit }}>{text}</div>;
}

function Beat({ props, index, time, unit }: { props: EpisodeInputProps; index: number; time: number; unit: number }) {
  const line = props.lines[index];
  const card = line.roots || { beat: "" };
  const vi = isVietnamese(line.text) || isVietnamese(card.meaning || "");
  const since = runStart(props.lines, index);
  const enter = slideIn(time, since, 0.35);
  const word = card.word || "";
  const head = card.head || "";
  const top = 330 * unit;
  const block = (children: React.ReactNode) => <div style={{ position: "absolute", left: 72 * unit, right: 72 * unit, top, display: "grid",
    justifyItems: "center", gap: 14 * unit, opacity: enter, transform: `translateY(${((1 - enter) * 24 * unit).toFixed(1)}px)` }}>{children}</div>;
  const meaningLine = (text?: string) => text ? <div style={{ fontFamily: HAND, color: DARK_GREEN, fontSize: 64 * unit, textAlign: "center",
    lineHeight: 1.15 }}>{text}</div> : null;
  const small = (text?: string, colourOf = BROWN) => text ? <div style={{ fontFamily: HAND, color: colourOf, fontSize: 38 * unit,
    textAlign: "center", lineHeight: 1.25, padding: `0 ${30 * unit}px` }}>{text}</div> : null;
  const caption = <Caption line={line} time={time} unit={unit}
    gloss={card.beat === "example" || card.beat === "head_example" ? card.example_vi : undefined} />;

  if (card.beat === "story") return <><StoryPicture card={card} progress={drawProgress(time, since)} unit={unit} />{caption}</>;
  if (card.beat === "twins") {
    const words = card.words || [];
    return <>{block(<>{words.map((item) => <Lettering key={item} segments={headSegments(item, head)} size={fitSize(item, 860, 150)} unit={unit} />)}
      <Underline progress={underlineProgress(time, line.startSec)} width={420} unit={unit} /></>)}{caption}</>;
  }
  if (card.beat === "wheel") {
    const words = card.words || [];
    const spots = wheelPositions(words.length, 330);
    return <><div style={{ position: "absolute", left: 540 * unit, top: 740 * unit, width: 0, height: 0 }}>
      <div style={{ position: "absolute", transform: "translate(-50%, -50%)", whiteSpace: "nowrap" }}>
        <Lettering segments={[{ text: head.split("/")[0].replace(/-/g, "").trim().toUpperCase(), role: "root" }]} size={130} unit={unit} /></div>
      {words.map((item, at) => {
        const show = slideIn(time, line.startSec + 0.15 + at * 0.12, 0.3);
        return <div key={item} style={{ position: "absolute", left: spots[at].x * unit, top: spots[at].y * unit, opacity: show,
          transform: `translate(-50%, -50%) scale(${(0.7 + 0.3 * show).toFixed(3)})`, whiteSpace: "nowrap" }}>
          <Lettering segments={headSegments(item, head)} size={54} unit={unit} /></div>;
      })}
    </div>{caption}</>;
  }
  if (card.beat === "origin" || card.beat === "head" || card.beat === "head_logic" || card.beat === "head_example") {
    const shown = head.split("/")[0].replace(/-/g, "").trim();
    const form = (card.origin || "").split("→")[0].trim();
    return <>{card.beat === "origin" ? <Label text={vi ? `Gốc ${card.origin_lang === "Greek" ? "Hy Lạp" : card.origin_lang || ""}` : `From ${card.origin_lang || ""}`} unit={unit} /> : null}
      {block(<><Lettering segments={[{ text: shown.toUpperCase(), role: "root" }]} size={fitSize(shown, 860, 170)} unit={unit} />
        <Underline progress={underlineProgress(time, since)} width={360} unit={unit} />
        {card.beat === "origin" && form ? <>{meaningLine(`${form} = ${card.meaning}`)}{(card.origin || "").includes("→")
          ? small(`${card.origin} → ${shown.toUpperCase()}`) : null}</> : meaningLine(card.meaning)}</>)}
      {caption}</>;
  }
  if (card.beat === "quiz" || card.beat === "follow") {
    return <><Label text={vi ? "Đoán từ cuối nhé!" : "Guess the last word!"} unit={unit} />
      {block(<><Lettering segments={wordSegments(word, card.parts, card.kind)} size={fitSize(word, 860, 160)} unit={unit} />
        <div style={{ fontFamily: HAND, color: INK, fontSize: 90 * unit }}>= ?</div></>)}
      <Picture card={card} progress={drawProgress(time, since)} unit={unit} />{caption}</>;
  }
  // hook, whole, split, example: the word stays while its beats go by
  const split = card.beat === "split" || card.beat === "example" ? splitProgress(time, card.beat === "split" ? line.startSec : -10) : 0;
  return <>{card.beat === "hook" ? <Label text={vi ? "Bạn có biết?" : "Did you know?"} unit={unit} /> : null}
    {card.beat === "puzzle" ? <Label text={vi ? "Vì sao?" : "Why?"} unit={unit} /> : null}
    {block(<><Lettering segments={wordSegments(word, card.parts, card.kind)} size={fitSize(word, 860 - split * 120, 170)} split={split} unit={unit} />
      <Underline progress={underlineProgress(time, since)} width={Math.min(560, 40 + word.length * 55)} unit={unit} />
      {meaningLine(card.meaning)}
      {split > 0 ? <div style={{ opacity: split }}>{small(card.breakdown)}</div> : null}</>)}
    <Picture card={card} progress={drawProgress(time, since)} unit={unit} />{caption}</>;
}

export function RootsScene(props: EpisodeInputProps) {
  const frame = useCurrentFrame(), { fps, height } = useVideoConfig();
  const time = frame / fps, unit = height / 1920;
  const index = lineAt(props.lines, time);
  return <AbsoluteFill data-short-style="roots" style={{ overflow: "hidden" }}>
    <Paper />
    {!props.soundtrackPath && props.audioPath ? <Audio src={resolvedMedia(props.audioPath)} /> : null}
    {index >= 0 ? <Beat props={props} index={index} time={time} unit={unit} /> : null}
  </AbsoluteFill>;
}
