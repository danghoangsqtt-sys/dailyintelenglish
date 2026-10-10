import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("remotion", async () => ({
  AbsoluteFill: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
  Img: ({ src }: { src: string }) => <img src={src} />,
  staticFile: (path: string) => path,
  useVideoConfig: () => ({ width: 1280, height: 720 }),
}));

import { SpriteStage } from "./Sprites";
import type { EpisodeLine, EpisodeSprites } from "./types";

describe("SpriteStage layer order", () => {
  it("draws an activity cutaway behind the visible speaking character", () => {
    const lines: EpisodeLine[] = [
      { startSec: 0, endSec: 3, speaker: "Alex", speakerId: "alex", text: "Cook.", words: [] },
    ];
    const sprites: EpisodeSprites = {
      characters: [{
        slot: 0,
        name: "Alex",
        faceEllipse: [0.5, 0.25, 0.08, 0.07],
        topFraction: 0.1,
        pictures: { "calm__closed": "alex.png" },
        offsets: {},
      }],
      lines: [{
        slot: 0,
        visibleSlots: [0],
        expression: "calm",
        listenerExpression: "calm",
        gesture: null,
        listenerGesture: null,
        mouth: [],
      }],
      backgrounds: { kitchen: "kitchen.png" },
      lineBackgrounds: ["kitchen"],
      cutaways: [{ startSec: 0, endSec: 3, url: "cooking.png" }],
    };

    const html = renderToStaticMarkup(
      <SpriteStage sprites={sprites} lines={lines} fps={30} frame={30} totalFrames={90} progress={0.5} />,
    );

    expect(html.indexOf('src="cooking.png"')).toBeGreaterThan(-1);
    expect(html.indexOf('src="alex.png"')).toBeGreaterThan(html.indexOf('src="cooking.png"'));
  });
});
