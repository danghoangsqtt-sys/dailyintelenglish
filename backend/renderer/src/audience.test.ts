import { describe, expect, it } from "vitest";
import { explains, learningFor } from "./learnMath";
import { sampleProps } from "./sampleShort";
import { episodeLearningSchema } from "./types";

describe("Phase 72 audience (ENH-054)", () => {
  it("shows the English definition, the Vietnamese meaning or both", () => {
    expect(explains("international")).toEqual({ en: true, vi: false });
    expect(explains("vietnamese")).toEqual({ en: false, vi: true });
    expect(explains("both")).toEqual({ en: true, vi: true });
    expect(explains(undefined)).toEqual({ en: true, vi: true });  // older props: both, as before
  });

  it("never leaves a card empty when the Vietnamese meaning is missing", () => {
    expect(explains("vietnamese", false)).toEqual({ en: true, vi: false });
    expect(explains("both", false)).toEqual({ en: true, vi: false });
  });

  it("keeps older learning props valid and reads the audience when it is there", () => {
    expect(episodeLearningSchema.parse({ vocab: [], idioms: [] }).audience).toBeUndefined();
    expect(episodeLearningSchema.parse({ vocab: [], idioms: [], audience: "vietnamese" }).audience).toBe("vietnamese");
    expect(() => episodeLearningSchema.parse({ vocab: [], idioms: [], audience: "martian" })).toThrow();
  });

  it("gives the batch preview a sample learning pack for the chosen audience", () => {
    const props = sampleProps("wordday", { title: "Word of the day: 'resilient'", brief: "able to recover quickly" }, "B1", "international") as never as
      { learning: { audience: string; vocab: { word: string }[] } };
    expect(props.learning.audience).toBe("international");
    expect(learningFor(props.learning as never, "resilient")?.meaningVi).toBe("nghĩa tiếng Việt");
    const top5 = sampleProps("top5", { title: "Top 5 phrases" }, "B1", "vietnamese") as never as { learning: { idioms: unknown[] } };
    expect(top5.learning.idioms).toHaveLength(5);
  });
});
