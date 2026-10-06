/** App sidebar (Task 27.2): collapse to an icon rail (remembered) and, on narrow screens, a drawer.
 *  Presentation only: it owns no app data. The studio pages (steps 2-7) already have their own side panel, so
 *  they start as a rail; everywhere else the sidebar is open on wide screens and a rail on medium ones. */
(function () {
  const KEY = "dbe.sidebar";
  const NARROW = window.matchMedia("(max-width: 779px)");
  const body = document.body;
  const sidebar = document.getElementById("app-sidebar");
  const toggle = document.getElementById("sidebar-toggle");
  // This script runs right after the sidebar markup (so the saved state applies before first paint), when the top
  // bar's menu button does not exist yet: it is looked up when needed and clicks are handled by delegation.
  const getOpener = () => document.getElementById("sidebar-open");
  const backdrop = document.getElementById("sidebar-backdrop");
  if (!sidebar || !toggle) return;

  function stored() {
    try {
      return localStorage.getItem(KEY);
    } catch {
      return null;
    }
  }

  function remember(value) {
    try {
      localStorage.setItem(KEY, value);
    } catch {
      /* the choice just is not remembered */
    }
  }

  function startsCollapsed() {
    return /^\/step[2-7]\b/.test(location.pathname) || window.innerWidth < 1100;
  }

  function setCollapsed(collapsed) {
    body.classList.toggle("sidebar-collapsed", collapsed);
    toggle.setAttribute("aria-expanded", String(!collapsed));
    const label = collapsed ? "Expand sidebar" : "Collapse sidebar";
    toggle.setAttribute("aria-label", label);
    toggle.title = label;
  }

  function openDrawer() {
    body.classList.add("sidebar-open");
    const opener = getOpener();
    if (opener) opener.setAttribute("aria-expanded", "true");
    const first = sidebar.querySelector("a.side-link");
    if (first) first.focus();
  }

  function closeDrawer(returnFocus) {
    if (!body.classList.contains("sidebar-open")) return;
    body.classList.remove("sidebar-open");
    const opener = getOpener();
    if (opener) {
      opener.setAttribute("aria-expanded", "false");
      if (returnFocus) opener.focus();
    }
  }

  const saved = stored();
  setCollapsed(saved ? saved === "collapsed" : startsCollapsed());

  toggle.addEventListener("click", () => {
    if (NARROW.matches) {
      closeDrawer(true);
      return;
    }
    const collapsed = !body.classList.contains("sidebar-collapsed");
    setCollapsed(collapsed);
    remember(collapsed ? "collapsed" : "expanded");
  });
  document.addEventListener("click", (event) => {
    if (event.target.closest && event.target.closest("#sidebar-open")) {
      if (body.classList.contains("sidebar-open")) closeDrawer(true);
      else openDrawer();
    }
  });
  if (backdrop) backdrop.addEventListener("click", () => closeDrawer(true));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeDrawer(true);
  });
  NARROW.addEventListener("change", () => closeDrawer(false));
})();
