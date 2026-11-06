/**
 * Phase 68 (ENH-050): silent sample props of a Shorts template from one batch idea, so the Shorts batch page can play
 * what the Short will look like before anything is written or voiced. The words are timed evenly (no audio); the real
 * Short is written by the AI and voiced by the narrator. Pure and deterministic, so vitest pins it.
 */
import rules from "../../../frontend/static/explainer-layout-rules.json";
import type { EpisodeInputProps, EpisodeLine } from "./types";
import type { SoloPayload, Visual } from "./soloTypes";

export type SampleTemplate = "news" | "blur" | "mistakes" | "wordday" | "top5" | "quiz" | "listen" | "chat" | "wyr" | "slowpod" | "flashcards"
  | "roots" | "whatis" | "levelup" | "picstory" | "loadword"
  | "grammar" | "readalong";
export type SampleIdea = { title: string; brief?: string; vi?: string };  // vi: Phase 92, the example clips' Vietnamese meaning
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
export function sampleParts(template: Exclude<SampleTemplate, "chat" | "wyr" | "slowpod" | "flashcards" | "roots" | "grammar" | "whatis" | "levelup" | "picstory" | "loadword" | "readalong">, idea: SampleIdea): Part[] {
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

function timed(texts: Array<{ text: string; speakerId: string; speaker: string; translation?: string }>, start: number): EpisodeLine[] {
  let time = start;
  return texts.map(({ text, speakerId, speaker, translation }) => {
    const words = text.split(/\s+/).filter(Boolean).map((word) => {
      const item = { text: word.replace(/[^\p{L}\p{N}'’-]/gu, "") || word, startSec: time, endSec: time + WORD_SEC * 0.85 };
      time += WORD_SEC;
      return item;
    });
    const line = { startSec: words[0]?.startSec ?? time, endSec: time, speaker, speakerId, text, words, ...(translation ? { translation } : {}) };
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

/** Phase 72 (ENH-054): a sample learning pack, so the preview shows the cards of the chosen audience. */
function sampleLearning(template: SampleTemplate, idea: SampleIdea, audience: string) {
  const vietnamese = idea.vi || "nghĩa tiếng Việt";
  const word = template === "wordday" ? (quoted(idea.title) ?? idea.title.split(/\s+/).slice(-1)[0].replace(/[^\p{L}'-]/gu, "") ?? "word") : "";
  const vocab = word ? [{ word, partOfSpeech: "noun", ipa: "", definitionEn: idea.brief || "", definitionVi: vietnamese, exampleSentence: "" }] : [];
  const idioms = template === "top5" ? [5, 4, 3, 2, 1].map((n) => ({ phrase: `Phrase number ${n}`, meaningEn: "", meaningVi: vietnamese, exampleSentence: "" })) : [];
  return { vocab, idioms, audience };
}

/** Silent sample props of a Shorts template for one idea (9:16). */
export function sampleProps(template: SampleTemplate, idea: SampleIdea, cefrLevel = "B1", audience = "both"): EpisodeInputProps {
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
  if (template === "slowpod" || template === "flashcards") {  // Phase 81: drawn from their lines, like chat
    const topic = (idea.title || "Daily routines").trim();
    const say: [string, string][] = template === "slowpod"
      ? [["Hi everyone, and welcome back to my slow English podcast.", "Chào mọi người, chào mừng trở lại với podcast tiếng Anh nói chậm."],
        [sentence(topic), "Chủ đề hôm nay."], ["The AI writes eight short and easy sentences.", "AI viết tám câu ngắn, dễ hiểu."],
        ["Follow Daily Beyond English for more slow English.", "Theo dõi Daily Beyond English để nghe thêm."]]
      : [[`Vocabulary: ${topic}.`, ""], ["wash up. wash up.", ""], ["make the bed. make the bed.", ""], ["brush your teeth. brush your teeth.", ""],
        ["Follow Daily Beyond English for more words.", ""]];
    const lines = timed(say.map(([text, translation]) => ({ text, translation, speakerId: "n", speaker: "Narrator" })), 0.3);
    const vocab = [["wash up", "phrasal verb", "/wɑːʃ ʌp/", "Rửa tay rửa mặt"], ["make the bed", "phrase", "/meɪk ðə bed/", "Dọn giường"],
      ["brush your teeth", "phrase", "/brʌʃ jɔːr tiːθ/", "Đánh răng"]]
      .map(([word, partOfSpeech, ipa, definitionVi]) => ({ word, partOfSpeech, ipa, definitionEn: "", definitionVi, exampleSentence: "" }));
    return { ...common, presentationMode: "classic", shortStyle: template, visualMode: "podcast_black",
      speakers: [{ id: "n", name: "Narrator", gender: "female" }], lines, learning: { vocab, idioms: [], audience },
      durationSeconds: lines.at(-1)!.endSec + 0.6 } as unknown as EpisodeInputProps;
  }
  if (template === "readalong") {
    const sentences = [
      "On Monday, I had a long list of things to do.",
      "I looked at the list and felt tired before I began.",
      "My friend said, “Choose one small task first.”",
      "I wrote one email and crossed it off my list.",
      "Then I made a cup of tea and started the next task.",
      "By lunch, the work felt easier.",
      "Now I still make lists, but I take them one step at a time.",
    ];
    const readalong = {title: "One Task at a Time", pictureUrl: "samples/levelup.jpg"};
    const lines = timed(sentences.map((text) => ({text, speakerId: "n", speaker: "Narrator"})), 0.3)
      .map((line) => ({...line, readalong}));
    return {...common, chapters: [], presentationMode: "classic", shortStyle: "readalong", visualMode: "podcast_black",
      speakers: [{id: "n", name: "Narrator", gender: "female"}], lines, durationSeconds: lines.at(-1)!.endSec + 0.6};
  }
  if (template === "loadword") {  // Phase 97: the word looped on a wall of itself, then shown with an example
    const fields = { word: "compensation", ipa: "/ˌkɑːmpenˈseɪʃn/", part_of_speech: "noun", meaning_en: "money paid for a loss", meaning_vi: "khoản đền bù", audience,
      example_en: "No amount of compensation can make up for it.", example_vi: "Không khoản đền bù nào bù đắp được.",
      articles: ["The debate over executive compensation has grown sharply this year", "Workers asked for fair compensation after the factory closed", "New rules on compensation will change how companies pay staff",
        "Many employees now compare compensation before they accept a job", "Critics say the compensation paid to managers is far too high"] };
    const say = [["Compensation.", { ...fields, beat: "load" }], ["Compensation.", { ...fields, beat: "reveal" }], [fields.example_en, { ...fields, beat: "example" }]] as const;
    const lines = timed(say.map(([text]) => ({ text, speakerId: "n", speaker: "Narrator" })), 0.1).map((line, at) => ({ ...line, loadword: say[at][1] }));
    return { ...common, learning: sampleLearning(template, idea, audience), presentationMode: "classic", shortStyle: "loadword", visualMode: "podcast_black",
      speakers: [{ id: "n", name: "Narrator", gender: "female" }], lines, durationSeconds: lines.at(-1)!.endSec + 0.6 } as unknown as EpisodeInputProps;
  }
  if (template === "picstory") {  // Phase 96.4: one picture for each sentence
    const say = [["I take off my shoes.", "shoes", "Tôi cởi giày.", 1], ["I walk on the sand.", "walk sand", "Tôi đi trên cát.", 2]] as const;
    const parts = say.map(([text, keywords, translation_vi, number]) => [text, { beat: "line", number, word: `line ${number}`, keywords: keywords.split(" "), translation_vi, audience,
      pictureUrl: `samples/picstory-${number}.jpg` }] as const);
    const lines = timed(parts.map(([text]) => ({ text, speakerId: "n", speaker: "Narrator" })), 0.4).map((line, at) => ({ ...line, picstory: parts[at][1] }));
    return { ...common, learning: sampleLearning(template, idea, audience), presentationMode: "classic", shortStyle: "picstory", visualMode: "podcast_black",
      speakers: [{ id: "n", name: "Narrator", gender: "female" }], lines, durationSeconds: lines.at(-1)!.endSec + 0.6 } as unknown as EpisodeInputProps;
  }
  if (template === "levelup") {  // Phase 96.6: a plain phrase, then the natural one twice, over its picture
    const pairs = [["I'm very busy", "I'm swamped", "ngập đầu trong công việc", "very busy with too much work"]];
    const say = pairs.flatMap(([basic, advanced, meaning_vi, meaning_en], at) => {
      const fields = { word: advanced, basic, advanced, meaning_vi, meaning_en, number: at + 1, audience, pictureUrl: "samples/levelup.jpg" };
      return [[`${basic}.`, { ...fields, beat: "basic" }], [`${advanced}.`, { ...fields, beat: "advanced" }], [`${advanced}.`, { ...fields, beat: "advanced" }]] as const;
    });
    const lines = timed(say.map(([text]) => ({ text, speakerId: "n", speaker: "Narrator" })), 0.2).map((line, at) => ({ ...line, levelup: say[at][1] }));
    return { ...common, learning: sampleLearning(template, idea, audience), presentationMode: "classic", shortStyle: "levelup", visualMode: "podcast_black",
      speakers: [{ id: "n", name: "Narrator", gender: "female" }], lines, durationSeconds: lines.at(-1)!.endSec + 0.6 } as unknown as EpisodeInputProps;
  }
  if (template === "whatis") {  // Phase 96.5: an object, the question, a silent 1-2-3, the name
    const say = [["plug", "/plʌɡ/", "phích cắm"], ["tap", "/tæp/", "vòi nước"]].flatMap(([word, ipa, meaning_vi], at) => {
      const fields = { word, ipa, meaning_vi, meaning_en: `a ${word}`, number: at + 1, audience, pictureUrl: `samples/whatis-${word}.jpg` };
      return [["What is this called?", { ...fields, beat: "ask", pause_after_ms: 3000 }], [`${word[0].toUpperCase()}${word.slice(1)}.`, { ...fields, beat: "answer" }]] as const;
    });
    const lines = timed(say.map(([text]) => ({ text, speakerId: "n", speaker: "Narrator" })), 0.1).map((line, at) => ({ ...line, whatis: say[at][1] }));
    let shift = 0;
    const spaced = lines.map((line, at) => {
      const moved = { ...line, startSec: line.startSec + shift, endSec: line.endSec + shift, words: line.words.map((word) => ({ ...word, startSec: word.startSec + shift, endSec: word.endSec + shift })) };
      if (say[at][1].beat === "ask") shift += 3;
      return moved;
    });
    return { ...common, learning: sampleLearning(template, idea, audience), presentationMode: "classic", shortStyle: "whatis", visualMode: "podcast_black",
      speakers: [{ id: "n", name: "Narrator", gender: "female" }], lines: spaced, durationSeconds: spaced.at(-1)!.endSec + 0.6 } as unknown as EpisodeInputProps;
  }
  if (template === "wordday") {  // Phase 96: one word said six times over its picture, drawn from its lines
    const word = quoted(idea.title) ?? idea.title.split(/\s+/).slice(-1)[0].replace(/[^\p{L}'-]/gu, "") ?? "word";
    const example_en = `It was a ${word} little room.`;
    const fields = { word, ipa: "/ˈkoʊ.zi/", part_of_speech: "adjective", meaning_en: (idea.brief ?? "").slice(0, 60), meaning_vi: idea.vi ?? "",
      example_en, example_vi: "Đó là một căn phòng nhỏ ấm cúng.", audience, pictureUrl: "samples/wordday.jpg" };
    const spoken = word.charAt(0).toUpperCase() + word.slice(1) + ".";
    const say = [...Array.from({ length: 6 }, (_, at) => [spoken, { ...fields, beat: "repeat", repeat: at + 1 }] as const),
      [example_en, { ...fields, beat: "example", repeat: 6 }] as const];
    const lines = timed(say.map(([text]) => ({ text, speakerId: "n", speaker: "Narrator" })), 0.1)
      .map((line, at) => ({ ...line, wordday: say[at][1] }));
    return { ...common, learning: sampleLearning(template, idea, audience), presentationMode: "classic", shortStyle: "wordday", visualMode: "podcast_black",
      speakers: [{ id: "n", name: "Narrator", gender: "female" }], lines, durationSeconds: lines.at(-1)!.endSec + 0.6 } as unknown as EpisodeInputProps;
  }
  if (template === "roots") {  // Phase 87: a word family's beats, drawn from their lines (the AI picks the real head)
    const part = (text: string, role: "prefix" | "root" | "suffix", meaning: string) => ({ text, role, meaning });
    const compress = [part("com", "prefix", "cùng nhau"), part("press", "root", "ép")];
    const say: [string, Record<string, unknown>][] = [
      ["Bạn có biết Express là bày tỏ,", { beat: "hook", word: "express", meaning: "bày tỏ", parts: [part("ex", "prefix", "ra ngoài"), part("press", "root", "ép")], icons: ["mood-smile"] }],
      ["nhưng Express và Impress cùng một gốc?", { beat: "twins", words: ["express", "impress"], head: "press", kind: "root" }],
      ["Sau video này, bạn sẽ nhớ được 5 từ tiếng Anh chỉ từ một gốc duy nhất!", { beat: "wheel", head: "press", kind: "root",
        words: ["express", "impress", "compress", "depress", "suppress"] }],
      ["Compress, nén lại.", { beat: "whole", word: "compress", meaning: "nén lại", parts: compress, icons: ["device-desktop", "file-zip"] }],
      ["COM là cùng nhau, PRESS là ép: ép sát vào nhau thì chiếm ít chỗ hơn.", { beat: "split", word: "compress", meaning: "nén lại", parts: compress,
        breakdown: "COM: cùng nhau · PRESS: ép", icons: ["device-desktop", "file-zip"] }],
      ["We compress the files to save space.", { beat: "example", word: "compress", meaning: "nén lại", parts: compress,
        breakdown: "COM: cùng nhau · PRESS: ép", example_en: "We compress the files to save space.", example_vi: "Chúng tôi nén các tệp để tiết kiệm dung lượng.",
        icons: ["device-desktop", "file-zip"] }],
      ["Đoán từ cuối nhé! Một bản tin bị khoá trong ngăn kéo.", { beat: "quiz", word: "suppress", parts: [part("sup", "prefix", "dưới"), part("press", "root", "đè")], icons: ["news", "lock"] }],
      ["Comment đáp án và theo dõi Daily Beyond English nhé!", { beat: "follow", word: "suppress" }]];
    const lines = timed(say.map(([text]) => ({ text, speakerId: "n", speaker: "Narrator" })), 0.3)
      .map((line, at) => ({ ...line, roots: say[at][1] }));
    return { ...common, presentationMode: "classic", shortStyle: "roots", visualMode: "podcast_black",
      speakers: [{ id: "n", name: "Narrator", gender: "female" }], lines, durationSeconds: lines.at(-1)!.endSec + 0.6 } as unknown as EpisodeInputProps;
  }
  if (template === "grammar") {  // Phase 88: a grammar lesson's beats, drawn from their lines (the AI writes the real lesson)
    const chip = (text: string, role: string) => ({ text, role });
    const hook = { beat: "hook", scene: 0, label: "HOOK • ĐẬP TAN HỌC VẸT", title: "CÂU BỊ ĐỘNG" };
    const formulas = { kind: "formulas", items: ["S + am/is/are + V3", "S + was/were + V3", "S + has/have + been + V3", "S + will be + V3"] };
    const one = { beat: "scene", scene: 1, label: "BẢN CHẤT CỐT LÕI", title: "Câu bị động = câu miêu tả trạng thái!", subtitle: "So sánh hai câu" };
    const compare = { kind: "compare", left_en: "She is beautiful.", left_vi: "Cô ấy đẹp.", right_en: "The room is cleaned.", right_vi: "Căn phòng được dọn." };
    const formula = { kind: "formula", chips: [chip("S", "s"), chip("BE", "be"), chip("V3", "v3")], text: "giống hệt S + BE + Adj" };
    const two = { beat: "scene", scene: 2, label: "BẺ KHOÁ V3", title: "Chiếc nhãn dán kết quả!" };
    const sticker = { kind: "sticker", text: "CLEANED" };
    const lego = { kind: "lego", chips: [chip("BE", "be"), chip("-ING", "ing")], result: chip("BEING", "be") };
    const summary = { beat: "summary", scene: 3, label: "TỔNG KẾT BẢN CHẤT", title: "CÂU BỊ ĐỘNG" };
    const table = { kind: "table", columns: ["Thì", "TO BE gánh thì", "Nhãn"] };
    const rows = [["Đơn", "is", "cleaned"], ["Tiếp diễn", "is being", "cleaned"], ["Hoàn thành", "has been", "cleaned"]];
    const quiz = { kind: "quiz", text: "The letter ___ yesterday.", options: ["was sent", "is sent"] };
    const say: [string, Record<string, unknown>][] = [
      ["Bạn đang phải học thuộc cả chục công thức câu bị động?", { ...hook, cards: [formulas] }],
      ["Quên hết đi!", { ...hook, cards: [formulas, { kind: "stamp", text: "QUÊN HẾT ĐI" }] }],
      ["Hiểu đúng bản chất câu bị động trong một phút!", { ...hook, cards: [{ kind: "promise", text: "Hiểu đúng bản chất câu bị động trong 1 phút!" }] }],
      ["Nhìn hai câu này: She is beautiful và The room is cleaned.", { ...one, cards: [compare] }],
      ["Giống hệt nhau: chủ ngữ, to be, rồi một từ miêu tả.", { ...one, cards: [compare, formula] }],
      ["V3 giống như một chiếc nhãn dán kết quả.", { ...two, cards: [sticker] }],
      ["Muốn tiếp diễn, ghép to be với ing thành being.", { ...two, cards: [sticker, lego] }],
      ["Tổng kết lại tất cả trong một bảng nhé.", { ...summary, cards: [{ ...table, rows: rows.slice(0, 1) }] }],
      ["Hoàn thành: has been cộng cleaned.", { ...summary, cards: [{ ...table, rows }] }],
      ["Câu hỏi nhanh: The letter ___ yesterday.", { beat: "quiz", scene: 4, label: "CÂU HỎI NHANH", title: "CÂU BỊ ĐỘNG", cards: [quiz] }],
      ["Comment đáp án và theo dõi Daily Beyond English nhé!", { beat: "follow", scene: 4, label: "CÂU HỎI NHANH", title: "CÂU BỊ ĐỘNG", cards: [quiz] }]];
    const lines = timed(say.map(([text]) => ({ text, speakerId: "n", speaker: "Narrator" })), 0.3)
      .map((line, at) => ({ ...line, grammar: say[at][1] }));
    return { ...common, presentationMode: "classic", shortStyle: "grammar", visualMode: "podcast_black",
      speakers: [{ id: "n", name: "Narrator", gender: "female" }], lines, durationSeconds: lines.at(-1)!.endSec + 0.6 } as unknown as EpisodeInputProps;
  }
  const parts = sampleParts(template as Exclude<SampleTemplate, "chat" | "wyr" | "slowpod" | "flashcards" | "roots" | "grammar" | "whatis" | "levelup" | "picstory" | "loadword" | "readalong">, idea);
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
    lines, solo, learning: sampleLearning(template, idea, audience), durationSeconds: time + 0.4 } as unknown as EpisodeInputProps;
}
