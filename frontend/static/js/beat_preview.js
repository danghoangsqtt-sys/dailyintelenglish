/**
 * Phase 78 (Task 78.2): the sketch of one storyboard beat as the talking-characters video lays it out, from
 * POST /api/projects/{id}/storyboard/preview. Shared by the storyboard review and the Shorts clip cards.
 *
 * The geometry copies the renderer (renderer/src/spriteTimeline.ts `canvasBox`, renderer/src/safeZone.ts `VERTICAL`):
 *   16:9 -- the scene fills the frame; each sprite box is 1.2x the frame height, as wide as the frame is high, centred
 *           at 27% / 73%, its highest head 5% from the top; an insert's illustration covers the frame.
 *   9:16 -- the picture is the top 830 of 1920 px (fading out from 500), captions sit at 790-1040 between x 216 and 864,
 *           sprites are 960 px tall with their heads at 1045, centred at x 355 / 725.
 * It is a sketch (one pose, no motion, no captions timing), labelled as such; the render stays the reference.
 */
(function () {
  const H = { slotX: [0.27, 0.73], spriteHeight: 1.2, headMargin: 0.05 };
  const V = { width: 1080, height: 1920, picture: 830, fadeFrom: 500, slotX: [355, 725], headTop: 1045, spriteHeight: 960,
    captions: { left: 216, top: 790, width: 648, height: 250 }, chips: 300, hook: 330 };
  const CANVAS_RATIO = 1280 / 1536;

  function el(tag, className, props = {}) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    Object.entries(props).forEach(([key, value]) => {
      if (key === "text") node.textContent = value;
      else if (key === "style") Object.assign(node.style, value);
      else node[key] = value;
    });
    return node;
  }

  const pct = (value) => `${(value * 100).toFixed(3)}%`;

  function image(url, className, style = {}, lazy = false) {
    // the scene and the characters are the sketch itself: load them at once; only the blurred backdrop may wait
    const node = el("img", className, { src: url, alt: "", loading: lazy ? "lazy" : "eager", decoding: "async", draggable: false });
    Object.assign(node.style, style);
    return node;
  }

  function sprites(item, vertical) {
    const ready = (item.characters || []).filter((member) => member.picture_url);
    if (!ready.length) return [];
    const top = Math.min(...ready.map((member) => member.top_fraction ?? 0.15), 0.15);
    return ready.map((member) => {
      let box;
      if (vertical) {
        const boxHeight = V.spriteHeight / V.height;                         // of the frame height
        const boxWidth = (V.spriteHeight * CANVAS_RATIO) / V.width;          // of the frame width
        const centre = (V.slotX[member.slot] ?? V.slotX[0]) / V.width;
        box = { left: centre - boxWidth / 2, top: V.headTop / V.height - top * boxHeight, width: boxWidth, height: boxHeight };
      } else {
        const boxHeight = H.spriteHeight;
        const boxWidth = (H.spriteHeight * CANVAS_RATIO * 9) / 16;
        box = { left: H.slotX[member.slot] - boxWidth / 2, top: H.headMargin - top * H.spriteHeight, width: boxWidth, height: boxHeight };
      }
      const speaking = member.speaker_index === item.speaking;
      return image(member.picture_url, `bp-sprite${speaking ? "" : " is-listening"}`, {
        left: pct(box.left), top: pct(box.top), width: pct(box.width), height: pct(box.height),
        transform: member.mirror ? "scaleX(-1)" : "",
      });
    });
  }

  /** The beat's sketch. options: {aspect: "16:9"|"9:16", hook, caption: {speaker, text}, label}. */
  function frame(item, options = {}) {
    const vertical = options.aspect === "9:16";
    const root = el("div", `bp-frame ${vertical ? "is-vertical" : "is-horizontal"}`, { role: "img" });
    root.setAttribute("aria-label", options.label || "Beat sketch");
    if (!item || item.error) {
      root.append(el("div", "bp-empty", { text: item?.error || "No sketch yet" }));
      return root;
    }
    const plate = item.scene?.preview_url || null;
    const illustration = item.kind === "insert" && item.illustration?.url ? item.illustration.url : null;
    const picture = el("div", "bp-picture");
    if (plate) picture.append(image(plate, "bp-cover"));
    if (illustration) picture.append(image(illustration, `bp-cover bp-illustration${item.illustration.status === "pending" ? " is-pending" : ""}`));
    if (!plate && !illustration) picture.append(el("div", "bp-empty", { text: item.scene ? `${item.scene.name}: no picture yet` : "No scene picture" }));
    if (vertical) {
      const ambient = el("div", "bp-ambient");
      if (plate) ambient.append(image(plate, "bp-cover", {}, true));
      root.append(ambient);
    }
    root.append(picture);
    if (!vertical) root.append(el("div", "bp-shade"));
    root.append(...sprites(item, vertical));
    if (options.caption?.text) {
      const band = el("div", "bp-caption");
      if (options.caption.speaker) band.append(el("span", "bp-caption-speaker", { text: options.caption.speaker }));
      band.append(el("span", "bp-caption-text", { text: options.caption.text }));
      if (vertical) Object.assign(band.style, { left: pct(V.captions.left / V.width), width: pct(V.captions.width / V.width),
        top: pct(V.captions.top / V.height), height: pct(V.captions.height / V.height) });
      root.append(band);
    }
    if (options.hook) {
      const hook = el("div", "bp-hook", { text: options.hook });
      hook.setAttribute("translate", "no");
      root.append(hook);
    }
    root.append(el("span", "bp-badge", { text: options.badge || "Sketch" }));
    return root;
  }

  /** Plain-language notes about what the render will (not) show for this beat. */
  function notes(item) {
    if (!item) return [];
    if (item.error) return [item.error];
    const out = [];
    if (!item.scene) out.push("No scene has a picture yet: make one in Activity Library → Scenes.");
    else if (!item.scene.preview_url) out.push(`${item.scene.name} has no picture yet; the video keeps the place before it.`);
    else if (item.scene_is_fallback) out.push(`No storyboard place has a picture: the video uses ${item.scene.name}.`);
    (item.characters || []).forEach((member) => {
      if (member.missing === "cast") out.push(`Speaker ${member.speaker_index + 1} has no character: choose one above.`);
      else if (member.missing === "sprites") out.push(`${member.name} has no talking sprites yet (Character Library).`);
    });
    if (item.kind === "insert") {
      const status = item.illustration?.status;
      if (status === "character" || status === "generic") out.push(`Illustration from the library, shown for up to ${item.illustration.max_seconds || 6} s.`);
      else if (status === "pending") out.push("Illustration waiting for approval: approve it above to use it.");
      else out.push("No illustration yet: the characters stay on screen. Draw or upload one above.");
    }
    return out;
  }

  window.BeatPreview = Object.freeze({ frame, notes });
})();
