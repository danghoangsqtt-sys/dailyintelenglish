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
      stored = localStorage.getItem(STORAGE_KEY) || "dark";
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

  return { init, toggle };
})();

document.addEventListener("DOMContentLoaded", Theme.init);
