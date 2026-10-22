/**
 * Phase 68 (ENH-050): silent sample props of a Shorts template from one batch idea, so the Shorts batch page can play
 * what the Short will look like before anything is written or voiced. The words are timed evenly (no audio); the real
 * Short is written by the AI and voiced by the narrator. Pure and deterministic, so vitest pins it.
 */
import rules from "../../frontend/static/explainer-layout-rules.json";
import type { EpisodeInputProps, EpisodeLine } from "./types";
import type { SoloPayload, Visual } from "./soloTypes";

export type SampleTemplate = "news" | "blur" | "mistakes" | "wordday" | "top5" | "quiz" | "listen" | "chat" | "wyr";
export type SampleIdea = { title: string; brief?: string };
export const SILENCE = "/static/media/silence.mp3";  // 1 s of silence: the preview has no voice
const WORD_SEC = 0.34, LINE_GAP = 0.3, SEGMENT_GAP = 0.2, FPS = 30, GAP = 0.015;

type Part = { visual: Visual; lines: string[]; scene?: string };

/** The quoted phrase of a title ("Stop Saying 'I Want'" -> "I want"), else null. */
export function quoted(text: string): string | null {
  const match = text.match(/['"‘“]([^'"’”]{2,60})['"’”]/);
  return match ? match[1].trim() : null;
}

const sentence = (text: string) => { const clean = text.trim().replace(/\s+/g, " "); return /[.!?]$/.test(clean) ? clean : `${clean}.`; };

/** The sample segments of a voice-only template (the visuals the AI plan would use). */
export function sampleParts(template: Exclude<SampleTemplate, "chat" | "wyr">, idea: SampleIdea): Part[] {
  const title = idea.title.trim() || "Your Short", brief = (idea.brief || "").trim() || "The AI writes this part from your idea.";
  const card = (cardTitle: string, bullets: string[] = [], emphasis = ""): Visual => ({ kind: "text_card", title: cardTitle, bullets, emphasis }) as Visual;
  const follow = (text: string): Part => ({ visual: card("Daily Beyond English", [], text), lines: [`${text}!`] });
  switch (template) {
    case "news":
      return [{ visual: card(title), lines: [sentence(title), "Welcome to Daily Beyond English."] },
        { visual: card("What happened", [brief]), lines: [sentence(brief)] },
        { visual: { kind: "quote", text: brief, highlight: brief.split(" ").slice(0, 2).join(" "), attribution: "" } as Visual,
          lines: ["Here is why it matters to people."] },
        follow("Follow for more English news")];
    case "blur":
      return [{ visual: card(title, [], title.split(" ").slice(-2).join(" ")), lines: [sentence(title)] },
        { visual: card(brief, [], brief.split(" ").slice(-2).join(" ")), lines: [sentence(brief)] },
        follow("Follow Daily Beyond English")];
    case "mistakes": {
      const wrong = quoted(title) ?? "the common mistake";
      return [{ visual: card(title), lines: [sentence(title)] },
        { visual: { kind: "diagram", template: "comparison", nodes: [{ id: "dont", label: "Don't say", detail: wrong },
          { id: "say", label: "Say", detail: "the natural way to say it" }], edges: [] } as Visual,
          lines: [`Don't say: ${wrong}.`, "Say: the natural way to say it.", sentence(brief)] },
        follow("Follow for more English tips")];
    }
    case "wordday": {
      const word = quoted(title) ?? title.split(/\s+/).slice(-1)[0].replace(/[^\p{L}'-]/gu, "") ?? "word";
      return [{ visual: card(word, ["word of the day", brief.slice(0, 60)], word), lines: [`Today's word is ${word}.`, sentence(brief)] },
        { visual: { kind: "quote", text: `Here is an example with ${word}.`, highlight: word, attribution: "" } as Visual,
          lines: [`Here is an example with ${word}.`] },
        { visual: card("How to remember", [], word), lines: ["A memory tip helps you keep it."] },
        follow("Follow for a new word every day")];
    }
    case "top5": {
      const items = ["five", "four", "three", "two", "one"].map((number, i): Part => ({
        visual: card(`Phrase number ${5 - i}`, [i === 0 ? brief.slice(0, 50) : "its meaning in a few words"]),
        lines: [`Number ${number}: phrase number ${5 - i}.`] }));
      return [{ visual: card(title), lines: [sentence(title)] }, ...items, follow("Follow for more phrases")];
    }
    case "quiz":
      return [{ visual: card(title), lines: [sentence(title)] },
        { visual: card(sentence(brief).replace(/\.$/, "?"), ["A the first answer", "B the second answer", "C the third answer"], "A the first answer"),
          lines: [`Question one: ${sentence(brief)}`, "A: the first answer. B: the second answer. C: the third answer.", "Three, two, one.",
            "The answer is A: the first answer."] },
        follow("Comment your score")];
    case "listen":
      return [{ visual: card(title), lines: [sentence(title)] },
        { visual: { kind: "quote", text: sentence(brief), highlight: brief.split(" ").slice(0, 2).join(" "), attribution: "" } as Visual,
          lines: ["Listen.", sentence(brief), "One more time.", sentence(brief), "Here is the sentence:", sentence(brief)] },
        follow("How many did you get")];
  }
}

function timed(texts: Array<{ text: string; speakerId: string; speaker: string }>, start: number): EpisodeLine[] {
  let time = start;
  return texts.map(({ text, speakerId, speaker }) => {
    const words = text.split(/\s+/).filter(Boolean).map((word) => {
      const item = { text: word.replace(/[^\p{L}\p{N}'’-]/gu, "") || word, startSec: time, endSec: time + WORD_SEC * 0.85 };
      time += WORD_SEC;
      return item;
    });
    const line = { startSec: words[0]?.startSec ?? time, endSec: time, speaker, speakerId, text, words };
    time += LINE_GAP;
    return line;
  });
}

function geometry() {
  const spec = rules.aspects["9:16"];
  const safe = spec.safe, header = spec.header, base = spec.caption;
  const caption = { ...base, y: safe.y + safe.height - base.height - GAP };
  const top = header.y + header.height + GAP;
  const board = { x: safe.x, y: top, width: safe.width, height: caption.y - GAP - top };
  return { rules_version: rules.version, style: "vox", aspects: { "9:16": { safe, caption, header, board, segments: [] } } };
}

/** Silent sample props of a Shorts template for one idea (9:16). */
export function sampleProps(template: SampleTemplate, idea: SampleIdea, cefrLevel = "B1"): EpisodeInputProps {
  const common = { episodeId: "sample", audioPath: SILENCE, fps: FPS, width: 1080, height: 1920, title: idea.title, topic: idea.brief || idea.title,
    cefrLevel, chapters: [], introSec: 0, outroSec: 0, outroText: "", captionStyle: "outline", layout: "vertical" } as const;
  if (template === "chat" || template === "wyr") {
    const speakers = [{ id: "a", name: "Mai", gender: "female" }, { id: "b", name: "Tom", gender: "male" }];
    const brief = (idea.brief || "Let's plan it together.").trim();
    const say = template === "chat"
      ? [["a", sentence(idea.title)], ["b", "Hey! Sure, tell me more."], ["a", sentence(brief)], ["b", "Sounds good to me."], ["a", "Great, see you then!"]]
      : [["a", "Let's play would you rather!"], ["a", `Would you rather ${quoted(idea.title) ?? "travel by train"} or stay at home?`],
        ["b", `I'd rather ${quoted(idea.title) ?? "travel by train"} because it is more fun.`], ["b", "Comment your choice and follow for more!"]];
    const lines = timed(say.map(([id, text]) => ({ text, speakerId: id, speaker: id === "a" ? "Mai" : "Tom" })), 0.3);
    return { ...common, presentationMode: "classic", shortStyle: template, visualMode: "podcast_black", speakers, lines,
      durationSeconds: lines.at(-1)!.endSec + 0.6 } as unknown as EpisodeInputProps;
  }
  const parts = sampleParts(template, idea);
  const lines: EpisodeLine[] = [], timeline: SoloPayload["timeline"] = [], segments: unknown[] = [];
  let time = 0.3;
  parts.forEach((part, index) => {
    const id = `sample-${index + 1}`;
    const made = timed(part.lines.map((text) => ({ text, speakerId: "n", speaker: "Narrator" })), time);
    lines.push(...made);
    const end = made.at(-1)!.endSec + SEGMENT_GAP;
    timeline.push({ id, start_sec: time, end_sec: end });
    segments.push({ id, intent: part.lines[0], visual: part.visual, scene: null, gestures: [], layouts: {}, locks: {}, needs_fact_review: false, source_notes: "" });
    time = end;
  });
  const solo = { plan: { project_id: "sample", revision: 1, status: "approved", source_fingerprint: "sample", segments, aspects: ["9:16"] },
    style: template, geometry: geometry(), timeline, pictures: {}, photos: {}, scenes: {}, activities: {} };
  return { ...common, presentationMode: "solo_explainer", visualMode: "podcast_black", speakers: [{ id: "n", name: "Narrator", gender: "female" }],
    lines, solo, durationSeconds: time + 0.4 } as unknown as EpisodeInputProps;
}
