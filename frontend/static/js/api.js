/**
 * Centralized API client. All backend calls go through here (CR-05) so
 * pages never hand-roll fetch() or parse the response envelope themselves.
 */
const Api = (() => {
  const BASE_URL = "";

  async function request(path, options = {}) {
    const response = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });

    let envelope;
    try {
      envelope = await response.json();
    } catch {
      throw new Error(`Request to ${path} failed with status ${response.status}`);
    }

    if (!response.ok || envelope.success === false) {
      throw new Error(envelope.error || `Request to ${path} failed`);
    }

    return envelope.data;
  }

  return {
    listProjects: () => request("/api/projects"),
    createProject: (config) =>
      request("/api/projects", { method: "POST", body: JSON.stringify(config) }),
    getProject: (id) => request(`/api/projects/${id}`),
    deleteProject: (id) => request(`/api/projects/${id}`, { method: "DELETE" }),
    getScript: (projectId) => request(`/api/projects/${projectId}/script`),
    generateScript: (projectId) =>
      request(`/api/projects/${projectId}/script/generate`, { method: "POST" }),
    regenerateLine: (projectId, lineId) =>
      request(`/api/projects/${projectId}/script/regenerate`, {
        method: "POST",
        body: JSON.stringify({ line_id: lineId }),
      }),
    saveScript: (projectId, lines) =>
      request(`/api/projects/${projectId}/script`, {
        method: "PUT",
        body: JSON.stringify({ lines }),
      }),
    listTtsEngines: () => request("/api/tts/engines"),
    listMusic: () => request("/api/music"),
    health: () => request("/health"),
  };
})();
