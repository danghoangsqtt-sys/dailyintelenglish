/** App sidebar (Task 27.2; Phase 93, D138/D140): one list draws the rail on every page -- the brand, "Create video",
 *  the five areas and Settings. It collapses to an icon rail (remembered); under 780 px it becomes a tab bar at the
 *  bottom of the screen. Presentation only: the one number it shows (videos waiting for the owner) comes from the
 *  review board the Automation tab already uses. */
(function () {
  const KEY = "dbe.sidebar";
  const body = document.body;
  const sidebar = document.getElementById("app-sidebar");
  if (!sidebar) return;

  const ICONS = {
    plus: '<circle cx="12" cy="12" r="8.5"/><path d="M12 8v8M8 12h8"/>',
    today: '<path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10v9.5h13V10"/><path d="M10 19.5v-5h4v5"/>',
    channel: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M8 4v5M16 4v5M7 13h4M7 16.5h7"/>',
    videos: '<rect x="4" y="4" width="16" height="16" rx="2.5"/><path d="M8 4v16M16 4v16M4 9h4M4 15h4M16 9h4M16 15h4"/>',
    library: '<rect x="4" y="4" width="7" height="7" rx="1.8"/><rect x="13" y="4" width="7" height="7" rx="1.8"/><rect x="4" y="13" width="7" height="7" rx="1.8"/><rect x="13" y="13" width="7" height="7" rx="1.8"/>',
    settings: '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
    collapse: '<path d="m14.5 6-6 6 6 6"/>',
  };
  const icon = (name) => `<svg class="side-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${ICONS[name]}</svg>`;
  // Which area a page belongs to (the old addresses keep working and light their new area).
  const AREAS = [
    ["create", /^\/(create|shorts-batch)\b/], ["today", /^\/$/], ["channel", /^\/(channel|automation)\b/],
    ["videos", /^\/(videos|step[1-7])\b/], ["library", /^\/(library|characters|activities|music)\b/], ["settings", /^\/settings\b/],
  ];
  const area = (AREAS.find(([, re]) => re.test(location.pathname)) || [""])[0];
  const link = (key, href, label, extra = "") =>
    `<a class="side-link side-${key}" href="${href}"${area === key ? ' aria-current="page"' : ""} aria-label="${label}" title="${label}">${icon(key)}<span class="side-label">${label}</span>${extra}</a>`;

  sidebar.innerHTML = `
    <a class="brand" href="/" aria-label="Daily Beyond English home" translate="no"><img class="brand-logo" src="/static/brand/logo-64.png" width="36" height="36" alt="" /><span class="brand-word"><b>Daily Beyond</b><small>English</small></span></a>
    <a class="side-create btn btn-primary" href="/create"${area === "create" ? ' aria-current="page"' : ""} aria-label="Create video" title="Create video">${icon("plus")}<span class="side-label">Create video</span></a>
    <nav class="side-nav" aria-label="Main">
      ${link("today", "/", "Today", '<span class="side-count" hidden></span>')}
      ${link("channel", "/channel", "Channel")}
      ${link("videos", "/videos", "Videos")}
      ${link("library", "/library", "Library")}
    </nav>
    <nav class="side-nav side-bottom" aria-label="More">${link("settings", "/settings", "Settings")}</nav>
    <button id="sidebar-toggle" class="side-toggle" type="button" aria-expanded="true" aria-controls="app-sidebar" aria-label="Collapse sidebar" title="Collapse sidebar">${icon("collapse")}<span class="side-label">Collapse</span></button>`;
  const toggle = document.getElementById("sidebar-toggle");

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
  function setCollapsed(collapsed) {
    body.classList.toggle("sidebar-collapsed", collapsed);
    toggle.setAttribute("aria-expanded", String(!collapsed));
    const label = collapsed ? "Expand sidebar" : "Collapse sidebar";
    toggle.setAttribute("aria-label", label);
    toggle.title = label;
  }
  const startsCollapsed = () => /^\/step[2-7]\b/.test(location.pathname) || window.innerWidth < 1100;
  const saved = stored();
  setCollapsed(saved ? saved === "collapsed" : startsCollapsed());
  // The initial width is committed before transitions are enabled (BUG-040).
  sidebar.getBoundingClientRect();
  body.classList.add("sidebar-ready");
  toggle.addEventListener("click", () => {
    const collapsed = !body.classList.contains("sidebar-collapsed");
    setCollapsed(collapsed);
    remember(collapsed ? "collapsed" : "expanded");
  });

  // Videos waiting for the owner: finished and not reviewed, needing attention, or sent back for changes.
  const WAITING = new Set(["waiting_review", "needs_attention", "changes"]);
  function showCount(count) {
    const badge = sidebar.querySelector(".side-count");
    if (!badge) return;
    badge.hidden = !count;
    badge.textContent = count ? String(count) : "";
  }
  window.addEventListener("dbe:waiting", (event) => showCount(event.detail));
  if (window.fetch && area !== "today") {
    fetch("/api/automation/board").then((r) => (r.ok ? r.json() : null)).then((json) => {
      const videos = (json && json.data && json.data.videos) || [];
      showCount(videos.filter((v) => WAITING.has(v.state)).length);
    }).catch(() => {});
  }
})();
