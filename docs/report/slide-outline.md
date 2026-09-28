# Slide outline — báo cáo dự án Daily Intel English Studio

**Thời gian:** Thứ 6, 2026-10-02
**Audience:** ban giám khảo (kỹ thuật, quan tâm tốc độ xử lý AI)
**Tone:** Technical-first hybrid — data lead, user value support
**Presenter:** owner (@dhsystem.sys)
**Format:** ~15-20 phút, 8 slides + demo live
**Backup:** pre-recorded video clips (Remotion karaoke + chip)

_Draft do PM (Claude Opus 4.7) soạn 2026-09-28. Owner customize brand/design/wording,
PM fill in real numbers sau khi benchmark chạy xong (Coder Report-UX-1 accepted trước)._

---

## Slide 1 — Title

- **Tên dự án:** Daily Intel English Studio
- **Sub-title:** AI-powered podcast production for English learners
- **Owner:** [tên owner]
- **Date:** 2026-10-02
- **Logo/branding placeholder**

_Speaker note:_ Introduce mình, background ngắn, mục đích trình bày (không quá 30 giây).

---

## Slide 2 — Vấn đề

**Tiêu đề:** Producing English learning podcasts is slow, expensive, and hard to keep consistent.

**3 gạch đầu dòng:**
- **Chậm:** 1 episode 8 phút cần vài giờ soạn script + record + edit + subtitle + thumbnail + YouTube description
- **Đắt:** đội ngũ full-stack (script writer + voice actor + video editor + graphic designer) là gánh nặng cho creator độc lập
- **Không đều tay:** CEFR calibration khó giữ ổn định qua nhiều episode; vocab/idiom teaching cần expertise ngôn ngữ

**Số liệu backup:** ước tính giờ công / cost per episode nếu owner có dữ liệu.

_Speaker note:_ "Đây là bài toán 1 creator độc lập gặp phải khi muốn scale content đều đặn hằng tuần."

---

## Slide 3 — Giải pháp

**Tiêu đề:** One AI pipeline, seven professional-quality outputs.

**Visual:** pipeline diagram từ trái qua phải:

```
Topic + CEFR → Script → Learning pack → TTS audio → Mixed audio →
    Video (subtitle burn) → Thumbnail (5 templates) → YouTube package (.zip)
```

**Ghi chú per step:**
- **Script:** Gemini 3.1 Flash-Lite generate dialogue theo topic + level + genre + số speaker
- **Learning pack:** Vocab/idiom/grammar/quiz auto-generate
- **TTS:** Edge TTS (10 accent × 3 gender = 30 voice)
- **Mix:** ffmpeg background music ducking, EBU R128 loudness normalization
- **Video:** ffmpeg subtitle burn-in, 16:9 + 9:16 aspect ratio
- **Thumbnail:** 5 template + Pillow render, 3-5 A/B variants
- **YouTube package:** titles/description/tags/chapters/transcript/vocab .zip

_Speaker note:_ "End-to-end: owner nhập topic, 45 giây sau có script, vài phút sau có full episode."

---

## Slide 4 — Kiến trúc AI (Cloud-first with local fallback)

**Tiêu đề:** Fast when the cloud is up, resilient when it isn't.

**Chain diagram:**

```
User request
    ↓
[1] Gemini 3.1 Flash-Lite ────→ Success? → Return
    ↓ fail/timeout/quota
[2] Gemini Flash-Lite (latest) → Success? → Return
    ↓
[3] OpenRouter: Nemotron 3 Super → Success? → Return
    ↓
[4] OpenRouter: Gemma 4 26B ──→ Success? → Return
    ↓
[5] OpenRouter: Dots3 Note ──→ Success? → Return
    ↓ every cloud path down
[6] Local qwen3.5:9b on RTX 3060 → Guaranteed answer
```

**Key features:**
- **Circuit breaker per provider** — 1 provider fail không kéo cả chain
- **Budget riêng per provider** — không đè quota
- **Kill switch:** `DIE_AI_ALLOW_CLOUD=false` → chuyển local 100%
- **Zero data leak:** API key never logged/returned/committed (Invariant I31)

_Speaker note:_ "Users không thấy fail — chain tự trượt xuống fallback trong <1s. Local qwen là bảo hiểm cuối, chạy hoàn toàn offline trên máy owner."

---

## Slide 5 — ⭐ Speed benchmark (main event)

**Tiêu đề:** 2.8× faster median, up to 4.4× best-vs-worst, on real B1 8-minute podcast.

**Chart PNG:** `docs/report/benchmark-chart.png` (đã build, real data)
- X-axis: 5 runs mỗi mode (bar cạnh nhau)
- Y-axis: wall time (seconds)
- Red: local (qwen3.5:9b on RTX 3060) — 5 real runs
- Green: cloud-first (Gemini→OpenRouter→local) — 5 real runs
- Dotted line = median mỗi mode

**Số liệu thật (Gate B-8 local 2026-09-23 + Gate B-11 cloud 2026-09-26, cùng topic "How small daily habits shape long-term health"):**

| Mode | n | Min | Median | Mean | Max | Stdev |
|---|---|---|---|---|---|---|
| **Local** (qwen3.5:9b, RTX 3060) | 5 | 105.4s | **126.5s** | 132.5s | 159.7s | 21.3s |
| **Cloud-first** (Gemini→OpenRouter→qwen fallback) | 5 | 36.1s | **45.2s** | 44.6s | 54.2s | 7.2s |

**Speed-up:**
- **2.80× median** (126.5s → 45.2s)
- **2.97× mean** (~3× ổn định)
- **4.42×** best cloud (36.1s) vs. worst local (159.7s)

**Ngoài speed:**
- Cloud-first stdev 7.2s vs local 21.3s = cloud predictable hơn 3× (dễ estimate ETA)
- Repetition 0.00% cả 2 mode (bounded repair pass)
- Media gate PASS cả 2 mode

**Raw data audit trail:** `docs/report/benchmark-summary.csv`

_Speaker note:_ "10 số đo real trên máy này, RTX 3060 12GB, không lab. Cloud fallback đảm bảo bảo backup local nếu network fail — kill switch `DIE_AI_ALLOW_CLOUD=false` chuyển 100% local trong 0 giây."

---

## Slide 6 — Chất lượng output (visual + educational)

**Tiêu đề:** Not just fast — production-quality output that teaches.

**Visual layout 2×2 hoặc 3 panel:**
- **Panel A:** Screenshot Remotion karaoke word-sync (active word highlighted yellow, speaker chip top-left)
- **Panel B:** Screenshot Step 3 Learning content (vocab card với IPA + PoS + EN/VI definition + example)
- **Panel C:** Screenshot YouTube package .zip content (metadata + description + chapters)
- **Panel D:** 3 CEFR levels comparison mini text (A1 vs B1 vs C1 same topic)

**Ghi chú:**
- Word-level karaoke (Phase 19 Task 19.3) — active word highlight sync với real Edge TTS WordBoundary
- Active-speaker indicator (Phase 19 Task 19.4) — chip color-coded per speaker, dark-theme palette
- 3 real sample episodes `docs/samples/{A1,B1,C1}/` chia sẻ trước buổi (attach .zip)

_Speaker note:_ "Output không chỉ nhanh mà thực sự dùng được — script pass CEFR review, vocab/idiom tuân thủ level, subtitle sync đến từng từ."

---

## Slide 7 — Demo live

**Tiêu đề:** Let's build one episode, live.

**Kịch bản demo (7-8 phút):**
1. Mở Dashboard → "+ New Project"
2. Step 1 Config: fill topic "Morning coffee routine" + B1 + small_talk + 2 speakers
3. Step 2 Generate Script → **quan sát progress banner** (elapsed counter + ETA visible từ Report-UX-1)
4. Đợi ~45s (elapsed counter tick, ~30s remaining hiển thị) → script hiện ra
5. Step 3 → Generate Learning → progress → learning content hiện
6. Step 4 → Generate All → TTS synth 12 lines → mix → audio player play
7. Step 5 → Render → video player play (subtitle burn-in visible)
8. Step 7 → YouTube Package → Download `.zip`

**Backup nếu network fail:**
- Pre-recorded video clip của toàn bộ flow trên (~4 min, sped up)
- 3 sample episodes .zip đã share trước

_Speaker note:_ "Tôi để đồng hồ trên màn hình để mọi người thấy real timing."

---

## Slide 8 — Roadmap + Q&A

**Tiêu đề:** What's built · What's next.

**Đã build (v1.1.0-beta, 2026-09-26):**
- 12 phase, 1178 test pass, 3 sample episodes
- Cloud-first AI với chain fallback
- Full 7-step production pipeline
- Standalone `.exe` (169 MB, PyInstaller)

**In-flight (Phase 19 Remotion, đang deploy):**
- Word-level karaoke captions
- Active-speaker indicator
- Progress UX improvements (elapsed + ETA)
- Tiếp tục: vocab pop-up cards, intro/outro, chapter bar

**Sắp tới (Phase 20 AI thumbnails):**
- Local image model trên RTX 3060 (cartoon/3D character per topic)
- Free, offline, zero API cost cho thumbnail

**Timeline:** [PLACEHOLDER — owner tự set 30/60/90 days]

**Q&A:** dự kiến ~5 phút.

---

## Speaker prep checklist (T5 tối / T6 sáng)

- [ ] Owner review + polish wording từng slide
- [ ] Convert markdown → Google Slides / PowerPoint / Keynote
- [ ] Chart PNG (`docs/report/benchmark-chart.png`) inserted vào slide 5
- [ ] 3 sample episodes `.zip` chia sẻ trước qua email/drive
- [ ] Pre-recorded backup video (~4 min sped-up walkthrough) inserted vào slide 7 (optional)
- [ ] Dev server dry-run: verify network, verify Gemini/OpenRouter keys active, verify Ollama running
- [ ] Timer visible cho demo (screen recording tool with timestamp overlay)

## Fallback plan nếu live demo fail

- **Network fail cloud AI:** kill switch auto-fallback local qwen — chậm hơn nhưng vẫn produce output → tự nhiên nói "đây là fallback đang hoạt động"
- **Ollama không chạy:** dùng `.exe` packaged trên máy khác, hoặc chuyển sang pre-recorded video clip
- **Toàn bộ máy hỏng:** slide screenshots + sample .zip vẫn đủ present

## PM's own note

- Slide 5 (speed benchmark) là core selling point cho panel này — invest polish tối đa
- Slide 4 (chain architecture) đủ technical để impress engineers nhưng đủ visual để non-tech follow
- Slide 6 tránh over-technical — audience mostly non-language-experts sẽ chỉ thấy "trông chuyên nghiệp"
- Slide 7 demo live có risk cao — luôn có backup video, luôn có 1 slide skip
- Slide 8 roadmap — owner tự thêm ambition (ví dụ multi-language, mobile app) nếu muốn signal vision
