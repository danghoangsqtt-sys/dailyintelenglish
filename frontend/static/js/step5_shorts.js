/**
 * Phase 37 (D98-D101): Step 5 "Shorts & TikTok" -- the whole episode in vertical, and the AI's highlight clips (edit the
 * lines and the hook, approve, render), each with its 9:16 cover and the Shorts / TikTok texts to copy.
 * Shown once the horizontal video exists (the vertical renders reuse its audio, storyboard and cast).
 */
(() => {
  const $ = (id) => document.getElementById(id);
  const projectId = new URLSearchParams(window.location.search).get("project_id");
  let busy = false;

  function el(tag, props = {}, children = []) {
    const node = document.createElement(tag);
    Object.entries(props).forEach(([key, value]) => {
      if (key === "dataset") Object.assign(node.dataset, value);
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
    return { visual_mode: mode, caption_style: caption };
  }

  async function call(path, method = "GET", body) {
    const response = await fetch(`/api/projects/${projectId}${path}`, {
      method, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined,
    });
    const envelope = await response.json();
    if (!response.ok || envelope.success === false) throw new Error(envelope.error || "Request failed");
    return envelope.data;
  }

  function copyButton(label, source) {
    return el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: `📋 ${label}`,
      onclick: async () => { try { await navigator.clipboard.writeText(source.value); } catch { source.select(); } } });
  }

  function clipCard(clip) {
    const from = el("input", { type: "number", min: 1, value: clip.line_from + 1, "aria-label": "First line" });
    const to = el("input", { type: "number", min: 1, value: clip.line_to + 1, "aria-label": "Last line" });
    const hook = el("input", { className: "hook", value: clip.hook, maxLength: 80, "aria-label": "Hook title" });
    const media = clip.video_url
      ? el("video", { src: `${clip.video_url}?t=${Date.now()}`, controls: true, poster: clip.cover_url || "" })
      : el("div", { className: "short-empty", textContent: clip.status === "approved" ? "Approved — render it" : "Not rendered yet" });
    const actions = el("div", { className: "short-actions" }, [
      el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: "Save", disabled: busy,
        onclick: () => run(() => call(`/shorts/${clip.id}`, "PATCH",
          { line_from: Number(from.value) - 1, line_to: Number(to.value) - 1, hook: hook.value }), "Saved.") }),
      clip.status === "proposed" ? el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: "Approve",
        dataset: { action: "approve" }, disabled: busy,
        onclick: () => run(() => call(`/shorts/${clip.id}`, "PATCH", { status: "approved", hook: hook.value }), "Approved.") }) : null,
      clip.status !== "proposed" ? el("button", { type: "button", className: "btn btn-primary btn-sm", dataset: { action: "render" },
        textContent: clip.status === "rendered" ? "Render again" : "Render", disabled: busy,
        onclick: () => run(() => call(`/shorts/${clip.id}/render`, "POST", renderOptions()), "Clip rendered.", "Rendering the clip…") }) : null,
      clip.video_url ? el("a", { className: "btn btn-ghost btn-sm", href: clip.video_url, download: "", textContent: "⬇ Video" }) : null,
      clip.cover_url ? el("a", { className: "btn btn-ghost btn-sm", href: clip.cover_url, download: "", textContent: "⬇ Cover" }) : null,
      el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: "Delete", disabled: busy,
        onclick: () => confirm("Delete this clip?") && run(() => call(`/shorts/${clip.id}`, "DELETE"), "Clip deleted.") }),
    ]);
    const shortsTitle = el("textarea", { readOnly: true, value: clip.packages.shorts.title, rows: 1, "aria-label": "Shorts title" });
    const shortsText = el("textarea", { readOnly: true, value: clip.packages.shorts.description, "aria-label": "Shorts description" });
    const tiktok = el("textarea", { readOnly: true, value: clip.packages.tiktok.caption, "aria-label": "TikTok caption" });
    return el("div", { className: "card short-card", dataset: { clip: clip.id, status: clip.status } }, [
      media,
      el("div", {}, [
        el("div", { className: "short-fields" }, ["Lines", from, "to", to, hook,
          el("span", { className: "status-chip", textContent: `${clip.status} · ${clip.seconds ?? "?"} s` })]),
        clip.reason ? el("p", { className: "section-hint", textContent: clip.reason }) : null,
        actions,
        el("div", { className: "short-texts" }, [
          el("strong", { textContent: "YouTube Shorts" }), shortsTitle, copyButton("Title", shortsTitle), shortsText,
          copyButton("Description", shortsText),
          el("strong", { textContent: "TikTok" }), tiktok, copyButton("Caption", tiktok),
        ]),
      ]),
    ]);
  }

  async function refresh() {
    const clips = await call("/shorts");
    $("shorts-list").replaceChildren(...(clips.length ? clips.map(clipCard)
      : [el("p", { className: "section-hint", textContent: "No clips yet: let the AI propose them." })]));
  }

  async function run(operation, done, working = "Working…") {
    if (busy) return;
    busy = true;
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
      await call("/video/vertical", "POST", renderOptions());
      showVerticalLink(true);
      $("vertical-progress").textContent = "Done.";
    } catch (error) {
      $("vertical-progress").textContent = error.message || "The vertical video could not be rendered.";
    } finally {
      button.disabled = false;
    }
  }

  function showVerticalLink(ready) {
    const link = $("download-mp4-vertical");
    link.hidden = !ready;
    if (ready) link.href = `/api/projects/${projectId}/video/download?format=mp4_vertical&t=${Date.now()}`;
  }

  async function init() {
    if (!projectId || !$("shorts-section")) return;
    let job = null;
    try {
      job = await call("/video/status");
    } catch {
      job = null;
    }
    if (!job || job.status !== "complete") {
      // no video yet: the section stays hidden until the first render on this page finishes
      document.addEventListener("video:rendered", init, { once: true });
      return;
    }
    $("shorts-section").hidden = false;
    showVerticalLink(Boolean(job.mp4_path_vertical));
    $("vertical-btn").addEventListener("click", renderVertical);
    $("shorts-propose-btn").addEventListener("click", () => run(() => call("/shorts/propose", "POST", { count: 3 }),
      "Clips proposed: adjust, approve and render them.", "The AI is choosing the best moments…"));
    await refresh().catch(() => {});
  }

  document.addEventListener("DOMContentLoaded", init);
})();
