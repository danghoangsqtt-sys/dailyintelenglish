# Topic-based project folders

## Choose the parent folder

In Step 1 when creating a project, or Step 7 in an existing project, choose the parent folder where the Topic library should live. The app remembers that parent for the Topic so related projects can share the same branch. Step 7 previews the resolved project folder before saving.

With hierarchical layout enabled, Channel Plan projects are organized as:

```text
<parent>/<Topic>/<Series>/Ep NN - <video title>/
```

Standalone projects without a Series use the project Topic and project name:

```text
<parent>/<project Topic>/<project name>/
```

Folder names are normalized for Windows. If a destination name collides with another project, the app adds a stable short identifier so both projects keep separate folders.

## Outputs and existing projects

Only output types checked in the export panel are synchronized into the project folder. The existing output generation hooks continue to update those selected files.

Projects already using an output folder remain in legacy mode after the migration. To use the hierarchy, select it explicitly or change the output location and save. Changing a destination does not move or delete files from the previous folder; those files remain available at their old location.

The database project remains in the app's data store. This setting controls exported deliverables such as video, subtitles, thumbnail, and script.
