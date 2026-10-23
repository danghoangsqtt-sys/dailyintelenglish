# PROJECT-CONTEXT.md — Daily Intel English Studio

<!-- crystallize_version: 0.8.0 -->

## Project output folders — Phase 76 (2026-10-23)

New hierarchical exports use a user-selected parent and resolve to Topic / Series / `Ep NN - video title`; standalone projects use project Topic / project name. The parent is remembered per Topic and checked outputs are synchronized automatically. Existing per-project output settings remain in legacy mode until the user changes the folder or selects the new layout. Old exported files are never moved or deleted. This exports selected deliverables, not the internal project database. See [Phase 76 plan](phases/76-topic-project-folders/PLAN.md) and [folder guide](../docs/operations/topic-project-folders.md).

## Current TTS direction — Phase 75 (2026-10-23)

Edge TTS remains the default. The owner accepted an OmniVoice Voice Design laughter audition made through the public Hugging Face Space and authorized integrating OmniVoice as an optional, explicit local engine. Phase 75 adds per-speaker selection, an editable voice description, local sample preview, native `[laughter]`/`[sigh]` cues, and an isolated GPU worker. Local model installation and RTX 3060 listening remain open. `[hắng giọng]` is not supported by OmniVoice and must produce an error without engine fallback. See [Phase 75](phases/75-omnivoice-local-tts/PLAN.md) and [setup guide](../docs/operations/omnivoice-local-tts.md).

Phase 74's script annotation/editor and Edge cue rendering are implemented; its Edge listening gate is superseded by the owner's newer engine direction, not approved. See [Phase 74 state](phases/74-ai-vocal-cues/PHASE-STATE.md).

## ViePilot Active Profile

profile_id: none / not configured

---

<product_vision>

## Product Vision

**Daily Intel English Studio** là công cụ sản xuất nội dung tiếng Anh được hỗ trợ bởi AI dành cho content creator Việt Nam muốn xây dựng kênh YouTube học tiếng Anh chuyên nghiệp.

### Core Value Proposition
- **Tạo nội dung chuẩn xác**: AI với prompt nghiêm ngặt đảm bảo từ vựng, ngữ pháp, collocation đúng chuẩn Oxford/Cambridge theo từng cấp độ CEFR
- **Pipeline hoàn chỉnh**: Từ ý tưởng → kịch bản → giọng đọc TTS → video podcast → YouTube description trong một app duy nhất
- **Local-first media**: generation and media storage run locally where supported. Edge TTS needs internet; OmniVoice is an optional local GPU engine after its separate model setup.
- **Không lo copyright**: Thư viện nhạc nền do người dùng tự quản lý

### Phase Overview

| Phase | Scope | Timeline |
|-------|-------|----------|
| **Phase 1** | Full feature build — tất cả tính năng cốt lõi | Day 1-7 |
| **Phase 2** | Testing, optimization, UX polish | Day 8-14 |
| **Phase 3** | Review, documentation, demo video | Day 15-21 |

### Anti-Goals (Không làm trong 21 ngày)
- ❌ Multi-user / cloud deployment
- ❌ Mobile app
- ❌ Auto-upload lên YouTube API
- ❌ Real-time collaboration
- ❌ Subscription/payment system

</product_vision>

---

## Domain Knowledge

### CEFR Level System
Ứng dụng phải kiểm soát ngôn ngữ theo 6 cấp độ CEFR:

| Level | Name | Đặc điểm ngôn ngữ |
|-------|------|--------------------|
| A1 | Beginner | Câu đơn giản, từ vựng cơ bản (500 từ), hiện tại đơn |
| A2 | Elementary | Câu ghép đơn giản, 1000 từ, quá khứ đơn |
| B1 | Intermediate | Clauses phức, 2000 từ, tenses đầy đủ |
| B2 | Upper-Intermediate | Complex grammar, 4000 từ, idioms phổ biến |
| C1 | Advanced | Nuanced language, collocations advanced, 8000 từ |
| C2 | Proficiency | Native-like, full idiom/slang range, 16000+ từ |

### Podcast Genre Rules
Mỗi genre có cấu trúc dialogue riêng:

| Genre | Turn Pattern | Typical Length | Filler Words |
|-------|-------------|----------------|--------------|
| Instructions | A leads, B follows/questions | Short turns | "So...", "Now..." |
| Debate | Alternating, interruptions OK | Medium turns | "Actually...", "But..." |
| Interview | Q&A structured | Mixed | "Hmm", "Right" |
| Small Talk | Rapid exchange | Short turns | "Yeah", "Oh really?" |
| Storytelling | Longer monologue sections | Long turns | "So...", "And then..." |
| News Report | Formal, minimal filler | Medium turns | Minimal |

### English Accent Characteristics
Các accent khác nhau ảnh hưởng đến vocabulary choice và expressions:

| Accent | Unique Features | Example Differences |
|--------|-----------------|---------------------|
| American | Rhotic 'r', non-British vocab | "trunk" vs "boot", "fall" vs "autumn" |
| British (RP) | Non-rhotic, formal vocabulary | "lift" vs "elevator", "flat" vs "apartment" |
| Australian | Informal tone, local slang | "arvo" (afternoon), "servo" (gas station) |
| Singaporean | Singlish particles sometimes | "lah", "can", pragmatic simplification |
| Indian | Formal register, specific idioms | High use of passive voice, formal address |

### Language Features Contract

| Feature | Usage Rules |
|---------|-------------|
| Collocation | Must be verifiable in Oxford Collocations Dictionary |
| Idiom | Must be level-appropriate (A2+ for simple, B2+ for complex) |
| Slang | C1+ only, must be contemporary (post-2020) |
| Local expressions | Must match selected accent region |
| Phrasal verbs | A2+ for separable, B1+ for inseparable |
| Business register | Toggle for formal/professional contexts |

---

## Business Rules

### Script Generation Rules
1. **Word count estimation**: ~130 words per minute (native), ~100 wpm (B1 level), ~80 wpm (A1 level)
2. **Speaker balance**: All speakers must have roughly equal line counts (±20%)
3. **No speaker monologue > 5 lines**: Must break up with other speaker
4. **Filler words**: Natural fillers required for Casual register (um, uh, you know, like)
5. **No repetition**: Same phrase may not appear more than twice in one script
6. **Topic relevance**: Every line must be topically relevant — no off-topic small talk beyond intro/outro

### TTS Rules
1. **Explicit engine**: Edge TTS is the default; OmniVoice runs only for speakers who select it. Never silently switch engines.
2. **Cache identity**: Include engine, voice, design description, settings, script text and cue recipe in the line fingerprint.
3. **GPU sharing**: OmniVoice handles one line in a one-shot child process inside the shared GPU lease.
4. **Supported cues**: Native OmniVoice `[laughter]` and `[sigh]`; `[h?ng gi?ng]` is unsupported and must fail with an actionable message.
5. **Timings**: Edge supplies word boundaries; OmniVoice does not. Do not fabricate word timings.
6. **Silence between lines**: 0.3s between same speaker, 0.5s between different speakers.
7. **Speed range**: 0.75x?1.5x; new-speaker defaults are resolved from the project's CEFR level.

### Audio Rules
1. **Background music volume**: Max -18dBFS when speech is playing (ducking)
2. **Output normalization**: Target -16 LUFS for YouTube
3. **MP3 bitrate**: 192kbps minimum
4. **WAV specs**: 44100 Hz, 16-bit stereo

### Video Rules
1. **Resolution**: 1280x720 (standard), 720x1280 (Shorts)
2. **Frame rate**: 30fps
3. **Subtitle font**: Bold, white with black outline, bottom 20% of frame
4. **Subtitle timing**: ±0.1s sync with audio
5. **Avatar layout**: Speaker 1 left (30% width), Speaker 2 right (30% width), center for title/background

### YouTube Package Rules
1. **Description max**: 5000 characters (YouTube limit)
2. **Tags max**: 500 characters total
3. **Timestamps format**: `0:00 Introduction`, `1:23 Main Discussion`
4. **Vocabulary format**: `word (part of speech) — definition [example]`

---

## Conventions

### Project Naming
- Project folders: `data/projects/{uuid}/`
- Audio files: `data/audio/{uuid}/{filename}`
- Video files: `data/video/{uuid}/{filename}`
- TTS cache: `data/tts_cache/{project_uuid}/.../{line_id}.mp3` with a fingerprint sidecar; Edge word timings use a `.words.json` sidecar, while OmniVoice intentionally has none.

### Prompt Templates Naming
- `prompts/script/{genre}_{cefr_level}.txt`
- `prompts/learning/vocabulary_{cefr_level}.txt`
- `prompts/thumbnail/fill_template.txt`
- `prompts/youtube/description.txt`

### API Response Format
```json
{
  "success": true,
  "data": {...},
  "error": null,
  "meta": {
    "processing_time_ms": 1234,
    "model_used": "qwen3.5:9b"
  }
}
```

### Generation Progress
Long-running AI/media tasks use job/status polling APIs. TTS line synthesis reports an engine error directly and does not perform automatic fallback.

---

## Constraints

### Hardware Constraints
- GPU: RTX 3060 12GB VRAM; local image generation and OmniVoice share one GPU lease. OmniVoice currently requests 8192 MiB free pending on-device measurement.
- Disk: Audio/video files can be large — warn if disk < 5GB free
- RAM: Pydub loads full audio into memory — max practical audio length ~45 min

### API Constraints
- Ollama (local, default as of Phase 14): one model resident (`OLLAMA_MAX_LOADED_MODELS=1`),
  one concurrent generation (`OLLAMA_NUM_PARALLEL=1`) — see docs/operations/local-ai.md
- Gemini API (dormant, unsupported rollback only): rate limit 15 RPM (free tier),
  1M token/request limit — not a normal-use constraint since Amendment D
- Edge TTS: No official rate limit, but respect 1 req/sec to avoid blocks

### Platform Constraints
- Windows-first: All paths must use `os.path` / `pathlib`, not hardcoded separators
- Python 3.11+: Use modern type hints, `match` statements where appropriate
- ffmpeg must be in PATH: Setup script must verify and guide installation

---

## User Stories & Use Cases

### Primary Use Cases

| ID | Actor | Goal | Acceptance |
|----|-------|------|------------|
| UC-01 | Creator | Tạo kịch bản debate B2 tiếng Anh-Mỹ 10 phút | Script có 2 speakers, collocations đúng B2, tự nhiên |
| UC-02 | Creator | Tạo audio với 2 giọng khác nhau (male/female) | Mix audio rõ ràng, giọng phân biệt, pause hợp lý |
| UC-03 | Creator | Export video podcast với subtitle | MP4 với subtitle đồng bộ + SRT file riêng |
| UC-04 | Creator | Tạo thumbnail chuyên nghiệp | 3+ phiên bản 1280x720, khác biệt nhau |
| UC-05 | Creator | Copy YouTube description đầy đủ | Description + chapters + transcript + vocabulary |
| UC-06 | Creator | Xem lại và chỉnh sửa kịch bản | Inline editor, re-generate từng câu |
| UC-07 | Creator | Quản lý thư viện bài đã tạo | Dashboard với search, filter theo level/genre |

---

## Skills

skills_used: none (no vp-brainstorm skill registry used)
