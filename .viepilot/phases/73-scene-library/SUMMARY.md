# Phase 73 - Scene Library delivery

Activity Library now hosts Activity pictures and Scenes as separate tabs. Scenes supports create/edit/duplicate, search/category/background/archive filters, AI background generation with progress/cancel, and archive/restore for custom scenes. Built-ins remain protected. Existing Character Library links lead to the new tab, with old background import available under Advanced.

Step5 removes the project shortlist chips. Each storyboard beat chooses from the active library with search; existing archived scene choices remain visible only on their current beats. Returning from library management refreshes choices without discarding unsaved beat edits. AI and rule fallback use active scenes; an empty library produces a free-text place.

Migration037 adds archived_at and an index. IDs, plates and old references remain intact. Archive leaves the picture version unchanged. Usage counts include project shortlists, storyboard beats and Solo current/history/approved references, deduplicated per project. Historical project rendering keeps its archived scene; automatic global selection excludes archives.

Verification is recorded in PHASE-STATE.md: 92 backend checks, 15 scene/activity checks, final 7 browser integration checks, 10 renderer/package regressions; static checks passed. These groups can overlap and are not a full-suite count. Screenshot reviewed from isolated data. Real GPU generation was not exercised; controlled generation fixtures verified the UI/API job flow.

Source implementation is ready for owner review. Restart an already-running application to apply migration037 and load changed backend code. No release/package was produced.


## Amendment 73.4 - requests and local/external AI

The scene editor accepts a short Vietnamese/English description. Prepare image prompt uses the configured text AI gateway and a versioned Jinja2 art-direction template; it returns validated English scene metadata and a detailed editable image prompt. The same canonical background composition is used by Copy prompt and the Qwen job. Original requests and prompts persist through edit/duplicate/reload. Preparation/copy/upload work without a local image GPU; generating a picture locally still requires Qwen.

External PNG/JPEG/WebP images can be uploaded on a scene card, decoded/reencoded into a 16:9 PNG. Bounded uploads, unique versioned paths, archive/concurrent-edit checks and atomic DB publication preserve old valid images on failures. Prompt changes invalidate the old preview. Request/prompt edits survive provider and clipboard errors; stale async replies do not overwrite new edits.

Migration038 is additive and backfills empty prompt fields. Restart a running source app to apply both migrations037/038. The existing EXE has not been rebuilt.

Verification: 89 backend/builder/pipeline checks and 18 UI/adjacent browser checks passed; relevant Qwen/Step5 regressions passed, static checks passed. Reviewed screenshot: C:/Users/Admin/AppData/Local/Temp/pytest-of-Admin/pytest-1552/test_brief_to_prompt_copy_save0/scene-prompt-desktop.png. Tests used controlled AI fixtures; real paid AI/GPU generation not run.
