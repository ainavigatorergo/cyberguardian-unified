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

# === Промпты для картинок под каждый канал ===
IMAGE_STYLES = {
    "cyber": (
        "Cybersecurity concept illustration, {topic}, "
        "dark navy blue and neon green colors, digital shield, padlock, "
        "circuit board elements, futuristic tech style, "
        "no text, no people, no faces, cinematic lighting, high quality"
    ),
    "ai": (
        "Artificial intelligence concept illustration, {topic}, "
        "dark purple and neon green colors, glowing neural network, "
        "robot brain, digital particles, futuristic tech style, "
        "no text, no people, no faces, cinematic lighting, high quality"
    ),
}


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
    """Генерирует пост для Telegram-канала (свой стиль для каждого)."""
    profile = CHANNELS[channel_key]

    # Дополнительные требования под каждый канал
    if channel_key == "cyber":
        extra = (
            "Акцент на защиту, угрозы, практические советы. "
            "Примеры: фишинг, утечки, взломы, VPN, пароли. "
            "Тон: спокойный, экспертный, без паники."
        )
    else:  # ai
        extra = (
            "Акцент на инструменты, кейсы, автоматизацию. "
            "Примеры: ChatGPT, Midjourney, промпты, нейросети для бизнеса. "
            "Тон: дружелюбный, практичный, с примерами."
        )

    prompt = f"""
{profile['prompt_prefix']}

Стиль: {profile['style']}

Особенности канала: {extra}

Напиши пост для Telegram-канала на тему: {topic}

Требования:
- Длина: 800–1200 символов.
- Начни с цепляющего заголовка с эмодзи.
- 2–3 абзаца по делу.
- Дай 3 практических совета или шага.
- Заверши вопросом к читателям для вовлечения.
- Добавь 3–5 хештегов, соответствующих каналу.
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


async def generate_image(topic: str, channel_key: str = "cyber") -> str:
    """
    Генерирует тематическую картинку через Pollinations.ai.
    Стиль зависит от канала: cyber или ai.
    """
    style_template = IMAGE_STYLES.get(channel_key, IMAGE_STYLES["cyber"])
    image_prompt = style_template.format(topic=topic)

    clean_prompt = urllib.parse.quote(image_prompt[:400])
    url = (
        f"https://image.pollinations.ai/prompt/{clean_prompt}"
        f"?width=1024&height=1024&nologo=true&model=flux"
    )
    return url
