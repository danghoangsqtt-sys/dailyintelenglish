/**
 * Phase 33 (Task 33.7, D80): the game-style character selector shared by Step 1 and Step 5.
 *
 * CharacterSelector.open({ slots, profiles, startSlot, onChoose }):
 *   slots    [{ index, label, characterId }] -- the project's speakers
 *   profiles active profiles from Api.listProfiles()
 *   onChoose (slotIndex, profile) => Promise|void -- called only by "Choose for <speaker>"
 * Clicking a roster card only previews it. A profile used by another speaker, or not ready for videos, cannot be chosen.
 */
const CharacterSelector = (() => {
  const STYLE_ID = "character-selector-style";
  const CSS = `
    .cs-backdrop { position: fixed; inset: 0; background: rgba(10, 20, 15, .55); z-index: 1000; display: grid; place-items: center; }
    .cs-dialog { width: min(1100px, calc(100% - 32px)); height: min(760px, calc(100% - 32px)); background: var(--surface);
      color: var(--text); border-radius: var(--radius); box-shadow: var(--shadow); display: grid;
      grid-template-rows: auto auto 1fr auto; overflow: hidden; font-size: 16px; }
    .cs-head { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; border-bottom: 1px solid var(--border); }
    .cs-head h2 { margin: 0; font-size: 20px; }
    .cs-slots { display: flex; flex-wrap: wrap; gap: 8px; padding: 10px 18px; border-bottom: 1px solid var(--border); }
    .cs-slot { border: 1px solid var(--border); border-radius: 999px; padding: 6px 12px; background: var(--surface); color: var(--text); cursor: pointer; }
    .cs-slot[aria-pressed="true"] { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
    .cs-body { display: grid; grid-template-columns: minmax(260px, 1fr) minmax(0, 1.2fr); gap: 0; min-height: 0; }
    .cs-roster { overflow: auto; padding: 14px 18px; border-right: 1px solid var(--border); display: grid; gap: 10px; align-content: start; }
    .cs-roster input { font-size: 16px; }
    .cs-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; }
    .cs-card { display: grid; gap: 4px; padding: 8px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface);
      color: var(--text); cursor: pointer; text-align: left; }
    .cs-card[aria-current="true"] { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
    .cs-card.is-unavailable { opacity: .55; }
    .cs-card img, .cs-empty { width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 8px; background: var(--border);
      display: grid; place-items: center; font-size: 28px; color: var(--muted); }
    .cs-card small { color: var(--muted); font-size: 13px; }
    .cs-preview { overflow: auto; padding: 18px; display: grid; gap: 10px; align-content: start; }
    .cs-preview img, .cs-preview .cs-empty { width: min(320px, 100%); aspect-ratio: 5 / 6; object-fit: contain; background: var(--border); }
    .cs-preview h3 { margin: 0; font-size: 22px; }
    .cs-note { color: var(--muted); }
    .cs-warn { color: var(--danger); }
    .cs-foot { display: flex; gap: 10px; justify-content: flex-end; align-items: center; padding: 12px 18px; border-top: 1px solid var(--border); }
    .cs-foot .cs-status { margin-right: auto; color: var(--muted); }
    @media (max-width: 760px) { .cs-body { grid-template-columns: 1fr; } .cs-roster { border-right: 0; border-bottom: 1px solid var(--border); max-height: 40vh; } }
  `;

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function picture(profile) {
    const pictures = profile.pictures || {};
    return pictures.portrait || pictures.base || null;
  }

  // Ready for a project: a profile whose readiness says so, or a character locked in the older local-generation flow.
  function castReady(profile) {
    return Boolean(profile.readiness?.video_ready) || profile.legacy_status === "locked";
  }

  function missing(profile) {
    const readiness = profile.readiness || {};
    return ["profile", "voice", "core_visuals"].flatMap((key) => readiness[key]?.missing || []);
  }

  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = CSS;
    document.head.append(style);
  }

  function open({ slots, profiles, startSlot = slots[0]?.index, onChoose }) {
    ensureStyle();
    const state = { slot: startSlot, previewId: null, query: "", busy: false };
    const slotOf = (index) => slots.find((slot) => slot.index === index);
    state.previewId = slotOf(state.slot)?.characterId || null;
    const backdrop = document.createElement("div");
    backdrop.className = "cs-backdrop";
    backdrop.innerHTML = `
      <div class="cs-dialog" role="dialog" aria-modal="true" aria-labelledby="cs-title">
        <div class="cs-head"><h2 id="cs-title">Choose the characters</h2>
          <button type="button" class="btn btn-ghost btn-sm" data-cs="close">Close</button></div>
        <div class="cs-slots" role="group" aria-label="Speakers"></div>
        <div class="cs-body">
          <div class="cs-roster"><input type="search" placeholder="Search characters" aria-label="Search characters" data-cs="search" />
            <div class="cs-grid" data-cs="grid"></div></div>
          <div class="cs-preview" data-cs="preview" aria-live="polite"></div>
        </div>
        <div class="cs-foot"><span class="cs-status" data-cs="status"></span>
          <button type="button" class="btn btn-primary" data-cs="choose" disabled>Choose</button></div>
      </div>`;
    const $ = (name) => backdrop.querySelector(`[data-cs="${name}"]`);

    function usedBy(profileId) {
      return slots.find((slot) => slot.characterId === profileId && slot.index !== state.slot) || null;
    }

    function blocker(profile) {
      const other = usedBy(profile.id);
      if (other) return `Already chosen for ${other.label}.`;
      const needed = missing(profile);
      if (!castReady(profile)) return `Not ready for videos yet: ${needed.slice(0, 4).join(", ") || "add its pictures"}.`;
      return null;
    }

    function render() {
      backdrop.querySelector(".cs-slots").innerHTML = slots.map((slot) => {
        const chosen = profiles.find((profile) => profile.id === slot.characterId);
        return `<button type="button" class="cs-slot" data-slot="${slot.index}" aria-pressed="${slot.index === state.slot}">
          ${escapeHtml(slot.label)}: ${chosen ? escapeHtml(chosen.name) : "<em>not chosen</em>"}</button>`;
      }).join("");
      const query = state.query.trim().toLowerCase();
      $("grid").innerHTML = profiles.filter((profile) => !query || profile.name.toLowerCase().includes(query)).map((profile) => {
        const image = picture(profile);
        return `<button type="button" class="cs-card${blocker(profile) ? " is-unavailable" : ""}" data-id="${profile.id}"
            aria-current="${profile.id === state.previewId}">
          ${image ? `<img src="${image}" alt="" loading="lazy" />` : '<span class="cs-empty" aria-hidden="true">?</span>'}
          <strong>${escapeHtml(profile.name)}</strong><small>${escapeHtml(profile.gender)} · ${escapeHtml(profile.accent || "")}</small>
        </button>`;
      }).join("") || '<p class="cs-note">No character matches.</p>';
      const profile = profiles.find((item) => item.id === state.previewId);
      const slot = slotOf(state.slot);
      if (!profile) {
        $("preview").innerHTML = '<p class="cs-note">Click a character to see it here.</p>';
        $("choose").disabled = true;
        $("choose").textContent = `Choose for ${slot?.label || "speaker"}`;
        return;
      }
      const image = picture(profile);
      const reason = blocker(profile);
      $("preview").innerHTML = `
        ${image ? `<img src="${image}" alt="${escapeHtml(profile.name)}" />` : '<span class="cs-empty" aria-hidden="true">?</span>'}
        <h3>${escapeHtml(profile.name)}</h3>
        <p>${escapeHtml(profile.gender)} · ${escapeHtml(profile.accent)} accent · voice ${escapeHtml(profile.voice?.voice_id || "")}
          · stands on the ${profile.gender === "male" ? "left" : "right"}</p>
        ${profile.intro ? `<p>${escapeHtml(profile.intro)}</p>` : ""}
        ${(profile.personality || []).length ? `<p class="cs-note">Personality: ${escapeHtml(profile.personality.join(", "))}</p>` : ""}
        <p class="cs-note">${profile.readiness?.talking_ready ? "Ready for talking videos." : profile.readiness?.video_ready
          ? "Ready for videos; the talking characters mode needs its Tier 1 pictures." : ""}</p>
        ${reason ? `<p class="cs-warn">${escapeHtml(reason)}</p>` : ""}`;
      $("choose").disabled = Boolean(reason) || state.busy || slot?.characterId === profile.id;
      $("choose").textContent = slot?.characterId === profile.id ? `Chosen for ${slot.label}` : `Choose for ${slot?.label || "speaker"}`;
    }

    function close() {
      backdrop.remove();
      document.removeEventListener("keydown", onKey);
    }

    function onKey(event) {
      if (event.key === "Escape") close();
    }

    backdrop.addEventListener("click", async (event) => {
      if (event.target === backdrop || event.target.closest('[data-cs="close"]')) return close();
      const slotButton = event.target.closest(".cs-slot");
      if (slotButton) {
        state.slot = Number(slotButton.dataset.slot);
        state.previewId = slotOf(state.slot)?.characterId || state.previewId;
        return render();
      }
      const card = event.target.closest(".cs-card");
      if (card) {
        state.previewId = card.dataset.id;  // preview only: nothing is assigned until "Choose for ..."
        return render();
      }
      if (event.target.closest('[data-cs="choose"]')) {
        const profile = profiles.find((item) => item.id === state.previewId);
        const slot = slotOf(state.slot);
        if (!profile || !slot || blocker(profile)) return;
        state.busy = true;
        $("status").textContent = "Saving…";
        render();
        try {
          await onChoose(slot.index, profile);
          slot.characterId = profile.id;
          $("status").textContent = `${profile.name} is ${slot.label}.`;
          const next = slots.find((item) => !item.characterId);
          if (next) state.slot = next.index;
        } catch (error) {
          $("status").textContent = error?.message || "That could not be saved.";
        } finally {
          state.busy = false;
          render();
        }
      }
    });
    $("search").addEventListener("input", (event) => {
      state.query = event.target.value;
      render();
    });
    document.addEventListener("keydown", onKey);
    document.body.append(backdrop);
    render();
    $("search").focus();
    return { close };
  }

  return { open, castReady };
})();
