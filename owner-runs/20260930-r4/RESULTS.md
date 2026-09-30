# Owner-machine results r4 (Task 20.2c) 2026-09-30
- Pinned commit: 81f6c67e67c514355acd462895e68e53dfb7724e
- Env: 2.11.0+cu128 12.8 True 0.40.0
- Memory (preflight): TotalVisibleMemorySize 33289648 / FreePhysicalMemory 16684776 / FreeVirtualMemory 12834480
## Per phase (p1_style, p2_assets, p3_m2, p4_frames)
### p1_style
- wall_sec: 119.6; error: none; load.load_sec: 6.798; lease.free_mb_before: 11591; lease.evicted_models: []
- per-image wall_time_sec: 21.111 / 21.407; peak_vram_allocated_mb: 9169.6; peak_vram_reserved_mb: 11610
### p2_assets
- wall_sec: 221.8; error: none; load.load_sec: 5.002; lease.free_mb_before: 11688; lease.evicted_models: []
- per-image wall_time_sec: 26.801 / 29.349; peak_vram_allocated_mb: 11185.1; peak_vram_reserved_mb: 13746
- encode: wall_time_sec 0.341, items 4, with_ip true, do_cfg true
### p3_m2
- wall_sec: 279.9; error: none; load.load_sec: 8.069; lease.free_mb_before: 11691; lease.evicted_models: []
- per-image wall_time_sec: 31.475 / 33.103; peak_vram_allocated_mb: 10928.9; peak_vram_reserved_mb: 11972
- renders: scene / action / variant -> wall_time_sec / peak_vram_allocated_mb / peak_vram_reserved_mb
  - classroom / waving / strict -> 31.475 / 10928.9 / 11972
  - classroom / waving / loose -> 32.147 / 10928.7 / 11972
  - classroom / pointing_up / strict -> 32.637 / 10928.7 / 11972
  - classroom / pointing_up / loose -> 32.767 / 10928.7 / 11972
  - kitchen / explaining / strict -> 32.772 / 10928.7 / 11972
  - kitchen / explaining / loose -> 32.994 / 10928.7 / 11972
  - kitchen / thinking / strict -> 33.103 / 10928.7 / 11972
  - kitchen / thinking / loose -> 33.068 / 10928.7 / 11972
### p4_frames
- wall_sec: not reported; error: none; load.load_sec: not reported; lease.free_mb_before: not reported; lease.evicted_models: not reported
- per-image wall_time_sec: 0.137 / 0.164; peak_vram_allocated_mb: not reported; peak_vram_reserved_mb: not reported
## gpu_snapshots: label -> vram_used_mb / vram_free_mb
- start -> 520 / 11591
- p1_style_lease_acquired -> 520 / 11591
- p1_style_worker_exited -> 423 / 11688
- p2_assets_lease_acquired -> 423 / 11688
- p2_assets_worker_exited -> 420 / 11691
- p3_m2_lease_acquired -> 420 / 11691
- p3_m2_worker_exited -> 413 / 11698
- end -> 418 / 11693
- missing files: none
## Owner decisions (LEAVE EMPTY -- the owner fills this in)
- Style v2 on base: closer to the wanted look?:
- Simple character recognisable across views / expressions / actions?:
- M2 natural, no seam? Pose strict or loose?:
- Frames with captions look professional?:
