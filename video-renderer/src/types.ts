import { z } from "zod";
import { CAPTION_STYLES } from "./captionStyle";
import { VISUAL_MODES } from "./podcastLayout";

/**
 * Phase 19 spike (Task 19.1) input-props shape, as a zod schema (Remotion's own recommended
 * pattern for typed `<Composition>` props in v4).
 *
 * Strict subset of what app/services/audio_service.py + video_service.py already compute --
 * no new DB read paths, no per-word timing (that is Task 19.2). See task card D19.1-b for the
 * field-by-field justification: .viepilot/phases/19-remotion/tasks/task-19.1.md
 */
/**
 * Task 19.3: one captured word, in mix-absolute seconds -- matches
 * `audio_jobs.word_timestamps_json`'s per-word shape exactly (D19.2-d). Empty array or
 * absent on `episodeLineSchema.words` means "no captured words for this line" -- render the
 * plain line-level fallback (older projects, omnivoice lines, Edge-TTS-empty edge case).
 */
export const episodeWordSchema = z.object({
  text: z.string(),
  startSec: z.number(),
  endSec: z.number(),
});

export const episodeLineSchema = z.object({
  startSec: z.number(),
  endSec: z.number(),
  /** Display label (e.g. "Alex") -- audio_jobs.timestamps_json's `label`, not the speaker UUID. */
  speaker: z.string(),
  /**
   * Task 19.4: the real `speakers.id` (DB UUID), kept separate from `speaker` (the display
   * name) because a project could have two speakers who happen to share a display name --
   * `activeSpeakerId` must always match by id, never by name.
   */
  speakerId: z.string(),
  text: z.string(),
  words: z.array(episodeWordSchema).optional().default([]),
});

/**
 * Task 19.4: one project speaker, for the persistent speaker-chip overlay. `avatarUrl` is a
 * path relative to video-renderer/public/ (same staticFile() convention as audioPath) --
 * absent when `speakers.avatar_image_path` is NULL in the real DB.
 */
export const episodeSpeakerSchema = z.object({
  id: z.string(),
  name: z.string(),
  gender: z.string(),
  avatarUrl: z.string().optional(),
  /** Phase 30: the cast character's full picture for the podcast "with characters" cards (falls back to `avatarUrl`). */
});

/**
 * Task 19.5: one vocabulary item from `learning_contents.vocabulary_json`. DB field names
 * are snake_case (`part_of_speech`/`definition_en`/`definition_vi`/`example_sentence`) --
 * converted to camelCase here, matching the same convention already applied to
 * `avatar_image_path` -> `avatarUrl` in Task 19.4.
 */
export const vocabItemSchema = z.object({
  word: z.string(),
  partOfSpeech: z.string(),
  ipa: z.string(),
  definitionEn: z.string(),
  definitionVi: z.string(),
  exampleSentence: z.string(),
});

/** Task 19.5: one idiom item from `learning_contents.idioms_json`, same camelCase convention. */
export const idiomItemSchema = z.object({
  phrase: z.string(),
  meaningEn: z.string(),
  meaningVi: z.string(),
  exampleSentence: z.string(),
});

/**
 * Task 19.5: optional top-level learning content for the vocab/idiom pop-up cards. Absent
 * entirely when the project has no `learning_contents` row; both arrays may independently be
 * empty. No line-level anchor exists on either item shape -- attachment is derived from item
 * text vs. line text at composition time (see `vocab.ts`).
 */
export const episodeLearningSchema = z.object({
  vocab: z.array(vocabItemSchema).default([]),
  idioms: z.array(idiomItemSchema).default([]),
});

/**
 * Task 19.6: one YouTube-style chapter marker, structured for the progress-bar overlay.
 * Produced by parsing `youtube_service.real_chapters_from_timestamps`'s plain-text
 * "MM:SS Label" output back into `{title, startSec}` pairs in the Python runner --
 * `real_chapters_from_timestamps` itself stays the single source of truth for *which* lines
 * become chapters and how labels are built (D19.6-e); this schema only describes the
 * already-decided result.
 */
export const chapterSchema = z.object({
  title: z.string(),
  startSec: z.number(),
});

export const episodeVisualsSchema = z.object({
  shots: z.record(z.string(), z.object({
    url: z.string(), kind: z.enum(["single", "duo_close", "duo_wide", "insert"]),
  })),
  lineShots: z.array(z.string().nullable()),
});

/** Phase 25 (D52-D55): the branded intro/outro -- Jenny's greeting + wish and farewell. Optional,
 * so older props files render the branded slides without a voice and with the default wish. */
export const episodeBrandSchema = z.object({
  wish: z.string(),
  farewellLine: z.string().optional(),
  greetingPath: z.string().optional(),
  farewellPath: z.string().optional(),
  greetingStartSec: z.number().optional(),
  farewellStartSec: z.number().optional(),
  /** true when the full-video soundtrack already carries the voices (so they are not played twice). */
  voicesInSoundtrack: z.boolean().default(false),
});

export const episodeInputPropsSchema = z.object({
  /** projects.id */
  episodeId: z.string(),
  lines: z.array(episodeLineSchema),
  speakers: z.array(episodeSpeakerSchema).default([]),
  learning: episodeLearningSchema.optional(),
  /**
   * Path to the mixed episode audio, relative to video-renderer/public/ (Remotion requires
   * every asset to live under public/ and be loaded via staticFile() -- absolute filesystem
   * paths are not supported). The runner script copies AudioService's mixed MP3
   * (audio_job["mp3_path"]) to public/spike-audio/<episodeId>.mp3 before invoking render.
   */
  audioPath: z.string(),
  fps: z.number(),
  width: z.number(),
  height: z.number(),
  /**
   * Task 19.6: intro/outro + chapter-bar fields. All optional with defaults so an older
   * runner invocation (or a hand-crafted props file) that omits them still renders --
   * `introSec`/`outroSec` default to the owner-signed timings, `outroText` to the
   * owner-approved exact string (task-19.6.md).
   */
  title: z.string().default(""),
  topic: z.string().default(""),
  cefrLevel: z.string().default(""),
  chapters: z.array(chapterSchema).default([]),
  introSec: z.number().default(2.5),
  outroSec: z.number().default(5.0),
  outroText: z.string().default("Thanks for watching · Subscribe for more · See you next episode!"),
  /** Task 20.2d: user-selected caption treatment (see `captionStyle.ts`). Optional with the
   * owner-preferred default so older runner invocations / props files still render. */
  captionStyle: z.enum(CAPTION_STYLES).default("outline"),
  visuals: episodeVisualsSchema.default({ shots: {}, lineShots: [] }),
  /** Phase 30 (ENH-021): what is behind the captions. "illustrated" = the drawn shots (the previous behaviour); the podcast
   * modes need no shots: a black screen, the cast's portrait cards, or one still picture (`stillUrl`). */
  visualMode: z.enum(VISUAL_MODES).default("illustrated"),
  stillUrl: z.string().optional(),
  /** Task 22.4 (D51): when set, one full-video soundtrack (voice + music bed covering the intro,
   * speech and outro, faded out on the last frame) plays from frame 0 instead of `audioPath`. */
  soundtrackPath: z.string().optional(),
  brand: episodeBrandSchema.optional(),
});

export type EpisodeWord = z.infer<typeof episodeWordSchema>;
export type EpisodeLine = z.infer<typeof episodeLineSchema>;
export type EpisodeSpeaker = z.infer<typeof episodeSpeakerSchema>;
export type VocabItem = z.infer<typeof vocabItemSchema>;
export type IdiomItem = z.infer<typeof idiomItemSchema>;
export type EpisodeLearning = z.infer<typeof episodeLearningSchema>;
export type Chapter = z.infer<typeof chapterSchema>;
export type EpisodeInputProps = z.infer<typeof episodeInputPropsSchema>;
export type EpisodeVisuals = z.infer<typeof episodeVisualsSchema>;
export type EpisodeBrand = z.infer<typeof episodeBrandSchema>;
