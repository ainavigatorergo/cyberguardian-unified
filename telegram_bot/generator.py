import aiohttp
import urllib.parse
import json
import os
import random
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

# === Рандомизированные стили картинок ===
IMAGE_STYLES = {
    "cyber": {
        "base": (
            "Cybersecurity concept illustration about {topic}, "
            "dark navy blue background with neon green accents, "
            "futuristic tech style, no text, no people, no faces, "
            "cinematic lighting, high quality"
        ),
        "subjects": [
            "digital shield with glowing circuit patterns",
            "padlock made of binary code and light particles",
            "matrix of falling green code forming a wall",
            "cyber eye scanning a network of connected nodes",
            "glowing key unlocking a firewall barrier",
            "hand made of circuit lines protecting a server",
            "data stream blocked by a holographic barrier",
            "encrypted tunnel with neon green walls",
            "surveillance camera in a digital grid",
            "broken chain link representing hacked password",
        ],
        "compositions": [
            "close-up view", "wide cinematic shot", "centered composition",
            "dramatic angle", "minimalist composition", "detailed macro shot",
            "isometric view", "top-down perspective", "symmetrical composition",
        ],
        "moods": [
            "tense and mysterious", "calm and protective",
            "futuristic and cold", "warm and reassuring",
            "dark and cinematic", "energetic and dynamic",
        ],
    },
    "ai": {
        "base": (
            "Artificial intelligence concept illustration about {topic}, "
            "dark purple and blue background with neon green accents, "
            "futuristic tech style, no text, no people, no faces, "
            "cinematic lighting, high quality"
        ),
        "subjects": [
            "glowing neural network with pulsing nodes",
            "robot head with illuminated circuits",
            "digital brain made of light particles",
            "abstract AI core with orbiting data streams",
            "holographic cube with interconnected nodes",
            "futuristic server room with glowing blue lights",
            "handshake between human hand and robotic hand made of light",
            "fractal pattern of AI algorithms unfolding",
            "spiral of glowing data representing machine learning",
            "floating geometric shapes forming an AI symbol",
        ],
        "compositions": [
            "close-up view", "wide cinematic shot", "centered composition",
            "dramatic angle", "minimalist composition", "detailed macro shot",
            "isometric view", "top-down perspective", "symmetrical composition",
        ],
        "moods": [
            "futuristic and inspiring", "calm and thoughtful",
            "energetic and bright", "mysterious and deep",
            "clean and professional", "curious and exploratory",
        ],
    },
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
    """Добавляет брендированную плашку с названием канала в правом нижнем углу."""
    try:
        img = Image.open(image_path).convert("RGB")
        w, h = img.size
        draw = ImageDraw.Draw(img)

        if channel_key == "cyber":
            text = "CyberGuardianSec"
            bg_color = (10, 20, 50)
            border_color = (0, 255, 150)
            text_color = (255, 255, 255)
        else:
            text = "AI Navigator"
            bg_color = (40, 10, 60)
            border_color = (0, 255, 130)
            text_color = (255, 255, 255)

        pad_x = int(w * 0.01)
        pad_y = int(h * 0.012)
        logo_w = int(w * 0.38)
        logo_h = int(h * 0.065)
        x1 = w - logo_w - pad_x
        y1 = h - logo_h - pad_y
        x2 = w - pad_x
        y2 = h - pad_y

        draw.rectangle([x1, y1, x2, y2], fill=bg_color, outline=border_color, width=2)

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
        print(f"   🏷️ Плашка: {text}")
        return True
    except Exception as e:
        print(f"   ⚠️ Ошибка плашки: {e}")
        return False


async def generate_image(topic: str, channel_key: str = "cyber") -> str:
    """Генерирует УНИКАЛЬНУЮ картинку с рандомизацией стиля."""
    style = IMAGE_STYLES.get(channel_key, IMAGE_STYLES["cyber"])

    subject = random.choice(style["subjects"])
    composition = random.choice(style["compositions"])
    mood = random.choice(style["moods"])

    image_prompt = (
        f"{style['base'].format(topic=topic)}. "
        f"Subject: {subject}. "
        f"Composition: {composition}. "
        f"Mood: {mood}."
    )

    clean_prompt = urllib.parse.quote(image_prompt[:500])
    seed = random.randint(1, 999999)
    url = (
        f"https://image.pollinations.ai/prompt/{clean_prompt}"
        f"?width=1024&height=1024&nologo=true&model=flux&seed={seed}"
    )
    if POLLINATIONS_API_KEY:
        url += f"&key={POLLINATIONS_API_KEY}"

    filename = f"{channel_key}_{abs(hash(topic + str(seed))) % 100000}.png"
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
        print(f"   🎨 {composition}, {mood}")
        return filepath
    except Exception as e:
        print(f"⚠️ Ошибка картинки: {e}")
        return url
