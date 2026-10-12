/**
 * Phase 33 (Tasks 33.4/33.5, D79/D84/D86): the Profiles tab of /characters.
 *
 * Quick create asks only name, gender, accent, nationality, appearance and outfit. A profile then shows its 29 picture slots
 * (the talking-sprite pack of data/library/sprites_inbox): each card has the picture to attach in the outside AI, the region
 * to select, the prompt and a drop zone. A file dropped on a card goes into that card's slot, whatever it is called.
 */
(() => {
  const $ = (id) => document.getElementById(id);
  const state = { profiles: [], selectedId: null, creating: false, slots: null, filter: "active", query: "" };
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
    state.profiles = await Api.listProfiles(query.toString());
    if (selectId && !state.profiles.some((profile) => profile.id === selectId)) selectId = null;
    state.selectedId = selectId;
    renderList();
  }

  // ------------------------------------------------------------------ Quick create (D79)

  function showCreate() {
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
    const body = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const profile = await Api.createProfile(body);
      state.creating = false;
      notice(`${profile.name} created. Make the base picture first: copy its prompt below.`);
      await loadProfiles(profile.id);
      await openProfile(profile.id);
    } catch (error) {
      notice(error.message || "The character could not be created.", true);
    }
  }

  // ------------------------------------------------------------------ profile detail

  async function openProfile(id) {
    state.creating = false;
    state.selectedId = id;
    renderList();
    $("profile-create").hidden = true;
    $("profile-detail").hidden = false;
    const [profile, slots] = await Promise.all([Api.getProfile(id), Api.listProfileSlots(id)]);
    state.slots = slots;
    renderDetail(profile);
    renderSlots();
  }

  function renderDetail(profile) {
    $("profile-name").textContent = profile.name;
    $("profile-summary").textContent =
      `${profile.gender} · ${profile.accent} · voice ${profile.voice.voice_id} · stands on the ${profile.gender === "male" ? "left" : "right"}, faces ${profile.sprite_facing}`;
    $("profile-archive").textContent = profile.archived ? "Restore" : "Archive";
    $("profile-delete").hidden = profile.is_seed;
    const readiness = profile.readiness;
    const missing = ["profile", "voice", "core_visuals", "talking_starter"].flatMap((key) => readiness[key].missing || []);
    $("profile-readiness").innerHTML = `
      <span class="profile-badges">${badges(readiness)}</span>
      ${missing.length ? `<p class="library-hint">Still needed: ${escapeHtml(missing.slice(0, 8).join(", "))}${missing.length > 8 ? ` and ${missing.length - 8} more` : ""}.</p>` : '<p class="library-hint">Ready for talking videos.</p>'}`;
    const form = $("profile-details-form");
    form.elements.intro.value = profile.intro || "";
    form.elements.personality.value = (profile.personality || []).join(", ");
    form.elements.speaking_style.value = profile.speaking_style || "";
    $("profile-prompt-pack").href = `/api/visuals/profiles/${profile.id}/prompt-pack.txt`;
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
    return `
      <article class="slot-card" data-slot="${card.key}" data-state="${status}">
        <header class="slot-card-head">
          <strong>${escapeHtml(card.file_name)}</strong>
          <span class="slot-chip slot-chip-${status}">${STATE_LABELS[status] || status}</span>
          <span class="slot-tier">Tier ${card.tier}</span>
        </header>
        <div class="slot-drop${canUpload ? "" : " is-disabled"}" tabindex="${canUpload ? 0 : -1}" role="button"
          aria-disabled="${!canUpload}" aria-label="Add the ${escapeHtml(card.file_name)} picture">
          ${asset ? `<img src="${asset.url}?v=${encodeURIComponent(asset.updated_at || "")}" alt="${escapeHtml(card.key)}" />`
            : `<span>${canUpload ? "Drop the picture here or click" : `Approve ${escapeHtml(card.parent)} first`}</span>`}
          <input type="file" accept="image/png,image/jpeg,image/webp" hidden ${canUpload ? "" : "disabled"} />
        </div>
        ${asset ? `<p class="slot-note">${escapeHtml(asset.validation?.method || "")}${problems.length ? ` — <span class="is-error">${escapeHtml(problems.join("; "))}</span>` : ""}</p>` : ""}
        <ol class="slot-steps">
          <li>${card.parent ? (card.parent_ready
              ? `Attach <a href="${card.parent_input_url}" download>the input picture</a> (${escapeHtml(card.parent)}).`
              : `Attach the ${escapeHtml(card.parent)} picture once it is approved.`)
            : "Start a new picture (no attachment)."}</li>
          ${card.region_text ? `<li>Select: ${escapeHtml(card.region_text)}.</li>` : ""}
          <li>Prompt <button type="button" class="btn btn-ghost btn-sm slot-copy">Copy</button>
            <textarea class="slot-prompt" readonly rows="4">${escapeHtml(card.prompt)}</textarea></li>
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
    const pending = cards.filter((card) => card.asset && card.asset.review_state === "needs_review");
    $("profile-approve-all").hidden = !pending.length;
    $("profile-approve-all").textContent = `Approve all pending (${pending.length})`;
    $("profile-slots").innerHTML = GROUPS.map(([group, title]) => {
      const inGroup = cards.filter((card) => card.group === group);
      return inGroup.length ? `<section class="slot-group"><h4>${title}</h4><div class="slot-grid">${inGroup.map(slotCard).join("")}</div></section>` : "";
    }).join("");
  }

  async function refreshSelected(message) {
    const id = state.selectedId;
    await loadProfiles(id);
    if (id) await openProfile(id);
    if (message) notice(message);
  }

  async function uploadToSlot(slotKey, file) {
    const card = document.querySelector(`.slot-card[data-slot="${slotKey}"]`);
    const drop = card?.querySelector(".slot-drop");
    if (drop) {  // local preview at once; replaced by the stored, aligned picture after the response
      drop.innerHTML = `<img src="${URL.createObjectURL(file)}" alt="" class="is-preview" /><span class="slot-busy">Placing and checking…</span>`;
    }
    try {
      await Api.uploadProfileSlot(state.selectedId, slotKey, file);
      await refreshSelected(`${slotKey}.png stored. Check it, then approve.`);
    } catch (error) {
      notice(`${slotKey}: ${error.message || "the picture could not be stored"}`, true);
      renderSlots();
    }
  }

  async function review(assetId, decision) {
    try {
      await Api.reviewProfileAsset(state.selectedId, assetId, decision);
      await refreshSelected(decision === "approve" ? "Approved." : "Rejected.");
    } catch (error) {
      notice(error.message || "The review could not be saved.", true);
    }
  }

  function setupSlotEvents() {
    const container = $("profile-slots");
    container.addEventListener("click", async (event) => {
      const card = event.target.closest(".slot-card");
      if (!card || event.target.tagName === "INPUT") return;  // the file input's own click must not reopen it
      const slot = state.slots.slots.find((item) => item.key === card.dataset.slot);
      if (event.target.closest(".slot-copy")) {
        await navigator.clipboard?.writeText(slot.prompt).catch(() => {});
        event.target.textContent = "Copied";
        return;
      }
      if (event.target.closest(".slot-approve")) return review(slot.asset.id, "approve");
      if (event.target.closest(".slot-reject")) return review(slot.asset.id, "reject");
      const drop = event.target.closest(".slot-drop");
      if (drop && !drop.classList.contains("is-disabled") && event.target.tagName !== "A") drop.querySelector("input").click();
    });
    container.addEventListener("change", (event) => {
      const input = event.target.closest(".slot-drop input");
      if (input?.files?.[0]) uploadToSlot(input.closest(".slot-card").dataset.slot, input.files[0]);
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
  function scheduleSave() {
    $("profile-save-state").textContent = "Saving…";
    clearTimeout(saveTimer);
    saveTimer = setTimeout(async () => {
      const form = $("profile-details-form");
      const patch = {
        intro: form.elements.intro.value,
        personality: form.elements.personality.value.split(",").map((item) => item.trim()).filter(Boolean),
        speaking_style: form.elements.speaking_style.value,
      };
      try {
        await Api.patchProfile(state.selectedId, patch);
        $("profile-save-state").textContent = "Saved";
      } catch (error) {
        $("profile-save-state").textContent = `Not saved: ${error.message || "try again"}`;
      }
    }, 600);
  }

  // ------------------------------------------------------------------ actions

  async function act(work, message) {
    try {
      await work();
      await refreshSelected(message);
    } catch (error) {
      notice(error.message || "That did not work.", true);
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
    $("profile-new").addEventListener("click", showCreate);
    $("profile-create-form").addEventListener("submit", submitCreate);
    $("profile-create-cancel").addEventListener("click", () => {
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
    $("profile-delete").addEventListener("click", () => {
      if (!window.confirm("Delete this character for good? Its pictures are removed too.")) return;
      act(async () => {
        await Api.deleteProfile(state.selectedId);
        state.selectedId = null;
        $("profile-detail").hidden = true;
      }, "Deleted.");
    });
    $("profile-approve-all").addEventListener("click", () => {
      const ids = state.slots.slots.filter((card) => card.asset?.review_state === "needs_review").map((card) => card.asset.id);
      act(() => Api.approveProfileAssets(state.selectedId, ids), `${ids.length} picture(s) approved.`);
    });
    $("profile-bulk").addEventListener("change", (event) => {
      const files = [...(event.target.files || [])];
      event.target.value = "";
      if (!files.length) return;
      act(async () => {
        const result = await Api.uploadProfileSlotsBatch(state.selectedId, files);
        const lines = [`${result.stored.length} stored`];
        if (result.unmatched.length) lines.push(`${result.unmatched.length} not named after a slot (drop them on their card)`);
        if (result.failed.length) lines.push(`${result.failed.length} refused: ${result.failed.map((item) => `${item.file} (${item.reason})`).join("; ")}`);
        setTimeout(() => notice(lines.join(" · "), Boolean(result.failed.length)), 0);
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
