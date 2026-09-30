# Phase 20 — Proposed Amendment B: Character Library + Scene Library ("asset-based" visuals)

- **Status:** PROPOSAL, awaiting owner and PM approval. Nothing below is implemented.
- **Written by:** Coder (cloud session), 2026-09-30, right after the owner's Task 20.2
  verdict.
- **Replaces, if approved:** the provisional tasks 20.3–20.5 of
  `docs/implementation/phase-20-ai-visuals.md` §3. Tasks 20.1 and 20.2 stay as they are.

## 1. The owner's direction (verbatim, 2026-09-30)

> *"cả base và lightning đều tốt nhưng lightning cho kết quả nhanh hơn và tôi nghĩ có thể cải
> thiện bằng cách tối ưu hóa prompt và luồng tạo nhân vật, có thể tạo nhân vật trước gồm các
> góc mặt và toàn thân, các biểu cảm khác nhau, sau đó sử dụng các nhân vật do người dùng
> chọn đã được tạo và lưu sẵn vào hệ thống (giống game) để đưa vào các bối cảnh khác nhau để
> tối ưu thời gian tạo ảnh tránh được sai sót, người dùng cũng có thể tạo sẵn các bối cảnh
> trước trong quá trình sử dụng và lưu lại các bối cảnh đó, đặt tên cho bối cảnh. Vậy thì
> việc tạo ảnh và cốt truyện sẽ không còn là prompt rời rạc ngẫu nhiên mà là những đối tượng
> đã được xác lập từ trước có nội dung mô tả rõ ràng và kết hợp lại với nhau, đảm bảo được sự
> đồng bộ thống nhất và giảm tải trọng cho hệ thống tạo sinh ảnh."*

In short:
- **Characters** are created once: several face angles and a full body, with several
  expressions. They are saved, and the user picks them like choosing a game character.
- **Scenes** are created once, named, saved, and reused.
- Images and the storyline are then **composed from these established, described objects**
  instead of from one-off random prompts. That gives consistency and less generation load.

## 2. Why this is the right shape (evidence from 20.2)

- **Consistency is decided once, at library time.** Run 2's IP sheet showed that one
  reference keeps a character recognisable. Generating each angle and expression **once**,
  with the owner approving each, removes per-episode drift entirely.
- **Generation load drops.**
  - Today, every thumbnail is a fresh generation: 2.1 s with Lightning, ~9.1 GB VRAM.
  - With IP-Adapter it is 7.5 s and ~11.1 GB, nearly the whole card, which forces a qwen
    eviction and costs a 12 s qwen reload.
  - A library turns most per-episode work into **reuse plus compositing**.
- **Fewer errors.** Lightning at CFG 0 ignores the negative prompt (20.2 finding). Run 2
  also showed Lightning inventing mascot characters in "background" images. Generating
  scenes *once*, owner-approved and explicitly "no people", removes both risks from the
  per-episode path.

## 3. Proposed design

### 3.1 Objects (additive SQLite migrations, nothing existing changes shape)

| Table | Key fields | Notes |
|---|---|---|
| `characters` | id, name, description (canonical text), style, base_seed, created_at | **Global library**, reused across episodes (recommended; the channel's recurring cast) |
| `character_assets` | id, character_id, view (`face_front`, `face_3q_left`, `face_3q_right`, `full_body_front`, …), expression (`neutral`, `happy`, `surprised`, `thinking`, `sad`, …), png_path (transparent), approved | One row per (view, expression) the owner approved |
| `scenes` | id, name, description, tags, seed, image_16x9_path, image_9x16_path, created_at | Named, reusable backgrounds, generated as "no people" |
| `speakers.character_id` | new nullable column | Links a speaker (Alex, Maya) to a library character. `speakers.avatar_image_path` (Task 1.7c) is set to the character's `face_front/neutral` asset, so Task 19.4's existing avatar slot keeps working (reuse, not a parallel path) |

### 3.2 Flows

1. **Create a character (the "character creator"):**
   - the owner writes or edits a description;
   - Lightning generates N portrait candidates;
   - the owner picks one as the reference;
   - IP-Adapter generates the chosen views × expressions from that reference;
   - the owner approves or regenerates each;
   - backgrounds are removed, and the assets are saved as transparent PNGs.
2. **Create a scene:**
   - the owner names and describes it;
   - Lightning generates 16:9 and 9:16 variants with "no people";
   - the owner approves, renames or regenerates.
3. **Compose (per episode).** Two modes:
   - **M1 "collage" (the proposed default):** Pillow composites scene + character cut-out
     (a chosen view/expression) + the existing Task 1.8b headline layer.
     - Under 1 s, CPU only, **zero GPU**, and 100% identical characters every time.
     - The Pillow template fallback stays (invariant 47).
   - **M2 "integrated render" (optional):** Lightning + IP-Adapter renders the character
     *into* the scene, for better lighting.
     - ~7.5 s and ~11.1 GB, so it needs the whole card (Task 20.1 lease; threshold
       11264).
     - Only on request.
4. **Storyline (later task):**
   - the script LLM receives the chosen characters' canonical descriptions and the scene
     names;
   - script sections are tagged with a scene, and lines optionally with an expression;
   - Remotion then shows each section's scene and each speaker's current expression in
     the avatar slot.

   This is the owner's *"cốt truyện … từ các đối tượng đã được xác lập"* ("a storyline
   built from established objects").

### 3.3 Proposed task list (replaces the provisional 20.3–20.5)

| Task | Content |
|---|---|
| **20.2b** | **Spike, owner machine:** (i) does IP-Adapter + Lightning keep identity across **profile and full-body** views and across expressions? (20.2 only tested near-frontal scenes.) (ii) background removal: candidates `rembg`/U²-Net and BiRefNet, **licence re-checked for commercial use** (invariant 49), cut-out quality on cartoon/3D. (iii) Is an M1 collage thumbnail acceptable to the owner's eye? |
| 20.3 | Library backend: migrations, storage under `data/library/`, CRUD API, generation jobs through the image worker + Task 20.1 lease, background removal |
| 20.4 | Library UI: the character creator (candidates → pick → views × expressions → approve) and the scene manager (create / name / regenerate) |
| 20.5 | Composition: thumbnail M1 (+ optional M2) behind the Phase 19.7-style opt-in + kill switch, falling back to the Pillow templates |
| 20.6 | In-video: speaker ↔ character (`speakers.character_id`), the avatar slot, a scene per section, and expression per line |
| 20.7 | Gate B-14 (owner visual sign-off on ≥ 3 real episodes) |
| 20.8 | Close-out |

Script/storyline integration (§3.2 step 4) can stay inside 20.6 or become its own phase, as
the PM decides.

### 3.4 Invariants check

| Invariant | How this design meets it |
|---|---|
| 46 local-only | All generation stays on the RTX 3060 |
| 47 fallback | The Pillow templates stay the fallback for every thumbnail |
| 48 VRAM shared | Every generation goes through the Task 20.1 lease; M1 needs no GPU at all |
| 49 licence | SDXL/Lightning OpenRAIL++, IP-Adapter Apache-2.0; the background-removal licence is checked in 20.2b |
| 50 reference images are the owner's own | Characters are invented and owner-approved (the plan allows "pick from generated candidates"). The app never draws a real person |

## 4. Questions for the owner (the answers shape 20.2b/20.3)

1. **One global library shared by all episodes** (a recurring cast, like a channel's
   mascots), or a separate cast per episode? Recommendation: global.
2. **The starting set of views and expressions.** Proposal: 3 face views + 1 full body ×
   5 expressions = 20 assets per character, about 20 × 7.5 s ≈ 2.5 min of GPU once per
   character.
3. **One fixed art style for the whole channel** (e.g. "modern 3D animation")? It keeps
   all characters and scenes visually coherent.
4. **Default composition mode:** M1 collage (fast, zero GPU, perfectly consistent), with M2
   only on request?
