# Phase 20 — Task 20.2g spike report: quality tuning (male redesign, pose-placed scenes, hand repair)

- **Run:** owner machine, runbook r7, 2026-10-01.
- **Pinned code:** `a6284bc`.
- **Evidence:** branch `owner-runs/20261001-r7` @ `091be65`.
- **Design:** `.viepilot/phases/20-ai-visuals/tasks/task-20.2g.md`.
- **Status:** **awaiting the owner's verdict.** The observations below are the Coder's
  reading.

## 1. Run facts

| Phase | Wall (s) | Per image (s) | Peak allocated / reserved (MB) | Prompt tokens max | Truncated |
|---|---|---|---|---|---|
| p1: 12 candidates | 290 | 21.2–21.9 | 9170 / 11610 | 72 | 0 |
| p2 (IP): 12 expressions + 4 encodes | 357 | 27.5–28.4 | 11185 / 13746 | 68 | 0 |
| p3 ControlNet one-pass (no encoders, IP layers): 16 renders | 614 | 36.6–37.6 | 10930 / **13216** | — | — |
| p4 hand repair (inpaint 768²): 32 hands | 245 | 6.9–7.2 | 8106 / 8910 | 38 | 0 |
| p5 frames | — | — | — | — | — |

- **No errors, no downloads.** The VRAM baseline returned after each worker.
- **P3 reserves 13.2 GB** (text2img ControlNet with CFG at 1344×768). That likely spills
  slightly, at 37 s/image against 30 s for the r5 inpaint renders. Production should
  watch this, e.g. with VAE tiling or one fewer resident component.

## 2. Observations (Coder's reading; the owner decides)

1. **Actions and placement: 16 of 16 followed** (`sheet_frames.png`).
   - waving, holding a book, pointing, talking with open hands;
   - the character stands left of centre and the vocab card is never covered.
2. **Scale:** a waist/knee-up medium shot, smaller than the r6 close-ups. The characters
   now read as standing *in* the room. Whether that is better than r6's closer framing
   is the owner's call.
3. **Male redesign** (`sheet_candidates.png`, `sheet_expressions.png`).
   - Friendlier, more attractive faces.
   - **The laughing expression now shows**, unlike r6.
4. **Outfit.**
   - The female is stable (yellow sweater, jeans); one render adds a white cardigan.
   - **The male in `r3_bright` gains an orange over-layer** on top of the teal hoodie,
     despite "jacket" in the negative. `r3_watercolor` stays closer to the teal hoodie +
     white tee.
5. **Hands** (`sheet_hands.png`, raw vs repaired).
   - At sheet resolution the differences are subtle: fingers are a little cleaner on
     some book-holding hands.
   - The full-resolution raw/fixed pairs are in the run folder on the owner's machine
     (`data\tmp\phase20g_character_v5\run_r7\`).

## Owner verdicts 2026-10-01 (verbatim, with translation)

*"1. Tôi thích ứng viên nam 1 đầu tóc gọn gàng đừng để tóc dài ẻo lả, 2 tay sau khi sửa đã
có nhiều cải thiện và chất lượng rất tốt; 3 tôi thích khung hình cận cảnh hơn, nhưng tôi
chưa thấy các dạng hình ảnh trò chuyện giữa 2 người, trò chuyện cảnh cận người và trò
chuyện góc rộng có bối cảnh như trường học và quán cafe; tôi thích nhân vật nam mặc quần áo
gọn gàng và slimfit hơn là áo khoắc hoodie rườm rà; về nhân vật nữ khá tốt rồi không cần
thay đổi thêm, nhưng màu sác của trang phục cũng cần phải để tâm vì dễ bị rối loạn màu
trang phục, nói chung về trang phục nam và nữ chỉ cần 1 áo và 1 quần; màu sắc của áo quần
đơn màu không họa tiết, không cần nhiều màu trên áo với quần"*

1. **Male: candidate 1**, with neat short hair, "not long, effeminate hair".
2. **The hand repair improved a lot: very good quality.**
3. **Close-up framing is preferred.**
   - Two-person conversations are missing: a close-up conversation, and wide
     conversations in a school and in a café.
4. **The male should wear neat slim-fit clothes**, not a bulky hoodie.
5. **The female is good; no change.**
6. **Outfits:** watch colour confusion. Exactly 1 top + 1 bottom, solid colours, no
   pattern, not many colours.

**The follow-up is Task 20.2h** (`.viepilot/phases/20-ai-visuals/tasks/task-20.2h.md`).
