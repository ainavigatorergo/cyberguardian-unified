import aiohttp
import urllib.parse
import json
import os
from PIL import Image, ImageDraw, ImageFont
from config import PROVOD_API_KEY, OPENROUTER_API_KEY, CHANNELS, DATA_DIR

POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "sk_IO2JusirCuHRbVzBfZ6EEoDUkcjyRqU6")

PROVOD_URL = "https://api.provod.ai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-20b:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "z-ai/glm-4.5-air:free",
    "google/gemma-3-12b-it:free",
]

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

IMAGES_DIR = os.path.join(DATA_DIR, "images")
os.makedirs(IMAGES_DIR, exist_ok=True)


def _load_used_topics(channel_key):
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
    profile = CHANNELS[channel_key]
    used = _load_used_topics(channel_key)
    used_str = ", ".join(used[-20:]) if used else "пока ничего"

    if channel_key == "cyber":
        context = (
            "Ниша: кибербезопасность. Тренды 2026: новые схемы фишинга, "
            "утечки данных, ИИ-мошенничество, защита аккаунтов, VPN, пароли."
        )
    else:
        context = (
            "Ниша: нейросети для бизнеса. Тренды 2026: ChatGPT, Midjourney, "
            "AI-агенты, автоматизация, промпты, нейросети для маркетинга."
        )

    prompt = f"""
Ты — контент-стратег для Telegram-канала «{profile['name']}».
{context}
Уже использованные темы (НЕ повторяйся): {used_str}

Придумай {count} свежих тем для постов (4–8 слов каждая).
Формат: только список, каждая с новой строки, без нумерации.
"""
    response = await _smart_call(prompt)
    ideas = [line.strip(" -•*0123456789.") for line in response.split("\n") if line.strip()]
    ideas = [i for i in ideas if 4 < len(i) < 80][:count]
    return ideas


async def generate_post(topic: str, channel_key: str) -> str:
    profile = CHANNELS[channel_key]

    if channel_key == "cyber":
        extra = "Акцент на защиту и практические советы. Тон: спокойный, экспертный, без паники."
    else:
        extra = "Акцент на инструменты и кейсы. Тон: дружелюбный, практичный, с примерами."

    prompt = f"""
{profile['prompt_prefix']}
Стиль: {profile['style']}
Особенности канала: {extra}

Напиши пост для Telegram-канала на тему: {topic}

Требования (ВАЖНО):
- Длина поста: СТРОГО 700–900 символов (не больше!).
- Начни с цепляющего заголовка с эмодзи.
- 2 абзаца по делу.
- 3 практических совета (коротко).
- Заверши коротким вопросом к читателям.
- Добавь 4 хештега.
- Без воды, без кликбейта.

Пост должен быть компактным, но полезным.
"""
    return await _smart_call(prompt)


def _add_branding(image_path: str, channel_key: str = "cyber"):
    """
    Добавляет брендированную плашку с названием канала в правом нижнем углу,
    полностью перекрывая логотип Pollinations.ai.
    """
    try:
        img = Image.open(image_path).convert("RGB")
        w, h = img.size
        draw = ImageDraw.Draw(img)

        # Настройки под каждый канал
        if channel_key == "cyber":
            text = "CyberGuardianSec"
            bg_color = (10, 20, 50)        # тёмно-синий
            border_color = (0, 255, 150)   # неоново-зелёный
            text_color = (255, 255, 255)
        else:
            text = "AI Navigator"
            bg_color = (40, 10, 60)        # тёмно-фиолетовый
            border_color = (0, 255, 130)
            text_color = (255, 255, 255)

        # Размеры плашки (расширены, чтобы точно перекрыть логотип)
        pad_x = int(w * 0.01)          # уменьшен отступ справа
        pad_y = int(h * 0.012)
        logo_w = int(w * 0.38)         # шире, чтобы захватить логотип
        logo_h = int(h * 0.065)
        x1 = w - logo_w - pad_x
        y1 = h - logo_h - pad_y
        x2 = w - pad_x
        y2 = h - pad_y

        # Фон плашки с рамкой
        draw.rectangle([x1, y1, x2, y2], fill=bg_color, outline=border_color, width=2)

        # Шрифт
        font_size = int(logo_h * 0.55)
        font = None
        for font_name in ["arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"]:
            try:
                font = ImageFont.truetype(font_name, font_size)
                break
            except:
                continue
        if font is None:
            font = ImageFont.load_default()

        # Центрируем текст
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except:
            tw, th = len(text) * font_size // 2, font_size

        tx = x1 + (logo_w - tw) // 2
        ty = y1 + (logo_h - th) // 2 - int(logo_h * 0.1)

        draw.text((tx, ty), text, font=font, fill=text_color)

        img.save(image_path, "PNG")
        print(f"   🏷️ Добавлена плашка: {text}")
        return True
    except Exception as e:
        print(f"   ⚠️ Не удалось добавить плашку: {e}")
        return False


async def generate_image(topic: str, channel_key: str = "cyber") -> str:
    """Генерирует картинку, скачивает, добавляет брендинг. Возвращает путь к файлу."""
    style_template = IMAGE_STYLES.get(channel_key, IMAGE_STYLES["cyber"])
    image_prompt = style_template.format(topic=topic)

    clean_prompt = urllib.parse.quote(image_prompt[:400])
    url = (
        f"https://image.pollinations.ai/prompt/{clean_prompt}"
        f"?width=1024&height=1024&nologo=true&model=flux"
    )
    if POLLINATIONS_API_KEY:
        url += f"&key={POLLINATIONS_API_KEY}"

    filename = f"{channel_key}_{abs(hash(topic)) % 100000}.png"
    filepath = os.path.join(IMAGES_DIR, filename)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=120) as resp:
                if resp.status != 200:
                    print(f"⚠️ Pollinations вернул {resp.status}")
                    return url
                content = await resp.read()
                with open(filepath, "wb") as f:
                    f.write(content)
        _add_branding(filepath, channel_key)
        return filepath
    except Exception as e:
        print(f"⚠️ Ошибка скачивания картинки: {e}")
        return url
