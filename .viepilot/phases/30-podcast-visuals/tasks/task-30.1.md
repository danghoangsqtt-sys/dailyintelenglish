# Task 30.1: Podcast composition (black, one still, character cards)

## Facts (read from the code)

- `Episode.tsx` draws `AudioWindowContent`: the shot background (`visualBackgroundForFrame`), the audio, the bottom shade, the
  chapter bar, the speaker chips (with `avatarUrl` when there is one), the vocabulary card (its position depends on the shot
  kind) and the captions. With no shots the root background is the flat `MIDNIGHT_BACKGROUND`.
- `types.ts`: `episodeSpeakerSchema` has `avatarUrl`; `episodeInputPropsSchema` has `visuals` (default empty), `soundtrackPath`,
  `brand`.

## Plan

1. `types.ts`: `visualMode` (`illustrated` | `podcast_black` | `podcast_characters` | `podcast_still`, default `illustrated`),
   `stillUrl` (optional) and a per-speaker `portraitUrl` (optional).
2. `Podcast.tsx` (new): `podcastLayer(mode)` (which layer a mode draws), `PodcastBackground` (pure black, or the still with a
   slow zoom 1 to 1.05 over the speech and a bottom shade), `CharacterCards` (portrait cards, centred, 280 x 373, the active
   card scaled 1.06 with a lit ring in the speaker colour and the others at 0.55 opacity, name label under each, a
   name-initial circle when a speaker has no picture); the card area starts below the vocabulary card so they never overlap.
3. `Episode.tsx`: `AudioWindowContent` takes `visualMode` and `stillUrl`; in a podcast mode it draws the podcast layer instead of
   the shot background and does not use `visuals`; the vocabulary card position is "top-right" in the podcast modes.
4. vitest (`podcast.test.ts`): the default mode keeps the old behaviour; `podcastLayer` for each mode; the card geometry (scale,
   opacity, positions for 2 and 3 speakers, inside the frame, below the vocabulary card); the still zoom stays in 1 to 1.05; the
   schema accepts the new props and rejects an unknown mode.

## Paths

- `video-renderer/src/types.ts`
- `video-renderer/src/Podcast.tsx` (new)
- `video-renderer/src/Episode.tsx`
- `video-renderer/src/podcast.test.ts` (new)

## Verification

`npx vitest run`, `npx tsc --noEmit`; stills of the three modes are rendered in Task 30.4.
