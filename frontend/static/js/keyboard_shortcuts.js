/**
 * Ctrl+Enter (Cmd+Enter on Mac) triggers a page's primary action button (Task 2.3b,
 * ROADMAP "UX Polish" item 3). Pure, synchronous, no network/state — same component
 * shape as StepNav. Escape-to-cancel needs no code: every confirm-gated action already
 * uses native window.confirm() (browser-cancelable on Escape for free), and the two
 * pages with inline-edit-then-commit fields already revert on Escape themselves.
 */
(() => {
  function isVisible(element) {
    return element.offsetParent !== null;
  }

  function init({ primaryButtonId }) {
    document.addEventListener("keydown", (event) => {
      if (!(event.ctrlKey || event.metaKey) || event.key !== "Enter") return;
      const button = document.getElementById(primaryButtonId);
      if (!button || button.disabled || !isVisible(button)) return;
      event.preventDefault();
      button.click();
    });
  }

  window.KeyboardShortcuts = Object.freeze({ init });
})();
