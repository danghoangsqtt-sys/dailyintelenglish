/** Dashboard page: load projects, render cards, filter + search. UI state only — no business logic. */
(() => {
  let allProjects = [];
  let activeFilter = "all";
  let searchTerm = "";
  let loadFailed = false;

  function showError(message) {
    const banner = document.getElementById("error-banner");
    banner.textContent = message;
    banner.hidden = false;
    banner.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function clearError() {
    const banner = document.getElementById("error-banner");
    banner.textContent = "";
    banner.hidden = true;
  }

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

    if (loadFailed) {
      // A failed load must never look identical to a genuinely empty account —
      // the error banner already explains what happened, so show neither the
      // grid nor the "No projects yet" copy here.
      grid.innerHTML = "";
      emptyState.hidden = true;
      return;
    }

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
      loadFailed = false;
      clearError();
    } catch (err) {
      console.error("Failed to load projects:", err);
      allProjects = [];
      loadFailed = true;
      showError("We couldn't load your projects. Please refresh the page.");
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
      window.location.href = "/step1";
    });
  }

  function setupProjectActions() {
    document.getElementById("project-grid").addEventListener("click", async (e) => {
      const button = e.target.closest("[data-action]");
      if (!button) return;
      const card = button.closest("[data-id]");
      const id = card.dataset.id;

      if (button.dataset.action === "delete") {
        if (!confirm("Delete this project? This cannot be undone.")) return;
        try {
          await Api.deleteProject(id);
          allProjects = allProjects.filter((p) => p.id !== id);
          clearError();
          render();
        } catch (err) {
          console.error("Failed to delete project:", err);
          showError("We couldn't delete this project. Please try again.");
        }
      }

      if (button.dataset.action === "continue") {
        const project = allProjects.find((p) => p.id === id);
        if (project && (project.status === "draft" || project.status === "script_generated")) {
          window.location.href = `/step2?project_id=${encodeURIComponent(id)}`;
        }
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    setupFilters();
    setupSearch();
    setupNewProjectButton();
    setupProjectActions();
    document.getElementById("theme-toggle").addEventListener("click", Theme.toggle);
    loadProjects();
  });
})();
