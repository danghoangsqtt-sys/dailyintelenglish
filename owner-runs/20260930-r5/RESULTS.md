# Owner-machine results r5 (Task 20.2e) 2026-09-30
- Pinned commit: c8bac2d995a9c297e82be7998fdfa80b487bfcb5
- Env: 2.11.0+cu128 12.8 True 0.40.0 1.30.0
- Memory (preflight): TotalVisibleMemorySize 33289648 / FreePhysicalMemory 15615676 / FreeVirtualMemory 11901148
- base_repo / scheduler (from phases.p1_style.load): cagliostrolab/animagine-xl-4.0 / EulerAncestralDiscreteScheduler
## Per phase (p1_style, p2_assets, p3_m2, p4_frames)
### p1_style
- wall_sec: 1443.5; error: none; load.load_sec: 5.157; load.download_or_cache_sec: 1256.223; lease.free_mb_before: 11553; lease.evicted_models: []
- per-image wall_time_sec: 19.777 / 20.165; peak_vram_allocated_mb: 9169.6; peak_vram_reserved_mb: 11610
### p2_assets
- wall_sec: 239.8; error: none; load.load_sec: 4.77; load.download_or_cache_sec: 0.834; lease.free_mb_before: 11669; lease.evicted_models: []
- per-image wall_time_sec: 25.546 / 28.312; peak_vram_allocated_mb: 11185.1; peak_vram_reserved_mb: 13746
- encode: style -> wall_time_sec / items / with_ip / do_cfg
  - action_webtoon -> 0.322 / 4 / true / true
  - bright_anime -> 0.313 / 4 / true / true
### p3_m2
- wall_sec: 268.8; error: none; load.load_sec: 8.209; load.download_or_cache_sec: 0.821; lease.free_mb_before: 11722; lease.evicted_models: []
- per-image wall_time_sec: 29.344 / 30.131; peak_vram_allocated_mb: 10929.4; peak_vram_reserved_mb: 11972
- renders: style / scene / action -> wall_time_sec / peak_vram_reserved_mb / segment.foreground_fraction / cut_sec
  - action_webtoon / classroom / waving -> 29.537 / 11972 / 0.2009 / 0.15
  - action_webtoon / classroom / pointing_up -> 29.344 / 11972 / 0.2167 / 0.148
  - action_webtoon / kitchen / explaining -> 29.662 / 11972 / 0.2358 / 0.157
  - action_webtoon / kitchen / thinking -> 29.8 / 11972 / 0.191 / 0.163
  - bright_anime / classroom / waving -> 29.914 / 11972 / 0.0441 / 0.17
  - bright_anime / classroom / pointing_up -> 30.022 / 11972 / 0.2142 / 0.167
  - bright_anime / kitchen / explaining -> 30.125 / 11972 / 0.2335 / 0.177
  - bright_anime / kitchen / thinking -> 30.131 / 11972 / 0.2212 / 0.179
### p4_frames
- wall_sec: not reported; error: none; load.load_sec: not reported; load.download_or_cache_sec: not reported; lease.free_mb_before: not reported; lease.evicted_models: not reported
- per-image wall_time_sec: not reported / not reported; peak_vram_allocated_mb: not reported; peak_vram_reserved_mb: not reported
## gpu_snapshots: label -> vram_used_mb / vram_free_mb
- start -> 558 / 11553
- p1_style_lease_acquired -> 558 / 11553
- p1_style_worker_exited -> 442 / 11669
- p2_assets_lease_acquired -> 442 / 11669
- p2_assets_worker_exited -> 389 / 11722
- p3_m2_lease_acquired -> 389 / 11722
- p3_m2_worker_exited -> 353 / 11758
- end -> 353 / 11758
- missing files: none
## Owner decisions (LEAVE EMPTY -- the owner fills this in)
- Style A (action_webtoon) or B (bright_anime)? Looks like the anime you want?:
- Character OK now (design + identity across assets and actions)?:
- Halo gone (blend vs cut in sheet_m2)?:
- Frames OK?:
