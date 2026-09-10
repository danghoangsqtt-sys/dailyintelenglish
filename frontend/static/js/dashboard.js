/** Dashboard page: load projects, render cards, filter + search. UI state only — no business logic. */
(() => {
  let allProjects = [];
  let activeFilter = "all";
  let searchTerm = "";

  const STATUS_LABELS = {
    draft: "Draft",
    script_generated: "Script Ready",
    audio_generated: "Audio Ready",
    video_generated: "Video Ready",
    complete: "Complete",
  };

  function statusLabel(status) {
    return STATUS_LABELS[status] || status;
  }

  function projectCardHtml(project) {
    const created = new Date(project.created_at || Date.now()).toLocaleDateString();
    return `
      <div class="project-card card" data-id="${project.id}">
        <div class="project-card-header">
          <h3>${escapeHtml(project.name || "Untitled Project")}</h3>
          <span class="badge badge-status-${project.status}">${statusLabel(project.status)}</span>
        </div>
        <div class="project-card-badges">
          ${project.cefr_level ? `<span class="badge">${project.cefr_level}</span>` : ""}
          ${project.genre ? `<span class="badge">${escapeHtml(project.genre)}</span>` : ""}
        </div>
        <div class="project-card-footer">
          <span class="project-date">${created}</span>
          <div class="project-actions">
            <button class="btn btn-ghost btn-sm" data-action="continue">Continue</button>
            <button class="btn btn-ghost btn-sm btn-danger" data-action="delete">Delete</button>
          </div>
        </div>
      </div>`;
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function render() {
    const grid = document.getElementById("project-grid");
    const emptyState = document.getElementById("empty-state");

    const filtered = allProjects.filter((p) => {
      const matchesFilter = activeFilter === "all" || p.status === activeFilter;
      const matchesSearch =
        !searchTerm || (p.name || "").toLowerCase().includes(searchTerm.toLowerCase());
      return matchesFilter && matchesSearch;
    });

    if (filtered.length === 0) {
      grid.innerHTML = "";
      emptyState.hidden = false;
      emptyState.querySelector("p").textContent =
        allProjects.length === 0
          ? "No projects yet. Create your first AI-powered podcast episode."
          : "No projects match your filters.";
    } else {
      emptyState.hidden = true;
      grid.innerHTML = filtered.map(projectCardHtml).join("");
    }
  }

  async function loadProjects() {
    try {
      allProjects = await Api.listProjects();
    } catch (err) {
      console.error("Failed to load projects:", err);
      allProjects = [];
    }
    render();
  }

  function setupFilters() {
    document.querySelectorAll("[data-filter]").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll("[data-filter]").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        activeFilter = btn.dataset.filter;
        render();
      });
    });
  }

  function setupSearch() {
    const input = document.getElementById("search-input");
    input.addEventListener("input", (e) => {
      searchTerm = e.target.value;
      render();
    });
  }

  function setupNewProjectButton() {
    document.getElementById("new-project-btn").addEventListener("click", () => {
      // Step 1 Config Wizard ships in Task 1.3 — placeholder until that route exists.
      alert("The New Project wizard is coming up next (Task 1.3).");
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    setupFilters();
    setupSearch();
    setupNewProjectButton();
    document.getElementById("theme-toggle").addEventListener("click", Theme.toggle);
    loadProjects();
  });
})();
