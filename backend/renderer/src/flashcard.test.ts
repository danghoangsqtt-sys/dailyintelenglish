import { describe, expect, it } from "vitest";
import { cardWord, deckCards, deckEntry, lineAt, partNumber, posLabel, slideIn } from "./flashcardMath";
import { sampleProps } from "./sampleShort";

describe("flashcard deck (Phase 81)", () => {
  it("reads card words from lines that say a word twice", () => {
    expect(cardWord("wash up. wash up.")).toBe("wash up");
    expect(cardWord("Brush your teeth. brush your teeth")).toBe("Brush your teeth");
    expect(cardWord("Vocabulary: daily routines.")).toBeNull();
    expect(cardWord("I wake up. Then I eat.")).toBeNull();
    const lines = ["Vocabulary: daily routines.", "wash up. wash up.", "make the bed. make the bed.", "Follow for more."].map((text) => ({ text }));
    expect(deckCards(lines)).toEqual([{ line: 1, word: "wash up" }, { line: 2, word: "make the bed" }]);
  });

  it("takes the card details from the lesson, an idiom when no word matches", () => {
    const learning = { vocab: [{ word: "to wash up", partOfSpeech: "phrasal verb", ipa: "/wɑːʃ ʌp/", definitionVi: "Rửa tay rửa mặt" }],
      idioms: [{ phrase: "make the bed", meaningVi: "Dọn giường" }] };
    expect(deckEntry(learning, "wash up")).toEqual({ word: "wash up", partOfSpeech: "phrasal verb", ipa: "/wɑːʃ ʌp/", meaningVi: "Rửa tay rửa mặt" });
    expect(deckEntry(learning, "Make the bed").meaningVi).toBe("Dọn giường");
    expect(deckEntry(undefined, "pivot")).toEqual({ word: "pivot", partOfSpeech: "", ipa: "", meaningVi: "" });
    expect(posLabel("verb")).toBe("v.") ;
    expect(posLabel("phrasal verb")).toBe("phr. v.");
  });

  it("knows the part, the playing line and the slide", () => {
    expect(partNumber("Sinh hoạt hằng ngày (P1)")).toBe(1);
    expect(partNumber("Daily routines, part 2")).toBe(2);
    expect(partNumber("Daily routines")).toBeNull();
    const lines = [{ startSec: 0, endSec: 2 }, { startSec: 2.3, endSec: 4 }];
    expect([lineAt(lines, -1), lineAt(lines, 1), lineAt(lines, 2.1), lineAt(lines, 9)]).toEqual([-1, 0, 0, 1]);
    expect(slideIn(0, 0)).toBe(0);
    expect(slideIn(1, 0)).toBe(1);
  });

  it("gives the batch page silent samples of both formats", () => {
    const slow = sampleProps("slowpod", { title: "My morning" });
    expect(slow.shortStyle).toBe("slowpod");
    expect(slow.lines[0].translation).toContain("podcast");
    const deck = sampleProps("flashcards", { title: "Daily routines (P1)" });
    expect(deck.shortStyle).toBe("flashcards");
    expect(deckCards(deck.lines)).toHaveLength(3);
  });
});
