/** Shared scene editor, preview and generation workflow, hosted in Activity Library. */
(() => {
  const state = {
    scenes: [], options: null, health: null,
    selectedSceneId: null, editingSceneId: null, sceneFilter: "all", busy: false, progress: null,
    search: "", plateFilter: "all", archiveFilter: "active", ready: false,
    preparing: false, copying: false, draftVersion: 0, requestForPrompt: "",
  };

  const $ = (id) => document.getElementById(id);
  let refreshVersion = 0;
  // Keep identical to recipes.SCENE_COMPOSITION; browser coverage checks the shared contract.
  const SCENE_COMPOSITION = "Landscape 16:9 background plate, eye-level wide view with believable perspective and open foreground space "
    + "for characters added later. The place is completely empty: no people, faces, human figures or silhouettes. "
    + "No text, letters, signs, logos or watermarks.";
  const sceneFields = ["name", "place", "staging", "category", "time_of_day", "source_request", "image_prompt"];
  const working = () => state.busy || state.preparing || state.copying;

  function canonicalPrompt(value) {
    const prompt = value.trim();
    return !prompt || prompt.endsWith(SCENE_COMPOSITION) ? prompt : `${prompt}\n\n${SCENE_COMPOSITION}`;
  }

  function editorValues() {
    const form = $("scene-form");
    return Object.fromEntries(sceneFields.map((key) => [key, form.elements[key].value]));
  }

  function promptChanged(scene) {
    const form = $("scene-form");
    return ["place", "time_of_day", "image_prompt"].some((key) => form.elements[key].value !== (scene[key] || ""));
  }

  function useSavedScene(scene) {
    if (working()) return false;
    const values = editorValues();
    if (state.editingSceneId === scene.id && sceneFields.some((key) => values[key] !== (scene[key] || ""))) {
      message("Save your scene changes before generating or uploading its background.", true);
      return false;
    }
    return true;
  }

  function renderEditorControls() {
    $("scene-form").querySelectorAll("input, select, textarea, button").forEach((field) => {
      field.disabled = (field.tagName === "BUTTON" ? working() : state.busy) || !state.ready;
    });
    $("prepare-scene-prompt").disabled = working() || !state.ready || !$("scene-source-request").value.trim();
    $("copy-scene-prompt").disabled = working() || !state.ready
      || (!$("scene-image-prompt").value.trim() && !state.editingSceneId);
    $("scene-prompt-status").textContent = state.preparing ? "Preparing image prompt…" : "";
    $("scene-request-stale").hidden = !$("scene-image-prompt").value.trim()
      || $("scene-source-request").value.trim() === state.requestForPrompt;
  }

  async function preparePrompt() {
    const brief = $("scene-source-request").value.trim();
    if (working() || !state.ready || !brief) return;
    if (!$("scene-source-request").reportValidity()) return;
    const version = state.draftVersion;
    state.preparing = true;
    renderScenes();
    message("");
    try {
      const draft = await Api.prepareScenePrompt(brief);
      if (version !== state.draftVersion) {
        message("Your draft changed while preparing. Your edits were kept; prepare again when ready.");
        return;
      }
      if (!draft?.image_prompt?.trim() || sceneFields.some((key) => typeof draft[key] !== "string")) {
        throw new Error("The text AI returned an incomplete scene draft. Please try again.");
      }
      const prompt = canonicalPrompt(draft.image_prompt);
      if (prompt.length > 6000) throw new Error("The image prompt is too long. Keep it within 6000 characters including background constraints.");
      const form = $("scene-form");
      sceneFields.forEach((key) => { form.elements[key].value = key === "image_prompt" ? prompt : draft[key]; });
      state.requestForPrompt = brief;
      state.draftVersion += 1;
      updateStaleWarning();
      message("Image prompt prepared. Review the details, then save your scene.");
    } catch (error) {
      message(error.message || "Could not prepare the image prompt. Check your text AI settings and try again.", true);
    } finally {
      state.preparing = false;
      renderScenes();
    }
  }

  async function writeClipboard(prompt) {
    try {
      await navigator.clipboard.writeText(prompt);
      return true;
    } catch { /* Older browsers and denied clipboard permissions can use a selected temporary field. */ }
    const previous = document.activeElement;
    const field = document.createElement("textarea");
    field.value = prompt;
    field.readOnly = true;
    field.style.cssText = "position:fixed;left:0;top:0;opacity:0";
    document.body.append(field);
    try {
      field.select();
      return document.execCommand("copy");
    } catch {
      return false;
    } finally {
      field.remove();
      previous?.focus({ preventScroll: true });
    }
  }

  async function copyPrompt() {
    if (working() || !state.ready) return;
    const version = state.draftVersion;
    const original = state.scenes.find((scene) => scene.id === state.editingSceneId);
    const useEffective = original && !promptChanged(original);
    state.copying = true;
    renderScenes();
    try {
      const prompt = useEffective ? (await Api.getScenePrompt(original.id)).prompt : canonicalPrompt($("scene-image-prompt").value);
      if (version !== state.draftVersion) {
        message("Your draft changed while copying. Copy again to use your latest edits.");
        return;
      }
      if (!prompt) throw new Error("Prepare or enter an image prompt first.");
      if (prompt.length > 6000) throw new Error("The image prompt is too long. Keep it within 6000 characters including background constraints.");
      if (!useEffective) {
        $("scene-image-prompt").value = prompt;
        state.draftVersion += 1;
        updateStaleWarning();
      }
      const copyVersion = state.draftVersion;
      const copied = await writeClipboard(prompt);
      if (copyVersion !== state.draftVersion) {
        message("Your draft changed while copying. Copy again to use your latest edits.");
        return;
      }
      if (!copied) {
        $("scene-image-prompt").value = prompt;
        state.draftVersion += 1;
        $("scene-image-prompt").focus();
        $("scene-image-prompt").select();
        throw new Error("Couldn't copy to clipboard — please select and copy the text manually.");
      }
      message("Image prompt copied.");
    } catch (error) {
      message(error.message || "Could not copy the image prompt.", true);
    } finally {
      state.copying = false;
      renderScenes();
    }
  }

  async function uploadBackground(scene, file) {
    if (!file || !useSavedScene(scene) || scene.archived_at) return;
    const body = new FormData();
    body.append("file", file);
    await act(() => Api.uploadSceneBackground(scene.id, body), "Scene background uploaded.");
  }

  function message(text, error = false) {
    const box = $("library-message");
    box.hidden = !text;
    box.classList.toggle("error", error);
    box.setAttribute("role", error ? "alert" : "status");
    box.textContent = text || "";
  }

  function canGenerate() {
    return Boolean(state.health?.enabled && state.health?.venv_image_present
      && document.documentElement.dataset.localImageAi !== "off");
  }

  function generationHint() {
    if (document.documentElement.dataset.localImageAi === "off") return "AI pictures are hidden on this computer.";
    if (!state.health?.enabled) return "AI visuals generation is disabled in settings.";
    if (!state.health?.venv_image_present) return "The local image environment is missing.";
    return "";
  }

  function setGenerateButton(button, allowed) {
    button.disabled = working() || !canGenerate() || !allowed;
    button.title = generationHint() || "Generate this saved scene's background with local Qwen.";
  }

  function optionList(select, values) {
    select.replaceChildren();
    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.append(option);
    });
  }

  function fillOptions() {
    const sceneForm = $("scene-form");
    optionList(sceneForm.elements.category, state.options.scene_categories || ["other"]);
    optionList(sceneForm.elements.time_of_day, state.options.times_of_day || ["day"]);
    sceneForm.elements.category.value = "other";
    sceneForm.elements.time_of_day.value = "day";
    // Form.reset() should return to these choices, rather than the API's first option.
    for (const field of [sceneForm.elements.category, sceneForm.elements.time_of_day]) {
      [...field.options].forEach((option) => { option.defaultSelected = option.value === field.value; });
    }
  }

  function matchesArchive(scene) {
    return state.archiveFilter === "all" || Boolean(scene.archived_at) === (state.archiveFilter === "archived");
  }

  function renderSceneFilters() {
    const bar = $("scene-filters");
    bar.replaceChildren();
    const present = [...new Set([...state.scenes.map((scene) => scene.category || "other"),
      ...(state.options?.scene_categories || [])])].sort();
    ["all", ...present].forEach((category) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "btn btn-ghost btn-sm";
      chip.dataset.category = category;
      const count = state.scenes.filter((scene) => matchesArchive(scene)
        && (category === "all" || (scene.category || "other") === category)).length;
      chip.textContent = `${category === "all" ? "All" : category} (${count})`;
      chip.setAttribute("aria-pressed", String(state.sceneFilter === category));
      chip.addEventListener("click", () => { state.sceneFilter = category; renderScenes(); });
      bar.append(chip);
    });
  }

  function updateStaleWarning() {
    const original = state.scenes.find((scene) => scene.id === state.editingSceneId);
    $("scene-stale-warning").hidden = !(original && original.preview_url && (
      promptChanged(original)));
  }

  function sceneMeta(scene) {
    const used = scene.used_count || 0;
    return `${scene.category || "other"} · ${scene.time_of_day || "day"} · ${scene.staging}`
      + ` · Used in ${used} project${used === 1 ? "" : "s"}${scene.archived_at ? " · Archived" : ""}`;
  }

  function renderSceneDetail() {
    const scene = state.scenes.find((item) => item.id === state.selectedSceneId) || null;
    $("scene-detail").hidden = !scene;
    if (!scene) return;
    const plate = $("scene-detail-plate");
    plate.hidden = !scene.preview_url;
    $("scene-detail-empty").hidden = Boolean(scene.preview_url);
    if (scene.preview_url) {
      plate.src = scene.preview_url;
      plate.alt = `${scene.name} plate`;
    }
    $("scene-detail-name").textContent = scene.name;
    $("scene-detail-place").textContent = scene.place;
    $("scene-detail-meta").textContent = sceneMeta(scene);
  }

  function selectScene(scene) {
    state.selectedSceneId = scene.id;
    document.querySelectorAll("#scene-grid .library-scene").forEach((card) =>
      card.setAttribute("aria-current", String(card.dataset.sceneId === scene.id)));
    renderSceneDetail();
  }

  function renderScenes() {
    renderSceneFilters();
    const grid = $("scene-grid");
    grid.replaceChildren();
    const visible = state.scenes.filter((scene) => matchesArchive(scene)
      && (state.sceneFilter === "all" || (scene.category || "other") === state.sceneFilter)
      && (state.plateFilter === "all" || Boolean(scene.preview_url) === (state.plateFilter === "ready"))
      && `${scene.name} ${scene.place} ${scene.category}`.toLocaleLowerCase().includes(state.search));
    $("scene-count").textContent = `${visible.length} of ${state.scenes.length} scenes`;
    $("scene-empty").hidden = visible.length > 0 || !state.ready;
    $("tab-scenes-count").textContent = String(state.scenes.filter((scene) => !scene.archived_at).length);
    renderEditorControls();
    $("new-scene").disabled = working() || !state.ready;
    visible.forEach((scene) => {
      const card = document.createElement("article");
      card.className = "card library-scene";
      card.classList.toggle("is-archived", Boolean(scene.archived_at));
      card.dataset.sceneId = scene.id;
      card.tabIndex = 0;
      card.addEventListener("keydown", (event) => {
        if (event.target === card && ["Enter", " "].includes(event.key)) {
          event.preventDefault(); selectScene(scene);
        }
      });
      card.setAttribute("aria-current", String(scene.id === state.selectedSceneId));
      card.addEventListener("click", (event) => {
        if (!event.target.closest("button, input, label")) selectScene(scene);
      });
      if (scene.preview_url) {
        const image = document.createElement("img");
        image.src = scene.preview_url;
        image.alt = `${scene.name} plate`;
        card.append(image);
      } else {
        const placeholder = document.createElement("div");
        placeholder.className = "scene-placeholder";
        placeholder.textContent = "No plate yet \u2014 generated on first use";
        card.append(placeholder);
      }
      const title = document.createElement("h3");
      title.textContent = scene.name;
      if (scene.is_builtin) {
        const badge = document.createElement("span");
        badge.className = "library-badge";
        badge.textContent = "Built-in";
        title.append(" ", badge);
      }
      if (scene.archived_at) {
        const badge = document.createElement("span");
        badge.className = "library-badge";
        badge.textContent = "Archived";
        title.append(" ", badge);
      }
      const place = document.createElement("p");
      place.textContent = scene.place;
      const meta = document.createElement("p");
      meta.className = "scene-meta";
      meta.textContent = sceneMeta(scene);
      const actions = document.createElement("div");
      actions.className = "library-actions";
      const edit = document.createElement("button");
      edit.type = "button";
      edit.className = "btn btn-ghost btn-sm";
      edit.textContent = "Edit";
      edit.disabled = working();
      edit.addEventListener("click", () => {
        if (working()) return;
        selectScene(scene);
        state.editingSceneId = scene.id;
        $("scene-editor-title").textContent = `Edit ${scene.name}`;
        const form = $("scene-form");
        form.elements.name.value = scene.name;
        form.elements.place.value = scene.place;
        form.elements.staging.value = scene.staging;
        form.elements.category.value = scene.category || "other";
        form.elements.time_of_day.value = scene.time_of_day || "day";
        form.elements.source_request.value = scene.source_request || "";
        form.elements.image_prompt.value = scene.image_prompt || "";
        state.requestForPrompt = (scene.source_request || "").trim();
        state.draftVersion += 1;
        renderEditorControls();
        updateStaleWarning();
        $("save-scene").textContent = "Save scene";
        $("cancel-scene-edit").hidden = false;
        form.scrollIntoView({ behavior: "smooth", block: "center" });
      });
      const preview = document.createElement("button");
      preview.type = "button";
      preview.className = "btn btn-ghost btn-sm needs-local-gpu";  // Phase 71: drawn with Qwen on this computer
      preview.textContent = scene.preview_url ? "↻ Plate" : "Make plate";
      setGenerateButton(preview, !scene.archived_at);
      preview.addEventListener("click", () => {
        if (useSavedScene(scene)) startJob(() => Api.generateScenePreview(scene.id));
      });
      const duplicate = document.createElement("button");
      duplicate.type = "button";
      duplicate.className = "btn btn-ghost btn-sm";
      duplicate.textContent = "Duplicate";
      duplicate.disabled = working();
      duplicate.addEventListener("click", () => act(() => Api.duplicateScene(scene.id), "Scene duplicated."));
      actions.append(edit, preview, duplicate);
      const file = document.createElement("input");
      file.type = "file";
      file.accept = "image/png,image/jpeg,image/webp";
      file.className = "scene-background-file";
      file.setAttribute("aria-label", `Upload background for ${scene.name}`);
      file.hidden = true;
      file.disabled = working() || Boolean(scene.archived_at);
      const upload = document.createElement("button");
      upload.type = "button";
      upload.className = "btn btn-ghost btn-sm";
      upload.textContent = "Upload image";
      upload.title = "Upload a PNG, JPEG or WebP background made with an outside AI.";
      upload.disabled = file.disabled;
      upload.addEventListener("click", () => { if (useSavedScene(scene)) file.click(); });
      file.addEventListener("change", () => {
        const selected = file.files[0];
        file.value = "";
        uploadBackground(scene, selected);
      });
      actions.append(upload, file);
      if (!scene.is_builtin) {
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "btn btn-ghost btn-sm";
        remove.textContent = scene.archived_at ? "Restore" : "Archive";
        remove.disabled = working();
        remove.addEventListener("click", async () => {
          if (scene.archived_at) {
            await act(() => Api.restoreScene(scene.id), "Scene restored.");
          } else if (await ConfirmDialog.ask(`Archive scene "${scene.name}"? Existing videos and storyboard choices are kept.`, { confirmLabel: "Archive" })) {
            if (await act(() => Api.archiveScene(scene.id), "Scene archived.")) {
              if (state.editingSceneId === scene.id) resetSceneForm();
            }
          }
        });
        actions.append(remove);
      }
      card.append(title, place, meta, actions);
      grid.append(card);
    });
    renderSceneDetail();
  }

  async function refresh() {
    const version = ++refreshVersion;
    const scenes = await Api.listScenes({ include_archived: true });
    if (version !== refreshVersion) return;
    state.scenes = scenes;
    state.ready = true;
    renderScenes();
  }

  async function act(operation, success) {
    if (working() || !state.ready) return false;
    refreshVersion += 1;
    try {
      state.busy = true;
      renderScenes();
      await operation();
      await refresh();
      message(success);
      return true;
    } catch (error) {
      message(error.message || "The library action failed.", true);
      return false;
    } finally {
      state.busy = false;
      renderScenes();
    }
  }

  async function startJob(operation) {
    if (working() || !state.ready || !canGenerate()) return;
    state.busy = true;
    renderScenes();
    message("");
    try {
      const job = await operation();
      const container = $("library-progress");
      state.progress?.destroy();
      state.progress = GenerationStatus.mount({
        element: container, baselineSec: 120, startedAtIso: job.created_at,
      });
      const cancel = $("cancel-library-job");
      cancel.hidden = false;
      cancel.disabled = false;
      cancel.onclick = async () => {
        cancel.disabled = true;
        try {
          await Api.cancelImageJob(job.id);
          message("Cancellation requested.");
        } catch (error) {
          cancel.disabled = false;
          message(error.message || "Could not cancel the job.", true);
        }
      };
      let current = job;
      while (!["complete", "error", "cancelled"].includes(current.status)) {
        state.progress.setProgress({ stageLabel: current.stage || "Queued", progressPercent: current.progress });
        await new Promise((resolve) => setTimeout(resolve, 500));
        current = await Api.getImageJob(job.id);
      }
      state.progress.setProgress({ stageLabel: current.stage, progressPercent: current.progress, done: true });
      if (current.status === "error") throw new Error(current.error || "Image generation failed.");
      await refresh();
      message(current.status === "cancelled" ? "Generation cancelled. Finished images were kept." : "Images are ready for review.");
    } catch (error) {
      message(error.message || "Image generation failed.", true);
    } finally {
      state.progress?.destroy();
      $("library-progress").replaceChildren();
      $("cancel-library-job").hidden = true;
      $("cancel-library-job").onclick = null;
      state.busy = false;
      renderScenes();
    }
  }

  function resetSceneForm() {
    state.draftVersion += 1;
    state.requestForPrompt = "";
    state.editingSceneId = null;
    $("scene-form").reset();
    $("scene-stale-warning").hidden = true;
    $("scene-editor-title").textContent = "New scene";
    $("save-scene").textContent = "Add scene";
    $("cancel-scene-edit").hidden = true;
    renderEditorControls();
  }

  function setupEvents() {
    $("new-scene").addEventListener("click", () => {
      if (working()) return;
      resetSceneForm();
      state.selectedSceneId = null;
      renderScenes();
      $("scene-form").elements.source_request.focus();
    });
    $("scene-search").addEventListener("input", (event) => {
      state.search = event.target.value.trim().toLocaleLowerCase(); renderScenes();
    });
    $("scene-plate-filter").addEventListener("change", (event) => {
      state.plateFilter = event.target.value; renderScenes();
    });
    $("scene-archive-filter").addEventListener("change", (event) => {
      state.archiveFilter = event.target.value; renderScenes();
    });
    $("scene-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      if (working() || !state.ready) return;
      const body = Object.fromEntries(new FormData(event.currentTarget));
      body.image_prompt = canonicalPrompt(body.image_prompt);
      if (body.image_prompt.length > 6000) {
        message("The image prompt is too long. Keep it within 6000 characters including background constraints.", true);
        return;
      }
      const version = state.draftVersion;
      const editing = state.editingSceneId;
      const original = state.scenes.find((scene) => scene.id === editing);
      const patch = original
        ? Object.fromEntries(Object.entries(body).filter(([key, value]) => value !== (original[key] ?? "")))
        : body;
      const saved = await act(() => editing ? Api.updateScene(editing, patch) : Api.createScene(body),
        editing ? "Scene saved." : "Scene added.");
      if (saved && version === state.draftVersion) resetSceneForm();
    });
    $("cancel-scene-edit").addEventListener("click", () => { if (!working()) resetSceneForm(); });
    $("scene-form").addEventListener("input", () => {
      state.draftVersion += 1;
      updateStaleWarning();
      renderEditorControls();
    });
    $("scene-form").addEventListener("change", () => {
      state.draftVersion += 1;
      updateStaleWarning();
      renderEditorControls();
    });
    $("prepare-scene-prompt").addEventListener("click", preparePrompt);
    $("copy-scene-prompt").addEventListener("click", copyPrompt);
    const reload = () => {
      if (state.ready && !working()) refresh().catch((error) => message(error.message || "The library could not load.", true));
    };
    window.addEventListener("dbe:scenes-changed", reload);
    window.addEventListener("dbe:scenes-open", reload);
    window.addEventListener("dbe:capabilities", () => { if (state.ready) renderScenes(); });
  }

  document.addEventListener("DOMContentLoaded", async () => {
    if (!$("scene-form")) return;
    setupEvents();
    renderScenes();
    try {
      const [options, health] = await Promise.allSettled([Api.getVisualsOptions(), Api.getVisualsHealth()]);
      state.options = options.status === "fulfilled" ? options.value : {};
      state.health = health.status === "fulfilled" ? health.value : null;
      fillOptions();
      await refresh();
    } catch (error) {
      message(error.message || "The library could not load.", true);
    }
  });
})();
