import { z } from "zod";
import { CAPTION_STYLES } from "./captionStyle";
import { VISUAL_MODES } from "./podcastLayout";
import { soloPayloadSchema } from "./soloTypes";

/**
 * Phase 19 spike (Task 19.1) input-props shape, as a zod schema (Remotion's own recommended
 * pattern for typed `<Composition>` props in v4).
 *
 * Strict subset of what backend/media/audio_service.py + video_service.py already compute --
 * no new DB read paths, no per-word timing (that is Task 19.2). See task card D19.1-b for the
 * field-by-field justification: .viepilot/phases/19-remotion/tasks/task-19.1.md
 */
/**
 * Task 19.3: one captured word, in mix-absolute seconds -- matches
 * `audio_jobs.word_timestamps_json`'s per-word shape exactly (D19.2-d). Empty array or
 * absent on `episodeLineSchema.words` means "no captured words for this line" -- render the
 * plain line-level fallback (older projects, Edge-TTS-empty edge case).
 */
export const episodeWordSchema = z.object({
  text: z.string(),
  startSec: z.number(),
  endSec: z.number(),
});

/** Phase 96: a Word of the day line's card (backend/content/word_repeat.py) with its picture and audience. */
export const wordCardSchema = z.object({
  beat: z.string().optional(),
  repeat: z.number().optional(),
  number: z.number().optional(),
  basic: z.string().optional(),
  advanced: z.string().optional(),
  keywords: z.array(z.string()).optional(),
  translation_vi: z.string().optional(),
  pause_after_ms: z.number().optional(),
  loop_ms: z.number().optional(),
  word: z.string().optional(),
  ipa: z.string().optional(),
  part_of_speech: z.string().optional(),
  meaning_en: z.string().optional(),
  meaning_vi: z.string().optional(),
  example_en: z.string().optional(),
  example_vi: z.string().optional(),
  picture: z.string().optional(),
  pictureUrl: z.string().optional(),
  audience: z.string().optional(),
});

/** Phase 87: one part of a word in a word-roots Short (prefix / root / suffix) and its meaning. */
export const rootsPartSchema = z.object({ text: z.string(), role: z.enum(["prefix", "root", "suffix"]), meaning: z.string().optional().default("") });

/** Phase 87: a word-roots Short's beat card, from the line's language notes (backend/content/word_family.py). */
export const rootsCardSchema = z.object({
  beat: z.string(),
  word: z.string().optional(),
  words: z.array(z.string()).optional(),
  parts: z.array(rootsPartSchema).optional(),
  head: z.string().optional(),
  kind: z.string().optional(),
  meaning: z.string().optional(),
  breakdown: z.string().optional(),
  origin: z.string().optional(),
  origin_lang: z.string().optional(),
  example_en: z.string().optional(),
  example_vi: z.string().optional(),
  answer: z.string().optional(),
  picture: z.string().optional(),
  icons: z.array(z.string()).optional(),
  pictureUrl: z.string().optional(),
});

/** Phase 88: a colour-coded chip of a grammar formula (role: s, v, o, be, ing, v3, modal, have, adj, plain). */
export const grammarChipSchema = z.object({ text: z.string(), role: z.string().optional().default("plain") });

/** Phase 88: one card of an easy-grammar Short (backend/content/grammar_lesson.py); the fields depend on its kind. */
export const grammarItemSchema = z.object({
  kind: z.string(),
  text: z.string().optional(),
  items: z.array(z.string()).optional(),
  chips: z.array(grammarChipSchema).optional(),
  result: grammarChipSchema.optional(),
  left_en: z.string().optional(),
  left_vi: z.string().optional(),
  right_en: z.string().optional(),
  right_vi: z.string().optional(),
  columns: z.array(z.string()).optional(),
  rows: z.array(z.array(z.string())).optional(),
  en: z.string().optional(),
  vi: z.string().optional(),
  marks: z.array(grammarChipSchema).optional(),
  options: z.array(z.string()).optional(),
});

/** Phase 88: a line's beat -- its scene header and every card shown so far in that scene. */
export const grammarCardSchema = z.object({
  beat: z.string(),
  scene: z.number().optional().default(0),
  label: z.string().optional().default(""),
  title: z.string().optional().default(""),
  subtitle: z.string().optional(),
  cards: z.array(grammarItemSchema).optional().default([]),
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
  /** Phase 81: the line's Vietnamese translation (slow English podcast). */
  translation: z.string().optional(),
  /** Phase 96: the card of a Word of the day Short. */
  wordday: wordCardSchema.optional(),
  whatis: wordCardSchema.optional(),
  levelup: wordCardSchema.optional(),
  picstory: wordCardSchema.optional(),
  loadword: wordCardSchema.optional(),
  /** Phase 87: the beat card of a word-roots Short. */
  roots: rootsCardSchema.optional(),
  /** Phase 88: the beat of an easy-grammar Short. */
  grammar: grammarCardSchema.optional(),
});

/**
 * Task 19.4: one project speaker, for the persistent speaker-chip overlay. `avatarUrl` is a
 * path relative to renderer/public/ (same staticFile() convention as audioPath) --
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
/** Phase 72 (ENH-054): whom the video is for -- an English definition, the Vietnamese meaning, or both. */
export const audienceSchema = z.enum(["international", "vietnamese", "both"]);
export type Audience = z.infer<typeof audienceSchema>;

export const episodeLearningSchema = z.object({
  vocab: z.array(vocabItemSchema).default([]),
  idioms: z.array(idiomItemSchema).default([]),
  audience: audienceSchema.optional(),  // absent = both
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

/** Phase 32: one talking sprite set. `pictures` maps a picture name (`calm__closed`, `smile__open`, `blink`, `gesture-wave`)
 * to its public path; `faceEllipse` is [cx, cy, rx, ry] as fractions of the 1280 x 1536 canvas; `offsets` is each picture's head
 * offset from the calm picture in canvas pixels; `topFraction` is where the figure starts on the canvas (0..1). */
export const spriteCharacterSchema = z.object({
  slot: z.number().int().min(0).max(1),
  name: z.string(),
  pictures: z.record(z.string(), z.string()),
  faceEllipse: z.tuple([z.number(), z.number(), z.number(), z.number()]),
  offsets: z.record(z.string(), z.tuple([z.number(), z.number()])).default({}),
  topFraction: z.number().default(0.15),
  /** Phase 33 (D82): show the pack mirrored, so the left figure looks right and the right figure looks left. */
  mirror: z.boolean().default(false),
  /** Phase 33 (Task 33.8): the time window of this entry -- with three or more speakers each segment shows its own pair. */
  fromSec: z.number().default(0),
  toSec: z.number().nullable().default(null),
});

/** Phase 32: what the sprites do on each line (`backend/library/sprite_plan.py`). */
export const spriteLineSchema = z.object({
  slot: z.number().int().min(0).max(1).nullable(),
  expression: z.string(),
  listenerExpression: z.string(),
  gesture: z.string().nullable(),
  listenerGesture: z.string().nullable(),
  mouth: z.array(z.tuple([z.number(), z.number()])),
});

export const spriteCutawaySchema = z.object({
  startSec: z.number().min(0), endSec: z.number().min(0), url: z.string(),
}).refine((item) => item.endSec > item.startSec && item.endSec - item.startSec <= 6);

export const episodeSpritesSchema = z.object({
  characters: z.array(spriteCharacterSchema),
  lines: z.array(spriteLineSchema),
  backgrounds: z.record(z.string(), z.string()).default({}),
  lineBackgrounds: z.array(z.string().nullable()).default([]),
  cutaways: z.array(spriteCutawaySchema).default([]),
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
  /** Phase 80: a Short (<= 1 min) -- no intro slide, a small logo during the content and a ~2 s end card. */
  short: z.boolean().optional(),
});

export const episodeInputPropsSchema = z.object({
  presentationMode: z.enum(["classic", "solo_explainer"]).optional(),
  solo: soloPayloadSchema.optional(),
  durationSeconds: z.number().finite().positive().optional(),
  /** projects.id */
  episodeId: z.string(),
  lines: z.array(episodeLineSchema),
  speakers: z.array(episodeSpeakerSchema).default([]),
  learning: episodeLearningSchema.optional(),
  /**
   * Path to the mixed episode audio, relative to renderer/public/ (Remotion requires
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
  /** Phase 30 (ENH-021) / 32: what is behind the captions -- a black screen, one still picture (`stillUrl`), or the
   * talking sprites (the default). Phase 44 (D123): the drawn-shot "illustrated" mode was removed with RealVisXL. */
  visualMode: z.enum(VISUAL_MODES).default("podcast_sprites"),
  stillUrl: z.string().optional(),
  /** Phase 32: the talking sprites of `visualMode: "podcast_sprites"`. */
  sprites: episodeSpritesSchema.optional(),
  /** Task 22.4 (D51): when set, one full-video soundtrack (voice + music bed covering the intro,
   * speech and outro, faded out on the last frame) plays from frame 0 instead of `audioPath`. */
  soundtrackPath: z.string().optional(),
  brand: episodeBrandSchema.optional(),
  /** Phase 37 (D100): "vertical" (1080x1920, Shorts/TikTok): picture on top, big captions in the middle, the characters
   * below. Default "horizontal" keeps every older props file unchanged. */
  layout: z.enum(["horizontal", "vertical"]).default("horizontal"),
  /** Phase 37 (D99): a highlight clip is a frame range of the vertical episode; its hook title shows as a banner for a
   * few seconds from `hookAtSec` (speech time). */
  hook: z.string().optional(),
  hookAtSec: z.number().optional(),
  /** Phase 65 (ENH-047): a two-character conversation Short drawn from its lines -- "chat" or "wyr" (would you rather). */
  shortStyle: z.enum(["chat", "wyr", "slowpod", "flashcards", "roots", "grammar", "wordday", "whatis", "levelup", "picstory", "loadword"]).optional(),
});

export type EpisodeWord = z.infer<typeof episodeWordSchema>;
export type RootsCard = z.infer<typeof rootsCardSchema>;
export type RootsPart = z.infer<typeof rootsPartSchema>;
export type GrammarCard = z.infer<typeof grammarCardSchema>;
export type GrammarItem = z.infer<typeof grammarItemSchema>;
export type GrammarChip = z.infer<typeof grammarChipSchema>;
export type EpisodeLine = z.infer<typeof episodeLineSchema>;
export type EpisodeSpeaker = z.infer<typeof episodeSpeakerSchema>;
export type VocabItem = z.infer<typeof vocabItemSchema>;
export type IdiomItem = z.infer<typeof idiomItemSchema>;
export type EpisodeLearning = z.infer<typeof episodeLearningSchema>;
export type Chapter = z.infer<typeof chapterSchema>;
export type EpisodeInputProps = z.infer<typeof episodeInputPropsSchema>;
export type EpisodeBrand = z.infer<typeof episodeBrandSchema>;
export type SpriteCharacter = z.infer<typeof spriteCharacterSchema>;
export type SpriteLine = z.infer<typeof spriteLineSchema>;
export type EpisodeSprites = z.infer<typeof episodeSpritesSchema>;
export type Layout = "horizontal" | "vertical";
