/** Settings page: read-only AI provider status. Local-only mode (Task 14.7) --
 * no API-key input, no mode selector; DIE_AI_ALLOW_CLOUD + DIE_AI_MODE + a key
 * is the unsupported rollback path (see README.md), not something this UI
 * exposes. */
(() => {
  const aiModeStatusEl = document.getElementById("ai-mode-status");

  const AI_MODE_SOURCE_LABELS = {
    database: "Saved in Settings",
    env: "Default (from environment)",
  };

  function renderAiModeStatus(status) {
    if (!aiModeStatusEl) return;
    const label = AI_MODE_SOURCE_LABELS[status.ai_mode_source] || status.ai_mode_source;
    aiModeStatusEl.textContent = `${status.ai_mode} — ${label}`;
  }

  async function loadStatus() {
    try {
      const status = await Api.getSettings();
      renderAiModeStatus(status);
    } catch (error) {
      if (aiModeStatusEl) aiModeStatusEl.textContent = error.message || "Could not load current status.";
    }
  }

  loadStatus();
})();
