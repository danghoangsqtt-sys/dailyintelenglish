/** Dark/light theme toggle, persisted per browser via localStorage. */
const Theme = (() => {
  const STORAGE_KEY = "die-theme";

  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    const toggleBtn = document.getElementById("theme-toggle");
    if (toggleBtn) toggleBtn.textContent = theme === "dark" ? "☀️" : "🌙";
  }

  function init() {
    let stored = "dark";
    try {
      stored = localStorage.getItem(STORAGE_KEY) || "light";
    } catch {
      /* localStorage unavailable — default to dark */
    }
    apply(stored);
  }

  function toggle() {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    apply(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* ignore persistence failure */
    }
  }

  /** Phase 58 (ENH-040): choose a theme directly (Settings → General). */
  function set(theme) {
    apply(theme === "dark" ? "dark" : "light");
    try {
      localStorage.setItem(STORAGE_KEY, theme === "dark" ? "dark" : "light");
    } catch {
      /* ignore persistence failure */
    }
  }

  return { init, toggle, set };
})();

document.addEventListener("DOMContentLoaded", Theme.init);
