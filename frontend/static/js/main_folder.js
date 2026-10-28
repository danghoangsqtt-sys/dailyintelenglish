/**
 * Phase 80 (owner 2026-10-26): the main save folder, shown wherever projects are made (Settings, Channel plan, Automation,
 * Shorts batch). Every new project gets <main folder>/<Topic>/<Series>/Ep NN - <title>/ under it; projects that already
 * have a folder keep it. Mount: any element with `data-main-folder` (optionally `data-compact`).
 */
(function () {
  const views = new Set();

  function el(tag, props = {}, children = []) {
    const node = document.createElement(tag);
    Object.entries(props).forEach(([key, value]) => {
      if (key === "dataset") Object.assign(node.dataset, value);
      else if (key.startsWith("aria-")) node.setAttribute(key, value);
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node[key] = value;
    });
    children.forEach((child) => child !== null && child !== undefined && node.append(child));
    return node;
  }

  function render(root, view, message = "", error = false) {
    const folder = view?.output_dir || "";
    const path = el("code", { className: "main-folder-path", textContent: folder || "Not chosen yet", title: folder });
    path.setAttribute("translate", "no");
    // Phase 83: with no folder chosen, the default folder is used (videos made by themselves never stay hidden in the app)
    const badge = folder && view?.is_default ? el("span", { className: "badge badge-status-draft", textContent: "Default" }) : null;
    const choose = el("button", { type: "button", className: "btn btn-primary btn-sm", textContent: folder ? "Change folder" : "Choose folder",
      onclick: () => pick(root, folder) });
    const clear = folder && !view?.is_default ? el("button", { type: "button", className: "btn btn-ghost btn-sm",
      textContent: view?.default_dir ? "Use the default folder" : "Stop using it", onclick: () => save(root, null) }) : null;
    const missing = view?.projects_without_folder || 0;
    const apply = folder && missing ? el("button", { type: "button", className: "btn btn-ghost btn-sm",
      textContent: `Give ${missing} project(s) without a folder their folder here`, onclick: () => applyAll(root) }) : null;
    root.replaceChildren(
      el("div", { className: "main-folder-head" }, [el("strong", { textContent: "Main save folder" }), path, badge]),
      el("p", { className: "main-folder-hint", textContent: folder
        ? "New projects are saved in their own folder here, by topic: Topic / Series / Ep NN - title. A project that already has a folder keeps it."
        : "Choose one folder: every new project (Step 1, Channel plan, Automation, Shorts batch) then gets its own folder there, by topic." }),
      el("div", { className: "main-folder-actions" }, [choose, clear, apply]),
      el("p", { className: `main-folder-status${error ? " is-error" : ""}`, role: "status", textContent: message }),
    );
  }

  async function load(root) {
    try {
      render(root, await Api.getMainFolder());
    } catch (error) {
      render(root, null, error.message || "The main folder could not load.", true);
    }
  }

  function refreshAll(view, message) {
    views.forEach((root) => render(root, view, message));
    document.dispatchEvent(new CustomEvent("main-folder:changed", { detail: view }));
  }

  async function pick(root, initial) {
    try {
      const chosen = await Api.chooseProjectFolder(initial || null);
      if (!chosen?.path) return;  // cancelled
      await save(root, chosen.path);
    } catch (error) {
      render(root, null, error.message || "The folder could not be chosen.", true);
      load(root);
    }
  }

  async function save(root, path) {
    try {
      const view = await Api.setMainFolder(path);
      refreshAll(view, path ? "Saved." : (view.output_dir ? "The default folder is used again." : "The main folder is no longer used for new projects."));
    } catch (error) {
      await load(root);
      root.querySelector(".main-folder-status").textContent = error.message || "The folder could not be saved.";
    }
  }

  async function applyAll(root) {
    try {
      const view = await Api.applyMainFolder();
      refreshAll(view, `${view.given} project(s) now have their folder.`);
    } catch (error) {
      root.querySelector(".main-folder-status").textContent = error.message || "That did not work.";
    }
  }

  function mountAll() {
    document.querySelectorAll("[data-main-folder]").forEach((root) => {
      if (views.has(root)) return;
      views.add(root);
      root.classList.add("main-folder");
      load(root);
    });
  }

  document.addEventListener("DOMContentLoaded", mountAll);
  window.MainFolder = Object.freeze({ mountAll, get: () => Api.getMainFolder() });
})();
