import { describe, expect, it } from "vitest";
import { soloPayloadSchema } from "./soloTypes";
import { episodeInputPropsSchema } from "./types";
import {
  chatState, chosenOption, cueAt, initials, isInteractStyle, listenPhase, quizItem, roundAt, sideOf, timerShare, wyrOptions, wyrRounds,
} from "./interactMath";

const words = ["Question", "one:", "A", "B", "C", "Three,", "two,", "one.", "The", "answer", "is", "B."]
  .map((text, i) => ({ text, startSec: 10 + i * 0.5, endSec: 10.4 + i * 0.5 }));
const line = (speakerId: string, text: string, startSec: number) => ({ speakerId, text, startSec, endSec: startSec + 2 });

describe("Phase 65 interactive Shorts (ENH-047)", () => {
  it("accepts the quiz and listen payloads and the conversation Short style", () => {
    for (const style of ["quiz", "listen"]) {
      expect(isInteractStyle(style)).toBe(true);
      const base = { plan: { segments: [{ id: "a" }] }, timeline: [{ id: "a", start_sec: 0, end_sec: 1 }], photos: {}, pictures: {},
        geometry: { rules_version: 2, style: "vox", aspects: {} }, style };
      expect(soloPayloadSchema.safeParse(base).success).toBe(true);
    }
    expect(episodeInputPropsSchema.shape.shortStyle.safeParse("chat").success).toBe(true);
    expect(episodeInputPropsSchema.shape.shortStyle.safeParse("news").success).toBe(false);
  });

  it("reads a quiz card's options and the right one, with or without letters", () => {
    const card = { kind: "text_card", title: "Which is correct?", bullets: ["A I am bored", "B I am boring", "C I bored"], emphasis: "A I am bored" } as never;
    expect(quizItem(card)).toEqual({ question: "Which is correct?", options: ["I am bored", "I am boring", "I bored"], answer: 0 });
    const loose = { kind: "text_card", title: "Q", bullets: ["A: on Monday", "B: in Monday"], emphasis: "on Monday" } as never;
    expect(quizItem(loose)!.answer).toBe(0);
    expect(quizItem({ kind: "quote", text: "x" } as never)).toBeNull();
  });

  it("times the countdown and the reveal from the spoken words", () => {
    expect(cueAt(words, 10, 16, "three", 0.5)).toBe(12.5);
    expect(cueAt(words, 10, 16, "answer", 0.7)).toBe(14.5);
    expect(cueAt(words, 10, 16, "here is", 0.65)).toBeCloseTo(13.9);
    expect(timerShare(13.5, 12.5, 14.5)).toBeCloseTo(0.5);
    expect(timerShare(14.6, 12.5, 14.5)).toBeNull();
  });

  it("hides the sentence from 'Listen' until 'Here is the sentence', across segments", () => {
    const said = ["Can", "you", "hear", "it?", "Listen.", "Can", "I", "get", "a", "latte?", "One", "more", "time.", "Can", "I", "get",
      "a", "latte?", "Here", "is", "the", "sentence:", "Can", "I", "get", "a", "latte?"].map((text, i) => ({ text, startSec: i, endSec: i + 0.5 }));
    expect(listenPhase(said, 2)).toBeNull();
    expect(listenPhase(said, 6)).toEqual({ phase: "listening", since: 4 });
    expect(listenPhase(said, 15)?.phase).toBe("listening");
    expect(listenPhase(said, 19)).toEqual({ phase: "revealed", since: 18 });
  });

  it("shows chat messages as they start, with typing dots just before the next", () => {
    const lines = [line("a", "Hey!", 1), line("b", "Hi there", 3.5), line("a", "Lunch?", 6)];
    expect(chatState(lines, 0.5)).toEqual({ shown: 0, typing: "a" });
    expect(chatState(lines, 2)).toEqual({ shown: 1, typing: null });
    expect(chatState(lines, 3)).toEqual({ shown: 1, typing: "b" });
    expect(chatState(lines, 7)).toEqual({ shown: 3, typing: null });
    expect([sideOf(lines, "a"), sideOf(lines, "b")]).toEqual(["left", "right"]);
    expect(initials("Mai Anh")).toBe("MA");
  });

  it("parses would-you-rather rounds and the option each answer picks", () => {
    expect(wyrOptions("Would you rather work from home or work in an office?")).toEqual(["work from home", "work in an office"]);
    expect(wyrOptions("Hello")).toBeNull();
    expect(chosenOption("I'd rather work from home because I hate traffic.", ["work from home", "work in an office"])).toBe(0);
    expect(chosenOption("Hmm, hard to say.", ["tea", "coffee"])).toBeNull();
    expect(chosenOption("I'd rather visit Tokyo because I love sushi.", ["visit sunny Paris", "bustling Tokyo"])).toBe(1);
    const lines = [line("a", "Let's play would you rather!", 0), line("a", "Would you rather fly or swim?", 2),
      line("b", "I'd rather fly, it is faster.", 4), line("a", "Would you rather read books or watch movies?", 6),
      line("b", "I'd rather watch movies with friends.", 8)];
    const rounds = wyrRounds(lines);
    expect(rounds.map((round) => [round.question, round.answer, round.chosen])).toEqual([[1, 2, 0], [3, 4, 1]]);
    expect([roundAt(rounds, lines, 1), roundAt(rounds, lines, 5), roundAt(rounds, lines, 9)]).toEqual([-1, 0, 1]);
  });
});
