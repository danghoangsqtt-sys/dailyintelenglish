/**
 * Step 2 — AI Script Generation. UI state + validation only; all persistence
 * goes through Api.* (frontend/static/js/api.js), never fetch() directly (CR-05).
 */
(() => {
  const SPEAKER_COLORS = ["#7c3aed", "#0ea5e9", "#f59e0b", "#10b981", "#ef4444", "#ec4899"];

  const state = {
    projectId: null,
    project: null,
    lines: [],
    isGenerating: false,
    regeneratingLineId: null,
  };

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str == null ? "" : str;
    return div.innerHTML;
  }

  function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  function showError(message) {
    const banner = document.getElementById("error-banner");
    banner.textContent = message;
    banner.hidden = false;
    banner.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function clearError() {
    const banner = document.getElementById("error-banner");
    banner.hidden = true;
    banner.textContent = "";
  }

  function setSaveStatus(text) {
    document.getElementById("save-status").textContent = text;
  }

  function setGenerateLoading(loading) {
    const btn = document.getElementById("generate-btn");
    btn.disabled = loading;
    btn.innerHTML = loading ? '<span class="spinner"></span> Generating…' : "✨ Generate Script";
  }

  function speakerIndex(speakerId) {
    const index = state.project.speakers.findIndex((s) => s.id === speakerId);
    return index >= 0 ? index : 0;
  }

  function speakerColor(speakerId) {
    return SPEAKER_COLORS[speakerIndex(speakerId) % SPEAKER_COLORS.length];
  }

  function speakerName(speakerId) {
    const speaker = state.project.speakers.find((s) => s.id === speakerId);
    return speaker ? speaker.name : "Unknown speaker";
  }

  function renderHeader() {
    document.getElementById("project-name").textContent = state.project.name;
    const speakerCount = state.project.speakers.length;
    document.getElementById("project-badges").innerHTML = `
      <span class="badge">${escapeHtml(state.project.cefr_level)}</span>
      <span class="badge">${escapeHtml(state.project.genre)}</span>
      <span class="badge">${speakerCount} speaker${speakerCount === 1 ? "" : "s"}</span>
    `;
  }

  function lineCardHtml(line) {
    const color = speakerColor(line.speaker_id);
    const name = speakerName(line.speaker_id);
    const notes = line.language_notes || {};
    const collocations = (notes.collocations || []).join(", ") || "—";
    const idioms = (notes.idioms || []).join(", ") || "—";
    const grammar = notes.grammar_point || "—";
    const isRegenerating = state.regeneratingLineId === line.id;

    return `
      <div class="card line-card" data-line-id="${line.id}">
        <div class="line-header">
          <span class="speaker-chip" style="background:${hexToRgba(color, 0.15)}; border-color:${hexToRgba(color, 0.4)}; color:${color};">${escapeHtml(name)}</span>
          <button class="btn btn-ghost btn-sm" data-action="regenerate" ${isRegenerating ? "disabled" : ""}>
            ${isRegenerating ? '<span class="spinner spinner-dark"></span> Regenerating…' : "🔄 Regenerate this line"}
          </button>
        </div>
        <div class="line-text" data-action="edit-text">${escapeHtml(line.text)}</div>
        <details class="notes-details">
          <summary>Language notes</summary>
          <div class="notes-body">
            <div><strong>Collocations:</strong> ${escapeHtml(collocations)}</div>
            <div><strong>Idioms:</strong> ${escapeHtml(idioms)}</div>
            <div><strong>Grammar:</strong> ${escapeHtml(grammar)}</div>
          </div>
        </details>
      </div>`;
  }

  function renderScript() {
    const generatePanel = document.getElementById("generate-panel");
    const list = document.getElementById("script-list");
    const actions = document.getElementById("script-actions");

    if (state.lines.length === 0) {
      generatePanel.hidden = false;
      actions.hidden = true;
      list.innerHTML = "";
      return;
    }

    generatePanel.hidden = true;
    actions.hidden = false;
    list.innerHTML = state.lines.map(lineCardHtml).join("");
  }

  async function autosave() {
    setSaveStatus("Saving…");
    try {
      const payload = state.lines.map((line) => ({
        speaker_id: line.speaker_id,
        text: line.text,
        language_notes: line.language_notes || { collocations: [], idioms: [], grammar_point: "" },
      }));
      await Api.saveScript(state.projectId, payload);
      setSaveStatus("Saved");
      setTimeout(() => {
        if (document.getElementById("save-status").textContent === "Saved") setSaveStatus("");
      }, 2000);
    } catch (err) {
      console.error("Failed to save script:", err);
      setSaveStatus("");
      showError("We couldn't save your edit. Please try again.");
    }
  }

  function startEdit(textEl) {
    const card = textEl.closest("[data-line-id]");
    const lineId = card.dataset.lineId;
    const line = state.lines.find((l) => l.id === lineId);
    if (!line) return;

    textEl.classList.add("editing");
    textEl.innerHTML = `<textarea>${escapeHtml(line.text)}</textarea>`;
    const textarea = textEl.querySelector("textarea");
    textarea.focus();
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);

    function commit() {
      const newText = textarea.value.trim();
      textEl.classList.remove("editing");
      if (newText && newText !== line.text) {
        line.text = newText;
        renderScript();
        autosave();
      } else {
        renderScript();
      }
    }

    textarea.addEventListener("blur", commit);
    textarea.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        textarea.blur();
      } else if (e.key === "Escape") {
        textarea.value = line.text;
        textarea.blur();
      }
    });
  }

  async function handleRegenerate(lineId) {
    if (state.regeneratingLineId) return;
    state.regeneratingLineId = lineId;
    clearError();
    renderScript();

    try {
      const updated = await Api.regenerateLine(state.projectId, lineId);
      const index = state.lines.findIndex((l) => l.id === lineId);
      if (index !== -1) state.lines[index] = updated;
    } catch (err) {
      console.error("Failed to regenerate line:", err);
      showError("We couldn't regenerate this line. Please try again.");
    } finally {
      state.regeneratingLineId = null;
      renderScript();
    }
  }

  async function handleGenerate() {
    if (state.isGenerating) return;
    state.isGenerating = true;
    setGenerateLoading(true);
    clearError();

    try {
      state.lines = await Api.generateScript(state.projectId);
      renderScript();
    } catch (err) {
      console.error("Failed to generate script:", err);
      showError("We couldn't generate the script. Please try again.");
    } finally {
      state.isGenerating = false;
      setGenerateLoading(false);
    }
  }

  function handleRegenerateAll() {
    if (state.isGenerating) return;
    const confirmed = confirm(
      "This will overwrite the entire script with a brand new AI-generated version. Continue?"
    );
    if (confirmed) handleGenerate();
  }

  function handleNextStep() {
    window.location.href = `/step3?project_id=${encodeURIComponent(state.projectId)}`;
  }

  function handleScriptListClick(e) {
    const editTarget = e.target.closest("[data-action='edit-text']");
    if (editTarget && !editTarget.classList.contains("editing")) {
      startEdit(editTarget);
      return;
    }
    const regenBtn = e.target.closest("[data-action='regenerate']");
    if (regenBtn && !regenBtn.disabled) {
      const card = regenBtn.closest("[data-line-id]");
      handleRegenerate(card.dataset.lineId);
    }
  }

  async function init() {
    const params = new URLSearchParams(window.location.search);
    state.projectId = params.get("project_id");
    if (!state.projectId) {
      showError("Missing project. Please start from the Dashboard.");
      return;
    }

    try {
      state.project = await Api.getProject(state.projectId);
    } catch (err) {
      console.error("Failed to load project:", err);
      showError("We couldn't load this project. Please go back to the Dashboard.");
      return;
    }

    renderHeader();
    document.getElementById("generate-btn").addEventListener("click", handleGenerate);
    document.getElementById("regenerate-all-btn").addEventListener("click", handleRegenerateAll);
    document.getElementById("next-step-btn").addEventListener("click", handleNextStep);
    document.getElementById("script-list").addEventListener("click", handleScriptListClick);

    try {
      state.lines = await Api.getScript(state.projectId);
    } catch (err) {
      console.error("Failed to load existing script:", err);
      showError("We couldn't load the existing script. Please try refreshing.");
    }
    renderScript();
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("theme-toggle").addEventListener("click", Theme.toggle);
    init();
  });
})();
