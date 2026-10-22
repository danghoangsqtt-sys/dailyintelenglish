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

  const profileView = view => view === "front" ? "?view=front" : "";
  const json = (method, body) => ({ method, body: JSON.stringify(body) });

  return {
    // Task 36.5 (D103-D105): the channel plan -- topics -> series -> episodes, the AI map and the calendar.
    // Phase 62 (ENH-044): automatic production
    getAutomation: () => request("/api/automation"),
    getAutomationBoard: () => request("/api/automation/board"),  // Phase 67: the review studio
    // Phase 72 (ENH-054): the audience -- international, Vietnamese or both
    getChannelAudience: () => request("/api/audience"),
    setChannelAudience: (audience) => request("/api/audience", json("PUT", { audience })),
    getProjectAudience: (projectId) => request(`/api/projects/${projectId}/audience`),
    setProjectAudience: (projectId, audience) => request(`/api/projects/${projectId}/audience`, json("PUT", { audience: audience || null })),
    // Phase 70 (ENH-052): the library package
    getLibraryPackage: () => request("/api/library-package"),
    exportLibraryPackage: () => request("/api/library-package/export", { method: "POST" }),
    importLibraryPackage: (file) => {
      const body = new FormData();
      body.append("file", file);
      return request("/api/library-package/import", { method: "POST", body });
    },
    // Phase 66 (ENH-048): Shorts in batches and today's news
    proposeBatchIdeas: (body) => request("/api/shorts-batch/ideas", json("POST", body)),
    createBatch: (body) => request("/api/shorts-batch/create", json("POST", body)),
    getNewsFeeds: () => request("/api/news/feeds"),
    saveNewsFeeds: (feeds) => request("/api/news/feeds", json("PUT", feeds)),
    getTodayNews: () => request("/api/news/today"),
    getNewsPicks: (body) => request("/api/news/picks", json("POST", body)),
    readNewsArticles: (links) => request("/api/news/articles", json("POST", { links })),
    // Phase 63 (ENH-045): the text of a public news page for a news Short
    readLink: (url) => request("/api/projects/read-link", json("POST", { url })),
    saveAutomationSettings: (patch) => request("/api/automation/settings", json("PUT", patch)),
    runAutomationNow: () => request("/api/automation/run-now", { method: "POST" }),
    stopAutomation: () => request("/api/automation/stop", { method: "POST" }),
    getChannel: () => request("/api/channel"),
    getChannelDashboard: () => request("/api/channel/dashboard"),
    proposeChannelPlan: (body) => request("/api/channel/plan/propose", json("POST", body)),
    applyChannelPlan: (plan, cast) => request("/api/channel/plan/apply", json("POST", { plan, cast })),
    createChannelTopic: (body) => request("/api/channel/topics", json("POST", body)),
    updateChannelTopic: (id, patch) => request(`/api/channel/topics/${id}`, json("PATCH", patch)),
    deleteChannelTopic: (id) => request(`/api/channel/topics/${id}`, { method: "DELETE" }),
    createChannelSeries: (topicId, body) => request(`/api/channel/topics/${topicId}/series`, json("POST", body)),
    updateChannelSeries: (id, patch) => request(`/api/channel/series/${id}`, json("PATCH", patch)),
    deleteChannelSeries: (id) => request(`/api/channel/series/${id}`, { method: "DELETE" }),
    addChannelEpisode: (seriesId, body) => request(`/api/channel/series/${seriesId}/episodes`, json("POST", body)),
    createSeriesProjects: (seriesId) => request(`/api/channel/series/${seriesId}/projects`, { method: "POST" }),
    updateChannelEpisode: (id, patch) => request(`/api/channel/episodes/${id}`, json("PATCH", patch)),
    deleteChannelEpisode: (id) => request(`/api/channel/episodes/${id}`, { method: "DELETE" }),
    scheduleChannel: (body) => request("/api/channel/schedule", json("POST", body)),
    // Phase 33 (Tasks 33.2-33.5): character profiles, picture slots and review.
    getProfileOptions: () => request("/api/visuals/profiles/options"),
    listProfiles: (query = "") => request(`/api/visuals/profiles${query ? `?${query}` : ""}`),
    getProfile: (id) => request(`/api/visuals/profiles/${id}`),
    createProfile: (body) => request("/api/visuals/profiles", { method: "POST", body: JSON.stringify(body) }),
    patchProfile: (id, patch) => request(`/api/visuals/profiles/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
    duplicateProfile: (id) => request(`/api/visuals/profiles/${id}/duplicate`, { method: "POST" }),
    archiveProfile: (id) => request(`/api/visuals/profiles/${id}/archive`, { method: "POST" }),
    restoreProfile: (id) => request(`/api/visuals/profiles/${id}/restore`, { method: "POST" }),
    deleteProfile: (id) => request(`/api/visuals/profiles/${id}`, { method: "DELETE" }),
    listProfileSlots: (id, view = "native") => request(`/api/visuals/profiles/${id}/slots${profileView(view)}`),
    profilePromptPackUrl: (id, view = "native") => `/api/visuals/profiles/${id}/prompt-pack.txt${profileView(view)}`,
    uploadProfileSlot: (id, slotKey, file, view = "native") => {
      const body = new FormData();
      body.append("file", file);
      return request(`/api/visuals/profiles/${id}/slots/${encodeURIComponent(slotKey)}/upload${profileView(view)}`, { method: "POST", body });
    },
    uploadProfileSlotsBatch: (id, files, view = "native") => {
      const body = new FormData();
      files.forEach((file) => body.append("files", file));
      return request(`/api/visuals/profiles/${id}/slots/upload-batch${profileView(view)}`, { method: "POST", body });
    },
    reviewProfileAsset: (id, assetId, decision, view = "native") =>
      request(`/api/visuals/profiles/${id}/assets/${assetId}/review${profileView(view)}`, { method: "PUT", body: JSON.stringify({ decision }) }),
    approveProfileAssets: (id, assetIds, view = "native") =>
      request(`/api/visuals/profiles/${id}/assets/approve${profileView(view)}`, { method: "POST", body: JSON.stringify({ asset_ids: assetIds }) }),
    listProjects: () => request("/api/projects"),
    copyProjectSettings: (id) => request(`/api/projects/${id}/copy-settings`, {method:"POST"}),
    createProject: (config) =>
      request("/api/projects", { method: "POST", body: JSON.stringify(config) }),
    getProject: (id) => request(`/api/projects/${id}`),
    getProjectProgress: (id) => request(`/api/projects/${encodeURIComponent(id)}/progress`),
    // Phase 57 (ENH-039): Step 1 help -- AI topic ideas and the text of a photographed dialogue or word list
    suggestTopicIdeas: (body) => request("/api/projects/topic-ideas", json("POST", body)),
    readSourceImage: (file, kind) => {
      const form = new FormData();
      form.set("kind", kind);
      form.set("file", file, file.name);
      return request("/api/projects/read-image", { method: "POST", body: form });
    },
    updateProject: (id, patch) =>
      request(`/api/projects/${id}`, { method: "PUT", body: JSON.stringify(patch) }),
    deleteProject: (id) => request(`/api/projects/${id}`, { method: "DELETE" }),
    getProjectExport: (id) => request(`/api/projects/${id}/export`),
    saveProjectExport: (id, settings) => request(`/api/projects/${id}/export`, json("PUT", settings)),
    stopProjectExport: (id) => request(`/api/projects/${id}/export`, { method: "DELETE" }),
    openProjectExport: (id) => request(`/api/projects/${id}/export/open`, { method: "POST" }),
    chooseProjectFolder: (initial) => request("/api/system/choose-folder", json("POST", { initial })),
    listShorts: (id) => request(`/api/projects/${id}/shorts`),
    proposeShorts: (id, count) => request(`/api/projects/${id}/shorts/propose`, json("POST", { count })),
    updateShort: (id, clipId, patch) => request(`/api/projects/${id}/shorts/${clipId}`, json("PATCH", patch)),
    deleteShort: (id, clipId) => request(`/api/projects/${id}/shorts/${clipId}`, { method: "DELETE" }),
    renderShort: (id, clipId, options) => request(`/api/projects/${id}/shorts/${clipId}/render`, json("POST", options)),
    renderVertical: (id, options) => request(`/api/projects/${id}/video/vertical`, json("POST", options)),
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
    listTtsVoices: (refresh = false) => request(`/api/tts/voices${refresh ? "?refresh=true" : ""}`),
    previewTtsVoice: (payload, options = {}) => request("/api/tts/voices/preview", {...json("POST", payload), ...options}),
    previewTtsLine: (projectId, lineId, options = {}) =>
      request(`/api/projects/${projectId}/tts/preview`, {
        method: "POST",
        body: JSON.stringify({ line_id: lineId, ...options }),
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
    listCharacters: () => request("/api/visuals/characters"),
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
    approveCharacterAsset: (id, assetId, approved) =>
      request(`/api/visuals/characters/${id}/assets/${assetId}/approve`, {
        method: "PUT", body: JSON.stringify({ approved }),
      }),
    lockCharacter: (id) => request(`/api/visuals/characters/${id}/lock`, { method: "POST" }),
    unlockCharacter: (id) => request(`/api/visuals/characters/${id}/unlock`, { method: "POST" }),
    listScenes: () => request("/api/visuals/scenes"),
    // Task 29.7: the shot library of ready-made pictures.
    listLibraryActivities: (filters = {}) => {
      const query = new URLSearchParams(Object.entries(filters).filter(([, value]) => value));
      return request(`/api/visuals/library/activities${query.toString() ? `?${query}` : ""}`);
    },
    importLibraryActivities: () => request("/api/visuals/library/activities/import", { method: "POST" }),
    uploadLibraryActivity: (formData) =>
      request("/api/visuals/library/activities/upload", { method: "POST", body: formData }),
    uploadLibraryActivitiesBatch: (formData) =>
      request("/api/visuals/library/activities/upload-batch", { method: "POST", body: formData }),
    updateLibraryActivity: (id, patch) => request(`/api/visuals/library/activities/${id}`, {
      method: "PATCH", body: JSON.stringify(patch),
    }),
    reviewLibraryActivity: (id, reviewState) => request(`/api/visuals/library/activities/${id}/review`, {
      method: "PATCH", body: JSON.stringify({ review_state: reviewState }),
    }),
    deleteLibraryActivity: (id) => request(`/api/visuals/library/activities/${id}`, { method: "DELETE" }),
    approveLibraryActivitiesBatch: (ids) => request("/api/visuals/library/activities/approve-batch", {
      method: "POST", body: JSON.stringify({ ids }),
    }),
    getLibraryActivityHistory: (id) => request(`/api/visuals/library/activities/${id}/history`),
    getLibraryBackgrounds: () => request("/api/visuals/library/backgrounds"),
    importLibraryBackgrounds: () => request("/api/visuals/library/backgrounds/import", { method: "POST" }),
    getActivityCoverage: (projectId) => request(`/api/projects/${projectId}/visuals/activity-coverage`),
    drawActivityIllustrations: (projectId) =>
      request(`/api/projects/${projectId}/visuals/activity-illustrations`, { method: "POST" }),
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
    getExplainerPlan: (projectId) => request(`/api/projects/${projectId}/explainer-plan`),
    getExplainerHistory: (projectId) => request(`/api/projects/${projectId}/explainer-plan/history`),
    arrangeExplainerPlan: (projectId, body) => request(`/api/projects/${projectId}/explainer-plan/layout`, json("POST", body)),
    previewExplainerPlan: (projectId, aspect) => request(`/api/projects/${projectId}/explainer-plan/preview?aspect=${encodeURIComponent(aspect)}`),
    saveExplainerPlan: (projectId, body) => request(`/api/projects/${projectId}/explainer-plan`, json("PATCH", body)),
    proposeExplainerPlan: (projectId, body) => request(`/api/projects/${projectId}/explainer-plan/propose`, json("POST", body)),
    approveExplainerPlan: (projectId, body) => request(`/api/projects/${projectId}/explainer-plan/approve`, json("POST", body)),
    listExplainerAssets: (projectId) => request(`/api/projects/${projectId}/explainer/assets`),
    getExplainerStageChoices: (projectId) => request(`/api/projects/${projectId}/explainer-plan/stage-choices`),
    uploadExplainerAsset: (projectId, file) => {
      const body = new FormData();
      body.append("file", file);
      return request(`/api/projects/${projectId}/explainer/assets`, { method: "POST", body });
    },
    setProjectCast: (projectId, cast) => request(`/api/projects/${projectId}/visuals/cast`, {
      method: "PUT", body: JSON.stringify(cast),
    }),
    setProjectScenes: (projectId, scenes) => request(`/api/projects/${projectId}/visuals/scenes`, {
      method: "PUT", body: JSON.stringify(scenes),
    }),
    listThumbnailTemplates: (projectId) => request(`/api/thumbnails/templates${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ""}`),
    listThumbnails: (projectId) => request(`/api/projects/${projectId}/thumbnails`),
    drawThumbnailTopicPicture: (projectId) => request(`/api/projects/${projectId}/thumbnails/topic-picture`, { method: "POST" }),
    // Phase 43 (D122): the characters drawn into a topic scene on this computer
    drawThumbnailAiScenes: (projectId, count) => request(`/api/projects/${projectId}/thumbnails/ai-scenes`, {
      method: "POST", body: JSON.stringify({ count }),
    }),
    listThumbnailAiScenes: (projectId) => request(`/api/projects/${projectId}/thumbnails/ai-scenes`),
    redrawThumbnailAiScene: (projectId, index) =>
      request(`/api/projects/${projectId}/thumbnails/ai-scenes/${index}/redraw`, { method: "POST" }),
    getThumbnailOutsidePrompt: (projectId) => request(`/api/projects/${projectId}/thumbnails/outside-prompt`),
    uploadThumbnailOutsideImage: (projectId, file) => {
      const body = new FormData();
      body.append("file", file);
      return request(`/api/projects/${projectId}/thumbnails/outside-image`, { method: "POST", body });
    },
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
    youtubeTranscriptUrl: (projectId) => `/api/projects/${projectId}/youtube/transcript.txt`,
    getVideoStatus: (projectId) => request(`/api/projects/${projectId}/video/status`),
    // Task 35.5: Remotion is the only renderer; `captionStyle`/`visualMode`/`stillSceneId` are sent when set.
    generateVideo: (projectId, { captionStyle = null, visualMode = null, stillSceneId = null } = {}) => {
      const body = {};
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
    health: () => request("/health"),
    getBuildInfo: () => request("/api/system/build"),
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
