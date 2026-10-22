import { describe, expect, it } from "vitest";
import { episodeInputPropsSchema } from "./types";
import { quoted, sampleParts, sampleProps, type SampleTemplate } from "./sampleShort";
import { mistakePair, countdownNumber } from "./learnMath";
import { quizItem, wyrRounds } from "./interactMath";

const idea = { title: "Stop Saying 'I Want' At Restaurants", brief: "Use polite phrases like 'I would like' when you order." };
const ALL: SampleTemplate[] = ["news", "blur", "mistakes", "wordday", "top5", "quiz", "listen", "chat", "wyr"];

describe("Phase 68 sample Shorts for the batch preview (ENH-050)", () => {
  it.each(ALL)("gives a valid, silent 9:16 sample for %s", (template) => {
    const props = sampleProps(template, idea, "A2");
    const parsed = episodeInputPropsSchema.parse(props);
    expect([parsed.width, parsed.height, parsed.layout, parsed.introSec, parsed.outroSec]).toEqual([1080, 1920, "vertical", 0, 0]);
    expect(parsed.audioPath).toBe("/static/media/silence.mp3");
    expect(parsed.lines.length).toBeGreaterThan(1);
    parsed.lines.forEach((line, i) => {
      expect(line.words.length).toBeGreaterThan(0);
      if (i) expect(line.startSec).toBeGreaterThan(parsed.lines[i - 1].endSec);
    });
    expect(parsed.durationSeconds!).toBeGreaterThan(parsed.lines.at(-1)!.endSec);
    if (template === "chat" || template === "wyr") {
      expect([parsed.presentationMode, parsed.shortStyle]).toEqual(["classic", template]);
    } else {
      const solo = parsed.solo!;
      expect(solo.style).toBe(template);
      expect(solo.timeline.length).toBe(solo.plan.segments.length);
      expect(solo.timeline[0].start_sec).toBeLessThanOrEqual(parsed.lines[0].startSec);
      expect(solo.timeline.at(-1)!.end_sec).toBeGreaterThanOrEqual(parsed.lines.at(-1)!.endSec);
      const board = solo.geometry.aspects["9:16"].board!;
      expect(board.height).toBeGreaterThan(0.3);
    }
  });

  it("uses the idea in the visuals each scene reads", () => {
    expect(quoted(idea.title)).toBe("I Want");
    const pair = sampleParts("mistakes", idea).find((part) => part.visual.kind === "diagram")!;
    expect(mistakePair(pair.visual)).toEqual({ wrong: "I Want", right: "the natural way to say it" });
    const top5 = sampleParts("top5", idea);
    expect(top5.map((_, i) => countdownNumber(top5.map((part) => ({ id: "x", visual: part.visual }) as never), i))).toEqual([null, 5, 4, 3, 2, 1, null]);
    const quiz = sampleParts("quiz", idea).find((part) => part.visual.kind === "text_card" && (part.visual.bullets ?? []).length === 3)!;
    expect(quizItem(quiz.visual)!.answer).toBe(0);
    expect(sampleParts("news", { title: "Storm hits the coast" })[0].visual).toMatchObject({ kind: "text_card", title: "Storm hits the coast" });
    const wyr = sampleProps("wyr", { title: "Would you rather 'fly' or swim" });
    expect(wyrRounds(wyr.lines.map((line) => ({ ...line })))[0].options).toEqual(["fly", "stay at home"]);
  });
});
