/** Shared progress and breadcrumb navigation for the seven-step project pipeline. */
(() => {
  const STEPS = Object.freeze([
    { number: 1, label: "Config", path: "/step1" },
    { number: 2, label: "Script", path: "/step2" },
    { number: 3, label: "Learning", path: "/step3" },
    { number: 4, label: "Audio", path: "/step4" },
    { number: 5, label: "Video", path: "/step5" },
    { number: 6, label: "Thumbnail", path: "/step6" },
    { number: 7, label: "YouTube", path: "/step7" },
  ]);

  function stepHref(path, projectId) {
    if (projectId == null || String(projectId).trim() === "") return path;
    const query = new URLSearchParams({ project_id: String(projectId) });
    return `${path}?${query.toString()}`;
  }

  function render(containerId, { projectId, currentStep }) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const current = Number(currentStep);
    if (!Number.isInteger(current) || current < 1 || current > STEPS.length) {
      throw new RangeError(`currentStep must be an integer from 1 to ${STEPS.length}`);
    }

    const nav = document.createElement("nav");
    nav.className = "step-nav";
    nav.setAttribute("aria-label", "Project steps");

    const progress = document.createElement("span");
    progress.textContent = `Step ${current} of ${STEPS.length}`;
    nav.appendChild(progress);

    STEPS.forEach((step) => {
      const link = document.createElement("a");
      link.className = "step-nav-pill";
      link.classList.toggle("active", step.number === current);
      link.dataset.step = String(step.number);
      link.href = stepHref(step.path, projectId);
      link.textContent = step.label;
      if (step.number === current) link.setAttribute("aria-current", "step");
      nav.appendChild(link);
    });

    container.replaceChildren(nav);
  }

  window.StepNav = Object.freeze({ render });
})();
