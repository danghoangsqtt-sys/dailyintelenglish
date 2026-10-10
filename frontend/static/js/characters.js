/** Global Character and Scene Library. All server calls go through Api. */
(() => {
  const SHEET_LABELS = {
    full_body: "Full body",
    portrait_calm: "Calm",
    portrait_smile: "Smile",
    portrait_surprised: "Surprised",
  };
  const state = {
    characters: [], scenes: [], options: null, health: null,
    selectedId: null, selectedSceneId: null, editingSceneId: null, sceneFilter: "all", busy: false, progress: null,
    filters: { q: "", state: "active", readiness: "" }, wizardStep: 0, wizardCharacter: null,
    saveTimer: null, savePending: null, saveError: null, saving: false,
    assetSlots: null, assetGroup: "core", bulkFiles: [],
  };

  const $ = (id) => document.getElementById(id);

  function message(text, error = false) {
    const box = $("library-message");
    box.hidden = !text;
    box.classList.toggle("error", error);
    box.setAttribute("role", error ? "alert" : "status");
    box.textContent = text || "";
  }

  function canGenerate() {
    return Boolean(state.health?.enabled && state.health?.venv_image_present);
  }

  function generationHint() {
    if (!state.health?.enabled) return "AI visuals generation is disabled in settings.";
    if (!state.health?.venv_image_present) return "The local image environment is missing.";
    return "";
  }

  function setGenerateButton(button, allowed) {
    button.disabled = state.busy || !canGenerate() || !allowed;
    button.title = generationHint() || (allowed ? "" : "Complete the previous character step first.");
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
    const form = $("character-wizard-form");
    const mapping = {
      gender: state.options.genders,
      age_group: state.options.age_groups,
      top_color: state.options.colors,
      top_item: state.options.tops,
      bottom_color: state.options.colors,
      bottom_item: state.options.bottoms,
    };
    Object.entries(mapping).forEach(([name, values]) => optionList(form.elements[name], values));
    form.elements.ethnicity.value = "Russian";
    form.elements.hair.value = "dark hair";
    form.elements.eyes.value = "brown eyes";
    form.elements.bottom_color.value = "navy blue";
    const sceneForm = $("scene-form");
    optionList(sceneForm.elements.category, state.options.scene_categories || ["other"]);
    optionList(sceneForm.elements.time_of_day, state.options.times_of_day || ["day"]);
    sceneForm.elements.category.value = "other";
    sceneForm.elements.time_of_day.value = "day";
  }

  function selectedCharacter() {
    return state.characters.find((character) => character.id === state.selectedId) || null;
  }

  function portrait(character) {
    const asset = (character?.assets || []).find((item) =>
      ["face", "portrait_calm"].includes(item.slot_key || item.kind) && (item.is_current ?? 1));
    return character?.face_url || character?.body_url || asset?.url || "";
  }

  const READINESS_LABELS = {
    profile: "Profile", voice: "Voice", visual: "Core visuals",
    talking_starter: "Talking starter", full_expressions: "Expressions", full_sprite_pack: "Full sprites",
  };

  function pill(label, item) {
    const node = document.createElement("span");
    node.className = `readiness-pill ${item?.state || "missing"}`;
    node.textContent = `${item?.state === "ready" ? "Ready" : "Needs work"} · ${label}`;
    return node;
  }

  function assetCard(asset, label, fullBody = false) {
    const card = document.createElement("article");
    card.className = `library-asset${fullBody ? " full-body" : ""}`;
    const image = document.createElement("img");
    image.src = asset.url;
    image.alt = `${label} portrait`;
    const title = document.createElement("strong");
    title.textContent = label;
    card.append(image, title);
    return card;
  }

  function renderCandidates(character) {
    const grid = $("candidate-grid");
    grid.replaceChildren();
    (character.assets || []).filter((asset) => asset.kind === "candidate").forEach((asset, index) => {
      const card = assetCard(asset, `Candidate ${index + 1}`);
      const pick = document.createElement("button");
      pick.className = "btn btn-ghost btn-sm";
      pick.type = "button";
      pick.textContent = character.reference_asset_id === asset.id ? "Selected" : "Choose this portrait";
      pick.disabled = state.busy || character.status === "locked";
      pick.addEventListener("click", () => act(
        () => Api.pickCharacterReference(character.id, asset.id), "Portrait selected."));
      card.append(pick);
      grid.append(card);
    });
  }

  function renderSheet(character) {
    const grid = $("sheet-grid");
    grid.replaceChildren();
    Object.entries(SHEET_LABELS).forEach(([kind, label]) => {
      const asset = (character.assets || []).find((item) => item.kind === kind);
      if (!asset) return;
      const card = assetCard(asset, label, kind === "full_body");
      const actions = document.createElement("div");
      actions.className = "library-actions";
      const approve = document.createElement("button");
      approve.type = "button";
      approve.className = "btn btn-ghost btn-sm";
      approve.textContent = asset.approved ? "Approved" : "Approve";
      approve.disabled = state.busy || character.status === "locked";
      approve.addEventListener("click", () => act(
        () => Api.approveCharacterAsset(character.id, asset.id, !asset.approved),
        asset.approved ? "Approval removed." : "Sheet asset approved."));
      const regenerate = document.createElement("button");
      regenerate.type = "button";
      regenerate.className = "btn btn-ghost btn-sm";
      regenerate.textContent = "Regenerate";
      setGenerateButton(regenerate, character.status !== "locked");
      regenerate.addEventListener("click", () => startJob(() => Api.generateCharacterSheet(character.id, kind)));
      actions.append(approve, regenerate);
      card.append(actions);
      grid.append(card);
    });
  }

  function renderCharacterList() {
    const list = $("character-list");
    list.replaceChildren();
    $("character-count").textContent = `${state.characters.length} profile${state.characters.length === 1 ? "" : "s"}`;
    if (!state.characters.length) {
      const empty = document.createElement("div");
      empty.className = "profile-empty card";
      empty.innerHTML = "<h2>No matching profiles</h2><p>Change the filters or create a new character.</p>";
      list.append(empty);
      return;
    }
    state.characters.forEach((character) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "profile-card";
      card.setAttribute("aria-current", String(character.id === state.selectedId));
      card.setAttribute("aria-label", `${character.name}, ${character.role || "profile"}`);
      card.addEventListener("click", () => { state.selectedId = character.id; renderCharacters(); });
      const art = document.createElement("span");
      art.className = "profile-card-art";
      const picture = portrait(character);
      if (picture) {
        const image = document.createElement("img");
        image.src = picture;
        image.alt = "";
        art.append(image);
      } else art.textContent = "Portrait needed";
      const copy = document.createElement("span");
      copy.className = "profile-card-copy";
      const name = document.createElement("strong");
      name.textContent = character.name;
      const role = document.createElement("small");
      role.textContent = character.role || "Role not set";
      const badges = document.createElement("span");
      badges.className = "profile-mini-badges";
      badges.append(pill("Profile", character.readiness?.profile), pill("Video", character.readiness?.visual),
        pill("Talk", character.readiness?.talking_starter));
      copy.append(name, role, badges);
      card.append(art, copy);
      list.append(card);
    });
  }

  function missingItems(character) {
    const result = [];
    Object.entries(READINESS_LABELS).forEach(([key, label]) => {
      const item = character.readiness?.[key];
      if (item?.state === "ready") return;
      result.push(`${label}: ${item?.missing?.length ? item.missing.join(", ") : "setup needed"}`);
    });
    return result;
  }

  function renderCharacterDetail() {
    const character = selectedCharacter();
    $("profile-empty").hidden = Boolean(character);
    $("profile-content").hidden = !character;
    if (!character) return;
    const hero = $("character-hero");
    hero.replaceChildren();
    const picture = portrait(character);
    if (picture) {
      const image = document.createElement("img");
      image.src = picture;
      image.alt = `${character.name} portrait`;
      hero.append(image);
    } else {
      const blank = document.createElement("div");
      blank.className = "profile-hero-placeholder";
      blank.textContent = "Portrait";
      hero.append(blank);
    }
    const copy = document.createElement("div");
    copy.innerHTML = `<h2></h2><p></p><p></p>`;
    copy.querySelector("h2").textContent = character.name;
    copy.querySelectorAll("p")[0].textContent =
      [character.role, character.lifecycle === "archived" ? "Archived" : ""].filter(Boolean).join(" · ");
    copy.querySelectorAll("p")[1].textContent =
      `Profile v${character.profile_version || 1} · Identity v${character.identity_version || 1}`;
    hero.append(copy);
    $("profile-intro").textContent = character.intro || "No introduction yet.";

    const grid = $("profile-readiness");
    grid.replaceChildren();
    Object.entries(READINESS_LABELS).forEach(([key, label]) => {
      const item = character.readiness?.[key] || { state: "missing", missing: [] };
      const card = document.createElement("div");
      card.className = "readiness-card";
      const title = document.createElement("strong");
      title.textContent = label;
      const detail = document.createElement("span");
      detail.textContent = item.state === "ready" ? "Ready"
        : (item.total ? `${item.complete || 0} of ${item.total}` : "Needs setup");
      card.append(title, detail, pill(item.state, item));
      grid.append(card);
    });
    const missing = $("profile-missing");
    missing.replaceChildren();
    const items = missingItems(character);
    (items.length ? items : ["All configured capabilities are ready."]).forEach((text) => {
      const li = document.createElement("li");
      li.textContent = text;
      missing.append(li);
    });

    const archived = character.lifecycle === "archived";
    $("resume-character").textContent = character.wizard_step >= 10 ? "Edit profile" :
      `Resume step ${character.wizard_step || 1}`;
    $("resume-character").disabled = archived || state.busy;
    $("duplicate-character").disabled = state.busy;
    $("archive-character").hidden = archived;
    $("restore-character").hidden = !archived;
    $("archive-character").disabled = state.busy || Boolean(character.is_seed);
    $("archive-character").title = character.is_seed ? "Seed profiles cannot be archived." : "";

    renderCandidates(character);
    renderSheet(character);
    const locked = character.status === "locked";
    setGenerateButton($("generate-candidates"), !locked);
    setGenerateButton($("generate-sheet"), Boolean(character.reference_asset_id && !locked));
    const approved = Object.keys(SHEET_LABELS).every((kind) =>
      (character.assets || []).some((asset) => asset.kind === kind && asset.approved));
    $("lock-character").hidden = locked;
    $("lock-character").disabled = state.busy || !approved || !character.reference_asset_id;
    $("unlock-character").hidden = !locked;
    $("unlock-character").disabled = state.busy;
    $("lock-summary").textContent = locked ? "Appearance and outfit are locked." :
      `${Object.keys(SHEET_LABELS).filter((kind) =>
        (character.assets || []).some((asset) => asset.kind === kind && asset.approved)).length} of 4 sheet assets approved.`;
  }

  function renderCharacters() { renderCharacterList(); renderCharacterDetail(); }

  function formValues() {
    const form = $("character-wizard-form");
    const body = {};
    ["name", "role", "intro", "speaking_style", "dialogue_behavior", "gender", "age_group",
      "ethnicity", "hair", "eyes", "extra", "top_color", "top_item", "bottom_color", "bottom_item",
      "default_accent", "default_tts_engine", "default_voice_id", "default_voice_description"]
      .forEach((name) => { body[name] = String(form.elements[name]?.value || "").trim(); });
    body.personality = String(form.elements.personality.value || "").split(",")
      .map((item) => item.trim()).filter(Boolean);
    ["default_speed", "default_pitch", "default_volume"].forEach((name) => {
      body[name] = Number(form.elements[name].value);
    });
    return body;
  }

  function fillWizard(character) {
    const form = $("character-wizard-form");
    form.reset();
    form.elements.ethnicity.value = "Russian";
    form.elements.hair.value = "dark hair";
    form.elements.eyes.value = "brown eyes";
    form.elements.bottom_color.value = "navy blue";
    if (!character) return;
    for (const field of form.querySelectorAll("[name]")) {
      if (field.name === "visual_source") continue;
      const value = field.name === "personality" ? (character.personality || []).join(", ") : character[field.name];
      if (value !== undefined && value !== null) field.value = value;
    }
  }

  function renderReadinessGuide() {
    document.querySelectorAll(".asset-guide [data-readiness]").forEach((box) => {
      const key = box.dataset.readiness;
      box.replaceChildren();
      if (!state.wizardCharacter) { box.textContent = "Save the profile first to see readiness."; return; }
      if (key === "activities") {
        const counts = state.wizardCharacter.readiness?.activities || {};
        box.textContent = `${counts.approved || 0} approved · ${counts.pending || 0} waiting for review`;
        return;
      }
      const item = state.wizardCharacter.readiness?.[key] || { state: "missing", missing: [] };
      const title = document.createElement("strong");
      title.textContent = item.state === "ready" ? "Ready" :
        `${item.complete || 0} of ${item.total || item.missing?.length || 0} approved`;
      box.append(title);
      if (item.missing?.length) {
        const list = document.createElement("ul");
        item.missing.forEach((slot) => { const li = document.createElement("li"); li.textContent = slot; list.append(li); });
        box.append(list);
      }
    });
  }

  function renderWizard() {
    const step = state.wizardStep;
    document.querySelectorAll(".wizard-step").forEach((section) => {
      section.hidden = Number(section.dataset.step) !== step;
    });
    $("wizard-step-label").textContent = `Step ${step} of 10`;
    $("wizard-progress-fill").style.width = `${step * 10}%`;
    $("wizard-progress-fill").parentElement.setAttribute("aria-valuenow", String(step));
    const dots = Array.from({ length: 11 }, (_, index) => {
      const dot = document.createElement("li");
      dot.textContent = index;
      dot.className = index === step ? "current" : (index < step ? "complete" : "");
      return dot;
    });
    $("wizard-step-dots").replaceChildren(...dots);
    $("wizard-back").disabled = step === 0;
    $("wizard-skip").hidden = ![8, 9, 10].includes(step);
    $("wizard-next").textContent = step === 10 ? "Finish setup" : "Continue";
    $("wizard-title").textContent = state.wizardCharacter?.name || "Create a character";
    const values = formValues();
    $("wizard-preview-name").textContent = values.name || state.wizardCharacter?.name || "New character";
    $("wizard-preview-role").textContent = values.role || "Build the profile one small step at a time.";
    const art = $("wizard-preview-art");
    art.replaceChildren();
    const picture = portrait(state.wizardCharacter);
    if (picture) {
      const image = document.createElement("img");
      image.src = picture;
      image.alt = "";
      art.append(image);
    } else art.textContent = "Portrait preview";
    const badges = $("wizard-preview-badges");
    badges.replaceChildren();
    if (state.wizardCharacter) {
      badges.append(pill("Profile", state.wizardCharacter.readiness?.profile),
        pill("Voice", state.wizardCharacter.readiness?.voice),
        pill("Talk", state.wizardCharacter.readiness?.talking_starter));
      $("wizard-prompt-pack").href = Api.characterPromptPackUrl(state.wizardCharacter.id);
    }
    renderReadinessGuide();
  }

  function openWizard(character = null) {
    state.wizardCharacter = character;
    state.wizardStep = character ? Math.max(0, Math.min(10, character.wizard_step || 1)) : 0;
    fillWizard(character);
    $("character-browser").hidden = true;
    $("character-wizard").hidden = false;
    $("wizard-save-status").textContent = character ? "All saved." : "The profile is created after the name step.";
    $("wizard-retry").hidden = true;
    localStorage.setItem("characterWizardId", character?.id || "new");
    renderWizard();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function changedFields(character, values) {
    return Object.fromEntries(Object.entries(values).filter(([key, value]) => {
      const current = key === "personality" ? (character.personality || []) : character[key];
      return JSON.stringify(current) !== JSON.stringify(value);
    }));
  }

  async function saveWizard(extra = {}) {
    if (state.saving) { state.savePending = extra; return state.wizardCharacter; }
    const values = formValues();
    if (!values.name) return state.wizardCharacter;
    state.saving = true;
    $("wizard-save-status").classList.remove("save-error");
    $("wizard-save-status").textContent = "Saving…";
    $("wizard-retry").hidden = true;
    try {
      let saved;
      if (!state.wizardCharacter) {
        saved = await Api.createCharacter({ ...values, ...extra });
        localStorage.setItem("characterWizardId", saved.id);
      } else {
        const patch = { ...changedFields(state.wizardCharacter, values), ...extra };
        saved = Object.keys(patch).length ? await Api.updateCharacter(state.wizardCharacter.id, patch)
          : state.wizardCharacter;
      }
      state.wizardCharacter = saved;
      state.selectedId = saved.id;
      const index = state.characters.findIndex((item) => item.id === saved.id);
      if (index >= 0) state.characters[index] = saved; else state.characters.push(saved);
      $("wizard-save-status").textContent = "Saved.";
      renderWizard();
      return saved;
    } catch (error) {
      state.saveError = error;
      $("wizard-save-status").textContent = error.message || "Save failed.";
      $("wizard-save-status").classList.add("save-error");
      $("wizard-retry").hidden = false;
      throw error;
    } finally {
      state.saving = false;
      if (state.savePending) {
        const pending = state.savePending;
        state.savePending = null;
        setTimeout(() => saveWizard(pending).catch(() => {}), 0);
      }
    }
  }

  async function refreshCharacters() {
    state.characters = await Api.listCharacters(state.filters);
    if (state.selectedId && !selectedCharacter()) state.selectedId = null;
    renderCharacters();
  }

  async function closeWizard() {
    clearTimeout(state.saveTimer);
    if (state.wizardCharacter && !state.saving) await saveWizard();
    localStorage.removeItem("characterWizardId");
    $("character-wizard").hidden = true;
    $("character-browser").hidden = false;
    state.selectedId = state.wizardCharacter?.id || state.selectedId;
    state.wizardCharacter = null;
    await refreshCharacters();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function scheduleAutosave() {
    renderWizard();
    if (!state.wizardCharacter) return;
    clearTimeout(state.saveTimer);
    $("wizard-save-status").textContent = "Unsaved changes…";
    state.saveTimer = setTimeout(() => saveWizard().catch(() => {}), 600);
  }

  async function advanceWizard() {
    const current = document.querySelector(`.wizard-step[data-step="${state.wizardStep}"]`);
    const invalid = [...current.querySelectorAll("[required]")].find((field) => !field.checkValidity());
    if (invalid) { invalid.reportValidity(); invalid.focus(); return; }
    const next = Math.min(10, state.wizardStep + 1);
    try {
      if (state.wizardStep === 0 && !state.wizardCharacter) {
        state.wizardStep = 1;
        renderWizard();
        return;
      }
      await saveWizard({ wizard_step: state.wizardStep === 10 ? 10 : next });
      if (state.wizardStep === 10) {
        await closeWizard();
        message("Character setup saved.");
        return;
      }
      state.wizardStep = next;
      renderWizard();
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch {
      // The failed save keeps local field values and exposes Retry.
    }
  }
  function studioSlots() { return state.assetSlots?.groups?.[state.assetGroup] || []; }

  function slotRules(slot) {
    const size = slot.exact_size || slot.minimum_size;
    return `${slot.transparent ? "Transparent PNG" : "PNG, JPEG or WebP"} · ${slot.exact_size ? "exactly" : "at least"} ${size[0]}×${size[1]}`;
  }

  async function reloadStudio() {
    state.assetSlots = await Api.getCharacterAssetSlots(state.wizardCharacter.id);
    state.wizardCharacter = await Api.getCharacter(state.wizardCharacter.id);
    renderAssetSlots();
    renderReadinessGuide();
  }

  function studioButton(label, className, action) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.textContent = label;
    button.addEventListener("click", action);
    return button;
  }

  function renderAssetSlots() {
    const grid = $("asset-slot-grid");
    grid.replaceChildren();
    $("asset-studio-title").textContent = `${state.wizardCharacter.name} · ${state.assetGroup.replace("_", " ")}`;
    studioSlots().forEach((slot) => {
      const card = document.createElement("article");
      card.className = `asset-slot-card${slot.group === "sprite" ? " sprite" : ""}`;
      const title = document.createElement("h3"); title.textContent = slot.title;
      const preview = document.createElement("div"); preview.className = "asset-slot-preview";
      if (slot.asset) {
        const image = document.createElement("img"); image.src = slot.asset.content_url; image.alt = slot.title; preview.append(image);
      } else preview.textContent = "No picture yet";
      const rules = document.createElement("p"); rules.className = "asset-slot-rules"; rules.textContent = slotRules(slot);
      const prompt = document.createElement("p"); prompt.className = "asset-slot-prompt"; prompt.textContent = slot.prompt;
      const upload = document.createElement("label"); upload.className = "slot-upload-label";
      upload.append(slot.asset ? "Replace picture" : "Add picture");
      const input = document.createElement("input"); input.type = "file";
      input.accept = slot.transparent ? "image/png" : "image/png,image/jpeg,image/webp";
      input.addEventListener("change", async () => {
        const file = input.files[0]; if (!file) return;
        const local = URL.createObjectURL(file);
        const image = document.createElement("img"); image.src = local; image.alt = file.name; preview.replaceChildren(image);
        try {
          const replace = Boolean(slot.asset && ["face", "full_body", "calm__closed"].includes(slot.key));
          if (replace && !confirm("This creates a new identity version and makes older current pictures stale. Continue?")) return;
          await Api.uploadCharacterAsset(state.wizardCharacter.id, slot.key, file, state.assetSlots.identity_version, replace);
          message(`${slot.title} uploaded. Review it before use.`); await reloadStudio();
        } catch (error) { message(`${file.name}: ${error.message}`, true); await reloadStudio(); }
        finally { URL.revokeObjectURL(local); }
      });
      upload.append(input);
      const actions = document.createElement("div"); actions.className = "slot-review-actions";
      if (slot.asset) {
        [["Approve", "approved"], ["Reject", "rejected"]].forEach(([label, review]) => {
          const button = studioButton(label, review === "approved" ? "btn btn-primary btn-sm" : "btn btn-ghost btn-sm", async () => {
            await Api.reviewCharacterAsset(state.wizardCharacter.id, slot.asset.id, review); await reloadStudio();
          });
          button.disabled = slot.state === review; actions.append(button);
        });
      }
      if (slot.group === "core") {
        const generate = studioButton("Generate locally", "btn btn-ghost btn-sm", async () => {
          const replace = Boolean(slot.asset && ["face", "full_body"].includes(slot.key));
          if (replace && !confirm("Generate a new identity version for this base picture?")) return;
          await startJob(() => Api.generateCharacterAsset(state.wizardCharacter.id, slot.key, replace));
          await reloadStudio();
        });
        setGenerateButton(generate, true); actions.append(generate);
      }
      card.append(title, pill(slot.state.replace("_", " "), { state: slot.state === "approved" ? "ready" : (slot.state === "missing" ? "missing" : "partial") }), preview, rules, prompt, upload, actions);
      grid.append(card);
    });
  }

  async function openAssetStudio(group) {
    if (!state.wizardCharacter) { message("Save the character first.", true); return; }
    state.assetGroup = group;
    state.assetSlots = await Api.getCharacterAssetSlots(state.wizardCharacter.id);
    $("asset-studio").hidden = false;
    document.querySelectorAll("#character-wizard > .wizard-header, #character-wizard > .wizard-progress, #wizard-step-dots, #character-wizard > .wizard-layout").forEach((node) => { node.hidden = true; });
    renderAssetSlots(); renderBulkMapping(); window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function closeAssetStudio() {
    $("asset-studio").hidden = true;
    document.querySelectorAll("#character-wizard > .wizard-header, #character-wizard > .wizard-progress, #wizard-step-dots, #character-wizard > .wizard-layout").forEach((node) => { node.hidden = false; });
    renderWizard();
  }

  function validateBulkMapping() {
    const chosen = state.bulkFiles.map((item) => item.slot).filter(Boolean);
    const duplicates = new Set(chosen.filter((slot, index) => chosen.indexOf(slot) !== index));
    document.querySelectorAll(".bulk-map-item").forEach((item, index) => item.classList.toggle("invalid", !state.bulkFiles[index].slot || duplicates.has(state.bulkFiles[index].slot)));
    const valid = state.bulkFiles.length > 0 && chosen.length === state.bulkFiles.length && !duplicates.size;
    $("asset-bulk-upload").disabled = !valid;
    $("asset-bulk-status").textContent = duplicates.size ? "Each picture needs a unique slot." : (state.bulkFiles.length && !valid ? "Choose a slot for every picture." : "");
    return valid;
  }

  function renderBulkMapping() {
    const list = $("asset-bulk-list"); list.replaceChildren();
    state.bulkFiles.forEach((entry, index) => {
      const item = document.createElement("article"); item.className = "bulk-map-item";
      const image = document.createElement("img"); image.src = entry.preview; image.alt = `Picture ${index + 1}`;
      const copy = document.createElement("div"); const name = document.createElement("strong"); name.textContent = `${index + 1}. ${entry.file.name}`;
      const select = document.createElement("select"); select.setAttribute("aria-label", `Slot for picture ${index + 1}`); select.append(new Option("Choose a slot", ""));
      studioSlots().forEach((slot) => select.append(new Option(slot.title, slot.key))); select.value = entry.slot;
      select.addEventListener("change", () => { entry.slot = select.value; validateBulkMapping(); });
      copy.append(name, select); item.append(image, copy); list.append(item);
    });
    validateBulkMapping();
  }

  async function uploadBulkAssets() {
    if (!validateBulkMapping()) return;
    $("asset-bulk-upload").disabled = true; $("asset-bulk-status").textContent = "Uploading…";
    try {
      const results = await Api.uploadCharacterAssetBatch(state.wizardCharacter.id,
        state.bulkFiles.map((entry) => entry.file), state.bulkFiles.map((entry, index) => ({ file_index: index, slot_key: entry.slot })), state.assetSlots.identity_version);
      const failed = results.filter((item) => !item.success);
      $("asset-bulk-status").textContent = failed.length ? `${results.length - failed.length} uploaded · ${failed.map((item) => `${item.slot_key}: ${item.error}`).join(" · ")}` : `${results.length} pictures uploaded. Review them below.`;
      await reloadStudio();
      if (!failed.length) {
        state.bulkFiles.forEach((entry) => URL.revokeObjectURL(entry.preview));
        state.bulkFiles = []; $("asset-bulk-input").value = ""; renderBulkMapping();
        $("asset-bulk-status").textContent = `${results.length} pictures uploaded. Review them below.`;
      }
    } catch (error) { $("asset-bulk-status").textContent = error.message; $("asset-bulk-upload").disabled = false; }
  }

  function renderSceneFilters() {
    const bar = $("scene-filters");
    bar.replaceChildren();
    const present = [...new Set(state.scenes.map((scene) => scene.category || "other"))].sort();
    if (!present.includes(state.sceneFilter)) state.sceneFilter = "all";
    ["all", ...present].forEach((category) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "btn btn-ghost btn-sm";
      chip.dataset.category = category;
      const count = category === "all" ? state.scenes.length
        : state.scenes.filter((scene) => (scene.category || "other") === category).length;
      chip.textContent = `${category === "all" ? "All" : category} (${count})`;
      chip.setAttribute("aria-pressed", String(state.sceneFilter === category));
      chip.addEventListener("click", () => { state.sceneFilter = category; renderScenes(); });
      bar.append(chip);
    });
  }

  function updateStaleWarning() {
    const form = $("scene-form");
    const original = state.scenes.find((scene) => scene.id === state.editingSceneId);
    $("scene-stale-warning").hidden = !(original && original.preview_url && (
      form.elements.place.value.trim() !== original.place || form.elements.time_of_day.value !== original.time_of_day));
  }

  function sceneMeta(scene) {
    const used = scene.used_count || 0;
    return `${scene.category || "other"} · ${scene.time_of_day || "day"} · ${scene.staging}`
      + ` · Used in ${used} project${used === 1 ? "" : "s"}`;
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
    const visible = state.scenes.filter(
      (scene) => state.sceneFilter === "all" || (scene.category || "other") === state.sceneFilter);
    visible.forEach((scene) => {
      const card = document.createElement("article");
      card.className = "card library-scene";
      card.dataset.sceneId = scene.id;
      card.setAttribute("aria-current", String(scene.id === state.selectedSceneId));
      card.addEventListener("click", (event) => {
        if (!event.target.closest("button")) selectScene(scene); // a button keeps its own meaning
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
      edit.addEventListener("click", () => {
        selectScene(scene);
        state.editingSceneId = scene.id;
        $("scene-editor-title").textContent = `Edit ${scene.name}`;
        const form = $("scene-form");
        form.elements.name.value = scene.name;
        form.elements.place.value = scene.place;
        form.elements.staging.value = scene.staging;
        form.elements.category.value = scene.category || "other";
        form.elements.time_of_day.value = scene.time_of_day || "day";
        updateStaleWarning();
        $("save-scene").textContent = "Save scene";
        $("cancel-scene-edit").hidden = false;
        form.scrollIntoView({ behavior: "smooth", block: "center" });
      });
      const preview = document.createElement("button");
      preview.type = "button";
      preview.className = "btn btn-ghost btn-sm";
      preview.textContent = scene.preview_url ? "↻ Plate" : "Make plate";
      setGenerateButton(preview, true);
      preview.addEventListener("click", () => startJob(() => Api.generateScenePreview(scene.id)));
      const duplicate = document.createElement("button");
      duplicate.type = "button";
      duplicate.className = "btn btn-ghost btn-sm";
      duplicate.textContent = "Duplicate";
      duplicate.addEventListener("click", () => act(() => Api.duplicateScene(scene.id), "Scene duplicated."));
      actions.append(edit, preview, duplicate);
      if (!scene.is_builtin) {
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "btn btn-ghost btn-sm";
        remove.textContent = "Delete";
        remove.addEventListener("click", async () => {
          if (confirm(`Delete scene "${scene.name}"?`)) await act(() => Api.deleteScene(scene.id), "Scene deleted.");
        });
        actions.append(remove);
      }
      card.append(title, place, meta, actions);
      grid.append(card);
    });
    renderSceneDetail();
  }

  async function refresh() {
    [state.characters, state.scenes, state.health] = await Promise.all([
      Api.listCharacters(state.filters), Api.listScenes(), Api.getVisualsHealth(),
    ]);
    if (state.selectedId && !selectedCharacter()) state.selectedId = null;
    renderCharacters();
    renderScenes();
  }

  async function act(operation, success) {
    try {
      state.busy = true;
      renderCharacters();
      await operation();
      await refresh();
      message(success);
    } catch (error) {
      message(error.message || "The library action failed.", true);
    } finally {
      state.busy = false;
      renderCharacters();
      renderScenes();
    }
  }

  async function startJob(operation) {
    if (state.busy || !canGenerate()) return;
    state.busy = true;
    renderCharacters();
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
      $("cancel-library-job").hidden = true;
      $("cancel-library-job").onclick = null;
      state.busy = false;
      renderCharacters();
      renderScenes();
    }
  }

  function resetSceneForm() {
    state.editingSceneId = null;
    $("scene-form").reset();
    $("scene-stale-warning").hidden = true;
    $("scene-editor-title").textContent = "New scene";
    $("save-scene").textContent = "Add scene";
    $("cancel-scene-edit").hidden = true;
  }

  function setupEvents() {
    $("new-character").addEventListener("click", () => openWizard());
    let searchTimer;
    $("character-search").addEventListener("input", (event) => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(async () => {
        state.filters.q = event.target.value.trim();
        try { await refreshCharacters(); } catch (error) { message(error.message, true); }
      }, 250);
    });
    [["character-state", "state"], ["character-readiness", "readiness"]].forEach(([id, key]) => {
      $(id).addEventListener("change", async (event) => {
        state.filters[key] = event.target.value;
        try { await refreshCharacters(); } catch (error) { message(error.message, true); }
      });
    });
    $("resume-character").addEventListener("click", () => openWizard(selectedCharacter()));
    $("duplicate-character").addEventListener("click", async () => {
      const character = selectedCharacter();
      if (!character) return;
      await act(async () => { const copy = await Api.duplicateCharacter(character.id); state.selectedId = copy.id; },
        "Profile duplicated.");
    });
    $("archive-character").addEventListener("click", async () => {
      const character = selectedCharacter();
      if (!character || !confirm(`Archive "${character.name}"? Existing projects keep their assignment.`)) return;
      await act(async () => { await Api.archiveCharacter(character.id); state.selectedId = null; }, "Profile archived.");
    });
    $("restore-character").addEventListener("click", async () => {
      const character = selectedCharacter();
      if (!character) return;
      await act(() => Api.restoreCharacter(character.id), "Profile restored.");
    });
    $("character-wizard-form").addEventListener("submit", (event) => {
      event.preventDefault();
      advanceWizard();
    });
    $("character-wizard-form").addEventListener("input", scheduleAutosave);
    $("character-wizard-form").addEventListener("change", scheduleAutosave);
    $("wizard-back").addEventListener("click", () => {
      state.wizardStep = Math.max(0, state.wizardStep - 1);
      renderWizard();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
    $("wizard-skip").addEventListener("click", advanceWizard);
    $("wizard-retry").addEventListener("click", () => saveWizard().catch(() => {}));
    $("wizard-close").addEventListener("click", () => closeWizard().catch((error) => message(error.message, true)));
    document.querySelectorAll(".open-asset-studio").forEach((button) => button.addEventListener("click", () =>
      openAssetStudio(button.dataset.group).catch((error) => message(error.message, true))));
    $("asset-studio-close").addEventListener("click", closeAssetStudio);
    $("asset-bulk-input").addEventListener("change", (event) => {
      state.bulkFiles.forEach((entry) => URL.revokeObjectURL(entry.preview));
      state.bulkFiles = [...event.target.files].map((file) => ({ file, slot: "", preview: URL.createObjectURL(file) }));
      renderBulkMapping();
    });
    $("asset-bulk-upload").addEventListener("click", uploadBulkAssets);
    $("generate-candidates").addEventListener("click", () => startJob(
      () => Api.generateCharacterCandidates(state.selectedId)));
    $("generate-sheet").addEventListener("click", () => startJob(
      () => Api.generateCharacterSheet(state.selectedId)));
    $("lock-character").addEventListener("click", () => act(
      () => Api.lockCharacter(state.selectedId), "Character locked."));
    $("unlock-character").addEventListener("click", () => act(
      () => Api.unlockCharacter(state.selectedId), "Character unlocked."));
    $("characters-tab").addEventListener("click", () => {
      $("characters-panel").hidden = false;
      $("scenes-panel").hidden = true;
      $("characters-tab").setAttribute("aria-selected", "true");
      $("scenes-tab").setAttribute("aria-selected", "false");
    });
    $("scenes-tab").addEventListener("click", () => {
      $("characters-panel").hidden = true;
      $("scenes-panel").hidden = false;
      $("characters-tab").setAttribute("aria-selected", "false");
      $("scenes-tab").setAttribute("aria-selected", "true");
    });
    $("scene-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const body = Object.fromEntries(new FormData(event.currentTarget));
      const editing = state.editingSceneId;
      const original = state.scenes.find((scene) => scene.id === editing);
      const patch = original
        ? Object.fromEntries(Object.entries(body).filter(([key, value]) => value !== original[key]))
        : body;
      await act(() => editing ? Api.updateScene(editing, patch) : Api.createScene(body),
        editing ? "Scene saved." : "Scene added.");
      resetSceneForm();
    });
    $("cancel-scene-edit").addEventListener("click", resetSceneForm);
    $("scene-form").elements.place.addEventListener("input", updateStaleWarning);
    $("scene-form").elements.time_of_day.addEventListener("change", updateStaleWarning);
    $("theme-toggle").addEventListener("click", Theme.toggle);
  }

  document.addEventListener("DOMContentLoaded", async () => {
    setupEvents();
    try {
      state.options = await Api.getVisualsOptions();
      fillOptions();
      await refresh();
      const resumeId = localStorage.getItem("characterWizardId");
      if (resumeId === "new") openWizard();
      else if (resumeId) {
        const character = state.characters.find((item) => item.id === resumeId) || await Api.getCharacter(resumeId);
        openWizard(character);
      }
    } catch (error) {
      message(error.message || "The library could not load.", true);
    }
  });
})();
