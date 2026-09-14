import aiohttp
import urllib.parse
import json
import os
import random
from PIL import Image, ImageDraw, ImageFont
from config import (
    PROVOD_API_KEY, OPENROUTER_API_KEY, CHANNELS, DATA_DIR,
    RUBRICS, POLLINATIONS_API_KEY
)

PROVOD_URL = "https://api.provod.ai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# === Модели provod.ai (перебор по очереди) ===
PROVOD_MODELS = [
    "gemini-3.5-flash",        # основная
    "gemini-2.5-flash",        # резерв
    "gemini-flash-latest",     # авто-подтягивает свежую версию
]

# === Модели OpenRouter (бесплатные) ===
OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-20b:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "z-ai/glm-4.5-air:free",
    "google/gemma-3-12b-it:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
]

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

USED_TOPICS_FILE = os.path.join(DATA_DIR, "used_topics.json")


# ============================================================
# ХРАНЕНИЕ ИСПОЛЬЗОВАННЫХ ТЕМ
# ============================================================

def load_used_topics():
    if not os.path.exists(USED_TOPICS_FILE):
        return {"cyber": [], "ai": []}
    try:
        with open(USED_TOPICS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"cyber": [], "ai": []}


def save_used_topics(data):
    with open(USED_TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
# API-ЗАПРОСЫ
# ============================================================

async def _call_api(url, api_key, model, prompt, temperature=0.85):
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        async with session.post(url, headers=headers, json=payload, timeout=120) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
            error_text = await resp.text()
            raise Exception(f"API error: {resp.status} - {error_text[:150]}")


async def _smart_call(prompt, temperature=0.85):
    """Пробует provod.ai (все модели), потом OpenRouter."""
    for model in PROVOD_MODELS:
        try:
            result = await _call_api(PROVOD_URL, PROVOD_API_KEY, model, prompt, temperature)
            print(f"   ✅ Ответ от provod.ai ({model})")
            return result
        except Exception as e:
            print(f"   ⚠️ provod [{model}]: {str(e)[:100]}")
            continue

    print("⚠️ Все модели provod.ai не сработали, пробуем OpenRouter...")

    if OPENROUTER_API_KEY:
        for model in OPENROUTER_MODELS:
            try:
                result = await _call_api(OPENROUTER_URL, OPENROUTER_API_KEY, model, prompt, temperature)
                print(f"   ✅ Ответ от OpenRouter ({model})")
                return result
            except Exception as e:
                print(f"   ⚠️ OR [{model}]: {str(e)[:100]}")
                continue
    else:
        print("⚠️ OPENROUTER_API_KEY не задан!")

    raise Exception("Все модели недоступны")


# ============================================================
# ПРОВЕРКА УНИКАЛЬНОСТИ ТЕМ
# ============================================================

async def is_topic_unique(topic, channel_key):
    used = load_used_topics().get(channel_key, [])
    if not used:
        return True

    recent = used[-30:]
    used_str = "\n".join([f"- {t}" for t in recent])

    prompt = f"""
Ты — редактор. Проверь, похожа ли новая тема на уже использованные по СМЫСЛУ.

Новая тема: "{topic}"

Уже использованные темы:
{used_str}

Если новая тема СЕМАНТИЧЕСКИ похожа хотя бы на одну, ответь: ПОХОЖА
Если тема действительно новая — ответь: УНИКАЛЬНА

Отвечай только одним словом: ПОХОЖА или УНИКАЛЬНА.
"""
    try:
        result = await _smart_call(prompt, temperature=0.3)
        result = result.strip().upper()
        is_unique = "УНИКАЛЬНА" in result
        print(f"   🔍 Проверка '{topic}': {result}")
        return is_unique
    except Exception as e:
        print(f"   ⚠️ Ошибка проверки: {e}")
        return True


# ============================================================
# ГЕНЕРАЦИЯ ИДЕЙ
# ============================================================

async def generate_ideas(channel_key, count=5):
    profile = CHANNELS[channel_key]
    used = load_used_topics().get(channel_key, [])
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


# ============================================================
# ГЕНЕРАЦИЯ ПОСТА
# ============================================================

async def generate_post(topic, channel_key, rubric=None):
    profile = CHANNELS[channel_key]

    if channel_key == "cyber":
        extra = "Акцент на защиту и практические советы. Тон: спокойный, экспертный, без паники."
    else:
        extra = "Акцент на инструменты и кейсы. Тон: дружелюбный, практичный, с примерами."

    if rubric:
        rubric_block = f"""
=== РУБРИКА ДНЯ ===
Название: {rubric['name']}
Задача: {rubric['task']}
"""
    else:
        rubric_block = ""

    prompt = f"""
{profile['prompt_prefix']}
Стиль: {profile['style']}
Особенности канала: {extra}
{rubric_block}

Напиши пост для Telegram-канала на тему: {topic}

Требования (ВАЖНО):
- Длина поста: СТРОГО 700–900 символов (не больше!).
- Начни с цепляющего заголовка с эмодзи.
- 2 абзаца по делу.
- 3 практических совета или шага.
- Заверши коротким вопросом к читателям.
- Добавь 4 хештега.
- Без воды, без кликбейта.
"""
    return await _smart_call(prompt)


# ============================================================
# ГЕНЕРАЦИЯ ЛОНГРИДА
# ============================================================

async def generate_longread(topic, channel_key, rubric=None):
    profile = CHANNELS[channel_key]

    rubric_block = ""
    if rubric:
        rubric_block = f"Рубрика: {rubric['name']}. Задача: {rubric['task']}"

    prompt = f"""
{profile['prompt_prefix']}
Стиль: {profile['style']}

{rubric_block}

Напиши ГЛУБОКИЙ пост-лонгрид на тему: {topic}

Требования:
- Длина: 1800–2500 символов.
- Начни с цепляющего заголовка с эмодзи.
- Структура: вступление, 3–4 раздела с подзаголовками (через HTML <b>), вывод.
- Разбирай тему подробно, с примерами и цифрами.
- 5–7 практических советов.
- Заверши вопросом к читателям.
- Добавь 4 хештега.
"""
    return await _smart_call(prompt, temperature=0.8)


# ============================================================
# ГЕНЕРАЦИЯ ОПРОСА
# ============================================================

async def generate_poll(topic, channel_key):
    profile = CHANNELS[channel_key]

    prompt = f"""
Ты — контент-мейкер канала «{profile['name']}» ({profile['prompt_prefix']}).

Придумай Telegram-опрос по теме: {topic}

Формат ответа (СТРОГО):
ВОПРОС: [вопрос до 100 символов]
ВАРИАНТ: [вариант 1]
ВАРИАНТ: [вариант 2]
ВАРИАНТ: [вариант 3]

Правила:
- Вопрос вовлекающий.
- 3 варианта, каждый до 30 символов.
- Без правильного ответа.
"""
    response = await _smart_call(prompt, temperature=0.9)

    lines = response.split("\n")
    question = ""
    options = []
    for line in lines:
        line = line.strip()
        if line.startswith("ВОПРОС:"):
            question = line.replace("ВОПРОС:", "").strip()
        elif line.startswith("ВАРИАНТ:"):
            opt = line.replace("ВАРИАНТ:", "").strip()
            if opt:
                options.append(opt)

    if not question or len(options) < 2:
        question = f"Что для вас важнее в теме «{topic}»?"
        options = ["Практика", "Теория", "Инструменты"]

    return {"question": question, "options": options[:4]}


# ============================================================
# БРЕНДИНГ КАРТИНОК
# ============================================================

def _add_branding(image_path, channel_key="cyber"):
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
        return True
    except Exception as e:
        print(f"   ⚠️ Ошибка плашки: {e}")
        return False


# ============================================================
# ГЕНЕРАЦИЯ КАРТИНКИ
# ============================================================

async def generate_image(topic, channel_key="cyber"):
    style = IMAGE_STYLES.get(channel_key, IMAGE_STYLES["cyber"])
    subject = random.choice(style["subjects"])
    composition = random.choice(style["compositions"])
    mood = random.choice(style["moods"])

    image_prompt = (
        f"{style['base'].format(topic=topic)}. "
        f"Subject: {subject}. Composition: {composition}. Mood: {mood}."
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
