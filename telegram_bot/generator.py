import aiohttp
import urllib.parse
import json
import os
import base64
import random
import re
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from config import (
    PROVOD_API_KEY, OPENROUTER_API_KEY, CHANNELS, DATA_DIR,
    POLLINATIONS_API_KEY, PEXELS_API_KEY,
    PROVOD_IMAGE_MODEL, PROVOD_IMAGE_URL,
    BRAND_HASHTAGS, RUBRIC_HASHTAGS, GENERAL_HASHTAGS, TOPIC_HASHTAG_POOL,
    PALETTES, RUBRIC_ACCENTS, POST_TEMPLATES, CARD_TEMPLATES,
    POST_HOOKS, POST_CLOSINGS,
)

PROVOD_URL = "https://api.provod.ai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
PEXELS_URL = "https://api.pexels.com/v1/search"

PROVOD_MODELS = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-flash-latest"]
OPENROUTER_MODELS = ["meta-llama/llama-3.3-70b-instruct:free", "google/gemma-3-12b-it:free"]

IMAGES_DIR = os.path.join(DATA_DIR, "images")
os.makedirs(IMAGES_DIR, exist_ok=True)
USED_TOPICS_FILE = os.path.join(DATA_DIR, "used_topics.json")

SAFE_ZONE = 110
TEXT_BOTTOM_LIMIT = 160


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
            print(f"   ⚠️ provod [{model}]: {str(e)[:80]}", flush=True)
    if OPENROUTER_API_KEY:
        for model in OPENROUTER_MODELS:
            try:
                return await _call_api(OPENROUTER_URL, OPENROUTER_API_KEY, model, prompt, temperature)
            except Exception as e:
                print(f"   ⚠️ OR [{model}]: {str(e)[:80]}", flush=True)
    raise Exception("Все модели недоступны")


def _clean_label(line: str) -> str:
    """Убирает **, ##, ###, __, бэктики, лишние пробелы из строки."""
    line = line.strip()
    line = re.sub(r'^[\*#_`\s]+', '', line)
    line = re.sub(r'[\*#_`\s]+$', '', line)
    return line.strip()


def parse_post_structure(text):
    result = {"title": "", "intro": "", "details": "", "bonus": "",
              "bullets": [], "question": "", "hashtags": "", "numbers": [],
              "_parse_failed": False}

    en_ru_map = {
        "TITLE": "ЗАГОЛОВОК",
        "INTRO": "ВСТУПЛЕНИЕ",
        "INTRODUCTION": "ВСТУПЛЕНИЕ",
        "DETAILS": "ПОДРОБНЕЕ",
        "DETAIL": "ПОДРОБНЕЕ",
        "BREAKDOWN": "РАЗБОР",
        "BONUS": "БОНУС",
        "POINT 1": "ПУНКТ 1",
        "POINT 2": "ПУНКТ 2",
        "POINT 3": "ПУНКТ 3",
        "POINT1": "ПУНКТ 1",
        "POINT2": "ПУНКТ 2",
        "POINT3": "ПУНКТ 3",
        "TIP 1": "СОВЕТ 1",
        "TIP 2": "СОВЕТ 2",
        "TIP 3": "СОВЕТ 3",
        "TIP1": "СОВЕТ 1",
        "TIP2": "СОВЕТ 2",
        "TIP3": "СОВЕТ 3",
        "QUESTION": "ВОПРОС",
        "HASHTAGS": "ХЕШТЕГИ",
        "TAGS": "ХЕШТЕГИ",
    }

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        clean = _clean_label(line)
        if not clean:
            continue
        u = clean.upper()

        # Заменяем английские метки
        for en, ru in en_ru_map.items():
            if u.startswith(en + ":") or u.startswith(en + " :") or u.startswith(en + "."):
                rest = clean[len(en):].lstrip(": .").strip()
                clean = f"{ru}: {rest}"
                u = clean.upper()
                break

        if ":" in clean:
            parts = clean.split(":", 1)
            label = parts[0].upper().strip()
            value = parts[1].strip()
        else:
            label = u
            value = ""

        if label.startswith("ЗАГОЛОВОК"):
            result["title"] = value
        elif label.startswith("ВСТУПЛЕНИЕ"):
            result["intro"] = value
        elif label.startswith("ПОДРОБНЕЕ") or label.startswith("РАЗБОР"):
            result["details"] = value
        elif label.startswith("БОНУС"):
            result["bonus"] = value
        elif (label.startswith("ПУНКТ") or label.startswith("СОВЕТ")
              or label.startswith("POINT") or label.startswith("TIP")):
            if value:
                bullet = re.sub(r'^\d+[\.\)]\s*', '', value)
                bullet = re.sub(r'^[-•—]\s*', '', bullet)
                if bullet:
                    result["bullets"].append(bullet)
        elif label.startswith("ВОПРОС"):
            result["question"] = value
        elif label.startswith("ХЕШТЕГ"):
            result["hashtags"] = value

    # Извлекаем проценты
    full_text = " ".join([result["intro"], result["details"], " ".join(result["bullets"])])
    percents = re.findall(r'(\d+[\.,]?\d*)\s*%', full_text)
    if len(percents) >= 2:
        try:
            result["numbers"] = [float(p.replace(',', '.')) for p in percents[:3]]
        except:
            result["numbers"] = []

    # Проверка на успешный парсинг
    if not result["title"] or len(result["bullets"]) < 2:
        result["_parse_failed"] = True

    return result


def build_post_text(p):
    parts = []
    if p["title"]: parts.append(p["title"])
    if p["intro"]: parts.append(p["intro"])
    if p["details"]: parts.append(p["details"])
    if p["bullets"]: parts.append("\n".join([f"{i}. {b}" for i, b in enumerate(p["bullets"][:5], 1)]))
    if p["bonus"]: parts.append(f"💡 {p['bonus']}")
    if p["question"]: parts.append(p["question"])
    if p["hashtags"]: parts.append(p["hashtags"])
    return "\n\n".join(parts)


async def is_topic_unique(topic, channel_key):
    used = load_used_topics().get(channel_key, [])
    if not used: return True
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


async def generate_ideas(channel_key, count=5):
    profile = CHANNELS[channel_key]
    used = load_used_topics().get(channel_key, [])
    used_str = ", ".join(used[-20:]) if used else "пока ничего"
    context = ("Ниша: кибербезопасность." if channel_key == "cyber" else "Ниша: нейросети для бизнеса.")
    prompt = f"""Ты — контент-стратег канала «{profile['name']}».
{context}
Уже использовано: {used_str}
Придумай {count} свежих тем (4–8 слов).
Формат: только список, каждая с новой строки."""
    response = await _smart_call(prompt)
    ideas = [line.strip(" -•*0123456789.") for line in response.split("\n") if line.strip()]
    return [i for i in ideas if 4 < len(i) < 80][:count]


def _get_fixed_hashtags(channel_key, rubric):
    tags = []
    brand = BRAND_HASHTAGS.get(channel_key, "")
    if brand: tags.append(brand)
    if rubric:
        rt = RUBRIC_HASHTAGS.get(channel_key, {}).get(rubric.get("key", ""), "")
        if rt: tags.append(rt)
    general = GENERAL_HASHTAGS.get(channel_key, "")
    if general: tags.append(general)
    return tags


def _get_topic_pool(channel_key, count=35):
    pool = TOPIC_HASHTAG_POOL.get(channel_key, [])
    return random.sample(pool, min(count, len(pool))) if pool else []


POST_TEMPLATE_PROMPTS = {
    "story": "СТРУКТУРА: История. Начни с конкретного момента из жизни. Разверни подробно, с эмоциями. В конце — вывод и 3 совета.",
    "breakdown": "СТРУКТУРА: Разбор. Начни с факта/новости. Разбери: ЧТО случилось / ПОЧЕМУ важно / ЧТО делать.",
    "checklist": "СТРУКТУРА: Чек-лист. Начни с проблемы. 5 коротких пунктов. В конце — 1 главный совет от себя.",
    "myth": "СТРУКТУРА: Миф vs Реальность. Начни с мифа. Развенчай. Дай доказательство. В конце — что делать вместо этого.",
}


async def generate_post(topic, channel_key, rubric=None, is_series=False):
    profile = CHANNELS[channel_key]
    author = profile["author"]
    rubric_block = f"Рубрика: {rubric['name']}" if rubric else ""

    template = random.choice(POST_TEMPLATES)
    template_hint = POST_TEMPLATE_PROMPTS.get(template, "")
    hook = random.choice(POST_HOOKS)
    closing = random.choice(POST_CLOSINGS)

    series_hint = ""
    if is_series:
        series_hint = """
=== СЕРИЙНОСТЬ ===
Это продолжение серии. Начни ВСТУПЛЕНИЕ с фразы:
«В прошлый вторник мы разбирали похожую тему. Сегодня — продолжение.»
"""

    fixed_tags = _get_fixed_hashtags(channel_key, rubric)
    pool_sample = _get_topic_pool(channel_key, count=35)
    fixed_tags_str = " ".join(fixed_tags) if fixed_tags else ""
    pool_str = ", ".join(pool_sample) if pool_sample else ""

    prompt = f"""{profile['prompt_prefix']}

О тебе:
- Тебя зовут {author['name']}
- {author['role']}
- Опыт: {author['experience']}
- {author['personal_touch']}

{rubric_block}

Напиши пост на тему: {topic}

{template_hint}

=== ХУК ОТКРЫТИЯ ===
Используй приём: {hook}

=== ИНТЕРАКТИВ В КОНЦЕ ===
В конце используй: {closing}
{series_hint}
=== ПРАВИЛА ЧЕЛОВЕЧНОСТИ ===
1. От первого лица: «я», «мне», «по моему опыту».
2. Личная история или пример.
3. Личное мнение: «на мой взгляд», «я считаю».
4. Эмоции: «меня бесит», «я в шоке», «обидно».
5. Разговорные обороты: «короче», «по сути», «честно».
6. Абзацы РАЗНОЙ длины.
7. Цифра, статистика, факт — если уместно.
8. ЗАПРЕЩЕНЫ шаблоны: «Важно отметить», «В современном мире».
9. Аудитория — обычные люди. Жаргон объясняй.
10. Финал — живой, с интерактивом.

=== ФОРМАТ ОТВЕТА СТРОГО ===

ВАЖНО: пиши БЕЗ ** выделений, без ## заголовков, без решёток, без звёздочек.
Только текст в формате:

ЗАГОЛОВОК: [до 60 символов, без эмодзи]
ВСТУПЛЕНИЕ: [2 предложения, 200–250 символов]
ПОДРОБНЕЕ: [3–4 предложения, 350–450 символов]
ПУНКТ 1: [до 80 символов, БЕЗ цифры в начале]
ПУНКТ 2: [до 80 символов, БЕЗ цифры в начале]
ПУНКТ 3: [до 80 символов, БЕЗ цифры в начале]
БОНУС: [150–200 символов]
ВОПРОС: [интерактив, до 90 символов]
ХЕШТЕГИ: [10–15 через пробел]

ПУНКТЫ — БЕЗ нумерации "1.", "2.", "3.".
МЕТКИ — БЕЗ звёздочек, решёток, подчёркиваний.

ХЕШТЕГИ:
Фиксированные: {fixed_tags_str}
Тематические (выбери 7–12): {pool_str}
Итого 10–15. Без повторов.

Длина: 1000–1300 символов."""

    # Первая попытка
    raw = await _smart_call(prompt)
    parsed = parse_post_structure(raw)

    # Вторая попытка при провале
    if parsed["_parse_failed"]:
        print(f"   ⚠️ Парсер не справился, повторная попытка...", flush=True)
        raw2 = await _smart_call(prompt, temperature=0.5)
        parsed2 = parse_post_structure(raw2)
        if not parsed2["_parse_failed"]:
            parsed = parsed2
            raw = raw2

    # Финальная проверка
    if parsed["_parse_failed"]:
        print(f"   ❌ Не удалось распарсить после двух попыток", flush=True)
        return None, parsed

    # Хештеги: добираем до 10
    existing_tags = parsed.get("hashtags", "").split()
    if len(existing_tags) < 10:
        need = 10 - len(existing_tags)
        pool = TOPIC_HASHTAG_POOL.get(channel_key, [])
        candidates = [t for t in pool if t not in existing_tags]
        random.shuffle(candidates)
        all_tags = existing_tags + fixed_tags + candidates[:need]
        seen, unique = set(), []
        for t in all_tags:
            if t not in seen:
                seen.add(t); unique.append(t)
        parsed["hashtags"] = " ".join(unique[:15])

    return build_post_text(parsed), parsed


async def generate_meme(topic, channel_key):
    prompt = f"""Ты — Егор, автор канала. Сделай КОРОТКИЙ ироничный пост-мем.

Тема: {topic}

ТРЕБОВАНИЯ:
1. Длина: 200-300 символов.
2. Формат «Ожидание / Реальность» ИЛИ короткая шутка с иронией.
3. Первая строка — цепляющая, с эмодзи.
4. В конце — короткий вопрос.
5. Без AI-шаблонов, живо и с юмором.
6. БЕЗ ** выделений, без ## и решёток.

ФОРМАТ:
ЗАГОЛОВОК: [с эмодзи, до 60 символов]
ВСТУПЛЕНИЕ: [2-3 строки мема, 150-200 символов]
ПОДРОБНЕЕ: [короткая шутка, 100-150 символов]
ПУНКТ 1:
ПУНКТ 2:
ПУНКТ 3:
БОНУС:
ВОПРОС: [до 70 символов]
ХЕШТЕГИ: [#мем #кибербезопасность #CyberGuardianSec #юмор]"""
    try:
        raw = await _smart_call(prompt, temperature=0.9)
        return raw
    except Exception as e:
        print(f"   ⚠️ Мем: {e}", flush=True)
        return f"😄 Мем дня\n\nКогда сменил пароль на надёжный, но забыл его.\n\nА вы как храните пароли?\n\n#мем #кибербезопасность"


async def generate_vk_version(post_text, channel_key):
    prompt = f"""Сократи пост для VK. Аудитория VK не читает длинные тексты.

Исходный пост:
{post_text[:1500]}

ТРЕБОВАНИЯ:
1. Длина: 300–500 символов.
2. ХУК в первой строке.
3. 3–5 хештегов.
4. Сохрани главную мысль и эмоцию.
5. В конце — вопрос к читателям.

КРИТИЧНО:
- НЕ вставляй ссылки на Telegram, t.me — я добавлю сам.
- НЕ вставляй название канала (@...).

Формат — только готовый текст."""
    try:
        return await _smart_call(prompt, temperature=0.7)
    except Exception as e:
        print(f"   ⚠️ VK-версия: {e}", flush=True)
        return post_text[:500]


async def generate_longread(topic, channel_key, rubric=None):
    profile = CHANNELS[channel_key]
    author = profile["author"]
    fixed_tags = _get_fixed_hashtags(channel_key, rubric)
    prompt = f"""{profile['prompt_prefix']}

О тебе: {author['name']}, {author['role']}. Опыт: {author['experience']}.

Напиши ГЛУБОКИЙ лонгрид на тему: {topic}
- 1800–2500 символов.
- ОТ ПЕРВОГО ЛИЦА, с личными историями.
- 3–4 раздела с <b>подзаголовками</b>.
- 5–7 советов.
- ХЕШТЕГИ: {fixed_tags}"""
    return await _smart_call(prompt, temperature=0.8)


async def generate_poll(topic, channel_key):
    profile = CHANNELS[channel_key]
    prompt = f"""Канал «{profile['name']}». Опрос по теме: {topic}
ФОРМАТ СТРОГО:
ВОПРОС: [до 100 символов]
ВАРИАНТ: [вариант 1]
ВАРИАНТ: [вариант 2]
ВАРИАНТ: [вариант 3]"""
    response = await _smart_call(prompt, temperature=0.9)
    q, opts = "", []
    for line in response.split("\n"):
        line = line.strip()
        if line.startswith("ВОПРОС:"): q = line.replace("ВОПРОС:", "").strip()
        elif line.startswith("ВАРИАНТ:"):
            o = line.replace("ВАРИАНТ:", "").strip()
            if o: opts.append(o)
    if not q or len(opts) < 2:
        q = f"Что важнее в теме «{topic}»?"
        opts = ["Практика", "Теория", "Инструменты"]
    return {"question": q, "options": opts[:4]}


# ============================================================
# ФОНЫ
# ============================================================

async def _build_image_prompt(post_text, channel_key):
    if channel_key == "cyber":
        style_context = (
            "Cybersecurity topic. Dark, cinematic, professional photography. "
            "Colors: deep navy blue, dark tones with neon green or cyan accents."
        )
    else:
        style_context = (
            "AI/technology topic. Cinematic, professional photography, futuristic. "
            "Colors: dark purple, deep blue with neon green or cyan accents."
        )
    prompt = f"""Проанализируй пост и составь ОДИН детальный промт для фоновой картинки (на английском).

{style_context}

ПОСТ:
{post_text[:800]}

ТРЕБОВАНИЯ:
1. Конкретный сюжет.
2. Стиль (cinematic / minimalist / tech photography).
3. Композиция с пустым местом сверху и снизу.
4. НИКАКОГО ТЕКСТА на картинке.
5. Размер: квадрат.

ФОРМАТ — только промт на английском, до 400 символов."""
    try:
        result = await _smart_call(prompt, temperature=0.6)
        result = result.strip().replace("\n", " ")
        result = re.sub(r'^["\']|["\']$', '', result)
        return result[:450]
    except Exception as e:
        print(f"   ⚠️ Промт: {e}", flush=True)
        fallback = _remove_emoji(post_text[:100])
        return f"cinematic tech photography about {fallback}, dark moody atmosphere, no text on image"


async def _generate_via_provod(prompt, channel_key):
    if not prompt: return None
    headers = {"Authorization": f"Bearer {PROVOD_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": PROVOD_IMAGE_MODEL,
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
        "response_format": "b64_json",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(PROVOD_IMAGE_URL, headers=headers, json=payload, timeout=120) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    print(f"   ⚠️ Provod Image [{resp.status}]: {err[:150]}", flush=True)
                    return None
                data = await resp.json()
        items = data.get("data", [])
        if not items: return None
        item = items[0]
        if "b64_json" in item:
            img_bytes = base64.b64decode(item["b64_json"])
            return Image.open(BytesIO(img_bytes)).convert("RGB")
        elif "url" in item:
            return await _download_image(item["url"])
        return None
    except Exception as e:
        print(f"   ⚠️ Provod Image: {e}", flush=True)
        return None


def _find_font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
             "arialbd.ttf" if bold else "arial.ttf",
             "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"]
    for n in names:
        try: return ImageFont.truetype(n, size)
        except: continue
    return ImageFont.load_default()


def _wrap_text(text, font, max_width, draw):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = current + " " + word if current else word
        try:
            bbox = draw.textbbox((0, 0), test, font=font)
            w = bbox[2] - bbox[0]
        except: w = len(test) * 20
        if w <= max_width:
            current = test
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    return lines


def _remove_emoji(text):
    return re.sub(r'[^\w\s\d\.,!?\-:;()«»"\']', '', text).strip()


def _extract_emoji(text):
    if not text: return ""
    for ch in text:
        if ord(ch) > 0x1F000: return ch
    return ""


async def _download_image(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=60) as resp:
                if resp.status != 200: return None
                content = await resp.read()
                return Image.open(BytesIO(content)).convert("RGB")
    except Exception as e:
        print(f"   ⚠️ Download: {e}", flush=True)
        return None


async def _search_pexels(query, orientation="square"):
    if not PEXELS_API_KEY or not query: return None
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": PEXELS_API_KEY}
            params = {"query": query, "per_page": 8, "orientation": orientation}
            async with session.get(PEXELS_URL, headers=headers, params=params, timeout=20) as resp:
                if resp.status != 200: return None
                data = await resp.json()
                photos = data.get("photos", [])
                if not photos: return None
                photo = random.choice(photos[:8])
                return photo["src"]["large2x"] or photo["src"]["large"]
    except Exception as e:
        print(f"   ⚠️ Pexels: {e}", flush=True)
        return None


async def _translate_to_english(text):
    prompt = f"""Переведи на английский и дай 3-5 ключевых слов для поиска фото.
Заголовок: "{text}"
Формат:
TRANSLATION: [перевод]
KEYWORDS: [3-5 слов через запятую]"""
    try:
        result = await _smart_call(prompt, temperature=0.3)
        translation, keywords = text, ""
        for line in result.split("\n"):
            if line.startswith("TRANSLATION:"):
                translation = line.replace("TRANSLATION:", "").strip()
            elif line.startswith("KEYWORDS:"):
                keywords = line.replace("KEYWORDS:", "").strip()
        return translation, keywords
    except:
        return text, ""


async def _get_pollinations_bg(topic, channel_key):
    topic_clean = _remove_emoji(topic)[:80]
    if channel_key == "cyber":
        style = f"abstract cybersecurity background about {topic_clean}, dark navy blue, neon green, no text, no people, cinematic"
    else:
        style = f"abstract AI technology background about {topic_clean}, dark purple, neon green, no text, no people, cinematic"
    clean = urllib.parse.quote(style[:400])
    seed = random.randint(1, 999999)
    url = f"https://image.pollinations.ai/prompt/{clean}?width=1080&height=1080&nologo=true&model=flux&seed={seed}"
    if POLLINATIONS_API_KEY: url += f"&key={POLLINATIONS_API_KEY}"
    return await _download_image(url)


async def _get_background(parsed, channel_key):
    post_text = build_post_text(parsed) if parsed else ""

    print(f"   🎨 Provod Image: строю промт...", flush=True)
    image_prompt = await _build_image_prompt(post_text, channel_key)
    print(f"   📝 Промт: {image_prompt[:100]}...", flush=True)
    img = await _generate_via_provod(image_prompt, channel_key)
    if img:
        return img, "provod"
    print(f"   ⚠️ Provod недоступен → Pexels", flush=True)

    title = parsed.get("title", "") if parsed else ""
    translation, keywords = await _translate_to_english(title)
    query = keywords if keywords else translation
    if query:
        print(f"   🔍 Pexels: {query}", flush=True)
        url = await _search_pexels(query)
        if url:
            img = await _download_image(url)
            if img: return img, "pexels"

    print(f"   🎨 Pollinations fallback", flush=True)
    img = await _get_pollinations_bg(translation or title, channel_key)
    if img: return img, "pollinations"

    return None, "gradient"


def _make_gradient(width, height, color_top, color_bottom):
    base = Image.new('RGB', (width, height), color_top)
    top = Image.new('RGB', (width, height), color_bottom)
    mask = Image.new('L', (width, height))
    mask_data = []
    for y in range(height):
        val = int(255 * (y / height))
        mask_data.extend([val] * width)
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base


def _brand_plate(draw, W, H, accent, brand):
    plate_w = 640; plate_h = 110
    margin = 20
    x1 = W - plate_w - margin
    y1 = H - plate_h - margin
    x2 = W - margin
    y2 = H - margin
    draw.rectangle([x1, y1, x2, y2], fill=(0, 0, 0))
    draw.rectangle([x1, y1, x2, y1 + 4], fill=accent)
    font_brand = _find_font(30, bold=True)
    draw.text((x1 + 30, y1 + 30), brand, font=font_brand, fill=accent)
    font_quote = _find_font(18)
    draw.text((x1 + 30, y1 + 72), "Егор, автор канала", font=font_quote, fill=(150, 150, 150))


def _draw_chart_pil(draw, W, H, numbers, accent):
    if not numbers or len(numbers) < 2: return
    nums = numbers[:3]
    max_val = max(nums) if nums else 1
    chart_w = 350
    chart_x = W - chart_w - 40
    chart_y = 200
    chart_h = 280
    bar_w = int((chart_w - 40 * (len(nums) - 1)) / len(nums))
    if bar_w < 20: bar_w = 20
    for i, num in enumerate(nums):
        x = chart_x + i * (bar_w + 40)
        bar_h = int((num / max_val) * (chart_h - 60))
        y = chart_y + (chart_h - bar_h) - 60
        draw.rectangle([x, y, x + bar_w, chart_y + chart_h - 60], fill=accent)
        font_v = _find_font(28, bold=True)
        try:
            bb = draw.textbbox((0, 0), f"{int(num)}%", font=font_v)
            tw = bb[2] - bb[0]
        except: tw = 40
        draw.text((x + (bar_w - tw) // 2, y - 40), f"{int(num)}%", font=font_v, fill=accent)


# ============================================================
# ШАБЛОНЫ КАРТОЧЕК
# ============================================================

def _card_classic(bg, parsed, channel_key, palette, brand, accent):
    W, H = 1080, 1080
    SAFE = SAFE_ZONE
    bg = bg.resize((W, H)).convert("RGB")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov = ImageDraw.Draw(overlay)
    ov.rectangle([0, 0, W, 480], fill=(0, 0, 0, 175))
    ov.rectangle([0, H - 620, W, H], fill=(0, 0, 0, 195))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(bg)
    pad = SAFE
    emoji = _extract_emoji(parsed.get("title", ""))
    y = SAFE - 20
    if emoji:
        font_e = _find_font(80)
        draw.text((pad, y), emoji, font=font_e)
        y += 110
    title = _remove_emoji(parsed.get("title", "")) or "Без заголовка"
    size = 54
    lines = []
    for size in [54, 50, 46, 42, 38]:
        font_t = _find_font(size, bold=True)
        lines = _wrap_text(title, font_t, W - 2 * pad, draw)
        if len(lines) <= 3:
            break
    for line in lines[:3]:
        draw.text((pad, y), line, font=font_t, fill=(0,0,0), stroke_width=5, stroke_fill=(0,0,0))
        draw.text((pad, y), line, font=font_t, fill=(255, 255, 255))
        y += size + 16
    bullets = parsed.get("bullets", [])[:3] or ["Подробности в посте", "Читай ниже", "Подпишись"]
    font_b = _find_font(34); font_n = _find_font(30, bold=True)
    y = H - 600
    for i, b in enumerate(bullets, 1):
        bc = _remove_emoji(b) or "..."
        cx, cy = pad + 26, y + 26
        draw.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=accent)
        num = str(i)
        try:
            bb = draw.textbbox((0, 0), num, font=font_n); nw, nh = bb[2]-bb[0], bb[3]-bb[1]
        except: nw, nh = 12, 20
        draw.text((cx - nw//2, cy - nh//2 - 5), num, font=font_n, fill=(0, 0, 0))
        for line in _wrap_text(bc, font_b, W - 2*pad - 80, draw)[:2]:
            if y + 48 > H - TEXT_BOTTOM_LIMIT:
                break
            draw.text((pad + 80, y), line, font=font_b, fill=(0,0,0), stroke_width=3, stroke_fill=(0,0,0))
            draw.text((pad + 80, y), line, font=font_b, fill=(240, 240, 240))
            y += 48
        y += 14
    _brand_plate(draw, W, H, accent, brand)
    return bg


def _card_gradient(bg, parsed, channel_key, palette, brand, accent):
    W, H = 1080, 1080
    SAFE = SAFE_ZONE
    bg = bg.resize((W, H)).convert("RGB")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov = ImageDraw.Draw(overlay)
    for x in range(W):
        alpha = int(220 * (1 - x / W * 0.7))
        ov.rectangle([x, 0, x+1, H], fill=(0, 0, 0, alpha))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(bg)
    pad = SAFE
    emoji = _extract_emoji(parsed.get("title", ""))
    y = SAFE + 20
    if emoji:
        font_e = _find_font(90)
        draw.text((pad, y), emoji, font=font_e)
        y += 130
    title = _remove_emoji(parsed.get("title", "")) or "Без заголовка"
    size = 58
    lines = []
    for size in [58, 54, 50, 46, 42]:
        font_t = _find_font(size, bold=True)
        lines = _wrap_text(title, font_t, int(W * 0.65), draw)
        if len(lines) <= 4:
            break
    for line in lines[:4]:
        draw.text((pad, y), line, font=font_t, fill=(0,0,0), stroke_width=6, stroke_fill=(0,0,0))
        draw.text((pad, y), line, font=font_t, fill=(255, 255, 255))
        y += size + 16
    bullets = parsed.get("bullets", [])[:3]
    font_b = _find_font(28)
    y += 30
    for b in bullets:
        if y + 44 > H - TEXT_BOTTOM_LIMIT:
            break
        bc = _remove_emoji(b)
        if not bc: continue
        draw.text((pad, y), f"— {bc}", font=font_b, fill=accent, stroke_width=2, stroke_fill=(0,0,0))
        y += 44
    _brand_plate(draw, W, H, accent, brand)
    return bg


def _card_accent(bg, parsed, channel_key, palette, brand, accent):
    W, H = 1080, 1080
    SAFE = SAFE_ZONE
    bg = bg.resize((W, H)).convert("RGB")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov = ImageDraw.Draw(overlay)
    ov.rectangle([0, 0, W, H], fill=(0, 0, 0, 180))
    ov.rectangle([0, H - 340, W, H], fill=(0, 0, 0, 230))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(bg)
    emoji = _extract_emoji(parsed.get("title", ""))
    y = SAFE + 40
    if emoji:
        font_big = _find_font(180)
        try:
            bb = draw.textbbox((0, 0), emoji, font=font_big)
            bw = bb[2] - bb[0]
            draw.text(((W - bw) // 2, y), emoji, font=font_big)
        except: pass
        y += 220
    title = _remove_emoji(parsed.get("title", "")) or "Без заголовка"
    size = 54
    lines = []
    for size in [54, 50, 46, 42, 38]:
        font_t = _find_font(size, bold=True)
        lines = _wrap_text(title, font_t, W - 2 * SAFE, draw)
        if len(lines) <= 4:
            break
    for line in lines[:4]:
        try:
            bb = draw.textbbox((0, 0), line, font=font_t); lw = bb[2] - bb[0]
        except: lw = 0
        x = (W - lw) // 2
        draw.text((x, y), line, font=font_t, fill=(0,0,0), stroke_width=6, stroke_fill=(0,0,0))
        draw.text((x, y), line, font=font_t, fill=(255, 255, 255))
        y += size + 16
    bullets = parsed.get("bullets", [])[:3]
    font_b = _find_font(28)
    y = H - 340
    for b in bullets[:3]:
        if y + 42 > H - TEXT_BOTTOM_LIMIT:
            break
        bc = _remove_emoji(b)
        if not bc: continue
        draw.text((SAFE, y), f"• {bc}", font=font_b, fill=accent)
        y += 42
    _brand_plate(draw, W, H, accent, brand)
    return bg


def _card_bottom_up(bg, parsed, channel_key, palette, brand, accent):
    W, H = 1080, 1080
    SAFE = SAFE_ZONE
    bg = bg.resize((W, H)).convert("RGB")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov = ImageDraw.Draw(overlay)
    ov.rectangle([0, 0, W, 520], fill=(0, 0, 0, 195))
    ov.rectangle([0, H - 620, W, H], fill=(0, 0, 0, 225))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(bg)
    pad = SAFE
    bullets = parsed.get("bullets", [])[:3] or ["Пункт 1", "Пункт 2", "Пункт 3"]
    font_b = _find_font(34); font_n = _find_font(30, bold=True)
    y = SAFE - 20
    for i, b in enumerate(bullets, 1):
        bc = _remove_emoji(b) or "..."
        cx, cy = pad + 26, y + 26
        draw.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=accent)
        num = str(i)
        try:
            bb = draw.textbbox((0, 0), num, font=font_n); nw, nh = bb[2]-bb[0], bb[3]-bb[1]
        except: nw, nh = 12, 20
        draw.text((cx - nw//2, cy - nh//2 - 5), num, font=font_n, fill=(0,0,0))
        for line in _wrap_text(bc, font_b, W - 2*pad - 80, draw)[:2]:
            draw.text((pad + 80, y), line, font=font_b, fill=(240, 240, 240))
            y += 46
        y += 14
    emoji = _extract_emoji(parsed.get("title", ""))
    y = H - 640
    if emoji:
        font_e = _find_font(80)
        draw.text((pad, y), emoji, font=font_e)
        y += 100
    title = _remove_emoji(parsed.get("title", "")) or "Без заголовка"
    size = 60
    lines = []
    for size in [60, 56, 52, 48, 44]:
        font_t = _find_font(size, bold=True)
        lines = _wrap_text(title, font_t, W - 2 * pad, draw)
        if len(lines) <= 3:
            break
    for line in lines[:3]:
        if y + size > H - TEXT_BOTTOM_LIMIT:
            break
        draw.text((pad, y), line, font=font_t, fill=(0,0,0), stroke_width=6, stroke_fill=(0,0,0))
        draw.text((pad, y), line, font=font_t, fill=(255, 255, 255))
        y += size + 16
    _brand_plate(draw, W, H, accent, brand)
    return bg


def _card_magazine(bg, parsed, channel_key, palette, brand, accent):
    W, H = 1080, 1080
    SAFE = SAFE_ZONE
    bg = bg.resize((W, H)).convert("RGB")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov = ImageDraw.Draw(overlay)
    ov.rectangle([0, 0, W, 220], fill=(0, 0, 0, 220))
    ov.rectangle([0, 220, W, H - 260], fill=(0, 0, 0, 145))
    ov.rectangle([0, H - 260, W, H], fill=(0, 0, 0, 220))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(bg)
    pad = SAFE
    font_cat = _find_font(24, bold=True)
    cat = "КИБЕРБЕЗОПАСНОСТЬ" if channel_key == "cyber" else "НЕЙРОСЕТИ И AI"
    draw.text((pad, SAFE - 20), cat, font=font_cat, fill=accent)
    draw.line([(pad, SAFE + 30), (W - pad, SAFE + 30)], fill=accent, width=3)
    emoji = _extract_emoji(parsed.get("title", ""))
    y = SAFE + 140
    if emoji:
        font_e = _find_font(110)
        try:
            bb = draw.textbbox((0, 0), emoji, font=font_e); bw = bb[2] - bb[0]
            draw.text(((W - bw) // 2, y), emoji, font=font_e)
        except: pass
        y += 140
    title = _remove_emoji(parsed.get("title", "")) or "Без заголовка"
    size = 68
    lines = []
    for size in [68, 62, 56, 50, 46]:
        font_t = _find_font(size, bold=True)
        lines = _wrap_text(title, font_t, W - 2 * pad, draw)
        if len(lines) <= 4:
            break
    for line in lines[:4]:
        if y + size > H - 320:
            break
        try:
            bb = draw.textbbox((0, 0), line, font=font_t); lw = bb[2] - bb[0]
        except: lw = 0
        x = (W - lw) // 2
        draw.text((x, y), line, font=font_t, fill=(0,0,0), stroke_width=6, stroke_fill=(0,0,0))
        draw.text((x, y), line, font=font_t, fill=(255, 255, 255))
        y += size + 16
    bullets = parsed.get("bullets", [])[:3]
    font_b = _find_font(26, bold=True)
    if bullets:
        y = H - 240
        text = " • ".join([_remove_emoji(b)[:30] for b in bullets if b])
        for line in _wrap_text(text, font_b, W - 2 * pad, draw)[:2]:
            if y + 36 > H - TEXT_BOTTOM_LIMIT:
                break
            draw.text((pad, y), line, font=font_b, fill=accent)
            y += 36
    _brand_plate(draw, W, H, accent, brand)
    return bg


def _card_meme(bg, parsed, channel_key, palette, brand, accent):
    W, H = 1080, 1080
    bg = bg.resize((W, H)).convert("RGB")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov = ImageDraw.Draw(overlay)
    ov.rectangle([0, 0, W, H], fill=(0, 0, 0, 190))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(bg)
    pad = SAFE + 40

    title = _remove_emoji(parsed.get("title", "")).upper() or "МЕМ ДНЯ"
    font_t = _find_font(56, bold=True)
    y = 200
    for line in _wrap_text(title, font_t, W - 2 * pad, draw)[:3]:
        try:
            bb = draw.textbbox((0, 0), line, font=font_t); lw = bb[2] - bb[0]
        except: lw = 0
        x = (W - lw) // 2
        draw.text((x, y), line, font=font_t, fill=(0,0,0), stroke_width=6, stroke_fill=(0,0,0))
        draw.text((x, y), line, font=font_t, fill=accent)
        y += 74

    y += 60
    intro = parsed.get("intro", "")
    if intro:
        font_b = _find_font(48, bold=True)
        for line in _wrap_text(intro, font_b, W - 2 * pad, draw)[:4]:
            if y + 64 > H - 300:
                break
            try:
                bb = draw.textbbox((0, 0), line, font=font_b); lw = bb[2] - bb[0]
            except: lw = 0
            x = (W - lw) // 2
            draw.text((x, y), line, font=font_b, fill=(255, 255, 255), stroke_width=4, stroke_fill=(0,0,0))
            y += 64

    emoji = _extract_emoji(parsed.get("title", ""))
    if emoji:
        font_e = _find_font(160)
        try:
            bb = draw.textbbox((0, 0), emoji, font=font_e); bw = bb[2] - bb[0]
            draw.text(((W - bw) // 2, H - 400), emoji, font=font_e)
        except: pass

    _brand_plate(draw, W, H, accent, brand)
    return bg


CARD_FUNCS = {
    "classic": _card_classic,
    "gradient": _card_gradient,
    "accent": _card_accent,
    "bottom_up": _card_bottom_up,
    "magazine": _card_magazine,
    "meme": _card_meme,
}


async def generate_image(parsed, channel_key="cyber", rubric=None):
    try:
        bg, source = await _get_background(parsed, channel_key)
        print(f"   📷 Фон: {source}", flush=True)

        palette = random.choice(PALETTES.get(channel_key, PALETTES["cyber"]))
        if rubric:
            accent = RUBRIC_ACCENTS.get(channel_key, {}).get(rubric.get("key", ""), palette["accent"])
        else:
            accent = palette["accent"]

        brand = "CyberGuardianSec" if channel_key == "cyber" else "AI Navigator"
        if bg is None:
            bg = _make_gradient(1080, 1080, palette["bg_top"], palette["bg_bottom"])

        if rubric and rubric.get("format") == "meme":
            template = "meme"
        else:
            template = random.choice(CARD_TEMPLATES)

        print(f"   🎨 Шаблон: {template}", flush=True)

        card = CARD_FUNCS[template](bg, parsed, channel_key, palette, brand, accent)

        numbers = parsed.get("numbers", []) if parsed else []
        if numbers and len(numbers) >= 2 and template not in ["meme"]:
            print(f"   📊 Инфографика: {numbers}", flush=True)
            draw = ImageDraw.Draw(card)
            _draw_chart_pil(draw, 1080, 1080, numbers, accent)

        filename = f"{channel_key}_{template}_{abs(hash(parsed.get('title','') + str(random.randint(1,99999)))) % 100000}.png"
        filepath = os.path.join(IMAGES_DIR, filename)
        card.save(filepath, "PNG")
        print(f"   ✅ Готово: {filename}", flush=True)
        return filepath
    except Exception as e:
        print(f"   ⚠️ Визуал: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return ""


def _create_article_cover(bg_img, title, channel_key):
    W, H = 1200, 630
    bg = bg_img.resize((W, H)).convert("RGB")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov = ImageDraw.Draw(overlay)
    ov.rectangle([0, 0, int(W * 0.72), H], fill=(0, 0, 0, 165))
    ov.rectangle([0, H - 80, W, H], fill=(0, 0, 0, 220))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(bg)
    palette = random.choice(PALETTES.get(channel_key, PALETTES["cyber"]))
    accent = palette["accent"]
    brand = "CyberGuardianSec" if channel_key == "cyber" else "AI Navigator"
    category = "КИБЕРБЕЗОПАСНОСТЬ" if channel_key == "cyber" else "НЕЙРОСЕТИ И AI"
    font_cat = _find_font(20, bold=True)
    font_t = _find_font(48, bold=True)
    font_b = _find_font(26, bold=True)
    pad = 50
    draw.text((pad, 30), category, font=font_cat, fill=accent)
    clean = _remove_emoji(title) or "Статья"
    y = 110
    for line in _wrap_text(clean, font_t, int(W * 0.65), draw)[:4]:
        draw.text((pad, y), line, font=font_t, fill=(0,0,0), stroke_width=5, stroke_fill=(0,0,0))
        draw.text((pad, y), line, font=font_t, fill=(255, 255, 255))
        y += 60
    draw.text((pad, H - 55), brand, font=font_b, fill=accent)
    return bg


async def generate_article_cover(title, channel_key="cyber"):
    try:
        image_prompt = await _build_image_prompt(title, channel_key)
        bg = await _generate_via_provod(image_prompt, channel_key)
        if not bg:
            translation, keywords = await _translate_to_english(title)
            query = keywords if keywords else translation
            url = await _search_pexels(query, orientation="landscape")
            bg = await _download_image(url) if url else None
        if not bg:
            bg = await _get_pollinations_bg(title, channel_key)
        if not bg:
            bg = Image.new("RGB", (1200, 630), (10, 20, 50) if channel_key == "cyber" else (40, 10, 60))
        cover = _create_article_cover(bg, title, channel_key)
        filename = f"cover_{channel_key}_{abs(hash(title)) % 100000}.png"
        filepath = os.path.join(IMAGES_DIR, filename)
        cover.save(filepath, "PNG")
        return filepath
    except Exception as e:
        print(f"   ⚠️ Обложка: {e}", flush=True)
        return ""
