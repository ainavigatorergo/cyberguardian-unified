import aiohttp
import urllib.parse
import json
import os
from config import PROVOD_API_KEY, OPENROUTER_API_KEY, CHANNELS, DATA_DIR

PROVOD_URL = "https://api.provod.ai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-20b:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "z-ai/glm-4.5-air:free",
    "google/gemma-3-12b-it:free",
]

# === Промпты для картинок ===
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


def _load_used_topics(channel_key):
    """Загружает список использованных тем."""
    path = os.path.join(DATA_DIR, "used_topics.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(channel_key, [])
    except:
        return []


async def _call_api(url: str, api_key: str, model: str, prompt: str):
    """Универсальный вызов API."""
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.85,
        }
        async with session.post(url, headers=headers, json=payload, timeout=120) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
            raise Exception(f"API error: {resp.status}")


async def _smart_call(prompt: str):
    """Пробует provod.ai, потом OpenRouter."""
    try:
        return await _call_api(PROVOD_URL, PROVOD_API_KEY, "gemini-3.5-flash", prompt)
    except Exception as e:
        print(f"⚠️ Provod.ai: {e}, пробуем OpenRouter...")

    if OPENROUTER_API_KEY:
        for model in OPENROUTER_MODELS:
            try:
                return await _call_api(OPENROUTER_URL, OPENROUTER_API_KEY, model, prompt)
            except Exception as e:
                print(f"⚠️ {model}: {e}")
                continue

    raise Exception("Все модели недоступны")


async def generate_ideas(channel_key: str, count: int = 5) -> list:
    """
    Генерирует свежие идеи для постов через AI.
    Учитывает использованные темы, чтобы не повторяться.
    """
    profile = CHANNELS[channel_key]
    used = _load_used_topics(channel_key)
    used_str = ", ".join(used[-20:]) if used else "пока ничего"

    if channel_key == "cyber":
        context = (
            "Ниша: кибербезопасность. Актуальные тренды 2026: новые схемы фишинга, "
            "утечки данных, ИИ-мошенничество, защита аккаунтов, VPN, пароли, "
            "социальная инженерия, взломы через мессенджеры."
        )
    else:
        context = (
            "Ниша: нейросети и автоматизация для бизнеса. Актуальные тренды 2026: "
            "ChatGPT, Midjourney, AI-агенты, автоматизация рутины, промпты, "
            "нейросети для маркетинга, контента, продаж."
        )

    prompt = f"""
Ты — контент-стратег для Telegram-канала «{profile['name']}».

{context}

Уже использованные темы (НЕ повторяйся): {used_str}

Придумай {count} свежих, цепляющих тем для постов.
Требования:
- Каждая тема — 4–8 слов.
- Актуально, полезно, вовлекает.
- Без кликбейта и паники.
- Разные подтемы (не одно и то же).

Формат ответа: только список тем, каждая с новой строки, без нумерации, без пояснений.
"""

    response = await _smart_call(prompt)
    # Разбиваем на строки и очищаем
    ideas = [line.strip(" -•*0123456789.") for line in response.split("\n") if line.strip()]
    ideas = [i for i in ideas if 4 < len(i) < 80][:count]
    return ideas


async def generate_post(topic: str, channel_key: str) -> str:
    """Генерирует пост для Telegram-канала."""
    profile = CHANNELS[channel_key]

    if channel_key == "cyber":
        extra = (
            "Акцент на защиту, угрозы, практические советы. "
            "Примеры: фишинг, утечки, взломы, VPN, пароли. "
            "Тон: спокойный, экспертный, без паники."
        )
    else:
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
- Заверши вопросом к читателям.
- Добавь 3–5 хештегов.
- Без воды, без кликбейта, без паники.
"""

    return await _smart_call(prompt)


async def generate_image(topic: str, channel_key: str = "cyber") -> str:
    """Генерирует тематическую картинку через Pollinations.ai."""
    style_template = IMAGE_STYLES.get(channel_key, IMAGE_STYLES["cyber"])
    image_prompt = style_template.format(topic=topic)

    clean_prompt = urllib.parse.quote(image_prompt[:400])
    url = (
        f"https://image.pollinations.ai/prompt/{clean_prompt}"
        f"?width=1024&height=1024&nologo=true&model=flux"
    )
    return url
