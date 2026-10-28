# Task 81.2 — Renderer scenes

## Objective
`SlowPodScene` and `FlashcardScene` draw the two formats in 9:16 inside the safe zone, beige paper + brand green.

## Paths
renderer/src/SlowPodScene.tsx, renderer/src/FlashcardScene.tsx, renderer/src/flashcardMath.ts, renderer/src/Episode.tsx, renderer/src/types.ts, renderer/src/sampleShort.ts, renderer/src/flashcard.test.ts

## File-Level Plan
- flashcardMath.ts (pure): card word from "<word>. <word>.", card index/total from line index, deck entry lookup in the learning pack, slide progress.
- SlowPodScene: current line's English (karaoke word highlight) large and bold, translation below, paper texture via CSS gradients, small header "SLOW ENGLISH PODCAST".
- FlashcardScene: header pill (topic + part), tag, cover card for line 0, card N/total, word, part of speech, IPA, green meaning card; neighbours peek at the sides; follow card at the end.
- Episode.tsx: route `shortStyle` slowpod / flashcards to the scenes (chat/wyr stay on ChatScene).
- sampleShort.ts: silent sample props for both.

## Verification
`cd renderer && npx vitest run && npx tsc --noEmit`; still frames from real props in 81.4.
