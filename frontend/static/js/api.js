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
    updateProject: (id, patch) =>
      request(`/api/projects/${id}`, { method: "PUT", body: JSON.stringify(patch) }),
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
    updateSpeaker: (projectId, speakerId, patch) =>
      request(`/api/projects/${projectId}/speakers/${speakerId}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
    listTtsEngines: () => request("/api/tts/engines"),
    previewTtsLine: (projectId, lineId) =>
      request(`/api/projects/${projectId}/tts/preview`, {
        method: "POST",
        body: JSON.stringify({ line_id: lineId }),
      }),
    ttsCacheUrl: (projectId, lineId) => `/api/projects/${projectId}/tts/cache/${lineId}.mp3`,
    generateAudio: (projectId, backgroundMusic) =>
      request(`/api/projects/${projectId}/audio/generate`, {
        method: "POST",
        body: JSON.stringify({ background_music: backgroundMusic || null }),
      }),
    getAudioStatus: (projectId) => request(`/api/projects/${projectId}/audio/status`),
    audioDownloadUrl: (projectId, format) => `/api/projects/${projectId}/audio/download?format=${format}`,
    listMusic: () => request("/api/music"),
    uploadMusic: (file) => {
      const body = new FormData();
      body.append("file", file);
      return request("/api/music", { method: "POST", body });
    },
    deleteMusic: (filename) =>
      request(`/api/music/${encodeURIComponent(filename)}`, { method: "DELETE" }),
    musicContentUrl: (filename) => `/api/music/${encodeURIComponent(filename)}`,
    // Task 22.7: track details (mood, tags, licence, credit) for the free-music library.
    getMusicOptions: () => request("/api/music/options"),
    // Task 22.9: classify tracks not analysed yet (pace, ~BPM, mood suggestion).
    analyseMusic: () => request("/api/music/analyse", { method: "POST" }),
    // Task 22.8: the library track that best fits a project's topic and length.
    suggestMusic: (projectId) => request(`/api/projects/${projectId}/music/suggest`, { method: "POST" }),
    updateMusic: (filename, details) =>
      request(`/api/music/${encodeURIComponent(filename)}`, { method: "PATCH", body: JSON.stringify(details) }),
    getVisualsHealth: () => request("/api/visuals/health"),
    getVisualsOptions: () => request("/api/visuals/options"),
    listCharacters: (filters = {}) => {
      const query = new URLSearchParams(Object.entries(filters).filter(([, value]) => value));
      return request(`/api/visuals/characters${query.toString() ? `?${query}` : ""}`);
    },
    getCharacter: (id) => request(`/api/visuals/characters/${id}`),
    createCharacter: (character) => request("/api/visuals/characters", {
      method: "POST", body: JSON.stringify(character),
    }),
    updateCharacter: (id, patch) => request(`/api/visuals/characters/${id}`, {
      method: "PATCH", body: JSON.stringify(patch),
    }),
    deleteCharacter: (id, force = false) => request(`/api/visuals/characters/${id}?force=${force}`, {
      method: "DELETE",
    }),
    duplicateCharacter: (id) => request(`/api/visuals/characters/${id}/duplicate`, { method: "POST" }),
    archiveCharacter: (id) => request(`/api/visuals/characters/${id}/archive`, { method: "POST" }),
    restoreCharacter: (id) => request(`/api/visuals/characters/${id}/restore`, { method: "POST" }),
    getCharacterDependencies: (id) => request(`/api/visuals/characters/${id}/dependencies`),
    getCharacterAssetSlots: (id) => request(`/api/visuals/characters/${id}/asset-slots`),
    characterPromptPackUrl: (id) => `/api/visuals/characters/${id}/prompt-pack`,
    generateCharacterCandidates: (id) => request(`/api/visuals/characters/${id}/candidates`, { method: "POST" }),
    pickCharacterReference: (id, assetId) => request(`/api/visuals/characters/${id}/reference`, {
      method: "PUT", body: JSON.stringify({ asset_id: assetId }),
    }),
    generateCharacterSheet: (id, kind = null) => request(`/api/visuals/characters/${id}/sheet`, {
      method: "POST", body: JSON.stringify(kind ? [{ kind }] : []),
    }),
    approveCharacterAsset: (id, assetId, approved) =>
      request(`/api/visuals/characters/${id}/assets/${assetId}/approve`, {
        method: "PUT", body: JSON.stringify({ approved }),
      }),
    lockCharacter: (id) => request(`/api/visuals/characters/${id}/lock`, { method: "POST" }),
    unlockCharacter: (id) => request(`/api/visuals/characters/${id}/unlock`, { method: "POST" }),
    listScenes: () => request("/api/visuals/scenes"),
    // Task 29.7: the shot library of ready-made pictures.
    listLibraryShots: (filters = {}) => {
      const query = new URLSearchParams(Object.entries(filters).filter(([, value]) => value));
      return request(`/api/visuals/library/shots${query.toString() ? `?${query}` : ""}`);
    },
    reviewLibraryShot: (id, reviewState) => request(`/api/visuals/library/shots/${id}`, {
      method: "PATCH", body: JSON.stringify({ review_state: reviewState }),
    }),
    listLibraryActivities: (filters = {}) => {
      const query = new URLSearchParams(Object.entries(filters).filter(([, value]) => value));
      return request(`/api/visuals/library/activities${query.toString() ? `?${query}` : ""}`);
    },
    importLibraryActivities: () => request("/api/visuals/library/activities/import", { method: "POST" }),
    uploadLibraryActivity: (formData) =>
      request("/api/visuals/library/activities/upload", { method: "POST", body: formData }),
    smartUploadLibraryActivities: (formData) =>
      request("/api/visuals/library/activities/smart-upload", { method: "POST", body: formData }),
    updateLibraryActivity: (id, patch) => request(`/api/visuals/library/activities/${id}`, {
      method: "PATCH", body: JSON.stringify(patch),
    }),
    reviewLibraryActivity: (id, reviewState) => request(`/api/visuals/library/activities/${id}/review`, {
      method: "PATCH", body: JSON.stringify({ review_state: reviewState }),
    }),
    getLibraryActivityHistory: (id) => request(`/api/visuals/library/activities/${id}/history`),
    getLibraryBackgrounds: () => request("/api/visuals/library/backgrounds"),
    importLibraryBackgrounds: () => request("/api/visuals/library/backgrounds/import", { method: "POST" }),
    getLibrarySprites: () => request("/api/visuals/library/sprites"),
    importLibrarySprites: () => request("/api/visuals/library/sprites/import", { method: "POST" }),
    getLibraryInbox: () => request("/api/visuals/library/inbox"),
    importLibraryInbox: () => request("/api/visuals/library/inbox/import", { method: "POST" }),
    deleteLibraryShot: (id) => request(`/api/visuals/library/shots/${id}`, { method: "DELETE" }),
    addProjectShotToLibrary: (projectId, shotId) =>
      request(`/api/projects/${projectId}/visuals/shots/${shotId}/to-library`, { method: "POST" }),
    getLibraryCoverage: (projectId) => request(`/api/projects/${projectId}/visuals/library-coverage`),
    getActivityCoverage: (projectId) => request(`/api/projects/${projectId}/visuals/activity-coverage`),
    createScene: (scene) => request("/api/visuals/scenes", { method: "POST", body: JSON.stringify(scene) }),
    updateScene: (id, patch) => request(`/api/visuals/scenes/${id}`, {
      method: "PATCH", body: JSON.stringify(patch),
    }),
    deleteScene: (id) => request(`/api/visuals/scenes/${id}`, { method: "DELETE" }),
    generateScenePreview: (id) => request(`/api/visuals/scenes/${id}/preview`, { method: "POST" }),
    duplicateScene: (id) => request(`/api/visuals/scenes/${id}/duplicate`, { method: "POST" }),
    getImageJob: (id) => request(`/api/visuals/jobs/${id}`),
    cancelImageJob: (id) => request(`/api/visuals/jobs/${id}/cancel`, { method: "POST" }),
    getProjectVisuals: (projectId) => request(`/api/projects/${projectId}/visuals`),
    getStoryboard: (projectId) => request(`/api/projects/${projectId}/storyboard`),
    saveStoryboard: (projectId, storyboard) => request(`/api/projects/${projectId}/storyboard`, {
      method: "PUT", body: JSON.stringify(storyboard),
    }),
    proposeStoryboard: (projectId) => request(`/api/projects/${projectId}/storyboard/propose`, { method: "POST" }),
    setProjectCast: (projectId, cast) => request(`/api/projects/${projectId}/visuals/cast`, {
      method: "PUT", body: JSON.stringify(cast),
    }),
    setProjectScenes: (projectId, scenes) => request(`/api/projects/${projectId}/visuals/scenes`, {
      method: "PUT", body: JSON.stringify(scenes),
    }),
    generateProjectShots: (projectId) =>
      request(`/api/projects/${projectId}/visuals/shots`, { method: "POST" }),
    regenerateProjectShot: (projectId, shotId) =>
      request(`/api/projects/${projectId}/visuals/shots/${shotId}/regenerate`, { method: "POST" }),
    listThumbnailTemplates: (projectId) => request(`/api/thumbnails/templates${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ""}`),
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
    youtubeExportUrl: (projectId) => `/api/projects/${projectId}/youtube/export`,
    getVideoStatus: (projectId) => request(`/api/projects/${projectId}/video/status`),
    listVideoTemplates: () => request("/api/video/templates"),
    // Task 19.7: renderer defaults to "ffmpeg" -- every pre-Phase-19 caller that omits it
    // behaves exactly as before. "remotion" only actually takes effect when the backend's
    // DIE_VIDEO_RENDERER kill switch already allows it (video_service._resolve_renderer).
    // Task 20.2d: `captionStyle` is only sent when given (Enhanced renders) -- Standard
    // request bodies stay exactly as before.
    // Phase 30: `visualMode` ("podcast_black" | "podcast_still") and `stillSceneId` are sent only
    // when set, so the default (the drawn story) keeps its body unchanged.
    generateVideo: (projectId, templateId, aspectRatio = "16:9", renderer = "ffmpeg", captionStyle = null,
                    visualMode = null, stillSceneId = null) => {
      const body = { template_id: templateId, aspect_ratio: aspectRatio, renderer };
      if (captionStyle) body.caption_style = captionStyle;
      if (visualMode) body.visual_mode = visualMode;
      if (stillSceneId) body.still_scene_id = stillSceneId;
      return request(`/api/projects/${projectId}/video/generate`, {
        method: "POST",
        body: JSON.stringify(body),
      });
    },
    videoDownloadUrl: (projectId, format) => `/api/projects/${projectId}/video/download?format=${format}`,
    getVideoHealth: () => request("/api/video/health"),
    uploadSpeakerAvatar: (projectId, speakerId, file) => {
      const body = new FormData();
      body.append("file", file);
      return request(`/api/projects/${projectId}/speakers/${speakerId}/avatar`, { method: "POST", body });
    },
    deleteSpeakerAvatar: (projectId, speakerId) =>
      request(`/api/projects/${projectId}/speakers/${speakerId}/avatar`, { method: "DELETE" }),
    health: () => request("/health"),
    getSettings: () => request("/api/settings"),
    updateAiMode: (aiMode) =>
      request("/api/settings/ai-mode", { method: "PUT", body: JSON.stringify({ ai_mode: aiMode }) }),
    updateCloudSettings: (baseUrl, model, apiKey, fallbackModels) =>
      request("/api/settings/cloud", {
        method: "PUT",
        body: JSON.stringify({
          base_url: baseUrl,
          model,
          api_key: apiKey || null,
          fallback_models: fallbackModels || null,
        }),
      }),
    clearCloudApiKey: () => request("/api/settings/cloud/api-key", { method: "DELETE" }),
    testCloudConnection: (baseUrl, model, apiKey) =>
      request("/api/settings/cloud/test-connection", {
        method: "POST",
        body: JSON.stringify({ base_url: baseUrl || null, model: model || null, api_key: apiKey || null }),
      }),
    // Task 18.8: OpenCode Zen / Gemini / dispatch order.
    updateOpenCodeZenSettings: (baseUrl, model, apiKey) =>
      request("/api/settings/cloud/opencode-zen", {
        method: "PUT",
        body: JSON.stringify({ base_url: baseUrl, model, api_key: apiKey || null }),
      }),
    clearOpenCodeZenApiKey: () => request("/api/settings/cloud/opencode-zen/api-key", { method: "DELETE" }),
    updateGeminiSettings: (baseUrl, models, apiKey) =>
      request("/api/settings/cloud/gemini", {
        method: "PUT",
        body: JSON.stringify({ base_url: baseUrl, models: models || null, api_key: apiKey || null }),
      }),
    clearGeminiCloudApiKey: () => request("/api/settings/cloud/gemini/api-key", { method: "DELETE" }),
    updateCloudProviderOrder: (order) =>
      request("/api/settings/cloud/order", { method: "PUT", body: JSON.stringify({ order }) }),
    // Durable AI jobs (Phase 13, Task 13.6) -- see frontend/static/js/ai_job.js
    // for the create/poll/resume lifecycle built on top of these.
    createScriptJob: (projectId) =>
      request(`/api/projects/${projectId}/ai-jobs`, {
        method: "POST",
        body: JSON.stringify({ operation: "script" }),
      }),
    createLearningJob: (projectId) =>
      request(`/api/projects/${projectId}/ai-jobs`, {
        method: "POST",
        body: JSON.stringify({ operation: "learning" }),
      }),
    getActiveAiJob: (projectId, operation) =>
      request(`/api/projects/${projectId}/ai-jobs/active?operation=${encodeURIComponent(operation)}`),
    getAiJob: (projectId, jobId) => request(`/api/projects/${projectId}/ai-jobs/${jobId}`),
    cancelAiJob: (projectId, jobId) =>
      request(`/api/projects/${projectId}/ai-jobs/${jobId}/cancel`, { method: "POST" }),
    getAiHealth: () => request("/api/ai/health"),
  };
})();
