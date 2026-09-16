/** Dashboard page: load projects, render cards, filter + search. UI state only — no business logic. */
(() => {
  let allProjects = [];
  let activeFilter = "all";
  let searchTerm = "";
  let loadFailed = false;
  let currentPage = 0;

  const PROJECTS_PER_PAGE = 24;

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

  const STATUS_TO_STEP = {
    draft: 2,
    script_generated: 2,
    audio_generated: 4,
    video_generated: 5,
    complete: 7,
  };

  function statusLabel(status) {
    return STATUS_LABELS[status] || status;
  }

  function projectCardHtml(project) {
    const created = new Date(project.created_at || Date.now()).toLocaleDateString();
    return `
      <div class="project-card card" data-id="${project.id}">
        <div class="project-thumb" aria-hidden="true">🎙️ Project preview</div>
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

  function renderPagination(totalPages) {
    const pagination = document.getElementById("project-pagination");
    const previousButton = document.getElementById("previous-page-btn");
    const nextButton = document.getElementById("next-page-btn");
    const indicator = document.getElementById("page-indicator");

    if (totalPages <= 1) {
      pagination.hidden = true;
      indicator.textContent = "";
      return;
    }

    pagination.hidden = false;
    previousButton.disabled = currentPage === 0;
    nextButton.disabled = currentPage === totalPages - 1;
    indicator.textContent = `Page ${currentPage + 1} of ${totalPages}`;
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

    const totalPages = Math.ceil(filtered.length / PROJECTS_PER_PAGE);
    currentPage = Math.max(0, Math.min(currentPage, Math.max(totalPages - 1, 0)));
    renderPagination(totalPages);

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
      const pageStart = currentPage * PROJECTS_PER_PAGE;
      const pageProjects = filtered.slice(pageStart, pageStart + PROJECTS_PER_PAGE);
      grid.innerHTML = pageProjects.map(projectCardHtml).join("");
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
        currentPage = 0;
        render();
      });
    });
  }

  function setupSearch() {
    const input = document.getElementById("search-input");
    input.addEventListener("input", (e) => {
      searchTerm = e.target.value;
      currentPage = 0;
      render();
    });
  }

  function setupPagination() {
    document.getElementById("previous-page-btn").addEventListener("click", () => {
      if (currentPage === 0) return;
      currentPage -= 1;
      render();
    });

    document.getElementById("next-page-btn").addEventListener("click", () => {
      currentPage += 1;
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
        const step = project ? STATUS_TO_STEP[project.status] : undefined;
        if (step !== undefined) {
          window.location.href = `/step${step}?project_id=${encodeURIComponent(id)}`;
        }
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    setupFilters();
    setupSearch();
    setupPagination();
    setupNewProjectButton();
    setupProjectActions();
    document.getElementById("theme-toggle").addEventListener("click", Theme.toggle);
    loadProjects();
  });
})();
