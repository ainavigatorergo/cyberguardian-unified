import aiohttp
import urllib.parse
from config import PROVOD_API_KEY, OPENROUTER_API_KEY, CHANNELS

PROVOD_URL = "https://api.provod.ai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Резервные бесплатные модели OpenRouter
OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-20b:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "z-ai/glm-4.5-air:free",
    "google/gemma-3-12b-it:free",
]


async def _call_api(url: str, api_key: str, model: str, prompt: str):
    """Универсальный вызов API (provod.ai или OpenRouter)."""
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8,
        }
        async with session.post(url, headers=headers, json=payload, timeout=120) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
            raise Exception(f"API error: {resp.status} - {await resp.text()}")


async def generate_post(topic: str, channel_key: str) -> str:
    """Генерирует пост для Telegram-канала."""
    profile = CHANNELS[channel_key]
    prompt = f"""
{profile['prompt_prefix']}

Стиль: {profile['style']}

Напиши пост для Telegram-канала на тему: {topic}

Требования:
- Длина: 800–1200 символов.
- Начни с цепляющего заголовка с эмодзи.
- 2–3 абзаца по делу.
- Дай 3 практических совета или шага.
- Заверши вопросом к читателям для вовлечения.
- Добавь 3–5 хештегов.
- Без воды, без кликбейта, без паники.
"""

    # Пробуем provod.ai
    try:
        return await _call_api(PROVOD_URL, PROVOD_API_KEY, "gemini-3.5-flash", prompt)
    except Exception as e:
        print(f"⚠️ Provod.ai не сработал: {e}. Пробуем OpenRouter...")

    # Пробуем OpenRouter по очереди
    if OPENROUTER_API_KEY:
        for model in OPENROUTER_MODELS:
            try:
                return await _call_api(OPENROUTER_URL, OPENROUTER_API_KEY, model, prompt)
            except Exception as e:
                print(f"⚠️ OpenRouter {model} не сработал: {e}")
                continue

    raise Exception("Все модели недоступны")


async def generate_image(prompt: str) -> str:
    """Генерирует картинку через Pollinations.ai (бесплатно, без ключей)."""
    clean_prompt = urllib.parse.quote(prompt[:200])
    url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width=1024&height=1024&nologo=true"
    return url
