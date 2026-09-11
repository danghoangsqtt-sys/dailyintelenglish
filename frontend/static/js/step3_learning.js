/**
 * Step 3 — Learning Content. UI state + validation only; all persistence
 * goes through Api.* (frontend/static/js/api.js), never fetch() directly (CR-05).
 */
(() => {
  // UI tab id -> LearningPack section key (the API/model uses "questions", the tab is "quiz").
  const TAB_SECTION = { vocabulary: "vocabulary", idioms: "idioms", grammar: "grammar", quiz: "questions" };

  const state = {
    projectId: null,
    project: null,
    pack: null,
    packLoadFailed: false,
    isGenerating: false,
    saveStatus: "saved", // "saved" | "dirty" | "saving" | "failed"
    saveQueued: false,
    dirtySections: new Set(),
    revealedQuiz: new Set(),
    activeTab: "vocabulary",
  };

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str == null ? "" : str;
    return div.innerHTML;
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

  function setSaveStatusState(newStatus, customMessage) {
    state.saveStatus = newStatus;
    const el = document.getElementById("save-status");
    if (!el) return;
    if (newStatus === "saving") {
      el.innerHTML = customMessage || "Saving…";
    } else if (newStatus === "saved") {
      el.innerHTML = customMessage || "Saved";
      setTimeout(() => {
        if (state.saveStatus === "saved" && el.textContent === (customMessage || "Saved")) {
          el.innerHTML = "";
        }
      }, 2000);
    } else if (newStatus === "dirty") {
      el.innerHTML = customMessage || "Unsaved changes";
    } else if (newStatus === "failed") {
      el.innerHTML =
        customMessage ||
        'Save failed — <button type="button" class="btn btn-ghost btn-xs" id="retry-save-btn" style="text-decoration:underline;padding:0 4px;font-size:12px;">Retry</button>';
      const retryBtn = document.getElementById("retry-save-btn");
      if (retryBtn) {
        retryBtn.onclick = (e) => {
          e.stopPropagation();
          autosave();
        };
      }
    }
    applyStateToDom();
  }

  function applyStateToDom() {
    const isBusy = state.saveStatus === "saving" || state.isGenerating;
    const hasUnsaved = state.saveStatus === "dirty" || state.saveStatus === "failed" || state.dirtySections.size > 0;
    const regenBtn = document.getElementById("regenerate-btn");
    if (regenBtn) regenBtn.disabled = isBusy || hasUnsaved;
    const nextBtn = document.getElementById("next-step-btn");
    if (nextBtn) nextBtn.disabled = state.saveStatus === "saving";
  }

  function setGenerateLoading(loading) {
    const btn = document.getElementById("generate-btn");
    btn.disabled = loading;
    btn.innerHTML = loading ? '<span class="spinner"></span> Generating…' : "✨ Generate Learning Pack";
  }

  function renderHeader() {
    document.getElementById("project-name").textContent = state.project.name;
    document.getElementById("project-badges").innerHTML = `
      <span class="badge">${escapeHtml(state.project.cefr_level)}</span>
      <span class="badge">${escapeHtml(state.project.genre)}</span>
    `;
  }

  // --- Tab content rendering ---

  function fieldSpan(section, index, field, value, extraClass = "") {
    return `<span class="field ${extraClass}" contenteditable="true" data-section="${section}" data-index="${index}" data-field="${field}">${escapeHtml(value)}</span>`;
  }

  function vocabItemHtml(item, index) {
    return `
      <div class="card item-card">
        <div class="item-head">
          ${fieldSpan("vocabulary", index, "word", item.word, "item-title")}
          ${fieldSpan("vocabulary", index, "part_of_speech", item.part_of_speech, "badge")}
          ${fieldSpan("vocabulary", index, "ipa", item.ipa, "ipa")}
        </div>
        <div class="field-row"><span class="field-label">EN:</span> ${fieldSpan("vocabulary", index, "definition_en", item.definition_en)}</div>
        <div class="field-row"><span class="field-label">VI:</span> ${fieldSpan("vocabulary", index, "definition_vi", item.definition_vi)}</div>
        <div class="field-row example-sentence"><span class="field-label">Example:</span> ${fieldSpan("vocabulary", index, "example_sentence", item.example_sentence)}</div>
      </div>`;
  }

  function idiomItemHtml(item, index) {
    return `
      <div class="card item-card">
        <div class="item-head">
          ${fieldSpan("idioms", index, "phrase", item.phrase, "item-title")}
        </div>
        <div class="field-row"><span class="field-label">EN:</span> ${fieldSpan("idioms", index, "meaning_en", item.meaning_en)}</div>
        <div class="field-row"><span class="field-label">VI:</span> ${fieldSpan("idioms", index, "meaning_vi", item.meaning_vi)}</div>
        <div class="field-row example-sentence"><span class="field-label">Example:</span> ${fieldSpan("idioms", index, "example_sentence", item.example_sentence)}</div>
      </div>`;
  }

  function grammarItemHtml(item, index) {
    const examples = (item.examples || []).map((ex) => `<li>${escapeHtml(ex)}</li>`).join("");
    return `
      <div class="card item-card">
        <div class="item-head">
          ${fieldSpan("grammar", index, "point", item.point, "item-title")}
        </div>
        <div class="field-row"><span class="field-label">Structure:</span> ${fieldSpan("grammar", index, "structure", item.structure, "ipa")}</div>
        <div class="field-row"><span class="field-label">EN:</span> ${fieldSpan("grammar", index, "explanation_en", item.explanation_en)}</div>
        <div class="field-row"><span class="field-label">VI:</span> ${fieldSpan("grammar", index, "explanation_vi", item.explanation_vi)}</div>
        ${examples ? `<ul class="examples-list">${examples}</ul>` : ""}
      </div>`;
  }

  function quizItemHtml(item, index) {
    const options = item.options || [];
    const optionsHtml = options
      .map((opt) => `<li class="${opt === item.correct_answer ? "correct" : ""}">${escapeHtml(opt)}</li>`)
      .join("");
    const revealed = state.revealedQuiz.has(index);
    return `
      <div class="card item-card">
        <div class="item-head">
          ${fieldSpan("questions", index, "question", item.question, "item-title")}
        </div>
        ${options.length ? `<ul class="options-list">${optionsHtml}</ul>` : ""}
        <button class="btn btn-ghost btn-sm" data-action="toggle-answer" data-index="${index}">
          ${revealed ? "🙈 Hide Answer" : "👁 Show Answer"}
        </button>
        <div class="quiz-answer" ${revealed ? "" : "hidden"}>
          <div class="field-row"><span class="field-label">Correct:</span> ${fieldSpan("questions", index, "correct_answer", item.correct_answer)}</div>
          <div class="field-row"><span class="field-label">Why:</span> ${fieldSpan("questions", index, "explanation", item.explanation)}</div>
        </div>
      </div>`;
  }

  const TAB_RENDERERS = {
    vocabulary: { key: "vocabulary", itemHtml: vocabItemHtml, empty: "No vocabulary items in this pack." },
    idioms: { key: "idioms", itemHtml: idiomItemHtml, empty: "No idioms in this pack." },
    grammar: { key: "grammar", itemHtml: grammarItemHtml, empty: "No grammar points in this pack." },
    quiz: { key: "questions", itemHtml: quizItemHtml, empty: "No quiz questions in this pack." },
  };

  function renderTab(tab) {
    const { key, itemHtml, empty } = TAB_RENDERERS[tab];
    const panel = document.getElementById(`${tab}-panel`);
    const items = (state.pack && state.pack[key]) || [];
    panel.innerHTML = items.length
      ? items.map((item, index) => itemHtml(item, index)).join("")
      : `<div class="empty-state">${empty}</div>`;
  }

  function renderAllTabs() {
    Object.keys(TAB_RENDERERS).forEach(renderTab);
    applyStateToDom();
  }

  function render() {
    const generatePanel = document.getElementById("generate-panel");
    const contentWrap = document.getElementById("content-wrap");

    if (state.packLoadFailed) {
      // Loading the existing pack failed — never show "Generate", since a real
      // pack may already exist and Generate would silently overwrite it.
      generatePanel.hidden = true;
      contentWrap.hidden = true;
      return;
    }

    if (!state.pack) {
      generatePanel.hidden = false;
      contentWrap.hidden = true;
      return;
    }

    generatePanel.hidden = true;
    contentWrap.hidden = false;
    renderAllTabs();
  }

  // --- Tabs ---

  function switchTab(tab) {
    if (!TAB_RENDERERS[tab]) return;
    state.activeTab = tab;
    document.querySelectorAll("#content-tabs .tab-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tab);
    });
    document.querySelectorAll(".tab-panel").forEach((panel) => {
      panel.hidden = panel.dataset.tabPanel !== tab;
    });
  }

  function handleTabsClick(e) {
    const btn = e.target.closest(".tab-btn");
    if (btn) switchTab(btn.dataset.tab);
  }

  // --- Autosave (coalesced trailing save) ---

  function markDirty(section) {
    state.dirtySections.add(section);
    setSaveStatusState("dirty");
    autosave();
  }

  async function runAutosave() {
    if (state.saveStatus === "saving") {
      state.saveQueued = true;
      return;
    }
    const sections = Array.from(state.dirtySections);
    if (sections.length === 0) {
      if (state.saveStatus !== "failed") {
        setSaveStatusState("saved");
      }
      return;
    }

    state.dirtySections.clear();
    setSaveStatusState("saving");
    clearError();

    try {
      const payload = {};
      sections.forEach((section) => {
        payload[section] = state.pack[section];
      });
      await Api.saveLearningPack(state.projectId, payload);

      if (state.dirtySections.size > 0 || state.saveQueued) {
        state.saveQueued = false;
        setSaveStatusState("dirty");
        await runAutosave();
      } else {
        setSaveStatusState("saved");
      }
    } catch (err) {
      console.error("Failed to save learning content:", err);
      // Re-add unsaved sections so edits remain dirty and recoverable
      sections.forEach((s) => state.dirtySections.add(s));
      setSaveStatusState("failed");
      showError("We couldn't save your edit. Please check your connection and click Retry.");
    }
  }

  function autosave() {
    if (state.saveStatus === "saving") {
      state.saveQueued = true;
      return;
    }
    setSaveStatusState("dirty");
    runAutosave();
  }

  // --- Inline field editing ---

  function commitField(el) {
    const { section, index, field } = el.dataset;
    if (!section || index === undefined || !field) return;
    const item = state.pack[section] && state.pack[section][Number(index)];
    if (!item) return;

    const newValue = el.textContent.trim();
    if (newValue === item[field]) return;
    if (!newValue) {
      // Never persist an empty required field — revert the DOM to the last known value.
      el.textContent = item[field];
      return;
    }

    item[field] = newValue;
    markDirty(section);
    renderTab(state.activeTab);
  }

  function handleContentFocusOut(e) {
    const field = e.target.closest(".field");
    if (field) commitField(field);
  }

  function handleContentKeydown(e) {
    const field = e.target.closest(".field");
    if (!field) return;
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      field.blur();
    } else if (e.key === "Escape") {
      const { section, index, field: fieldName } = field.dataset;
      const item = state.pack[section] && state.pack[section][Number(index)];
      field.textContent = item ? item[fieldName] : field.textContent;
      field.blur();
    }
  }

  function handleContentClick(e) {
    const toggleBtn = e.target.closest('[data-action="toggle-answer"]');
    if (!toggleBtn) return;
    const index = Number(toggleBtn.dataset.index);
    if (state.revealedQuiz.has(index)) {
      state.revealedQuiz.delete(index);
    } else {
      state.revealedQuiz.add(index);
    }
    renderTab("quiz");
  }

  // --- Generate / Regenerate ---

  async function handleGenerate() {
    if (state.isGenerating || state.saveStatus !== "saved" || state.dirtySections.size > 0) {
      if (state.saveStatus !== "saved" || state.dirtySections.size > 0) {
        showError("Please save or resolve unsaved edits before generating a new pack.");
      }
      return;
    }
    state.isGenerating = true;
    setGenerateLoading(true);
    clearError();

    try {
      state.pack = await Api.generateLearningPack(state.projectId);
      state.revealedQuiz.clear();
      render();
    } catch (err) {
      console.error("Failed to generate learning content:", err);
      showError("We couldn't generate the learning pack. Please try again.");
    } finally {
      state.isGenerating = false;
      setGenerateLoading(false);
    }
  }

  function handleRegenerate() {
    if (state.isGenerating || state.saveStatus !== "saved" || state.dirtySections.size > 0) {
      if (state.saveStatus !== "saved" || state.dirtySections.size > 0) {
        showError("Please save or resolve unsaved edits before regenerating the learning pack.");
      }
      return;
    }
    const confirmed = confirm(
      "This will overwrite the entire learning pack (vocabulary, idioms, grammar, quiz) with a brand new AI-generated version. Continue?"
    );
    if (confirmed) handleGenerate();
  }

  async function handleNextStep() {
    const nextBtn = document.getElementById("next-step-btn");

    if (state.saveStatus === "saving") {
      setSaveStatusState("saving", "Saving changes before proceeding…");
      if (nextBtn) nextBtn.disabled = true;
      const startTime = Date.now();
      while (state.saveStatus === "saving") {
        if (Date.now() - startTime > 10000) break; // 10s timeout
        await new Promise((r) => setTimeout(r, 50));
      }
    } else if (state.saveStatus === "dirty" || state.saveStatus === "failed" || state.dirtySections.size > 0 || state.saveQueued) {
      if (nextBtn) nextBtn.disabled = true;
      await runAutosave();
    }

    if (state.saveStatus === "saved" && state.dirtySections.size === 0) {
      window.location.href = `/step4?project_id=${encodeURIComponent(state.projectId)}`;
    } else {
      if (nextBtn) nextBtn.disabled = false;
      showError("Cannot proceed: Changes could not be saved. Please click Retry.");
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
    document.getElementById("regenerate-btn").addEventListener("click", handleRegenerate);
    document.getElementById("next-step-btn").addEventListener("click", handleNextStep);
    document.getElementById("content-tabs").addEventListener("click", handleTabsClick);
    const contentWrap = document.getElementById("content-wrap");
    contentWrap.addEventListener("click", handleContentClick);
    contentWrap.addEventListener("focusout", handleContentFocusOut);
    contentWrap.addEventListener("keydown", handleContentKeydown);

    try {
      state.pack = await Api.getLearningPack(state.projectId);
      state.packLoadFailed = false;
    } catch (err) {
      console.error("Failed to load existing learning content:", err);
      state.packLoadFailed = true;
      showError("We couldn't load the existing learning content. Please try refreshing.");
    }
    render();
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("theme-toggle").addEventListener("click", Theme.toggle);
    window.addEventListener("beforeunload", (e) => {
      if (state.saveStatus !== "saved" || state.saveQueued || state.dirtySections.size > 0) {
        e.preventDefault();
        e.returnValue = "";
      }
    });
    init();
  });
})();
