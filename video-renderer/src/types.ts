import { z } from "zod";

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
  text: z.string(),
  words: z.array(episodeWordSchema).optional().default([]),
});

export const episodeInputPropsSchema = z.object({
  /** projects.id */
  episodeId: z.string(),
  lines: z.array(episodeLineSchema),
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
});

export type EpisodeWord = z.infer<typeof episodeWordSchema>;
export type EpisodeLine = z.infer<typeof episodeLineSchema>;
export type EpisodeInputProps = z.infer<typeof episodeInputPropsSchema>;
