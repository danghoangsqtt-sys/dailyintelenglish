# Owner-machine results r3 (Task 20.2b) 2026-09-30
- Pinned commit: 88b01d4092f5ecd628fd35fb538e0d69d4284ebd
- Env: 2.11.0+cu128 12.8 True 1.30.0
- Memory (preflight): TotalVisibleMemorySize 33289648 / FreePhysicalMemory 15562336 / FreeVirtualMemory 9878244
## Per phase (p1_style_lightning, p1_style_base, p2_assets, p3_actions, p4_cutouts, p5_m1, p6_m2)
### p1_style_lightning
- wall_sec: 50; error: none; load.load_sec: 13.614; lease.free_mb_before: 11578; lease.evicted_models: []
- per-image wall_time_sec: 2.164 / 6.078; peak_vram_allocated_mb: 9149.5; peak_vram_reserved_mb: 13134
### p1_style_base
- wall_sec: 90.7; error: none; load.load_sec: 11.665; lease.free_mb_before: 11641; lease.evicted_models: []
- per-image wall_time_sec: 22.058 / 27.553; peak_vram_allocated_mb: 9169.6; peak_vram_reserved_mb: 13320
### p2_assets
- wall_sec: 225.4; error: none; load.load_sec: 7.387; lease.free_mb_before: 11706; lease.evicted_models: []
- per-image wall_time_sec: 9.705 / 10.855; peak_vram_allocated_mb: 11164; peak_vram_reserved_mb: 13582
- encode: wall_time_sec 0.25, items 4, with_ip true
### p3_actions
- wall_sec: 832.7; error: none; load.load_sec: 790.355; lease.free_mb_before: 11697; lease.evicted_models: []
- per-image wall_time_sec: 8.021 / 9.114; peak_vram_allocated_mb: 10790; peak_vram_reserved_mb: 12966
### p4_cutouts
- wall_sec: 51.5; error: none; load.load_sec: not reported; lease.free_mb_before: not reported; lease.evicted_models: not reported
- per-image wall_time_sec: 0.809 / 0.941; peak_vram_allocated_mb: not reported; peak_vram_reserved_mb: not reported
- cut-outs: input -> foreground_fraction / soft_edge_fraction
  - asset_full_body_neutral.png -> 0.4843 / 0.0204
  - asset_full_body_happy.png -> 0.476 / 0.0203
  - asset_full_body_surprised.png -> 0.4865 / 0.0187
  - asset_full_body_thinking.png -> 0.484 / 0.0188
  - asset_full_body_sad.png -> 0.4827 / 0.0193
  - action_waving.png -> 0.1918 / 0.0259
  - action_pointing.png -> 0.2061 / 0.0221
  - action_thinking.png -> 0.1895 / 0.0537
  - action_cheering.png -> 0.2606 / 0.0192
### p5_m1
- wall_sec: not reported; error: none; load.load_sec: not reported; lease.free_mb_before: not reported; lease.evicted_models: not reported
- per-image wall_time_sec: 0.165 / 0.195; peak_vram_allocated_mb: not reported; peak_vram_reserved_mb: not reported
### p6_m2
- wall_sec: 80; error: none; load.load_sec: 13.103; lease.free_mb_before: 11598; lease.evicted_models: []
- per-image wall_time_sec: 26.491 / 27.208; peak_vram_allocated_mb: 11147.8; peak_vram_reserved_mb: 12476
## gpu_snapshots: label -> vram_used_mb / vram_free_mb
- start -> 533 / 11578
- p1_style_lightning_lease_acquired -> 533 / 11578
- p1_style_lightning_worker_exited -> 470 / 11641
- p1_style_base_lease_acquired -> 470 / 11641
- p1_style_base_worker_exited -> 405 / 11706
- p2_assets_lease_acquired -> 405 / 11706
- p2_assets_worker_exited -> 414 / 11697
- p3_actions_lease_acquired -> 414 / 11697
- p3_actions_worker_exited -> 514 / 11597
- p6_m2_lease_acquired -> 513 / 11598
- p6_m2_worker_exited -> 457 / 11654
- end -> 457 / 11654
- missing files: none
## Owner decisions (LEAVE EMPTY -- the owner fills this in)
- Style: Ghibli-like enough? Lightning vs base?:
- Same character across views / expressions / actions?:
- Cut-out quality OK?:
- M1 naive vs M1 integrated vs M2: which looks natural (not stiff)?:
