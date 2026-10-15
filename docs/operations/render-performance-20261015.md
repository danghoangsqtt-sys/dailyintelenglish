# Render performance diagnosis — 2026-10-15

## Confirmed cause and adopted change

The installed Remotion 4.0.529 lets Chrome choose its graphics backend. On this Windows/RTX 3060 machine, a direct `SystemInfo.getInfo` probe of the task-owned headless browser reports:

| Selection | Actual renderer | GPU compositing / rasterization |
|---|---|---|
| Automatic (previous) | ANGLE / Vulkan **SwiftShader software device** | Disabled, software |
| Explicit `angle` | ANGLE / **NVIDIA RTX 3060, Direct3D 11** | Enabled |

The animated portrait combines full-size pictures, masks, blur, gradients, rotated sprites and moving captions across 7,484 frames at 1080x1920. The previous browser was doing this compositing in software. Changing the compositor addresses a measured bottleneck; it does not change the transcript, assets, timing, motion, output resolution, encoder or quality settings.

`DIE_REMOTION_GL` accepts `auto`, `angle` or `swangle`. Windows defaults to `angle`; other platforms retain `auto`. Set `auto` to restore Chrome's automatic choice if a driver behaves differently. The shared render deadline remains configurable separately. There is no silent encoder change or retry on arbitrary graphics errors.

## Controlled measurements

Same actual Episode props, 1080x1920, 30 fps, 8 workers, frames 300–1499 (40 seconds); sequential runs, with no other render competing:

| Pair | Auto elapsed | ANGLE elapsed | Elapsed reduction |
|---|---:|---:|---:|
| Episode wrapper, identical motion | 71.392 s | 46.627 s | 34.7% |
| Production `src/index.ts`, reverse order | 70.812 s | 47.975 s | 32.2% |

Production average capture time falls from **242 to 136 ms** per measured capture. Removing only the tiny character rotation did **not** improve the 1,200-frame wrapper run (73.176 s versus 71.392 s); do not blame that effect alone. Short 90-frame probes also found blur/compositing cost, but their startup overhead is too large to claim full-episode savings from them. The first cold wrapper run included a 14-second bundle and copying, so it is not a valid warm speed comparison.

Three decoded comparison frames (global 300, 900, 1499) have mean absolute channel differences 1.34–1.93/255; only 0.04–0.14% of pixels differ by over 20 in any channel. Geometry/content is retained; GPU rasterization and H.264 quantization produce small pixel differences. Representative frames were inspected.

## What remains slow / limits of this conclusion

- Encoding still uses **CPU libx264**, as confirmed by the production log. Enabling the browser GPU compositor does not switch FFmpeg to NVENC.
- A portrait frame has 2.25 times the pixels of 1280x720; full-screen blur/masks and image resampling remain work even with GPU compositing.
- Before this change, real full outputs took 768.178 s landscape and 2058.309 s portrait. The slow portrait's average capture was 1190 ms versus 10 ms piping. Its final stitch took 3.437 s, so final muxing was not the main delay.
- The full-run 1190 ms capture cost is higher than the isolated 40-second sample. Long-run resource/cache behavior or machine load may contribute; this experiment does not establish their individual shares.
- **No new full-episode elapsed time is claimed.** The verified improvement is 32–35% for these controlled samples. The owner's usage trial will provide the next full-run measurements.

Evidence: `data/tmp/exe-trial-20261015/{gpu-info.json,controlled-results.json,source-results.json,visual-comparison.json}` and the corresponding retained logs/MP4s. Existing full outputs were preserved.
