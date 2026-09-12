/**
 * Centralized API client. All backend calls go through here (CR-05) so
 * pages never hand-roll fetch() or parse the response envelope themselves.
 */
const Api = (() => {
  const BASE_URL = "";

  async function request(path, options = {}) {
    const defaultHeaders = options.body instanceof FormData ? {} : { "Content-Type": "application/json" };
    const response = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers: { ...defaultHeaders, ...(options.headers || {}) },
    });

    let envelope;
    try {
      envelope = await response.json();
    } catch {
      throw new Error(`Request to ${path} failed with status ${response.status}`);
    }

    if (!response.ok || envelope.success === false) {
      const error = new Error(envelope.error || `Request to ${path} failed`);
      error.status = response.status;
      throw error;
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
    generateLearningPack: (projectId) =>
      request(`/api/projects/${projectId}/learning/generate`, { method: "POST" }),
    getLearningPack: (projectId) => request(`/api/projects/${projectId}/learning`),
    saveLearningPack: (projectId, pack) =>
      request(`/api/projects/${projectId}/learning`, { method: "PUT", body: JSON.stringify(pack) }),
    listTtsEngines: () => request("/api/tts/engines"),
    listMusic: () => request("/api/music"),
    uploadMusic: (file) => {
      const body = new FormData();
      body.append("file", file);
      return request("/api/music", { method: "POST", body });
    },
    deleteMusic: (filename) =>
      request(`/api/music/${encodeURIComponent(filename)}`, { method: "DELETE" }),
    musicContentUrl: (filename) => `/api/music/${encodeURIComponent(filename)}`,
    listThumbnailTemplates: () => request("/api/thumbnails/templates"),
    listThumbnails: (projectId) => request(`/api/projects/${projectId}/thumbnails`),
    generateThumbnails: (projectId, templateName, variantCount) =>
      request(`/api/projects/${projectId}/thumbnails/generate`, {
        method: "POST",
        body: JSON.stringify({ template_name: templateName, variant_count: variantCount }),
      }),
    selectThumbnailFavorite: (projectId, thumbnailId) =>
      request(`/api/projects/${projectId}/thumbnails/${thumbnailId}/favorite`, {
        method: "PUT",
      }),
    editThumbnail: (projectId, thumbnailId, edit) =>
      request(`/api/projects/${projectId}/thumbnails/${thumbnailId}`, {
        method: "PATCH",
        body: JSON.stringify(edit),
      }),
    generateYoutubePackage: (projectId) =>
      request(`/api/projects/${projectId}/youtube/generate`, { method: "POST" }),
    getYoutubePackage: (projectId) => request(`/api/projects/${projectId}/youtube`),
    health: () => request("/health"),
  };
})();
