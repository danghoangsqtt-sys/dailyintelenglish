/**
 * Shared "Saved" / "Saving…" header indicator (Task 2.3e, ROADMAP "UX Polish" item 6).
 * Pure, synchronous, no network/state of its own — same component shape as StepNav and
 * KeyboardShortcuts. Additive alongside each page's existing inline #save-status element,
 * not a replacement for it.
 */
(() => {
  const LABELS = {
    saved: "Saved",
    dirty: "Unsaved changes",
    saving: "Saving…",
    failed: "Save failed",
  };

  function mount(containerId) {
    const container = document.getElementById(containerId);
    let currentStatus = null;

    function update(status) {
      currentStatus = status;
      if (!container) return;
      container.textContent = LABELS[status] || "";
      container.dataset.status = status;
      if (status === "saved") {
        setTimeout(() => {
          if (currentStatus === "saved") container.textContent = "";
        }, 2000);
      }
    }

    return { update };
  }

  window.SaveIndicator = Object.freeze({ mount });
})();
