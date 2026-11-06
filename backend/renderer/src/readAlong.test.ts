import {describe, expect, it} from "vitest";
import {readingWords} from "./ReadAlongScene";
import {sampleProps} from "./sampleShort";
import {episodeInputPropsSchema, type EpisodeLine} from "./types";

describe("Read Along", () => {
  it("keeps the full written passage even with partial word timings", () => {
    const line: EpisodeLine = {
      text: "“Hello,” I didn't say it loudly.", speaker: "Lina", speakerId: "n", startSec: 0, endSec: 3,
      words: [{text: "Hello", startSec: 0, endSec: 0.2}, {text: "didn't", startSec: 0.5, endSec: 0.9}],
    };
    const words = readingWords(line);
    expect(words.map((word) => word.text).join(" ")).toBe(line.text);
    expect(words[0].timing?.endSec).toBe(0.2);
    expect(words[1].timing).toBeUndefined();
    expect(words[2].timing?.startSec).toBe(0.5);
    expect(words[3].timing).toBeUndefined();
  });

  it("provides a valid 9:16 preview with the same picture for the whole passage", () => {
    const props = episodeInputPropsSchema.parse(sampleProps("readalong", {title: "A test"}));
    expect(props.shortStyle).toBe("readalong");
    expect(props.height / props.width).toBe(16 / 9);
    expect(props.lines.length).toBeGreaterThan(4);
    expect(new Set(props.lines.map((line) => line.readalong?.pictureUrl)).size).toBe(1);
    expect(props.lines.every((line) => readingWords(line).every((word) => word.timing))).toBe(true);
  });
});
