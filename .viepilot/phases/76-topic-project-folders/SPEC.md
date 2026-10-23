# SPEC — Phase 76: Topic / Series / Video project folders

Source: owner-approved brainstorm in [session-2026-10-23-project-folders.md](../../../docs/brainstorm/session-2026-10-23-project-folders.md).

## Goal

Let users choose a parent output directory for a Topic and have selected project outputs automatically land in a predictable hierarchy. Reuse the existing Step 1 / Step 7 export panel and keep the current component checkboxes.

## Requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| R76-01 | New hierarchical exports resolve to `<chosen parent>/<Topic>/<Series>/Ep NN - <episode title>` for Channel Plan episodes. | Backend path tests cover Topic, Series, episode names and distinct episodes. |
| R76-02 | A standalone project resolves to `<chosen parent>/<project topic>/<project name>` and has no synthetic Series directory. | API/service tests verify the project fields become the two readable path components. |
| R76-03 | The chosen parent directory is stored per Topic identity and suggested to other projects in that Topic. Channel Plan Topics use their stable ID; standalone Topics use a normalized topic key. | Persistence tests verify sibling reuse and case/whitespace normalization for freeform topics. |
| R76-04 | Topic, Series and video components are Windows-safe, bounded in length and collision-safe without overwriting another project's outputs. | Unit/API checks cover invalid characters, reserved names, long strings and duplicate labels. |
| R76-05 | Existing project export settings continue to use their current exact destination until the owner changes that project's save mode/location. Old files are never moved or deleted. | Migration defaults existing records to legacy mode; tests cover re-save, clear and existing-file retention. |
| R76-06 | Only checked output components are synchronized; each selected component continues to refresh automatically when regenerated. | Existing export tests plus hierarchy-aware sync checks. |
| R76-07 | Step 1 and Step 7 show the selected parent and the fully resolved project destination; the user can choose, save, open and stop using the folder through the existing panel. | Browser checks verify preview and actions in both steps. |

## Boundaries

- No project database/media backup bundle; the owner selected the existing output checkbox model.
- Do not rename or reorganize files already exported from legacy projects.
- A project switching to hierarchical mode writes new copies at its resolved destination; the old destination remains untouched.
- Do not package, install, commit or publish as part of this phase.
- Reuse the current UI component and styles; no separate visual redesign is in scope.

## Storage and resolution direction

- Add an additive SQLite migration for topic-level export roots and an explicit layout mode on each project export setting. Existing rows default to `legacy`.
- Use the stable Channel Plan topic ID as the shared key for episodes. For standalone projects, normalize the project's topic text into a stable case-insensitive key.
- A new or opted-in project uses the Topic root plus Channel Plan names. For standalone projects, use `projects.topic` and `projects.name`.
- A no-series project's folder is `<parent>/<topic>/<project name>`.
- Save the resolved relative folder at opt-in time. Later Topic/title edits do not silently relocate copies; saving the folder settings again refreshes the preview and path.
- Keep per-project selected output items in the existing `project_exports` record.

## Delivery gates

1. New hierarchical selection creates/updates only the chosen project's checked exports at the resolved path.
2. Other unconfigured projects in the same Topic can reuse the saved parent; already configured legacy projects remain untouched.
3. Channel Plan and standalone paths are stable, human-readable, safe on Windows and collision-safe.
4. Existing legacy behavior, automatic sync hooks, Open folder and Stop saving behavior remain valid.
5. Focused backend/API/browser checks, Python lint and JavaScript syntax checks pass.

## Assumptions to resolve in implementation

- The folder name for a standalone video's final level is `projects.name`, the app's project/video name.
- At save time, reserve the proposed relative path against other hierarchical projects using the same parent. If the folder is already reserved or exists, add a short stable project identifier to the video-folder label. Persist the relative path so later projects cannot rename an earlier project's destination.
- Changing the export mode/location affects that project's copies only. It updates the shared Topic parent suggestion for future hierarchical configurations, but never bulk-migrates sibling projects.
