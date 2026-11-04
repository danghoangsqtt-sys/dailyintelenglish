/**
 * Phase 37 (D98-D101): Step 5 "Shorts & TikTok" -- the whole episode in vertical, and the AI's highlight clips (edit the
 * lines and the hook, approve, render), each with its 9:16 cover and the Shorts / TikTok texts to copy.
 * Shown once the horizontal video exists (the vertical renders reuse its audio, storyboard and cast).
 *
 * Phase 78 (Task 78.3): a clip not rendered yet shows a 9:16 sketch of its opening (BeatPreview, with the hook banner and
 * its first line); its length follows the edited lines (30-90 s); Approve keeps edited lines; the vertical episode plays
 * inline. A project whose main video is already a vertical Short has nothing to cut here and says so.
 */
(() => {
  const $ = (id) => document.getElementById(id);
  const projectId = new URLSearchParams(window.location.search).get("project_id");
  const MIN_SECONDS = 30;
  const MAX_SECONDS = 90;
  // a Short of these styles is itself a vertical video of a minute or less (backend/schemas/project.py SHORT_STYLES)
  const VERTICAL_MAIN_STYLES = ["news", "blur", "mistakes", "wordday", "top5", "quiz", "listen", "slowpod", "flashcards", "roots", "grammar", "whatis", "levelup", "picstory", "chat", "wyr"];
  let busy = false;
  let timestamps = [];
  let lineSpeakers = [];
  let sketches = null;  // the saved storyboard's per-beat sketches, loaded once per refresh

  function el(tag, props = {}, children = []) {
    const node = document.createElement(tag);
    Object.entries(props).forEach(([key, value]) => {
      if (key === "dataset") Object.assign(node.dataset, value);
      else if (key.startsWith("aria-") || key === "role") node.setAttribute(key, value);
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node[key] = value;
    });
    (Array.isArray(children) ? children : [children]).forEach((child) => child !== null && child !== undefined && node.append(child));
    return node;
  }

  /** The picture mode and caption style chosen above for the horizontal video. */
  function renderOptions() {
    const mode = document.querySelector("#visual-mode-group [aria-pressed='true']")?.dataset.visualMode || "podcast_sprites";
    const caption = document.querySelector("#caption-style-group [aria-pressed='true']")?.dataset.captionStyle || "outline";
    // the scene picture chosen for the horizontal video (Market, …) -- without it the vertical fell back to the first plate
    const scene = ["podcast_still", "podcast_sprites"].includes(mode) ? $("still-scene")?.value || null : null;
    return { visual_mode: mode, caption_style: caption, ...(scene ? { still_scene_id: scene } : {}) };
  }

  function copyButton(label, source) {
    return el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: `📋 ${label}`,
      onclick: async () => { try { await navigator.clipboard.writeText(source.value); } catch { source.select(); } } });
  }

  /** Seconds of lines `from`..`to` (0-based) from the measured audio, or null when they are not lines of the script. */
  function seconds(from, to) {
    if (!(from >= 0 && to >= from && to < timestamps.length)) return null;
    return Number(timestamps[to].end_sec) - Number(timestamps[from].start_sec);
  }

  function lengthText(from, to) {
    const value = seconds(from, to);
    if (value === null) return { text: "Lines out of range", ok: false };
    const ok = value >= MIN_SECONDS && value <= MAX_SECONDS;
    return { text: `${value.toFixed(1)} s${ok ? "" : " — a clip lasts 30–90 s"}`, ok };
  }

  function sketch(clip) {
    const beat = (sketches || []).find((item) => !item.error && item.line_from <= clip.line_from && clip.line_from <= item.line_to);
    const stamp = timestamps[clip.line_from];
    return BeatPreview.frame(beat || null, {
      aspect: "9:16", hook: clip.hook, badge: "Sketch — not rendered",
      caption: stamp ? { speaker: stamp.label || lineSpeakers[clip.line_from] || "", text: stamp.text || "" } : null,
      label: "Clip sketch",
    });
  }

  function clipCard(clip) {
    const from = el("input", { type: "number", min: 1, max: timestamps.length || undefined, value: clip.line_from + 1,
      "aria-label": "First line" });
    const to = el("input", { type: "number", min: 1, max: timestamps.length || undefined, value: clip.line_to + 1,
      "aria-label": "Last line" });
    const hook = el("input", { className: "hook", value: clip.hook, maxLength: 80, "aria-label": "Hook title" });
    hook.setAttribute("translate", "no");
    const length = el("span", { className: "short-length", "aria-live": "polite" });
    const status = el("span", { className: `status-chip short-status is-${clip.status}`, textContent: clip.status });
    const media = el("div", { className: "short-media" });

    function update() {
      const info = lengthText(Number(from.value) - 1, Number(to.value) - 1);
      length.textContent = info.text;
      length.classList.toggle("is-bad", !info.ok);
      if (!clip.video_url) media.replaceChildren(sketch({ ...clip, line_from: Number(from.value) - 1, hook: hook.value || clip.hook }));
    }
    [from, to, hook].forEach((input) => input.addEventListener("input", update));

    if (clip.video_url) {
      media.append(el("video", { src: `${clip.video_url}?t=${Date.now()}`, controls: true, preload: "metadata",
        poster: clip.cover_url ? `${clip.cover_url}?t=${Date.now()}` : "" }));
    }
    update();

    const lines = () => ({ line_from: Number(from.value) - 1, line_to: Number(to.value) - 1 });
    const actions = el("div", { className: "short-actions" }, [
      el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: "Save", disabled: busy,
        onclick: () => run(() => Api.updateShort(projectId, clip.id, { ...lines(), hook: hook.value }), "Saved.") }),
      clip.status === "proposed" ? el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: "Approve",
        dataset: { action: "approve" }, disabled: busy,
        // Phase 78 (V5): approving keeps the line numbers being edited (they were dropped unless saved first)
        onclick: () => run(() => Api.updateShort(projectId, clip.id, { ...lines(), status: "approved", hook: hook.value }),
          "Approved.") }) : null,
      clip.status !== "proposed" ? el("button", { type: "button", className: "btn btn-primary btn-sm", dataset: { action: "render" },
        textContent: clip.status === "rendered" ? "Render again" : "Render", disabled: busy,
        onclick: () => run(() => Api.renderShort(projectId, clip.id, renderOptions()), "Clip rendered.", "Rendering the clip…") }) : null,
      clip.video_url ? el("a", { className: "btn btn-ghost btn-sm", href: clip.video_url, download: "", textContent: "⬇ Video" }) : null,
      clip.cover_url ? el("a", { className: "btn btn-ghost btn-sm", href: clip.cover_url, download: "", textContent: "⬇ Cover" }) : null,
      el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: "Delete", disabled: busy,
        onclick: async () => (await ConfirmDialog.ask("Delete this clip?", { confirmLabel: "Delete", danger: true })) && run(() => Api.deleteShort(projectId, clip.id), "Clip deleted.") }),
    ]);
    const shortsTitle = el("textarea", { readOnly: true, value: clip.packages.shorts.title, rows: 1, "aria-label": "Shorts title" });
    const shortsText = el("textarea", { readOnly: true, value: clip.packages.shorts.description, "aria-label": "Shorts description" });
    const tiktok = el("textarea", { readOnly: true, value: clip.packages.tiktok.caption, "aria-label": "TikTok caption" });
    const texts = el("details", { className: "short-texts", open: clip.status === "rendered" }, [
      el("summary", { textContent: "Texts for YouTube Shorts and TikTok" }),
      // a <details> does not lay out its content as a grid itself: the body holds the rows
      el("div", { className: "short-texts-body" }, [
        el("strong", { textContent: "YouTube Shorts" }), shortsTitle, copyButton("Title", shortsTitle), shortsText,
        copyButton("Description", shortsText),
        el("strong", { textContent: "TikTok" }), tiktok, copyButton("Caption", tiktok),
      ]),
    ]);
    return el("div", { className: "card short-card", dataset: { clip: clip.id, status: clip.status } }, [
      media,
      el("div", { className: "short-body" }, [
        el("div", { className: "short-fields" }, [
          el("label", { className: "short-field" }, [el("span", { textContent: "First line" }), from]),
          el("label", { className: "short-field" }, [el("span", { textContent: "Last line" }), to]),
          el("label", { className: "short-field is-hook" }, [el("span", { textContent: "Hook title" }), hook]),
        ]),
        el("div", { className: "short-meta" }, [status, length]),
        clip.reason ? el("p", { className: "short-reason", textContent: clip.reason }) : null,
        actions,
        texts,
      ]),
    ]);
  }

  async function loadContext() {
    try {
      const audio = await Api.getAudioStatus(projectId);
      timestamps = audio?.timestamps || [];
      lineSpeakers = timestamps.map((stamp) => stamp.label || "");
    } catch {
      timestamps = [];
    }
    try {
      sketches = (await Api.previewStoryboard(projectId)).beats;
    } catch {
      sketches = [];
    }
  }

  async function refresh() {
    const clips = await Api.listShorts(projectId);
    if (clips.some((clip) => !clip.video_url) && sketches === null) await loadContext();
    $("shorts-list").replaceChildren(...(clips.length ? clips.map(clipCard)
      : [el("p", { className: "section-hint", textContent: "No clips yet: let the AI propose them." })]));
  }

  async function run(operation, done, working = "Working…") {
    if (busy) return;
    busy = true;
    document.querySelectorAll("#shorts-list button").forEach((button) => { button.disabled = true; });
    $("shorts-progress").textContent = working;
    try {
      await operation();
      $("shorts-progress").textContent = done;
    } catch (error) {
      $("shorts-progress").textContent = error.message || "That did not work.";
    } finally {
      busy = false;
      await refresh().catch(() => {});
    }
  }

  async function renderVertical() {
    const button = $("vertical-btn");
    button.disabled = true;
    $("vertical-progress").textContent = "Rendering the vertical episode… (a few minutes)";
    try {
      await Api.renderVertical(projectId, renderOptions());
      showVertical(true);
      $("vertical-progress").textContent = "Done.";
    } catch (error) {
      $("vertical-progress").textContent = error.message || "The vertical video could not be rendered.";
    } finally {
      button.disabled = false;
    }
  }

  /** Phase 78 (V7): the vertical episode plays here, not only as a download. */
  function showVertical(ready) {
    const link = $("download-mp4-vertical");
    const player = $("vertical-player");
    link.hidden = !ready;
    if (player) player.closest(".vertical-result").hidden = !ready;
    if (!ready) return;
    const url = `/api/projects/${projectId}/video/download?format=mp4_vertical&t=${Date.now()}`;
    link.href = url;
    if (player) player.src = url;
  }

  let wired = false;

  async function init() {
    if (!projectId || !$("shorts-section")) return;
    let job = null;
    try {
      job = await Api.getVideoStatus(projectId);
    } catch {
      job = null;
    }
    if (!job || job.status !== "complete") {
      // no video yet: the section stays hidden until the first render on this page finishes
      document.addEventListener("video:rendered", init, { once: true });
      return;
    }
    $("shorts-section").hidden = false;
    // Phase 78 (V8): a Short is already a vertical video of a minute or less: nothing to cut or re-render here
    const project = await Api.getProject(projectId).catch(() => null);
    if (VERTICAL_MAIN_STYLES.includes(project?.explainer_style)) {
      $("shorts-tools").hidden = true;
      $("shorts-vertical-main").hidden = false;
      return;
    }
    showVertical(Boolean(job.mp4_path_vertical));
    if (wired) return;
    wired = true;
    $("vertical-btn").addEventListener("click", renderVertical);
    $("shorts-propose-btn").addEventListener("click", () => run(async () => {
      await Api.proposeShorts(projectId, 3);
      sketches = null;  // the sketches follow the storyboard as it is now
    }, "Clips proposed: adjust, approve and render them.", "The AI is choosing the best moments…"));
    await refresh().catch(() => {});
  }

  document.addEventListener("DOMContentLoaded", init);
})();
