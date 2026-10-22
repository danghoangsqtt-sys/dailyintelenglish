import {CaptionBand, CAPTION_TEXT_STYLE} from "./CaptionBand";
import {SoloScene} from "./SoloScene";
import {VoxScene} from "./VoxScene";
import {NewsScene} from "./NewsScene";
import {BlurScene} from "./BlurScene";
import {LearnScene} from "./LearnScene";
import {InteractScene} from "./InteractScene";
import {ChatScene} from "./ChatScene";
import {resolvedMedia} from "./Presenter";
import React, { useMemo } from "react";
import { AbsoluteFill, Audio, Img, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { BrandIntro, BrandOutro } from "./Brand";
import { computeProgressForFrame } from "./chapters";
import { activeTokenIndex, buildKaraokeTokens, captionPageAtTime, paginateCaptionTokens, withScriptPunctuation } from "./karaoke";
import { activeSpeakerId } from "./speakers";
import { activeItemForFrame, attachItemsToLines, type LearningItem } from "./vocab";
import { BOTTOM_SHADE_STYLE, captionStyleSpec, type CaptionStyle } from "./captionStyle";
import { PodcastLayerView } from "./Podcast";
import { SpriteStage } from "./Sprites";
import { podcastLayer, type VisualMode } from "./podcastLayout";
import { VERTICAL } from "./safeZone";
import { captionLayout } from "./motionLayout";
import { captionMotion, learningMotion, readingProgress, speakingMeter, wordAccent } from "./verticalMotion";
import type {
  Chapter, EpisodeInputProps, EpisodeLearning, EpisodeLine, EpisodeSpeaker, EpisodeSprites, Layout,
} from "./types";

/** Average pixel color of frontend/static/video_backgrounds/midnight.png (measured 2026-09-28
 * via PIL: Image.open(...).convert("RGB").resize((1,1)).getpixel((0,0)) == (14, 15, 21)).
 * Per PM clarification (D19.1-c), the spike uses this flat color instead of the real PNG.
 * Exported (Task 19.6) so `StillFrame.tsx` shares the exact same background. */
export const MIDNIGHT_BACKGROUND = "#0E0F15";

/** Byte-identical to the 19.1 spike's plain-band text style -- Task 19.3 must not regress
 * font/size/shadow/position from the spike look (D19.3-b). Only the active karaoke word's
 * color deviates from this, applied as a single override per word span. */


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

function SpeakerChip({ speaker, color, isActive, meter }: {
  speaker: EpisodeSpeaker; color: string; isActive: boolean; meter?: number[];
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "6px 14px",
        borderRadius: 999,
        // a dark backing keeps the quiet speaker's name readable over a bright picture (walkthrough 2026-10-14)
        backgroundColor: isActive ? color : "rgba(0,0,0,0.55)",
        opacity: isActive ? 1 : INACTIVE_CHIP_OPACITY,
        transform: isActive ? "scale(1.08)" : "scale(1)",
        boxShadow: meter && isActive ? `0 0 18px ${color}55` : undefined,
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
      {meter ? <span style={{ display: "flex", alignItems: "center", gap: 2, height: 16, width: 10,
        opacity: isActive ? 0.9 : 0.35 }}>
        {meter.map((height, index) => <span key={index} style={{ width: 2, height, borderRadius: 2,
          background: isActive ? "#102519" : "#FFFFFF" }} />)}
      </span> : null}
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
function SpeakerChips({ speakers, activeId, layout = "horizontal" }: {
  speakers: EpisodeSpeaker[]; activeId: string | null; layout?: Layout;
}) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (speakers.length === 0) {
    return null;
  }
  return (
    <div
      style={{
        position: "absolute",
        ...(layout === "vertical"  // Phase 42: inside the safe zone, under the platform's top bar
          // CSS zoom scales the offsets too, so they are given in unzoomed pixels
          ? { top: VERTICAL.speakerChips.top / 1.4, left: VERTICAL.speakerChips.left / 1.4,
            width: VERTICAL.speakerChips.width / 1.4, justifyContent: "center", zoom: 1.4 }
          : { top: "5%", left: "5%" }),
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
          meter={speakingMeter(frame, fps, speaker.id === activeId)}
        />
      ))}
    </div>
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
function VocabCard({ item, opacity, position, layout = "horizontal", timeSec = 0, startSec = 0, endSec = 0 }: {
  item: LearningItem; opacity: number; position: "top-right" | "top-center"; layout?: Layout;
  timeSec?: number; startSec?: number; endSec?: number;
}) {
  const motion = learningMotion(timeSec, startSec, endSec);
  return (
    <div
      style={{
        position: "absolute",
        ...(layout === "vertical"  // Centered learning card, inside the safe zone and clear of the speaker row.
          ? { top: VERTICAL.vocabCard.top / VERTICAL.vocabCard.zoom, left: VERTICAL.vocabCard.left / VERTICAL.vocabCard.zoom,
            width: VERTICAL.vocabCard.width / VERTICAL.vocabCard.zoom, boxSizing: "border-box",
            maxHeight: VERTICAL.vocabCard.height / VERTICAL.vocabCard.zoom, overflow: "hidden", zoom: VERTICAL.vocabCard.zoom,
            border: "1px solid rgba(213,209,137,0.32)",
            transform: `translate(${motion.x.toFixed(2)}px, ${motion.y.toFixed(2)}px) rotate(${motion.rotation.toFixed(3)}deg) scale(${motion.scale.toFixed(4)})`,
            transformOrigin: "50% 50%" }
          : { top: "5%", ...(position === "top-center" ? { left: "50%" } : { right: "5%" }),
            width: "32%", boxSizing: "border-box", border: "1px solid rgba(213,209,137,0.32)",
            transform: `${position === "top-center" ? "translateX(-50%) " : ""}translate(${motion.x.toFixed(2)}px, ${motion.y.toFixed(2)}px) rotate(${motion.rotation.toFixed(3)}deg) scale(${motion.scale.toFixed(4)})`,
            transformOrigin: "50% 50%" }),
        opacity,
        backgroundColor: "rgba(14, 15, 21, 0.85)",
        borderRadius: 12,
        padding: "14px 18px",
        fontFamily: CAPTION_TEXT_STYLE.fontFamily,
        color: "#FFFFFF",
      }}
    >
      <>
        <div style={{ position: "absolute", left: 0, top: 12, bottom: 12, width: 3, borderRadius: 999,
          background: "linear-gradient(#FFD54A, #82B976)" }} />
        {motion.sweep < 1 ? <div style={{ position: "absolute", top: 0, bottom: 0, width: 26,
          left: `${-15 + motion.sweep * 125}%`, transform: "skewX(-20deg)",
          background: "linear-gradient(90deg, transparent, rgba(255,235,168,0.1), transparent)" }} /> : null}
      </>
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

/** Phase 37 (D99): a highlight clip opens on its hook title -- a big yellow banner for HOOK_SECONDS, fading in and out. */
const HOOK_SECONDS = 3.5;

export function hookOpacity(currentTimeSec: number, hookAtSec: number): number {
  const fadeIn = interpolate(currentTimeSec, [hookAtSec - 0.6, hookAtSec - 0.2], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const fadeOut = interpolate(currentTimeSec, [hookAtSec + HOOK_SECONDS - 0.4, hookAtSec + HOOK_SECONDS], [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return Math.min(fadeIn, fadeOut);
}

function HookBanner({ hook, opacity }: { hook: string; opacity: number }) {
  if (opacity <= 0) return null;
  return (
    <div style={{ position: "absolute", left: VERTICAL.hookBanner.left, width: VERTICAL.hookBanner.width, top: VERTICAL.hookBanner.top,
      opacity, display: "flex", justifyContent: "center" }}>
      <div style={{ background: "#FFD23F", color: "#14301F", borderRadius: 28, padding: "26px 34px", fontFamily: "Arial, sans-serif",
        fontSize: 60, fontWeight: 800, lineHeight: 1.1, textAlign: "center", boxShadow: "0 10px 40px rgba(0,0,0,0.45)" }}>
        {hook}
      </div>
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
  visualMode = "podcast_sprites",
  stillUrl,
  sprites,
  playAudio = true,
  layout = "horizontal",
  hook,
  hookAtSec,
}: {
  lines: EpisodeLine[];
  speakers: EpisodeSpeaker[];
  learning: EpisodeLearning | undefined;
  audioPath: string;
  fps: number;
  audioDurationSec: number;
  chapters: Chapter[];
  captionStyle: CaptionStyle;
  /** Phase 30/32: what is behind the captions (Phase 44, D123: the drawn-shot track is gone). */
  visualMode?: VisualMode;
  stillUrl?: string;
  /** Phase 32: the talking sprites of the "podcast_sprites" mode. */
  sprites?: EpisodeSprites;
  /** Task 22.4: false when the episode's full-video soundtrack already carries the voice. */
  playAudio?: boolean;
  /** Phase 37: the vertical layout, and a highlight clip's hook banner. */
  layout?: Layout;
  hook?: string;
  hookAtSec?: number;
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
  const protectedPhrases = useMemo(() => [
    ...(learning?.idioms ?? []).map(item => item.phrase),
    ...(learning?.vocab ?? []).map(item => item.word),
  ], [learning]);
  const layer = podcastLayer(visualMode);
  const speechProgress = audioDurationSec > 0 ? frame / (audioDurationSec * fps) : 0;
  // a clip's hook banner has the top of the frame to itself while it shows
  const hookShown = hook && hookAtSec !== undefined ? hookOpacity(currentTimeSec, hookAtSec) : 0;

  return (
    <>
      {layer === "sprites" && sprites ? (
        <SpriteStage sprites={sprites} lines={lines} fps={fps} frame={frame} progress={speechProgress}
          totalFrames={Math.round(audioDurationSec * fps)} layout={layout} />
      ) : (
        <PodcastLayerView layer={layer === "sprites" ? "black" : layer} stillUrl={stillUrl} progress={speechProgress} />
      )}
      {playAudio ? <Audio src={staticFile(audioPath)} startFrom={0} /> : null}
      {captionStyleSpec(captionStyle).bottomShade && layout !== "vertical" ? <div style={BOTTOM_SHADE_STYLE} /> : null}
      <ChapterProgressBar frame={frame} fps={fps} audioDurationSec={audioDurationSec} chapters={chapters} />
      <SpeakerChips speakers={speakers} activeId={activeId} layout={layout} />
      {activeLearningItem ? (
        <VocabCard
          item={activeLearningItem.item}
          opacity={
            vocabCardOpacity(currentTimeSec, activeLearningItem.slotStartSec, activeLearningItem.slotEndSec) * (1 - hookShown)
          }
          position={layer === "sprites" || layout === "vertical" ? "top-center" : "top-right"}
          layout={layout}
          timeSec={currentTimeSec}
          startSec={activeLearningItem.slotStartSec}
          endSec={activeLearningItem.slotEndSec}
        />
      ) : null}
      {line ? (
        <div
          style={{
            position: "absolute",
            ...(layout === "vertical"  // Phase 42: left of the platform's button column, above the characters
              ? { left: VERTICAL.captions.left, width: VERTICAL.captions.width, top: VERTICAL.captions.top,
                height: VERTICAL.captions.height, alignItems: "center", padding: 0 }
              : { left: 0, right: 0, bottom: "6%", padding: "0 12%" }),
            display: "flex",
            justifyContent: "center",
          }}
        >
          <CaptionBand line={line} currentTimeSec={currentTimeSec} captionStyle={captionStyle} layout={layout}
            protectedPhrases={protectedPhrases} />
        </div>
      ) : null}
      {hook && hookAtSec !== undefined ? <HookBanner hook={hook} opacity={hookShown} /> : null}
    </>
  );
}

/** Task 19.6 (D19.6-b/c): opacity envelope in frame units (no fps conversion needed by
 * callers) -- fades in over `fadeInFrames`, holds, fades out over the last `fadeOutFrames`
 * of `totalFrames`. */
export const Episode: React.FC<EpisodeInputProps> = ({
  width,
  height,
  solo,
  presentationMode,
  durationSeconds,
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
  captionStyle,
  visualMode,
  stillUrl,
  sprites,
  soundtrackPath,
  brand,
  layout = "horizontal",
  hook,
  hookAtSec,
  shortStyle,
}) => {
  // D19.6-a: total video = intro + audio + outro (Option B, extend). `audioDurationSec` is
  // the same "last line's endSec" measure Root.tsx's calculateMetadata already uses for the
  // pre-19.6 audio-only duration -- kept as a single source of truth between the two files.
  const audioDurationSec = durationSeconds ?? (lines.length > 0 ? lines[lines.length - 1].endSec : 0);
  const introFrames = Math.round(introSec * fps);
  const audioFrames = Math.round(audioDurationSec * fps);
  const outroFrames = Math.round(outroSec * fps);

  return (
    <AbsoluteFill style={{ backgroundColor: MIDNIGHT_BACKGROUND }}>
      {/* Task 22.4 (D51): the music bed spans intro + speech + outro, so it plays from frame 0. */}
      {soundtrackPath ? <Audio src={resolvedMedia(soundtrackPath)} startFrom={0} /> : null}
      {introFrames > 0 ? <Sequence from={0} durationInFrames={introFrames} name="Intro">
        {/* Phase 42 (D121): the vertical video has its own intro, laid out inside the safe zone */}
        <BrandIntro title={title} topic={topic} cefrLevel={cefrLevel} speakers={speakers} brand={brand} layout={layout} />
      </Sequence> : null}
      <Sequence from={introFrames} durationInFrames={audioFrames} name="Audio">
        {presentationMode === "solo_explainer" && solo ? <>
          {!soundtrackPath ? <Audio src={resolvedMedia(audioPath)} /> : null}
          {solo.style === "news" ? <NewsScene {...{solo,presentationMode,durationSeconds,width,height,lines,speakers,learning,audioPath,fps,title,topic,cefrLevel,chapters,introSec,outroSec,captionStyle,visualMode,stillUrl,sprites,soundtrackPath,brand,layout,hook,hookAtSec}} episodeId={solo.plan.project_id} outroText="" /> :
          solo.style === "quiz" || solo.style === "listen" ? <InteractScene {...{solo,presentationMode,durationSeconds,width,height,lines,speakers,learning,audioPath,fps,title,topic,cefrLevel,chapters,introSec,outroSec,captionStyle,visualMode,stillUrl,sprites,soundtrackPath,brand,layout,hook,hookAtSec}} episodeId={solo.plan.project_id} outroText="" /> :
          solo.style === "mistakes" || solo.style === "wordday" || solo.style === "top5" ? <LearnScene {...{solo,presentationMode,durationSeconds,width,height,lines,speakers,learning,audioPath,fps,title,topic,cefrLevel,chapters,introSec,outroSec,captionStyle,visualMode,stillUrl,sprites,soundtrackPath,brand,layout,hook,hookAtSec}} episodeId={solo.plan.project_id} outroText="" /> :
          solo.style === "blur" ? <BlurScene {...{solo,presentationMode,durationSeconds,width,height,lines,speakers,learning,audioPath,fps,title,topic,cefrLevel,chapters,introSec,outroSec,captionStyle,visualMode,stillUrl,sprites,soundtrackPath,brand,layout,hook,hookAtSec}} episodeId={solo.plan.project_id} outroText="" /> :
          solo.style === "vox" ? <VoxScene {...{solo,presentationMode,durationSeconds,width,height,lines,speakers,learning,audioPath,fps,title,topic,cefrLevel,chapters,introSec,outroSec,captionStyle,visualMode,stillUrl,sprites,soundtrackPath,brand,layout,hook,hookAtSec}} episodeId={solo.plan.project_id} outroText="" /> :
          <SoloScene {...{solo,presentationMode,durationSeconds,width,height,lines,speakers,learning,audioPath,fps,title,topic,cefrLevel,chapters,introSec,outroSec,captionStyle,visualMode,stillUrl,sprites,soundtrackPath,brand,layout,hook,hookAtSec}} episodeId={solo.plan.project_id} outroText="" />}
        </> : shortStyle ? <ChatScene {...{presentationMode,durationSeconds,width,height,lines,speakers,learning,audioPath,fps,title,topic,cefrLevel,chapters,introSec,outroSec,captionStyle,visualMode,stillUrl,sprites,soundtrackPath,brand,layout,hook,hookAtSec,shortStyle}} episodeId="" outroText="" /> : <AudioWindowContent
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
          playAudio={!soundtrackPath}
          layout={layout}
          hook={hook}
          hookAtSec={hookAtSec}
        />}
      </Sequence>
      {outroFrames > 0 ? <Sequence from={introFrames + audioFrames} durationInFrames={outroFrames} name="Outro">
        <BrandOutro brand={brand} layout={layout} />
      </Sequence> : null}
    </AbsoluteFill>
  );
};
