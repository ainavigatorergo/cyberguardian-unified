---
title: CyberGuardian Unified Studio
emoji: 🔥
colorFrom: purple
colorTo: blue
sdk: docker
pinned: false
---

# CyberGuardian Unified — AI Video Studio

Автоматизированная студия для создания контента по двум темам:
- 🔐 Кибербезопасность (CyberGuardianSec)
- 🤖 Нейросети для бизнеса (AI Navigator)

## Что умеет

- Генерирует сценарии через Gemini (provod.ai)
- Создаёт озвучку через Edge TTS
- Генерирует ключевые сцены через Agnes AI (до 500 сек/день)
- Собирает фоновый видеоряд из Pexels и Pixabay
- Создаёт видео в форматах 16:9 (YouTube) и 9:16 (Shorts/TikTok)
- Генерирует SEO-метаданные, субтитры, обложки

## Переменные окружения

Добавь в **Settings → Variables and secrets**:

- `OPENAI_API_KEY` — ключ provod.ai
- `OPENAI_BASE_URL` — https://api.provod.ai/v1
- `GEMINI_MODEL` — gemini-3.5-flash
- `PEXELS_API_KEY` — ключ Pexels
- `PIXABAY_API_KEY` — ключ Pixabay
- `AGNES_API_KEY` — ключ Agnes AI
- `OUTPUT_BASE_DIR` — /tmp/project_output
