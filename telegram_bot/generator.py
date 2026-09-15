import aiohttp
import urllib.parse
import json
import os
import random
import re
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from config import (
    PROVOD_API_KEY, OPENROUTER_API_KEY, CHANNELS, DATA_DIR,
    RUBRICS, POLLINATIONS_API_KEY
)

PROVOD_URL = "https://api.provod.ai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

PROVOD_MODELS = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-flash-latest"]
OPENROUTER_MODELS = ["meta-llama/llama-3.3-70b-instruct:free", "google/gemma-3-12b-it:free"]

IMAGES_DIR = os.path.join(DATA_DIR, "images")
os.makedirs(IMAGES_DIR, exist_ok=True)
USED_TOPICS_FILE = os.path.join(DATA_DIR, "used_topics.json")


# ============================================================
# ХРАНЕНИЕ ТЕМ
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
# API
# ============================================================

async def _call_api(url, api_key, model, prompt, temperature=0.85):
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": temperature}
        async with session.post(url, headers=headers, json=payload, timeout=120) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
            raise Exception(f"API error: {resp.status}")


async def _smart_call(prompt, temperature=0.85):
    for model in PROVOD_MODELS:
        try:
            return await _call_api(PROVOD_URL, PROVOD_API_KEY, model, prompt, temperature)
        except Exception as e:
            print(f"   ⚠️ provod [{model}]: {str(e)[:80]}")
    if OPENROUTER_API_KEY:
        for model in OPENROUTER_MODELS:
            try:
                return await _call_api(OPENROUTER_URL, OPENROUTER_API_KEY, model, prompt, temperature)
            except Exception as e:
                print(f"   ⚠️ OR [{model}]: {str(e)[:80]}")
    raise Exception("Все модели недоступны")


# ============================================================
# ПАРСИНГ СТРУКТУРЫ
# ============================================================

def parse_post_structure(text):
    result = {"title": "", "intro": "", "bullets": [], "question": "", "hashtags": ""}
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        u = line.upper()
        if u.startswith("ЗАГОЛОВОК"):
            result["title"] = line.split(":", 1)[1].strip() if ":" in line else ""
        elif u.startswith("ВСТУПЛЕНИЕ"):
            result["intro"] = line.split(":", 1)[1].strip() if ":" in line else ""
        elif u.startswith("ПУНКТ"):
            if ":" in line:
                result["bullets"].append(line.split(":", 1)[1].strip())
        elif u.startswith("ВОПРОС"):
            result["question"] = line.split(":", 1)[1].strip() if ":" in line else ""
        elif u.startswith("ХЕШТЕГ"):
            result["hashtags"] = line.split(":", 1)[1].strip() if ":" in line else ""
    return result


def build_post_text(p):
    parts = []
    if p["title"]: parts.append(p["title"])
    if p["intro"]: parts.append(p["intro"])
    if p["bullets"]:
        parts.append("\n".join([f"{i}. {b}" for i, b in enumerate(p["bullets"][:3], 1)]))
    if p["question"]: parts.append(p["question"])
    if p["hashtags"]: parts.append(p["hashtags"])
    return "\n\n".join(parts)


# ============================================================
# УНИКАЛЬНОСТЬ ТЕМ
# ============================================================

async def is_topic_unique(topic, channel_key):
    used = load_used_topics().get(channel_key, [])
    if not used:
        return True
    recent = used[-30:]
    used_str = "\n".join([f"- {t}" for t in recent])
    prompt = f"""Ты — редактор. Похожа ли новая тема на уже использованные по СМЫСЛУ?
Новая тема: "{topic}"
Уже использованные:
{used_str}
Ответь одним словом: ПОХОЖА или УНИКАЛЬНА."""
    try:
        result = await _smart_call(prompt, temperature=0.3)
        return "УНИКАЛЬНА" in result.upper()
    except:
        return True


# ============================================================
# ГЕНЕРАЦИЯ ИДЕЙ
# ============================================================

async def generate_ideas(channel_key, count=5):
    profile = CHANNELS[channel_key]
    used = load_used_topics().get(channel_key, [])
    used_str = ", ".join(used[-20:]) if used else "пока ничего"
    context = (
        "Ниша: кибербезопасность." if channel_key == "cyber"
        else "Ниша: нейросети для бизнеса."
    )
    prompt = f"""Ты — контент-стратег канала «{profile['name']}».
{context}
Уже использовано: {used_str}
Придумай {count} свежих тем (4–8 слов).
Формат: только список, каждая с новой строки."""
    response = await _smart_call(prompt)
    ideas = [line.strip(" -•*0123456789.") for line in response.split("\n") if line.strip()]
    return [i for i in ideas if 4 < len(i) < 80][:count]


# ============================================================
# ГЕНЕРАЦИЯ ПОСТА
# ============================================================

async def generate_post(topic, channel_key, rubric=None):
    profile = CHANNELS[channel_key]
    extra = ("Тон: спокойный, экспертный, без паники."
             if channel_key == "cyber"
             else "Тон: дружелюбный, практичный, с примерами.")
    rubric_block = f"Рубрика: {rubric['name']}. Задача: {rubric['task']}" if rubric else ""

    prompt = f"""{profile['prompt_prefix']}
Стиль: {profile['style']}
Особенности: {extra}
{rubric_block}

Напиши пост на тему: {topic}

ФОРМАТ ОТВЕТА СТРОГО:
ЗАГОЛОВОК: [цепляющий заголовок БЕЗ эмодзи, до 55 символов]
ВСТУПЛЕНИЕ: [1–2 предложения, до 180 символов]
ПУНКТ 1: [совет БЕЗ эмодзи, до 55 символов]
ПУНКТ 2: [совет БЕЗ эмодзи, до 55 символов]
ПУНКТ 3: [совет БЕЗ эмодзи, до 55 символов]
ВОПРОС: [вопрос к читателям, до 70 символов]
ХЕШТЕГИ: [4 хештега через пробел]"""

    raw = await _smart_call(prompt)
    parsed = parse_post_structure(raw)

    if not parsed["title"] or len(parsed["bullets"]) < 2:
        print("   ⚠️ AI вернул неструктурированный текст")
        return raw, {"title": topic, "bullets": [], "intro": "", "question": "", "hashtags": ""}

    return build_post_text(parsed), parsed


async def generate_longread(topic, channel_key, rubric=None):
    profile = CHANNELS[channel_key]
    rubric_block = f"Рубрика: {rubric['name']}. Задача: {rubric['task']}" if rubric else ""
    prompt = f"""{profile['prompt_prefix']}
Стиль: {profile['style']}
{rubric_block}
Напиши ГЛУБОКИЙ лонгрид на тему: {topic}
Требования:
- 1800–2500 символов.
- Вступление, 3–4 раздела с <b>подзаголовками</b>, вывод.
- 5–7 советов.
- Вопрос к читателям.
- 4 хештега."""
    return await _smart_call(prompt, temperature=0.8)


async def generate_poll(topic, channel_key):
    profile = CHANNELS[channel_key]
    prompt = f"""Канал «{profile['name']}». Придумай Telegram-опрос по теме: {topic}
ФОРМАТ СТРОГО:
ВОПРОС: [до 100 символов]
ВАРИАНТ: [вариант 1]
ВАРИАНТ: [вариант 2]
ВАРИАНТ: [вариант 3]"""
    response = await _smart_call(prompt, temperature=0.9)
    q, opts = "", []
    for line in response.split("\n"):
        line = line.strip()
        if line.startswith("ВОПРОС:"):
            q = line.replace("ВОПРОС:", "").strip()
        elif line.startswith("ВАРИАНТ:"):
            o = line.replace("ВАРИАНТ:", "").strip()
            if o: opts.append(o)
    if not q or len(opts) < 2:
        q = f"Что для вас важнее в теме «{topic}»?"
        opts = ["Практика", "Теория", "Инструменты"]
    return {"question": q, "options": opts[:4]}


# ============================================================
# ВИЗУАЛ: AI-фон + текстовая плашка
# ============================================================

def _find_font(size, bold=False):
    names = [
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
        "Arial Bold.ttf" if bold else "Arial.ttf",
        "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf",
    ]
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except:
            continue
    return ImageFont.load_default()


def _wrap_text(text, font, max_width, draw):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = current + " " + word if current else word
        try:
            bbox = draw.textbbox((0, 0), test, font=font)
            w = bbox[2] - bbox[0]
        except:
            w = len(test) * 20
        if w <= max_width:
            current = test
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    return lines


def _remove_emoji(text):
    """Убирает эмодзи и проблемные символы."""
    return re.sub(r'[^\w\s\d\.,!?\-:;()«»"\']', '', text).strip()


async def _get_ai_background(topic, channel_key):
    """Скачивает атмосферный AI-фон (без текста, без людей)."""
    topic_clean = _remove_emoji(topic)[:80]

    if channel_key == "cyber":
        style = (
            f"abstract cybersecurity background about {topic_clean}, "
            "dark navy blue and neon green, digital network, circuit patterns, "
            "no text, no people, no faces, no logos, cinematic, high quality"
        )
    else:
        style = (
            f"abstract AI technology background about {topic_clean}, "
            "dark purple and neon green, neural network, glowing particles, "
            "no text, no people, no faces, no logos, cinematic, high quality"
        )

    clean = urllib.parse.quote(style[:400])
    seed = random.randint(1, 999999)
    url = (
        f"https://image.pollinations.ai/prompt/{clean}"
        f"?width=1080&height=1080&nologo=true&model=flux&seed={seed}"
    )
    if POLLINATIONS_API_KEY:
        url += f"&key={POLLINATIONS_API_KEY}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=120) as resp:
                if resp.status != 200:
                    return None
                content = await resp.read()
                return Image.open(BytesIO(content)).convert("RGB")
    except Exception as e:
        print(f"   ⚠️ Ошибка загрузки фона: {e}")
        return None


def _overlay_text_on_bg(bg_img, parsed, channel_key):
    """Накладывает текст поверх AI-фона."""
    W, H = 1080, 1080
    bg = bg_img.resize((W, H)).convert("RGB")

    # Затемняющие плашки
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    # Верхняя плашка (заголовок)
    ov_draw.rectangle([0, 0, W, 420], fill=(0, 0, 0, 170))
    # Нижняя плашка (пункты + бренд)
    ov_draw.rectangle([0, H - 560, W, H], fill=(0, 0, 0, 190))
    # Плашка под бренд (правый нижний угол — перекрывает pollinations.ai)
    ov_draw.rectangle([W - 500, H - 90, W, H], fill=(0, 0, 0, 240))

    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(bg)

    if channel_key == "cyber":
        accent = (0, 255, 150)
        brand = "CyberGuardianSec"
    else:
        accent = (0, 255, 130)
        brand = "AI Navigator"

    font_title = _find_font(60, bold=True)
    font_bullet = _find_font(36)
    font_num = _find_font(30, bold=True)
    font_brand = _find_font(32, bold=True)

    pad = 60

    # === ЗАГОЛОВОК (без эмодзи) ===
    title = _remove_emoji(parsed.get("title", "Без заголовка"))
    if not title:
        title = "Без заголовка"

    y = 80
    for line in _wrap_text(title, font_title, W - 2 * pad, draw)[:3]:
        draw.text((pad, y), line, font=font_title, fill=(0, 0, 0),
                  stroke_width=5, stroke_fill=(0, 0, 0))
        draw.text((pad, y), line, font=font_title, fill=(255, 255, 255))
        y += 74

    # === ПУНКТЫ ===
    bullets = parsed.get("bullets", [])[:3]
    if not bullets:
        bullets = ["Подробности в посте", "Читай ниже", "Подпишись на канал"]

    y = H - 520
    for i, bullet in enumerate(bullets, 1):
        bullet_clean = _remove_emoji(bullet)
        if not bullet_clean:
            bullet_clean = "..."

        # Кружок с цифрой
        cx, cy = pad + 26, y + 26
        draw.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=accent)
        num = str(i)
        try:
            bbox = draw.textbbox((0, 0), num, font=font_num)
            nw, nh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except:
            nw, nh = 12, 20
        draw.text((cx - nw // 2, cy - nh // 2 - 5), num, font=font_num, fill=(0, 0, 0))

        # Текст пункта
        for line in _wrap_text(bullet_clean, font_bullet, W - 2 * pad - 80, draw)[:2]:
            draw.text((pad + 80, y), line, font=font_bullet, fill=(0, 0, 0),
                      stroke_width=3, stroke_fill=(0, 0, 0))
            draw.text((pad + 80, y), line, font=font_bullet, fill=(240, 240, 240))
            y += 50
        y += 14

    # === БРЕНД (с тёмной подложкой) ===
    draw.text((W - 440, H - 65), brand, font=font_brand, fill=accent)

    return bg


async def generate_image(parsed, channel_key="cyber"):
    """AI-фон + наложение текста."""
    try:
        print(f"   🎨 Скачиваю AI-фон...")
        bg = await _get_ai_background(parsed.get("title", ""), channel_key)

        if bg:
            print(f"   ✏️ Накладываю текст...")
            card = _overlay_text_on_bg(bg, parsed, channel_key)
        else:
            print(f"   ⚠️ Фон не загрузился, использую градиент")
            if channel_key == "cyber":
                bg = Image.new("RGB", (1080, 1080), (10, 20, 50))
            else:
                bg = Image.new("RGB", (1080, 1080), (40, 10, 60))
            card = _overlay_text_on_bg(bg, parsed, channel_key)

        filename = f"{channel_key}_card_{abs(hash(parsed.get('title', '') + str(random.randint(1,99999)))) % 100000}.png"
        filepath = os.path.join(IMAGES_DIR, filename)
        card.save(filepath, "PNG")
        print(f"   ✅ Готово: {filename}")
        return filepath
    except Exception as e:
        print(f"   ⚠️ Ошибка визуала: {e}")
        return ""
