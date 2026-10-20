/**
 * Phase 33 (Tasks 33.4/33.5, D79/D84/D86): the Profiles tab of /characters.
 *
 * Quick create asks only name, gender, accent, nationality, appearance and outfit. A profile then shows its 29 picture slots
 * (the talking-sprite pack of data/library/sprites_inbox): each card has the picture to attach in the outside AI, the region
 * to select, the prompt and a drop zone. A file dropped on a card goes into that card's slot, whatever it is called.
 */
(() => {
  const $ = (id) => document.getElementById(id);
  const state = { profiles: [], selectedId: null, creating: false, slots: null, filter: "active", query: "",
    voicePicker: null, voiceProfileId: null, openToken: 0, listToken: 0, view: "native", assetBusy: false, slotsLoading: false, createBusy: false,
    slotErrors: {} };  // "profile:view:slot" -> why the last upload to that card was refused (BUG-049)
  const GROUPS = [
    ["base", "Base picture"],
    ["expression", "Expressions"],
    ["mouth", "Open mouths"],
    ["blink", "Blink"],
    ["gesture", "Gestures"],
  ];
  const STATE_LABELS = {
    empty: "Empty", waiting: "Waiting for its parent", needs_review: "Needs review", approved: "Approved",
    rejected: "Rejected", stale: "Make again (new base)",
  };

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function notice(text, isError = false) {
    const box = $("profile-message");
    box.textContent = text;
    box.hidden = !text;
    box.classList.toggle("is-error", isError);
  }

  function cardPicture(profile) {
    const pictures = profile.pictures || {};
    return pictures.portrait || pictures.base || null;
  }

  function badges(readiness) {
    const items = [];
    if (readiness.video_ready) items.push('<span class="profile-badge is-ok">Video ready</span>');
    if (readiness.talking_ready) items.push('<span class="profile-badge is-ok">Talking ready</span>');
    const pack = readiness.full_sprite_pack;
    items.push(`<span class="profile-badge">${pack.have}/${pack.need} pictures</span>`);
    const front = readiness.front_presenter;
    if (front?.have) items.push(`<span class="profile-badge${front.ready ? " is-ok" : ""}">Front ${front.have}/${front.need}</span>`);
    return items.join("");
  }

  function renderList() {
    const list = $("profile-list");
    if (!state.profiles.length) {
      list.innerHTML = '<p class="library-hint">No characters yet. Press New character.</p>';
      return;
    }
    list.innerHTML = state.profiles.map((profile) => {
      const picture = cardPicture(profile);
      return `
        <button type="button" class="profile-card${profile.id === state.selectedId ? " is-selected" : ""}" data-id="${profile.id}"
          aria-pressed="${profile.id === state.selectedId}">
          ${picture ? `<img src="${picture}" alt="" loading="lazy" />` : '<span class="profile-card-empty" aria-hidden="true">?</span>'}
          <span class="profile-card-body">
            <strong>${escapeHtml(profile.name)}</strong>
            <span class="profile-card-meta">${escapeHtml(profile.gender)} · ${escapeHtml(profile.accent || "no accent")}${profile.archived ? " · archived" : ""}</span>
            <span class="profile-badges">${badges(profile.readiness)}</span>
          </span>
        </button>`;
    }).join("");
  }

  async function loadProfiles(selectId = state.selectedId) {
    const query = new URLSearchParams({ state: state.filter, q: state.query });
    const token = ++state.listToken, selectionToken = state.openToken;
    const profiles = await Api.listProfiles(query.toString());
    if (token !== state.listToken) return;
    state.profiles = profiles;
    if (selectionToken === state.openToken && !state.assetBusy) {
      if (selectId && !state.profiles.some(profile => profile.id === selectId)) selectId = null;
      state.selectedId = selectId;
    }
    renderList();
  }

  // ------------------------------------------------------------------ Quick create (D79)

  async function showCreate() {
    if (operationBlocked()) return;
    if (!(await canLeaveVoice(null))) return;
    await flushDetails();
    state.openToken += 1;
    destroyVoicePicker();
    state.creating = true;
    state.selectedId = null;
    renderList();
    $("profile-create").hidden = false;
    $("profile-detail").hidden = true;
    $("profile-create-form").reset();
    $("profile-create-form").elements.name.focus();
  }

  async function submitCreate(event) {
    event.preventDefault();
    if (state.createBusy || state.assetBusy) return;
    const form = event.currentTarget;
    const body = Object.fromEntries(new FormData(form));
    state.createBusy = true;
    Array.from(form.elements).forEach(element => { element.disabled = true; });
    try {
      const profile = await Api.createProfile(body);
      state.creating = false;
      notice(`${profile.name} created. Make the base picture first: copy its prompt below.`);
      await loadProfiles(profile.id);
      state.createBusy = false;
      await openProfile(profile.id);
    } catch (error) {
      notice(error.message || "The character could not be created.", true);
    } finally {
      state.createBusy = false;
      Array.from(form.elements).forEach(element => { element.disabled = false; });
    }
  }

  // ------------------------------------------------------------------ profile detail

  function destroyVoicePicker() {
    state.voicePicker?.destroy();
    state.voicePicker = null;
    state.voiceProfileId = null;
  }

  async function canLeaveVoice(nextId) {
    if (state.voiceProfileId !== nextId && state.voicePicker?.isSaving()) {
      notice("Wait until the voice finishes saving before switching characters.");
      return false;
    }
    if (!state.voicePicker?.hasUnsaved() || state.voiceProfileId === nextId) return true;
    return ConfirmDialog.ask("Discard the unsaved voice selection?", {confirmLabel: "Discard"});
  }

  function voiceValues(profile) {
    return {voiceId: profile.voice.voice_id, revision: profile.voice_revision, parameters: {
      speed: profile.voice.speed, pitch: profile.voice.pitch, volume: profile.voice.volume,
    }};
  }

  function updateVoiceSummary(profile) {
    $("profile-summary").textContent =
      `${profile.gender} · ${profile.accent} · profile voice ${profile.voice.voice_id} · ${state.view === "front" ? "front presenter, looking at the viewer" : `stands on the ${profile.gender === "male" ? "left" : "right"}, faces ${profile.sprite_facing}`}`;
    const index = state.profiles.findIndex(item => item.id === profile.id);
    if (index >= 0) state.profiles[index] = {...state.profiles[index], ...profile};
    renderList();
  }

  function mountVoicePicker(profile) {
    if (state.voiceProfileId === profile.id && state.voicePicker) return;
    destroyVoicePicker();
    const id = profile.id;
    state.voiceProfileId = id;
    state.voicePicker = VoicePicker.mount($("profile-voice-picker"), {
      ...voiceValues(profile), editParameters: true,
      savedMessage: "Profile voice saved. Existing videos keep their saved voice; use Apply profile voice in Audio Studio to update one.",
      onDirtyChange: () => setAssetLocks(),
      onSave: async value => {
        const updated = await Api.patchProfile(id, {
          default_voice_id: value.voice_id, default_speed: value.speed, default_pitch: value.pitch,
          default_volume: value.volume, expected_voice_revision: value.expected_voice_revision,
        });
        if (state.selectedId === id) updateVoiceSummary(updated);
        return {revision: updated.voice_revision};
      },
      onReload: async () => {
        const updated = await Api.getProfile(id);
        if (state.selectedId === id) updateVoiceSummary(updated);
        return voiceValues(updated);
      },
    });
  }

  function operationBlocked() {
    if (state.voicePicker?.isSaving()) {
      notice("Wait until the voice finishes saving before switching characters.");
      return true;
    }
    if (!state.assetBusy && !state.createBusy) return false;
    notice("Wait until the current picture or character finishes saving before switching.");
    return true;
  }

  function setAssetLocks() {
    const busy = state.assetBusy || state.slotsLoading || state.createBusy || Boolean(state.voicePicker?.isSaving());
    document.querySelectorAll("[data-picture-view], #profile-approve-all, #profile-bulk, #profile-search, #profile-filter").forEach(element => { element.disabled = busy; });
    document.querySelectorAll(".slot-actions button, .slot-copy, .slot-drop input").forEach(element => {
      const card = state.slots?.slots?.find(item => item.key === element.closest(".slot-card")?.dataset.slot);
      element.disabled = busy || (element.tagName === "INPUT" && !card?.parent_ready);
    });
    document.querySelectorAll(".slot-drop").forEach(element => {
      const card = state.slots?.slots?.find(item => item.key === element.closest(".slot-card")?.dataset.slot);
      const disabled = busy || !card?.parent_ready;
      element.classList.toggle("is-disabled", disabled);
      element.setAttribute("aria-disabled", String(disabled));
      element.tabIndex = disabled ? -1 : 0;
    });
    ["profile-new", "profile-duplicate", "profile-archive", "profile-delete"].forEach(key => {
      $(key).disabled = busy || (key !== "profile-new" && Boolean(state.voicePicker?.hasUnsaved()));
    });
    Array.from($("profile-details-form").elements).forEach(element => { element.disabled = state.slotsLoading; });
    $("profile-slots").setAttribute("aria-busy", String(busy));
  }

  async function openProfile(id, {assetRefresh = false} = {}) {
    if (!assetRefresh && operationBlocked()) return;
    if (!(await canLeaveVoice(id))) return;
    await flushDetails();
    const token = ++state.openToken, view = state.view;
    state.creating = false;
    state.selectedId = id;
    state.slots = null;
    state.slotsLoading = true;
    state.voicePicker?.setDisabled(true);
    renderList();
    renderSlots();
    setAssetLocks();
    $("profile-create").hidden = true;
    $("profile-detail").hidden = false;
    try {
      const [profile, slots] = await Promise.all([Api.getProfile(id), Api.listProfileSlots(id, view)]);
      if (token !== state.openToken || state.selectedId !== id || view !== state.view) return;
      state.slots = slots;
      renderDetail(profile);
      mountVoicePicker(profile);
      renderSlots();
    } finally {
      if (token === state.openToken) {
        state.slotsLoading = false;
        state.voicePicker?.setDisabled(state.assetBusy || state.voiceProfileId !== state.selectedId);
        setAssetLocks();
      }
    }
  }

  async function selectView(view) {
    if (operationBlocked() || !state.selectedId) return;
    state.view = view;
    try { await openProfile(state.selectedId); }
    catch (error) { notice(error.message || "Pictures could not load. Select the tab to retry.", true); }
  }

  function renderDetail(profile) {
    $("profile-name").textContent = profile.name;
    updateVoiceSummary(profile);
    $("profile-archive").textContent = profile.archived ? "Restore" : "Archive";
    $("profile-delete").hidden = profile.is_seed;
    const readiness = profile.readiness;
    const parts = state.view === "front" ? ["profile", "voice", "front_presenter"] : ["profile", "voice", "core_visuals", "talking_starter"];
    const missing = parts.flatMap((key) => readiness[key]?.missing || []);
    $("profile-readiness").innerHTML = `
      <span class="profile-badges">${badges(readiness)}</span>
      ${missing.length ? `<p class="library-hint">Still needed: ${escapeHtml(missing.slice(0, 8).join(", "))}${missing.length > 8 ? ` and ${missing.length - 8} more` : ""}.</p>` : `<p class="library-hint">${state.view === "front" ? "All front presenter pictures are approved." : "Ready for talking videos."}</p>`}`;
    const form = $("profile-details-form");
    form.elements.intro.value = profile.intro || "";
    form.elements.personality.value = (profile.personality || []).join(", ");
    form.elements.speaking_style.value = profile.speaking_style || "";
    $("profile-prompt-pack").href = Api.profilePromptPackUrl(profile.id, state.view);
  }

  function slotState(card) {
    if (card.asset) return card.asset.review_state;
    return card.parent_ready ? "empty" : "waiting";
  }

  function slotCard(card) {
    const status = slotState(card);
    const asset = card.asset;
    const problems = asset?.validation?.problems || [];
    const canUpload = card.parent_ready;
    const refused = state.slotErrors[slotErrorKey(state.selectedId, state.view, card.key)];
    return `
      <article class="slot-card" data-slot="${card.key}" data-state="${status}">
        <header class="slot-card-head">
          <strong>${escapeHtml(card.title || card.file_name)}</strong>
          <span class="slot-chip slot-chip-${status}">${STATE_LABELS[status] || status}</span>
          <span class="slot-tier">Tier ${card.tier}</span>
        </header>
        ${state.view === "front" ? `<p class="slot-note">Save as <strong>${escapeHtml(card.file_name)}</strong> · Full body · Fixed camera · Same identity and outfit</p>` : ""}
        <div class="slot-drop${canUpload ? "" : " is-disabled"}" tabindex="${canUpload ? 0 : -1}" role="button"
          aria-disabled="${!canUpload}" aria-label="Add the ${escapeHtml(card.file_name)} picture">
          ${asset ? `<img src="${asset.url}?v=${encodeURIComponent(asset.updated_at || "")}" alt="${escapeHtml(card.key)}" />`
            : `<span>${canUpload ? "Drop the picture here or click" : `Approve ${escapeHtml(card.parent)} first`}</span>`}
          <input type="file" accept="image/png,image/jpeg,image/webp" hidden ${canUpload ? "" : "disabled"} />
        </div>
        ${refused ? `<p class="slot-note slot-refused" role="alert"><span class="is-error">Not stored: ${escapeHtml(refused)}</span></p>` : ""}
        ${asset ? `<p class="slot-note">${escapeHtml(asset.validation?.method || "")}${problems.length ? ` — <span class="is-error">${escapeHtml(problems.join("; "))}</span>` : ""}</p>` : ""}
        <ol class="slot-steps">
          <li>${card.parent ? (card.parent_ready
              ? `Attach <a href="${card.parent_input_url}" download>the input picture</a> (${escapeHtml(card.parent)}).`
              : `Attach the ${escapeHtml(card.parent)} picture once it is approved.`)
            : card.identity_reference_url ? `Attach <a href="${card.identity_reference_url}" download>the existing identity picture</a>; turn the same person toward the camera.` : "Start a new picture from the profile description."}</li>
          ${card.region_text ? `<li>Select: ${escapeHtml(card.region_text)}.</li>` : ""}
          <li>Prompt <button type="button" class="btn btn-ghost btn-sm slot-copy">Copy</button>
            <textarea class="slot-prompt" aria-label="${escapeHtml(card.title || card.file_name)} strict prompt" readonly rows="${state.view === "front" ? 12 : 4}">${escapeHtml(card.prompt)}</textarea></li>
        </ol>
        ${status === "needs_review" ? `
          <div class="slot-actions">
            <button type="button" class="btn btn-primary btn-sm slot-approve">Approve</button>
            <button type="button" class="btn btn-ghost btn-sm slot-reject">Reject</button>
          </div>` : ""}
      </article>`;
  }

  function renderSlots() {
    const cards = state.slots?.slots || [];
    const front = state.view === "front";
    const total = front ? 21 : 29;
    const approved = cards.filter(card => card.asset?.review_state === "approved").length;
    document.querySelectorAll("[data-picture-view]").forEach(button => {
      const selected = button.dataset.pictureView === state.view;
      button.setAttribute("aria-selected", String(selected)); button.tabIndex = selected ? 0 : -1;
    });
    $("profile-slots").setAttribute("aria-labelledby", `profile-view-${state.view}`);
    $("profile-pack-heading").textContent = front ? "Front-facing presenter pictures" : "Conversation pictures";
    $("profile-pack-progress").textContent = state.slotsLoading && !state.slots ? "Loading pictures…" : `${approved}/${total} approved${approved === total ? " · complete" : ""}`;
    $("profile-pack-help").textContent = front
      ? "Create and approve the front neutral first. Then import and review the 9 closed gestures, followed by their open mouths and blink. Keep the same face and clothing. Screen-left/right means the viewer's screen."
      : "Make each picture with an outside AI from its card: attach the input picture, select the region, paste the prompt. Drop the result on the same card; it is renamed and placed for you.";
    const pending = cards.filter((card) => card.asset && card.asset.review_state === "needs_review");
    $("profile-approve-all").hidden = !pending.length;
    $("profile-approve-all").textContent = `Approve all pending (${pending.length})`;
    $("profile-slots").dataset.view = state.view;
    const groups = state.view === "front" ? [GROUPS[0], GROUPS[4], GROUPS[2], GROUPS[3]] : GROUPS;
    $("profile-slots").innerHTML = groups.map(([group, title]) => {
      const inGroup = cards.filter((card) => card.group === group);
      return inGroup.length ? `<section class="slot-group"><h4>${title}</h4><div class="slot-grid">${inGroup.map(slotCard).join("")}</div></section>` : "";
    }).join("");
    setAssetLocks();
  }

  async function refreshSelected(message) {
    const id = state.selectedId;
    await loadProfiles(id);
    if (id) await openProfile(id);
    if (message) notice(message);
  }

  const slotErrorKey = (id, view, slot) => `${id}:${view}:${slot}`;

  async function assetAction(work, message, slot = null) {
    if (state.assetBusy || state.createBusy || state.slotsLoading || !state.slots) return;
    if (state.voicePicker?.isSaving()) { notice("Wait until the voice finishes saving before changing pictures."); return; }
    const id = state.selectedId, view = state.view;
    state.assetBusy = true;
    state.voicePicker?.setDisabled(true);
    setAssetLocks();
    try {
      await flushDetails();
      const result = await work(id, view);
      if (slot) delete state.slotErrors[slotErrorKey(id, view, slot)];
      for (const item of result?.stored || []) if (item.slot) delete state.slotErrors[slotErrorKey(id, view, item.slot)];
      for (const item of result?.failed || []) if (item.slot) state.slotErrors[slotErrorKey(id, view, item.slot)] = item.reason;
      await openProfile(id, {assetRefresh: true});
      notice(typeof message === "function" ? message(result) : message || "Saved.", Boolean(result?.failed?.length));
    } catch (error) {
      notice(error.message || "The picture change could not be saved. Try again.", true);
      if (slot) state.slotErrors[slotErrorKey(id, view, slot)] = error.message || "The picture could not be stored.";
      renderSlots();
    } finally {
      state.assetBusy = false;
      state.voicePicker?.setDisabled(state.voiceProfileId !== state.selectedId);
      setAssetLocks();
    }
  }

  async function uploadToSlot(slotKey, file) {
    if (state.assetBusy || state.slotsLoading) return;
    const url = URL.createObjectURL(file);
    try {
      await assetAction(async (id, view) => {
        const drop = document.querySelector(`.slot-card[data-slot="${slotKey}"] .slot-drop`);
        if (drop) drop.innerHTML = `<img src="${url}" alt="" class="is-preview" /><span class="slot-busy">Placing and checking…</span>`;
        return Api.uploadProfileSlot(id, slotKey, file, view);
      }, `${slotKey}.png stored. Check it, then approve.`, slotKey);
    } finally { URL.revokeObjectURL(url); }
  }

  async function review(assetId, decision) {
    return assetAction((id, view) => Api.reviewProfileAsset(id, assetId, decision, view), decision === "approve" ? "Approved." : "Rejected.");
  }

  function setupSlotEvents() {
    const container = $("profile-slots");
    container.addEventListener("click", async (event) => {
      const card = event.target.closest(".slot-card");
      if (!card || state.assetBusy || state.slotsLoading || !state.slots || event.target.tagName === "INPUT") return;  // the file input's own click must not reopen it
      const slot = state.slots.slots.find((item) => item.key === card.dataset.slot);
      if (event.target.closest(".slot-copy")) {
        try {
          if (!navigator.clipboard) throw new Error("Clipboard unavailable");
          await navigator.clipboard.writeText(slot.prompt);
          event.target.textContent = "Copied";
        } catch {
          card.querySelector("textarea")?.select();
          notice("The browser could not copy. The prompt is selected; press Ctrl+C.", true);
        }
        return;
      }
      if (event.target.closest(".slot-approve")) return review(slot.asset.id, "approve");
      if (event.target.closest(".slot-reject")) return review(slot.asset.id, "reject");
      const drop = event.target.closest(".slot-drop");
      if (drop && !drop.classList.contains("is-disabled") && event.target.tagName !== "A") drop.querySelector("input").click();
    });
    container.addEventListener("change", (event) => {
      const input = event.target.closest(".slot-drop input");
      if (input?.files?.[0]) {
        const file = input.files[0]; input.value = "";
        uploadToSlot(input.closest(".slot-card").dataset.slot, file);
      }
    });
    container.addEventListener("keydown", (event) => {
      const drop = event.target.closest(".slot-drop");
      if (drop && !drop.classList.contains("is-disabled") && (event.key === "Enter" || event.key === " ")) {
        event.preventDefault();
        drop.querySelector("input").click();
      }
    });
    container.addEventListener("dragover", (event) => {
      const drop = event.target.closest(".slot-drop");
      if (drop && !drop.classList.contains("is-disabled")) {
        event.preventDefault();
        drop.classList.add("is-over");
      }
    });
    container.addEventListener("dragleave", (event) => event.target.closest(".slot-drop")?.classList.remove("is-over"));
    container.addEventListener("drop", (event) => {
      const drop = event.target.closest(".slot-drop");
      if (!drop || drop.classList.contains("is-disabled")) return;
      event.preventDefault();
      const file = event.dataTransfer?.files?.[0];
      if (file) uploadToSlot(drop.closest(".slot-card").dataset.slot, file);
    });
  }

  // ------------------------------------------------------------------ autosave of the optional details

  let saveTimer = null;
  let pendingDetails = null;
  let detailSavePromise = Promise.resolve();
  function scheduleSave() {
    const form = $("profile-details-form");
    pendingDetails = {id: state.selectedId, patch: {
      intro: form.elements.intro.value,
      personality: form.elements.personality.value.split(",").map(item => item.trim()).filter(Boolean),
      speaking_style: form.elements.speaking_style.value,
    }};
    $("profile-save-state").textContent = "Saving…";
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => flushDetails().catch(error => notice(error.message, true)), 600);
  }

  async function flushDetails() {
    clearTimeout(saveTimer);
    saveTimer = null;
    const pending = pendingDetails;
    pendingDetails = null;
    if (pending) {
      detailSavePromise = detailSavePromise.catch(() => {}).then(async () => {
        try {
          await Api.patchProfile(pending.id, pending.patch);
          if (state.selectedId === pending.id) $("profile-save-state").textContent = "Saved";
        } catch (error) {
          pendingDetails = pendingDetails || pending;
          if (state.selectedId === pending.id) $("profile-save-state").textContent = "Not saved — retry editing";
          throw error;
        }
      });
    }
    return detailSavePromise;
  }

  // ------------------------------------------------------------------ actions

  async function act(work, message) {
    if (operationBlocked() || state.slotsLoading) return;
    state.assetBusy = true;
    state.voicePicker?.setDisabled(true);
    setAssetLocks();
    try {
      await flushDetails();
      await work();
      await loadProfiles(state.selectedId);
      if (state.selectedId) await openProfile(state.selectedId, {assetRefresh: true});
      notice(message || "Saved.");
    } catch (error) {
      notice(error.message || "That did not work.", true);
    } finally {
      state.assetBusy = false;
      state.voicePicker?.setDisabled(state.voiceProfileId !== state.selectedId);
      setAssetLocks();
    }
  }

  function setupEvents() {
    // A picture that cannot load shows the neutral placeholder, never a broken-image icon.
    $("profile-list").addEventListener("error", (event) => {
      if (event.target.tagName === "IMG") {
        const empty = document.createElement("span");
        empty.className = "profile-card-empty";
        empty.setAttribute("aria-hidden", "true");
        empty.textContent = "?";
        event.target.replaceWith(empty);
      }
    }, true);
    $("profile-new").addEventListener("click", () => showCreate().catch(error => notice(error.message, true)));
    $("profile-create-form").addEventListener("submit", submitCreate);
    $("profile-create-cancel").addEventListener("click", () => {
      if (operationBlocked()) return;
      $("profile-create").hidden = true;
      state.creating = false;
    });
    $("profile-list").addEventListener("click", (event) => {
      const card = event.target.closest(".profile-card");
      if (card) openProfile(card.dataset.id).catch((error) => notice(error.message, true));
    });
    $("profile-search").addEventListener("input", (event) => {
      state.query = event.target.value;
      loadProfiles().catch((error) => notice(error.message, true));
    });
    $("profile-filter").addEventListener("change", (event) => {
      state.filter = event.target.value;
      loadProfiles().catch((error) => notice(error.message, true));
    });
    $("profile-duplicate").addEventListener("click", () => act(async () => {
      const copy = await Api.duplicateProfile(state.selectedId);
      state.selectedId = copy.id;
    }, "Duplicated. The copy has no pictures yet."));
    $("profile-archive").addEventListener("click", () => {
      const profile = state.profiles.find((item) => item.id === state.selectedId);
      act(() => (profile?.archived ? Api.restoreProfile(state.selectedId) : Api.archiveProfile(state.selectedId)),
        profile?.archived ? "Restored." : "Archived.");
    });
    $("profile-delete").addEventListener("click", async () => {
      if (!(await ConfirmDialog.ask("Delete this character for good? Its pictures are removed too.", { confirmLabel: "Delete", danger: true }))) return;
      act(async () => {
        await Api.deleteProfile(state.selectedId);
        state.selectedId = null;
        state.openToken += 1;
        destroyVoicePicker();
        $("profile-detail").hidden = true;
      }, "Deleted.");
    });
    document.querySelectorAll("[data-picture-view]").forEach(button => {
      button.addEventListener("click", () => selectView(button.dataset.pictureView));
      button.addEventListener("keydown", event => {
        if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
        event.preventDefault();
        if (state.assetBusy || state.slotsLoading) return;
        const next = event.key === "Home" ? "native" : event.key === "End" ? "front" : state.view === "native" ? "front" : "native";
        $("profile-view-" + next).focus();
        selectView(next);
      });
    });
    window.addEventListener("beforeunload", event => {
      if (!state.assetBusy && !state.createBusy) return;
      event.preventDefault(); event.returnValue = "";
    });
    $("profile-approve-all").addEventListener("click", () => {
      const ids = state.slots?.slots?.filter(card => card.asset?.review_state === "needs_review").map(card => card.asset.id) || [];
      if (ids.length) assetAction((id, view) => Api.approveProfileAssets(id, ids, view), `${ids.length} picture(s) approved.`);
    });
    $("profile-bulk").addEventListener("change", event => {
      const files = [...(event.target.files || [])];
      event.target.value = "";
      if (!files.length) return;
      assetAction((id, view) => Api.uploadProfileSlotsBatch(id, files, view), result => {
        const lines = [`${result.stored.length} stored`];
        if (result.unmatched.length) lines.push(`${result.unmatched.length} not named after a slot (drop them on their card)`);
        if (result.failed.length) lines.push(`${result.failed.length} refused: ${result.failed.map(item => `${item.file} (${item.reason})`).join("; ")}`);
        return lines.join(" · ");
      });
    });
    $("profile-details-form").addEventListener("input", scheduleSave);
    setupSlotEvents();
  }

  document.addEventListener("DOMContentLoaded", async () => {
    if (!$("profiles-panel")) return;
    setupEvents();
    try {
      const options = await Api.getProfileOptions();
      $("profile-create-form").elements.accent.innerHTML = options.accents
        .map((accent) => `<option value="${accent}"${accent === "scottish"
          ? ' title="Edge TTS has no Scottish voice: this accent uses the British voices"' : ""}>${accent.replace("_", " ")}</option>`)
        .join("");
      await loadProfiles();
    } catch (error) {
      notice(error.message || "The characters could not load.", true);
    }
  });
})();
