# Phase 30: Podcast visual modes (ENH-021)

**Status:** planned and started 2026-10-07 from the owner's request: "three picture options for the video: a podcast with no
character pictures and a black background; a podcast with the characters' pictures; a podcast with one still picture of a
scene."

## 0. Why

Drawing a shot set takes about 20 to 35 minutes of GPU. A podcast-style video needs no drawn shots at all: the audio, the
captions, the vocabulary cards and a simple picture are enough, and the video is ready in about two minutes.

## 1. The four visual modes (Enhanced / Remotion renders)

| Mode | What the screen shows behind the captions |
|---|---|
| **Illustrated story** (today) | the drawn shots of the storyboard (a plain dark background if there are none) |
| **Podcast: black** | a pure black background, speaker names, no pictures of any person |
| **Podcast: with characters** | the cast's pictures side by side (portrait cards), the active speaker's card lit and enlarged, the other dimmed; a dark background |
| **Podcast: one still** | one still picture of a library scene (its plate) for the whole episode, with a very slow zoom |

All four keep the brand intro and outro, the captions (the owner's chosen style), the vocabulary cards, the chapter bar and
the music. The Standard (ffmpeg) renderer is unchanged and ignores the mode.

## 2. Design

- **Props:** `visualMode` (`illustrated` default, `podcast_black`, `podcast_characters`, `podcast_still`), `stillUrl`, and a
  `portraitUrl` per speaker (the cast character's full-body sheet view, else the face). A podcast mode never passes the drawn
  shots, and `podcast_black` / `podcast_still` do not pass speaker pictures either.
- **Composition (`Podcast.tsx`):** `PodcastBackground` (black, or the still with a slow zoom and a bottom shade) and
  `CharacterCards` (portrait cards, spring scale for the active speaker, name label, a lit ring in the speaker colour).
  `Episode.tsx` picks the layer by `visualMode`.
- **API:** `GenerateVideoRequest` gets `visual_mode` and `still_scene_id`. `podcast_still` uses the chosen scene's plate (a scene
  without a plate is refused with a clear message); with no scene chosen, the project's first scene with a plate, else the first
  library scene that has a plate. `podcast_characters` needs a cast: a speaker without a cast character shows a name-initial card.
- **Step 5:** a "Video pictures" chip group (the four modes, remembered like the renderer choice), a scene picker for the still,
  disabled with a hint when the renderer is Standard; the podcast modes do not require generated shots.

## 3. Tasks

| Task | What | Accept when |
|---|---|---|
| 30.1 | **Composition:** `visualMode` props, `Podcast.tsx` (background, still, character cards), `Episode.tsx` wiring; vitest | vitest green, `tsc` clean |
| 30.2 | **API and props:** `visual_mode`, `still_scene_id`, the props builder for each mode, validation | Python tests green |
| 30.3 | **Step 5:** the chip group, the scene picker, persistence, the disabled states | browser tests green; screenshot |
| 30.4 | **Real renders:** one episode in each of the three new modes; frames and times; sent to the owner | the owner sees all three |
