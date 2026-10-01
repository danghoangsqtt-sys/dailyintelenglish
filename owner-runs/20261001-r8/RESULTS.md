# Owner-machine results r8 (Task 20.2h) 2026-10-01
- Pinned commit: 887ea854d366eab9818a5a2a8d00d33c103d1ace
- Env: 2.11.0+cu128 12.8 True 0.40.0 1.30.0
- Memory (preflight): TotalVisibleMemorySize 33289648 / FreePhysicalMemory 16618964 / FreeVirtualMemory 11842276
- r7 faces found (from phases.p1_cards_encode.cards[].r7_face_found): r3_watercolor/female_student: true; r3_watercolor/male_student: true; r3_bright/female_student: true; r3_bright/male_student: true
- Packaged files: L_env.txt, L_r8.json, L_r8.err, preflight.txt, 3 sheets, 4 cards, 20 frames, 3 worker logs; missing: none

## p1_cards_encode
- wall_sec: 135.2; error: none; load.load_sec: 4.76; lease: free_mb_before 11707, evicted_models []
- per-image wall_time_sec: min 28.462 / max 30.053; peak_vram_allocated_mb: max 11185.1; peak_vram_reserved_mb: max 13746.0
- prompt_tokens: max 72; prompt_truncated: 0 images true
- cards: 4; encodes: 10
- ip_faces per encode: r3_watercolor/single_female_cafe 1; r3_watercolor/single_male_classroom 1; r3_watercolor/duo_closeup_cafe 2; r3_watercolor/duo_wide_school 2; r3_watercolor/duo_wide_cafe 2; r3_bright/single_female_cafe 1; r3_bright/single_male_classroom 1; r3_bright/duo_closeup_cafe 2; r3_bright/duo_wide_school 2; r3_bright/duo_wide_cafe 2

## p2_renders
- wall_sec: 926.6; error: none; load.load_sec: 8.741; lease: free_mb_before 11685, evicted_models []
- per-image wall_time_sec: min 38.291 / max 48.56; peak_vram_allocated_mb: max 10929.9; peak_vram_reserved_mb: max 13216.0
- prompt_tokens: not recorded per render; prompt_truncated: not recorded per render
- renders: 20

## p3_hands
- wall_sec: 336.8; error: none; load.load_sec: 6.271; lease: free_mb_before 11706, evicted_models []
- per-image wall_time_sec: min 6.978 / max 7.502; peak_vram_allocated_mb: max 8105.6; peak_vram_reserved_mb: max 8910.0
- prompt_tokens: max 38; prompt_truncated: 0 images true
- hand repairs: 44

## p4_frames
- wall_sec: not recorded; error: none; load.load_sec: not recorded; lease: not recorded
- per-image wall_time_sec: not recorded; peak_vram_allocated_mb: not recorded; peak_vram_reserved_mb: not recorded
- prompt_tokens: not recorded; prompt_truncated: not recorded
- frames: 20

## gpu_snapshots
- start -> vram_used_mb 404 / vram_free_mb 11707
- p1_cards_encode_lease_acquired -> vram_used_mb 404 / vram_free_mb 11707
- p1_cards_encode_worker_exited -> vram_used_mb 426 / vram_free_mb 11685
- p2_renders_lease_acquired -> vram_used_mb 426 / vram_free_mb 11685
- p2_renders_worker_exited -> vram_used_mb 405 / vram_free_mb 11706
- p3_hands_lease_acquired -> vram_used_mb 405 / vram_free_mb 11706
- p3_hands_worker_exited -> vram_used_mb 374 / vram_free_mb 11737
- end -> vram_used_mb 368 / vram_free_mb 11743

## Owner decisions
