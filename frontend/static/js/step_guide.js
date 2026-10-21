/**
 * Phase 56 (ENH-038): the next-step bar of the seven step pages. It reads which steps the project has done
 * (GET /api/projects/{id}/progress) and says, at the bottom of the step, whether this step is done, what is still
 * missing, and links to the next step. Presentation only: the step scripts are untouched, so it refreshes itself when
 * the window regains focus and every 15 s while the page is visible.
 */
(() => {
  const REFRESH_MS = 15000;
  const match = /^\/step([1-7])\b/.exec(location.pathname);
  const projectId = new URLSearchParams(location.search).get("project_id");
  if (!match || !projectId || typeof Api === "undefined") return;
  const current = Number(match[1]);
  let bar = null;

  function el(tag, props = {}, children = []) {
    const node = document.createElement(tag);
    Object.assign(node, props);
    (Array.isArray(children) ? children : [children]).forEach((child) => child && node.append(child));
    return node;
  }

  const href = (step) => `${step.path}?${new URLSearchParams({ project_id: projectId })}`;

  function render(progress) {
    const step = progress.steps[current - 1];
    const next = progress.steps[current];  // undefined on Step 7
    const earlier = progress.steps.slice(0, current - 1).find((item) => !item.done);
    if (!bar) {
      bar = el("div", { id: "step-guide", className: "step-guide" });
      bar.setAttribute("role", "status");
      (document.querySelector(".pane-stage") || document.getElementById("pane-main") || document.body).append(bar);
    }
    bar.dataset.done = String(step.done);
    const state = el("div", { className: "step-guide-state" }, [
      el("strong", { textContent: step.done ? `✓ Step ${current} — ${step.label} is done` : `Step ${current} — ${step.label}` }),
      step.done ? null : el("span", { textContent: `To finish this step: ${step.todo}` }),
      earlier ? el("a", { className: "step-guide-earlier", href: href(earlier),
        textContent: `Step ${earlier.number} — ${earlier.label} is not done yet` }) : null,
    ]);
    const action = next
      ? el("a", { className: `btn ${step.done ? "btn-primary" : "btn-ghost"} btn-sm step-guide-next`, href: href(next),
        textContent: `Next: Step ${next.number} — ${next.label} →` })
      : el("a", { className: `btn ${step.done ? "btn-primary" : "btn-ghost"} btn-sm step-guide-next`, href: "/",
        textContent: step.done ? "All steps done — back to the Dashboard" : "Back to the Dashboard" });
    bar.replaceChildren(state, action);
    // the step list ticks the steps before this one; tick only the ones really done
    progress.steps.forEach((item) => {
      const dot = document.querySelector(`#step-nav [data-step="${item.number}"] .step-dot`);
      if (!dot || item.number === current) return;
      dot.classList.toggle("done", item.done);
      dot.textContent = item.done ? "✓" : String(item.number);
    });
  }

  async function refresh() {
    try {
      render(await Api.getProjectProgress(projectId));
    } catch {
      /* no bar for a project the server does not know (or while it is unreachable) */
    }
  }

  document.addEventListener("DOMContentLoaded", refresh);
  window.addEventListener("focus", refresh);
  setInterval(() => document.visibilityState === "visible" && refresh(), REFRESH_MS);
  window.StepGuide = Object.freeze({ refresh });
})();
