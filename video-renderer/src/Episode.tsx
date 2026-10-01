import React, { useMemo } from "react";
import { AbsoluteFill, Audio, Img, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { computeProgressForFrame } from "./chapters";
import { activeTokenIndex, buildKaraokeTokens } from "./karaoke";
import { activeSpeakerId } from "./speakers";
import { activeItemForFrame, attachItemsToLines, type LearningItem } from "./vocab";
import { BOTTOM_SHADE_STYLE, captionStyleSpec, type CaptionStyle } from "./captionStyle";
import { visualBackgroundForFrame, vocabCardPosition } from "./visuals";
import type { Chapter, EpisodeInputProps, EpisodeLearning, EpisodeLine, EpisodeSpeaker, EpisodeVisuals } from "./types";

/** Average pixel color of frontend/static/video_backgrounds/midnight.png (measured 2026-09-28
 * via PIL: Image.open(...).convert("RGB").resize((1,1)).getpixel((0,0)) == (14, 15, 21)).
 * Per PM clarification (D19.1-c), the spike uses this flat color instead of the real PNG.
 * Exported (Task 19.6) so `StillFrame.tsx` shares the exact same background. */
export const MIDNIGHT_BACKGROUND = "#0E0F15";

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

function CaptionBand({
  line,
  currentTimeSec,
  captionStyle,
}: {
  line: EpisodeLine;
  currentTimeSec: number;
  captionStyle: CaptionStyle;
}) {
  const tokens = useMemo(() => buildKaraokeTokens(line), [line]);
  // Task 20.2d: the selected treatment only overrides textShadow (and optionally wraps the
  // span in a box) -- font/size/color/alignment stay the D19.3-b base style.
  const spec = captionStyleSpec(captionStyle);
  const textStyle = { ...CAPTION_TEXT_STYLE, ...spec.text, ...(spec.box ?? {}) };

  if (tokens.length === 0) {
    // D19.3-c fallback: the plain line-level span (only the 20.2d style layer is added).
    return (
      <span style={textStyle}>
        {line.speaker}: {line.text}
      </span>
    );
  }

  const activeIndex = activeTokenIndex(tokens, currentTimeSec * 1000);
  return (
    <span style={textStyle}>
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

/** Task 19.5 (D19.5-d): ~200ms fade in/out rather than a pop cut, relative to the active
 * item's own time slot (not the whole line's duration) -- so a 2-item line's cards each get
 * their own fade in/out at the mid-line handoff, not just at the line's outer edges. */
const VOCAB_CARD_FADE_SECONDS = 0.2;

function vocabCardOpacity(currentTimeSec: number, slotStartSec: number, slotEndSec: number): number {
  const fadeIn = interpolate(currentTimeSec, [slotStartSec, slotStartSec + VOCAB_CARD_FADE_SECONDS], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(currentTimeSec, [slotEndSec - VOCAB_CARD_FADE_SECONDS, slotEndSec], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return Math.min(fadeIn, fadeOut);
}

/**
 * Task 19.5: pop-up card for the active vocab word / idiom phrase, top-right corner --
 * opposite the speaker chips (top-left, 19.4) and the caption band (bottom, 19.1/19.3), so it
 * can never collide with either even when speaker chips wrap to a second row at 5-6 speakers.
 */
function VocabCard({ item, opacity, position }: { item: LearningItem; opacity: number; position: "top-right" | "top-center" }) {
  return (
    <div
      style={{
        position: "absolute",
        top: "5%",
        ...(position === "top-center" ? { left: "50%", transform: "translateX(-50%)" } : { right: "5%" }),
        maxWidth: "32%",
        opacity,
        backgroundColor: "rgba(14, 15, 21, 0.85)",
        borderRadius: 12,
        padding: "14px 18px",
        fontFamily: CAPTION_TEXT_STYLE.fontFamily,
        color: "#FFFFFF",
      }}
    >
      {item.kind === "vocab" ? (
        <>
          <div style={{ fontSize: 24, fontWeight: 700 }}>
            {item.word} <span style={{ fontSize: 18, fontWeight: 400, fontStyle: "italic" }}>({item.partOfSpeech})</span>
          </div>
          <div style={{ fontSize: 18, fontStyle: "italic", opacity: 0.8 }}>/{item.ipa}/</div>
          <div style={{ fontSize: 18, marginTop: 6 }}>{item.definitionEn}</div>
          <div style={{ fontSize: 18, opacity: 0.85 }}>{item.definitionVi}</div>
          <div style={{ fontSize: 18, fontStyle: "italic", marginTop: 6, opacity: 0.9 }}>{item.exampleSentence}</div>
        </>
      ) : (
        <>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{item.phrase}</div>
          <div style={{ fontSize: 18, marginTop: 6 }}>{item.meaningEn}</div>
          <div style={{ fontSize: 18, opacity: 0.85 }}>{item.meaningVi}</div>
          <div style={{ fontSize: 18, fontStyle: "italic", marginTop: 6, opacity: 0.9 }}>{item.exampleSentence}</div>
        </>
      )}
    </div>
  );
}

/** Task 19.6 (D19.6-d): thin full-width strip at the very top edge -- opposite the
 * bottom-anchored caption band, and above the speaker chips' own `top: "5%"` origin so the
 * two overlays never collide. */
const CHAPTER_BAR_HEIGHT = 6;

function ChapterProgressBar({
  frame,
  fps,
  audioDurationSec,
  chapters,
}: {
  frame: number;
  fps: number;
  audioDurationSec: number;
  chapters: Chapter[];
}) {
  const progress = computeProgressForFrame(frame, fps, audioDurationSec, chapters);
  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        height: CHAPTER_BAR_HEIGHT,
        backgroundColor: "rgba(255,255,255,0.15)",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          bottom: 0,
          left: 0,
          width: `${progress.overallPct * 100}%`,
          backgroundColor: "rgba(255,255,255,0.85)",
        }}
      />
      {progress.chapters.map((chapter, index) => (
        <div
          key={`${chapter.startSec}-${index}`}
          style={{
            position: "absolute",
            top: 0,
            bottom: 0,
            left: `${chapter.pct * 100}%`,
            width: 2,
            backgroundColor: "rgba(14,15,21,0.9)",
          }}
        />
      ))}
    </div>
  );
}

/**
 * Task 19.6: the audio-window's full content (karaoke caption band, speaker chips, vocab
 * card, chapter progress bar) -- exactly what `Episode.tsx` rendered before this task, now
 * extracted so `StillFrame.tsx` can render the identical visuals at a single frame (D19.6-f).
 * Reads `useCurrentFrame()` itself rather than receiving a frame prop: when mounted inside
 * `<Sequence from={introFrames}>`, Remotion remaps that call to already be relative to the
 * Sequence's own start (confirmed against `remotion/dist/cjs/Sequence.js`'s
 * `frameInParent - from`), so this component's `currentTimeSec = frame / fps` lines up with
 * `line.startSec`/`endSec` with no manual offset math -- and when mounted directly as
 * `StillFrame`'s top-level composition (no wrapping Sequence), frame 0 is already the audio
 * window's own start, so the exact same code path applies unchanged.
 */
export function AudioWindowContent({
  lines,
  speakers,
  learning,
  audioPath,
  fps,
  audioDurationSec,
  chapters,
  captionStyle,
  visuals,
}: {
  lines: EpisodeLine[];
  speakers: EpisodeSpeaker[];
  learning: EpisodeLearning | undefined;
  audioPath: string;
  fps: number;
  audioDurationSec: number;
  chapters: Chapter[];
  captionStyle: CaptionStyle;
  visuals: EpisodeVisuals;
}) {
  const frame = useCurrentFrame();
  const currentTimeSec = frame / fps;
  const line = activeLine(lines, currentTimeSec);
  const activeId = activeSpeakerId(currentTimeSec, lines);

  const attachedLearning = useMemo(
    () => attachItemsToLines(learning?.vocab ?? [], learning?.idioms ?? [], lines),
    [learning, lines]
  );
  const activeLearningItem = activeItemForFrame(currentTimeSec, lines, attachedLearning);
  const background = visualBackgroundForFrame(frame, fps, lines, visuals);

  return (
    <>
      {background.previous ? (
        <Img src={staticFile(background.previous)} style={{ position: "absolute", width: "100%", height: "100%",
          objectFit: "cover", opacity: background.current ? 1 : 1 - background.opacity }} />
      ) : null}
      {background.current ? (
        <Img src={staticFile(background.current)} style={{ position: "absolute", width: "100%", height: "100%",
          objectFit: "cover", opacity: background.opacity, transform: `scale(${background.scale})` }} />
      ) : null}
      <Audio src={staticFile(audioPath)} startFrom={0} />
      {captionStyleSpec(captionStyle).bottomShade ? <div style={BOTTOM_SHADE_STYLE} /> : null}
      <ChapterProgressBar frame={frame} fps={fps} audioDurationSec={audioDurationSec} chapters={chapters} />
      <SpeakerChips speakers={speakers} activeId={activeId} />
      {activeLearningItem ? (
        <VocabCard
          item={activeLearningItem.item}
          opacity={vocabCardOpacity(currentTimeSec, activeLearningItem.slotStartSec, activeLearningItem.slotEndSec)}
          position={vocabCardPosition(background.kind)}
        />
      ) : null}
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
          <CaptionBand line={line} currentTimeSec={currentTimeSec} captionStyle={captionStyle} />
        </div>
      ) : null}
    </>
  );
}

/** Task 19.6 (D19.6-b/c): opacity envelope in frame units (no fps conversion needed by
 * callers) -- fades in over `fadeInFrames`, holds, fades out over the last `fadeOutFrames`
 * of `totalFrames`. */
function fadeOpacity(frame: number, totalFrames: number, fadeInFrames: number, fadeOutFrames: number): number {
  const fadeIn = interpolate(frame, [0, fadeInFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(frame, [totalFrames - fadeOutFrames, totalFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return Math.min(fadeIn, fadeOut);
}

/** Task 19.6 (D19.6-b): "{a} & {b}" for two speakers, comma-separated for 3+, just the name
 * for a solo project, "" when the project has no speakers at all. */
function speakerNamesLabel(speakers: EpisodeSpeaker[]): string {
  if (speakers.length === 0) {
    return "";
  }
  if (speakers.length === 1) {
    return speakers[0].name;
  }
  if (speakers.length === 2) {
    return `${speakers[0].name} & ${speakers[1].name}`;
  }
  return speakers.map((speaker) => speaker.name).join(", ");
}

const INTRO_FADE_IN_SECONDS = 0.5;
const INTRO_FADE_OUT_SECONDS = 0.5;

/** Task 19.6 (D19.6-b): title slide -- project title, speaker names, `[CEFR] topic` tag. */
function Intro({
  title,
  topic,
  cefrLevel,
  speakers,
  fps,
  durationInFrames,
}: {
  title: string;
  topic: string;
  cefrLevel: string;
  speakers: EpisodeSpeaker[];
  fps: number;
  durationInFrames: number;
}) {
  const frame = useCurrentFrame();
  const opacity = fadeOpacity(
    frame,
    durationInFrames,
    Math.round(INTRO_FADE_IN_SECONDS * fps),
    Math.round(INTRO_FADE_OUT_SECONDS * fps)
  );
  const names = speakerNamesLabel(speakers);
  const tag = [cefrLevel ? `[${cefrLevel}]` : "", topic].filter(Boolean).join(" ");

  return (
    <AbsoluteFill
      style={{
        backgroundColor: MIDNIGHT_BACKGROUND,
        alignItems: "center",
        justifyContent: "center",
        opacity,
      }}
    >
      <div style={{ fontFamily: CAPTION_TEXT_STYLE.fontFamily, color: "#FFFFFF", textAlign: "center" }}>
        <div style={{ fontSize: 56, fontWeight: 700 }}>{title}</div>
        {names ? (
          <div style={{ fontSize: 32, fontWeight: 700, marginTop: 16, color: SPEAKER_COLORS[0] }}>{names}</div>
        ) : null}
        {tag ? <div style={{ fontSize: 22, marginTop: 12, opacity: 0.85 }}>{tag}</div> : null}
      </div>
    </AbsoluteFill>
  );
}

const OUTRO_FADE_IN_SECONDS = 0.5;
const OUTRO_FADE_OUT_SECONDS = 1.0;

/** Task 19.6 (D19.6-c): owner-approved CTA text, centered, same background as the intro. */
function Outro({ text, fps, durationInFrames }: { text: string; fps: number; durationInFrames: number }) {
  const frame = useCurrentFrame();
  const opacity = fadeOpacity(
    frame,
    durationInFrames,
    Math.round(OUTRO_FADE_IN_SECONDS * fps),
    Math.round(OUTRO_FADE_OUT_SECONDS * fps)
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: MIDNIGHT_BACKGROUND,
        alignItems: "center",
        justifyContent: "center",
        opacity,
      }}
    >
      <div style={{ ...CAPTION_TEXT_STYLE, fontSize: 36, maxWidth: "80%" }}>{text}</div>
    </AbsoluteFill>
  );
}

export const Episode: React.FC<EpisodeInputProps> = ({
  lines,
  speakers,
  learning,
  audioPath,
  fps,
  title,
  topic,
  cefrLevel,
  chapters,
  introSec,
  outroSec,
  outroText,
  captionStyle,
  visuals,
}) => {
  // D19.6-a: total video = intro + audio + outro (Option B, extend). `audioDurationSec` is
  // the same "last line's endSec" measure Root.tsx's calculateMetadata already uses for the
  // pre-19.6 audio-only duration -- kept as a single source of truth between the two files.
  const audioDurationSec = lines.length > 0 ? lines[lines.length - 1].endSec : 0;
  const introFrames = Math.round(introSec * fps);
  const audioFrames = Math.round(audioDurationSec * fps);
  const outroFrames = Math.round(outroSec * fps);

  return (
    <AbsoluteFill style={{ backgroundColor: MIDNIGHT_BACKGROUND }}>
      <Sequence from={0} durationInFrames={introFrames} name="Intro">
        <Intro title={title} topic={topic} cefrLevel={cefrLevel} speakers={speakers} fps={fps} durationInFrames={introFrames} />
      </Sequence>
      <Sequence from={introFrames} durationInFrames={audioFrames} name="Audio">
        <AudioWindowContent
          lines={lines}
          speakers={speakers}
          learning={learning}
          audioPath={audioPath}
          fps={fps}
          audioDurationSec={audioDurationSec}
          chapters={chapters}
          captionStyle={captionStyle}
          visuals={visuals}
        />
      </Sequence>
      <Sequence from={introFrames + audioFrames} durationInFrames={outroFrames} name="Outro">
        <Outro text={outroText} fps={fps} durationInFrames={outroFrames} />
      </Sequence>
    </AbsoluteFill>
  );
};
