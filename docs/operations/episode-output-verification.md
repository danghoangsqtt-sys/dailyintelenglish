# Episode title and output folders: owner follow-up, 2026-10-15

## Confirmed behavior

The existing Ep. 2 horizontal MP4 reproduced the owner's screenshot at 4.5 seconds: the first line ended in `Ep.` and the second began with `2:`. The existing export was at `D:\Example-videos\Local Market\video.mp4`.

The source already contains BUG-036 (separate series and episode title, nonbreaking `Ep. 2`) and ENH-035 (one episode subfolder). A source fix does not rewrite previously rendered MP4 files or backfill previous exports.

The running `dist/DailyIntelEnglishStudio/DailyIntelEnglishStudio.exe` was built October 7 and serves port 8000. Its separate AppData database contains one old draft, not the three Dinner Party episodes. The episode data is in the workspace `data/app.db`. This does not establish which earlier process generated the reported MP4.

## Applied output repair

Before startup and regeneration, the SQLite backup API captured the workspace database and the existing horizontal/vertical MP4 and SRT files were copied into:

`data/backups/episode-output-20261015/`

The current source is running at **http://127.0.0.1:8001**, using workspace data. There were no queued/running AI or image jobs before startup. The existing EXE process was retained. No EXE build or release was performed.

The normal `/video/generate` API successfully regenerated Ep. 2, preserving its existing narration, music, sprites, and cached brand voice. Its export hook created:

`D:\Example-videos\Local Market\Ep 02 - Shopping at the Market\`

The selected existing assets (video, vertical video, subtitles, thumbnails, YouTube metadata) are exported there. Files in the parent folder are retained. Horizontal video and subtitle hashes in the parent still match their original snapshot.

The normal `/video/vertical` API also successfully regenerated and exported the 1080 × 1920 episode. Both outputs now contain the corrected intro. Measured API processing times were 162.246 seconds for horizontal and 274.145 seconds for vertical.

## Verification

- Existing export tests: **11 passed**; title/brand tests: **7 passed**.
- Actual horizontal MP4: **1280 × 720, H.264/AAC, 249.514667 seconds**; audio/video duration difference below 0.1 seconds. Exported MP4 SHA-256 matches the newly generated source MP4.
- Actual vertical MP4: **1080 × 1920, H.264/AAC, 249.514667 seconds**; audio/video duration difference below 0.1 seconds. Its exported SHA-256 also matches the new source MP4. The parent's old vertical MP4 still matches the snapshot. The extracted 4.5-second frame was visually inspected and keeps `Ep. 2` together without clipping the series or episode title.
- Intro images rendered at the real horizontal/vertical composition sizes and inspected. Horizontal MP4 frame extracted at 4.5 seconds confirms `Ep. 2` stays together and the series name has its own line.
- A real Playwright visit to Step 7 confirmed the resolved episode destination and the new explanatory text. API reads confirmed Ep. 1 and Ep. 3 receive the same series-root suggestion and resolve to distinct names:

```text
Local Market/
  Ep 01 - Choosing the Menu/           (destination for Ep. 1)
  Ep 02 - Shopping at the Market/      (created and exported)
  Ep 03 - Cooking the Final Dish/      (destination for Ep. 3)
```

- JavaScript and PowerShell syntax checks passed. The launcher's exact SQLite backup code was exercised against the snapshot: integrity check passed, all 13 projects present. An occupied-port invocation stopped before starting another server, as intended.
- Disposable measurements, API results and screenshots: `data/tmp/episode-output-verification/`.

## Open the current source after restarting Windows

From the project directory:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_studio.ps1
```

The launcher uses the workspace database, creates a fresh SQLite backup before startup, and opens port 8001. If a server is already listening there, open the existing source session. It will refuse to silently connect to an unrelated process. In Project Folder, choose the shared series root; the application adds the episode subfolder automatically when saving/exporting.

Formal owner/PM acceptance and existing release gates remain pending. This verification does not declare them complete.
