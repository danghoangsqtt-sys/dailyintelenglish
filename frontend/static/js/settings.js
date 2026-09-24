/** Settings page (Task 18.3): AI mode selector (local / cloud-first), cloud
 * provider form (base URL, model, write-only key), test connection, and the
 * effective-mode/reason display (PM review C3) -- lets the page show WHY the
 * effective mode differs from the selected one, when it does.
 *
 * The diagnostic "cloud" (no-fallback) mode is deliberately not exposed here
 * -- only "local" and "cloud_first" are user-facing choices.
 */
(() => {
  const localRadio = document.getElementById("ai-mode-local");
  const cloudFirstRadio = document.getElementById("ai-mode-cloud-first");
  const disabledNoteEl = document.getElementById("ai-mode-disabled-note");
  const effectiveStatusEl = document.getElementById("effective-mode-status");
  const fallbackRateEl = document.getElementById("fallback-rate-status");

  const baseUrlInput = document.getElementById("cloud-base-url");
  const modelInput = document.getElementById("cloud-model");
  const fallbackModelsInput = document.getElementById("cloud-fallback-models");
  const apiKeyInput = document.getElementById("cloud-api-key");
  const keyStatusEl = document.getElementById("cloud-key-status");
  const circuitStatusEl = document.getElementById("circuit-status");

  const saveBtn = document.getElementById("save-cloud-settings-btn");
  const clearKeyBtn = document.getElementById("clear-cloud-key-btn");
  const testConnectionBtn = document.getElementById("test-connection-btn");
  const testConnectionResultEl = document.getElementById("test-connection-result");
  const saveStatusEl = document.getElementById("save-status");

  // Task 18.8: provider order, Gemini, OpenCode Zen.
  const providerOrderInput = document.getElementById("cloud-provider-order");
  const providerOrderStatusEl = document.getElementById("cloud-provider-order-status");

  const geminiBaseUrlInput = document.getElementById("gemini-base-url");
  const geminiModelsInput = document.getElementById("gemini-models");
  const geminiApiKeyInput = document.getElementById("gemini-api-key");
  const geminiKeyStatusEl = document.getElementById("gemini-key-status");
  const saveGeminiBtn = document.getElementById("save-gemini-settings-btn");
  const clearGeminiKeyBtn = document.getElementById("clear-gemini-key-btn");
  const geminiSaveStatusEl = document.getElementById("gemini-save-status");

  const zenBaseUrlInput = document.getElementById("zen-base-url");
  const zenModelInput = document.getElementById("zen-model");
  const zenApiKeyInput = document.getElementById("zen-api-key");
  const zenKeyStatusEl = document.getElementById("zen-key-status");
  const saveZenBtn = document.getElementById("save-zen-settings-btn");
  const clearZenKeyBtn = document.getElementById("clear-zen-key-btn");
  const zenSaveStatusEl = document.getElementById("zen-save-status");

  const EFFECTIVE_MODE_LABELS = { local: "Local", cloud: "Cloud", cloud_first: "Cloud-first" };

  function renderAiModeRadios(status) {
    if (!localRadio || !cloudFirstRadio) return;
    localRadio.checked = status.ai_mode === "local";
    cloudFirstRadio.checked = status.ai_mode === "cloud_first";
    cloudFirstRadio.disabled = !status.allow_cloud;
    cloudFirstRadio.closest(".settings-radio-option")?.classList.toggle("is-disabled", !status.allow_cloud);

    if (disabledNoteEl) {
      if (!status.allow_cloud) {
        disabledNoteEl.hidden = false;
        disabledNoteEl.textContent =
          "Cloud is disabled by DIE_AI_ALLOW_CLOUD=false — ask whoever manages this install's .env to enable it.";
        disabledNoteEl.classList.add("is-error");
      } else {
        disabledNoteEl.hidden = true;
        disabledNoteEl.classList.remove("is-error");
      }
    }
  }

  function renderEffectiveModeStatus(status) {
    if (!effectiveStatusEl) return;
    const selectedLabel = EFFECTIVE_MODE_LABELS[status.ai_mode] || status.ai_mode;
    const effectiveLabel = EFFECTIVE_MODE_LABELS[status.effective_mode] || status.effective_mode;
    if (status.effective_mode === status.ai_mode) {
      effectiveStatusEl.textContent = `Selected: ${selectedLabel} — running as ${effectiveLabel}.`;
    } else {
      effectiveStatusEl.textContent =
        `Selected: ${selectedLabel} — running as ${effectiveLabel} (${status.effective_reason}).`;
    }
  }

  function renderCloudForm(status) {
    if (baseUrlInput && document.activeElement !== baseUrlInput) baseUrlInput.value = status.cloud_base_url || "";
    if (modelInput && document.activeElement !== modelInput) modelInput.value = status.cloud_model || "";
    if (fallbackModelsInput && document.activeElement !== fallbackModelsInput) {
      fallbackModelsInput.value = (status.cloud_fallback_models || []).join(", ");
    }
    if (keyStatusEl) {
      const sourceLabel = { database: "saved in Settings", env: "from environment", none: "not configured" }[
        status.cloud_source
      ] || status.cloud_source;
      keyStatusEl.textContent = status.cloud_configured
        ? `Key ending in ${status.cloud_last4} (${sourceLabel}).`
        : `No key configured (${sourceLabel}).`;
      keyStatusEl.classList.remove("is-error", "is-success");
    }
  }

  function renderFallbackRate(health) {
    if (!fallbackRateEl) return;
    const rate = health && health.fallback_rate;
    if (!rate || !rate.window) {
      fallbackRateEl.textContent = "Fallback rate: no completed AI jobs yet.";
      return;
    }
    const pct = (value) => (value == null ? "n/a" : `${Math.round(value * 100)}%`);
    fallbackRateEl.textContent =
      `Fallback rate (last ${rate.window} jobs): ${pct(rate.call_fallback_rate)} of calls, ` +
      `${pct(rate.job_fallback_rate)} of jobs.`;
  }

  function _hhmm(iso) {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function renderCircuitStatus(health) {
    // Task 18.8 (D28) Q4: circuit_open/circuit_open_until now mean "every
    // configured provider is paused" -- the old single-provider "Cloud
    // paused until HH:MM" line is shown only in that all-paused case.
    // Otherwise, if some (but not all) configured providers are paused, a
    // smaller per-provider note names them and says what's covering.
    if (!circuitStatusEl) return;
    if (health && health.circuit_open && health.circuit_open_until) {
      circuitStatusEl.hidden = false;
      circuitStatusEl.textContent = `Cloud paused until ${_hhmm(health.circuit_open_until)} (free daily limit reached)`;
      return;
    }
    const providers = (health && health.providers) || {};
    const names = Object.keys(providers);
    const paused = names.filter((name) => providers[name].circuit_open);
    if (paused.length === 0) {
      circuitStatusEl.hidden = true;
      return;
    }
    const active = names.filter((name) => !providers[name].circuit_open);
    const pausedLabel = paused
      .map((name) => `${name} paused until ${providers[name].circuit_open_until ? _hhmm(providers[name].circuit_open_until) : "?"}`)
      .join(", ");
    circuitStatusEl.hidden = false;
    circuitStatusEl.textContent = active.length ? `${pausedLabel}; using ${active.join("/")}` : pausedLabel;
  }

  function renderProviderOrder(status) {
    if (providerOrderInput && document.activeElement !== providerOrderInput) {
      providerOrderInput.value = (status.cloud_provider_order || []).join(", ");
    }
  }

  function renderGeminiForm(status) {
    const gemini = status.gemini || {};
    if (geminiBaseUrlInput && document.activeElement !== geminiBaseUrlInput) geminiBaseUrlInput.value = gemini.base_url || "";
    if (geminiModelsInput && document.activeElement !== geminiModelsInput) {
      geminiModelsInput.value = (gemini.models || []).join(", ");
    }
    if (geminiKeyStatusEl) {
      geminiKeyStatusEl.textContent = gemini.configured
        ? `Key ending in ${gemini.key_last4}.`
        : "No key configured.";
      geminiKeyStatusEl.classList.remove("is-error", "is-success");
    }
  }

  function renderZenForm(status) {
    const zen = status.opencode_zen || {};
    if (zenBaseUrlInput && document.activeElement !== zenBaseUrlInput) zenBaseUrlInput.value = zen.base_url || "";
    if (zenModelInput && document.activeElement !== zenModelInput) zenModelInput.value = zen.model || "";
    if (zenKeyStatusEl) {
      zenKeyStatusEl.textContent = zen.configured ? `Key ending in ${zen.key_last4}.` : "No key configured.";
      zenKeyStatusEl.classList.remove("is-error", "is-success");
    }
  }

  async function loadFallbackRate() {
    try {
      const health = await Api.getAiHealth();
      renderFallbackRate(health);
      renderCircuitStatus(health);
    } catch (error) {
      if (fallbackRateEl) fallbackRateEl.textContent = "";
    }
  }

  async function loadStatus() {
    try {
      const status = await Api.getSettings();
      renderAiModeRadios(status);
      renderEffectiveModeStatus(status);
      renderCloudForm(status);
      renderProviderOrder(status);
      renderGeminiForm(status);
      renderZenForm(status);
      return status;
    } catch (error) {
      if (effectiveStatusEl) effectiveStatusEl.textContent = error.message || "Could not load current status.";
      return null;
    }
  }

  async function handleModeChange(newMode) {
    try {
      await Api.updateAiMode(newMode);
      await loadStatus();
    } catch (error) {
      if (disabledNoteEl) {
        disabledNoteEl.hidden = false;
        disabledNoteEl.textContent = error.message || "Could not save the AI mode.";
        disabledNoteEl.classList.add("is-error");
      }
      await loadStatus(); // revert the radio to the actually-saved value
    }
  }

  async function handleSave() {
    if (!saveStatusEl) return;
    saveStatusEl.classList.remove("is-error", "is-success");
    saveStatusEl.textContent = "Saving…";
    try {
      const fallbackModels = fallbackModelsInput.value
        .split(",")
        .map((entry) => entry.trim())
        .filter(Boolean);
      await Api.updateCloudSettings(baseUrlInput.value, modelInput.value, apiKeyInput.value, fallbackModels);
      apiKeyInput.value = "";
      saveStatusEl.textContent = "Saved.";
      saveStatusEl.classList.add("is-success");
      await loadStatus();
    } catch (error) {
      saveStatusEl.textContent = error.message || "Could not save.";
      saveStatusEl.classList.add("is-error");
    }
  }

  async function handleClearKey() {
    if (!saveStatusEl) return;
    try {
      await Api.clearCloudApiKey();
      apiKeyInput.value = "";
      saveStatusEl.textContent = "Key cleared.";
      saveStatusEl.classList.remove("is-error");
      saveStatusEl.classList.add("is-success");
      await loadStatus();
    } catch (error) {
      saveStatusEl.textContent = error.message || "Could not clear the key.";
      saveStatusEl.classList.remove("is-success");
      saveStatusEl.classList.add("is-error");
    }
  }

  async function handleTestConnection() {
    if (!testConnectionResultEl) return;
    testConnectionResultEl.classList.remove("is-error", "is-success");
    testConnectionResultEl.textContent = "Testing…";
    try {
      const result = await Api.testCloudConnection(baseUrlInput.value, modelInput.value, apiKeyInput.value);
      if (result.ok) {
        testConnectionResultEl.textContent = "OK";
        testConnectionResultEl.classList.add("is-success");
      } else {
        const statusPart = result.status != null ? ` (${result.status})` : "";
        testConnectionResultEl.textContent = `${result.error}${statusPart}`;
        testConnectionResultEl.classList.add("is-error");
      }
    } catch (error) {
      testConnectionResultEl.textContent = error.message || "Could not test the connection.";
      testConnectionResultEl.classList.add("is-error");
    }
  }

  async function handleSaveProviderOrder() {
    if (!providerOrderStatusEl) return;
    providerOrderStatusEl.classList.remove("is-error", "is-success");
    providerOrderStatusEl.textContent = "Saving…";
    try {
      const order = providerOrderInput.value
        .split(",")
        .map((entry) => entry.trim())
        .filter(Boolean);
      await Api.updateCloudProviderOrder(order);
      providerOrderStatusEl.textContent = "Saved.";
      providerOrderStatusEl.classList.add("is-success");
      await loadStatus();
    } catch (error) {
      providerOrderStatusEl.textContent = error.message || "Could not save.";
      providerOrderStatusEl.classList.add("is-error");
    }
  }

  async function handleSaveGemini() {
    if (!geminiSaveStatusEl) return;
    geminiSaveStatusEl.classList.remove("is-error", "is-success");
    geminiSaveStatusEl.textContent = "Saving…";
    try {
      const models = geminiModelsInput.value
        .split(",")
        .map((entry) => entry.trim())
        .filter(Boolean);
      await Api.updateGeminiSettings(geminiBaseUrlInput.value, models, geminiApiKeyInput.value);
      geminiApiKeyInput.value = "";
      geminiSaveStatusEl.textContent = "Saved.";
      geminiSaveStatusEl.classList.add("is-success");
      await loadStatus();
    } catch (error) {
      geminiSaveStatusEl.textContent = error.message || "Could not save.";
      geminiSaveStatusEl.classList.add("is-error");
    }
  }

  async function handleClearGeminiKey() {
    if (!geminiSaveStatusEl) return;
    try {
      await Api.clearGeminiCloudApiKey();
      geminiApiKeyInput.value = "";
      geminiSaveStatusEl.textContent = "Key cleared.";
      geminiSaveStatusEl.classList.remove("is-error");
      geminiSaveStatusEl.classList.add("is-success");
      await loadStatus();
    } catch (error) {
      geminiSaveStatusEl.textContent = error.message || "Could not clear the key.";
      geminiSaveStatusEl.classList.remove("is-success");
      geminiSaveStatusEl.classList.add("is-error");
    }
  }

  async function handleSaveZen() {
    if (!zenSaveStatusEl) return;
    zenSaveStatusEl.classList.remove("is-error", "is-success");
    zenSaveStatusEl.textContent = "Saving…";
    try {
      await Api.updateOpenCodeZenSettings(zenBaseUrlInput.value, zenModelInput.value, zenApiKeyInput.value);
      zenApiKeyInput.value = "";
      zenSaveStatusEl.textContent = "Saved.";
      zenSaveStatusEl.classList.add("is-success");
      await loadStatus();
    } catch (error) {
      zenSaveStatusEl.textContent = error.message || "Could not save.";
      zenSaveStatusEl.classList.add("is-error");
    }
  }

  async function handleClearZenKey() {
    if (!zenSaveStatusEl) return;
    try {
      await Api.clearOpenCodeZenApiKey();
      zenApiKeyInput.value = "";
      zenSaveStatusEl.textContent = "Key cleared.";
      zenSaveStatusEl.classList.remove("is-error");
      zenSaveStatusEl.classList.add("is-success");
      await loadStatus();
    } catch (error) {
      zenSaveStatusEl.textContent = error.message || "Could not clear the key.";
      zenSaveStatusEl.classList.remove("is-success");
      zenSaveStatusEl.classList.add("is-error");
    }
  }

  localRadio?.addEventListener("change", () => {
    if (localRadio.checked) handleModeChange("local");
  });
  cloudFirstRadio?.addEventListener("change", () => {
    if (cloudFirstRadio.checked) handleModeChange("cloud_first");
  });
  saveBtn?.addEventListener("click", handleSave);
  clearKeyBtn?.addEventListener("click", handleClearKey);
  testConnectionBtn?.addEventListener("click", handleTestConnection);
  providerOrderInput?.addEventListener("change", handleSaveProviderOrder);
  saveGeminiBtn?.addEventListener("click", handleSaveGemini);
  clearGeminiKeyBtn?.addEventListener("click", handleClearGeminiKey);
  saveZenBtn?.addEventListener("click", handleSaveZen);
  clearZenKeyBtn?.addEventListener("click", handleClearZenKey);

  loadStatus();
  loadFallbackRate();
})();
