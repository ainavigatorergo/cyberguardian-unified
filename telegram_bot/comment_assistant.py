import asyncio
import json
import os
import re
import random
from datetime import datetime
import aiohttp
from config import DATA_DIR, PROVOD_API_KEY, OPENROUTER_API_KEY

ADMIN_FILE = os.path.join(DATA_DIR, "admin_chat.json")

DEFAULT_ADMIN_CHAT_ID = 5053770400

PROVOD_URL = "https://api.provod.ai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

PROVOD_MODELS = ["gemini-3.5-flash", "gemini-2.5-flash"]
OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-12b-it:free",
]

# === ЧЁРНЫЙ СПИСОК (без комментов / не существуют / похожи на мои) ===
BLACKLIST = [
    # Без комментариев
    "cisoclub",
    "true_security",
    "true_sec",
    "infosec",                      # без комментов
    "kiber_bez",                    # КИБЕР БЕЗ...
    "chatgpt_ru",                   # ChatGPT - Ru
    "gpt_chat_ru",
    "ai_startups",
    "claude_ru",
    "gemini_ru",
    "chatgpt_ru_official",
    "security_alert",               # не существует
    "cybersecurity_ru",             # похож на мой канал
    "seeallochnaya",                # только с личного аккаунта
    "syoloshchnaya",
    "ai_for_business",              # AI-для бизнеса | Внедрение, без комментов
    "машинное_обучение",            # дубль по названию
    "machinelearning_ru",           # без комментов
]

SEARCH_KEYWORDS = {
    "cyber": [
        "кибербезопасность", "cybersecurity", "инфобез",
        "хакеры", "hacking", "утечки", "data breach", "уязвимость",
        "защита данных", "приватность", "VPN", "пароли", "фишинг",
        "безопасность", "security", "malware", "атака",
    ],
    "ai": [
        "нейросети", "нейросеть", "AI", "artificial intelligence", "ChatGPT",
        "машинное обучение", "AI для бизнеса",
        "автоматизация", "промпты", "Midjourney", "GPT", "LLM",
        "искусственный интеллект", "нейронные сети", "OpenAI",
    ],
}

# === КАНАЛЫ ДЛЯ ПОИСКА (только активные, с открытыми комментами) ===
SEED_CHANNELS = {
    "cyber": [
        "positive_technologies", "bizone_ru", "codeby_ru", "xakep_ru",
        "anti_malware", "cnews_ru", "sec_ru", "bugbounty_ru",
        "pentestit", "security_moscow", "in4security", "aciso_ru",
        "itsec_ru", "safe_zone_ru", "cyberpolice_ru", "antiphishing_ru",
        "data_security_ru", "cyber_news_ru", "security_week",
        "infosec_ru", "itsec_news", "cyber_security_news", "hack_news",
        "kaspersky", "securitylab",
    ],
    "ai": [
        "ai_news_ru", "neural_networks", "gpt_ru", "ai_art_ru",
        "openai_ru", "data_secrets", "aiconference", "neuro_ru",
        "midjourney_ru", "dl_ru", "gpt4_ru", "ai_daily",
        "deep_learning_ru", "prompt_engineering", "neuro_channel",
        "ai_machinelearning_big_data", "ai_discussions", "llm_ru",
        "ai_tools_ru", "neuro_news", "ai_practice", "gpt_news_ru",
        "ai_technologies", "neural_networks_ru", "machine_learning_news",
    ],
}


def _load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default


def _save_json(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Не удалось сохранить {path}: {e}")


def save_admin_chat_id(chat_id: int):
    _save_json(ADMIN_FILE, {"chat_id": chat_id})
    print(f"✅ Сохранён admin chat_id: {chat_id}")


def get_admin_chat_id():
    data = _load_json(ADMIN_FILE, {})
    saved = data.get("chat_id")
    if saved:
        return saved
    return DEFAULT_ADMIN_CHAT_ID


def is_blacklisted(channel):
    ch_lower = channel.lower()
    for b in BLACKLIST:
        if b.lower() in ch_lower or ch_lower in b.lower():
            return True
    return False


async def _call_api(url, api_key, model, prompt, temperature=0.7):
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
        async with session.post(url, headers=headers, json=payload, timeout=90) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
            raise Exception(f"API error: {resp.status}")


async def _smart_call(prompt, temperature=0.7):
    for model in PROVOD_MODELS:
        try:
            return await _call_api(PROVOD_URL, PROVOD_API_KEY, model, prompt, temperature)
        except Exception as e:
            print(f"   ⚠️ provod [{model}]: {str(e)[:80]}")
            continue
    if OPENROUTER_API_KEY:
        for model in OPENROUTER_MODELS:
            try:
                return await _call_api(OPENROUTER_URL, OPENROUTER_API_KEY, model, prompt, temperature)
            except Exception as e:
                print(f"   ⚠️ OR [{model}]: {str(e)[:80]}")
                continue
    return None


async def _check_channel_web_preview(channel):
    url = f"https://t.me/s/{channel}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as resp:
                if resp.status != 200:
                    return {}
                html = await resp.text()

        title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html)
        title = title_match.group(1) if title_match else channel

        desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', html)
        description = desc_match.group(1) if desc_match else ""

        # Проверка наличия группы обсуждений
        has_comments = "tgme_widget_message_replies" in html

        posts = re.findall(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', html, re.DOTALL)
        last_post = ""
        if posts:
            last_post = re.sub(r'<[^>]+>', '', posts[-1])
            last_post = last_post[:400].replace("\n", " ")

        return {
            "title": title,
            "description": description,
            "last_post": last_post,
            "url": f"https://t.me/{channel}",
            "has_comments": has_comments,
        }
    except Exception as e:
        print(f"⚠️ Ошибка проверки {channel}: {e}")
        return {}


def _matches_keywords(text, channel_key):
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in SEARCH_KEYWORDS.get(channel_key, []))


async def generate_comment_variants(post_text, channel_key):
    if channel_key == "cyber":
        context = "Ты — эксперт по кибербезопасности, ведёшь канал CyberGuardianSec."
    else:
        context = "Ты — эксперт по нейросетям и автоматизации, ведёшь канал AI Navigator."

    prompt = f"""
{context}

Вот пост в чужом канале:
"{post_text[:500]}"

Напиши ТРИ разных варианта комментария к этому посту.

Требования:
- 2–3 предложения каждый.
- Экспертный, полезный, по делу.
- Без ссылок на свой канал.
- Варианты РАЗНЫЕ по подходу.

Формат ответа СТРОГО:
ВАРИАНТ 1: [текст]
ВАРИАНТ 2: [текст]
ВАРИАНТ 3: [текст]
"""
    response = await _smart_call(prompt, temperature=0.8)
    if not response:
        return []

    variants = []
    for line in response.split("\n"):
        line = line.strip()
        if line.startswith("ВАРИАНТ"):
            text = line.split(":", 1)[1].strip() if ":" in line else ""
            if text:
                variants.append(text)
    return variants[:3]


async def discover_channels(channel_key, max_new=3):
    """
    Возвращает только каналы с ОТКРЫТЫМИ комментариями.
    """
    candidates = list(SEED_CHANNELS.get(channel_key, []))
    random.shuffle(candidates)

    new_channels = []
    checked = 0

    # Первый проход — только с открытыми комментами
    for ch in candidates:
        if len(new_channels) >= max_new:
            break
        if checked >= 25:
            break
        checked += 1

        if is_blacklisted(ch):
            continue

        info = await _check_channel_web_preview(ch)
        if not info:
            continue

        if is_blacklisted(info.get("title", "")):
            continue

        # ТОЛЬКО с открытыми комментами
        if not info.get("has_comments"):
            print(f"   ⏭️ {ch} — комментарии закрыты")
            continue

        combined = f"{info['title']} {info['description']} {info['last_post']}"
        if _matches_keywords(combined, channel_key):
            new_channels.append({
                "channel": ch,
                "title": info["title"],
                "last_post": info["last_post"][:250],
                "url": info["url"],
                "has_comments": True,
            })

    return new_channels


async def send_daily_digest(bot):
    target = get_admin_chat_id()
    print(f"📤 Дайджест → chat_id: {target}")

    try:
        await bot.send_message(
            target,
            "🔔 <b>Дайджест для комментирования</b>\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            "🔍 Ищу каналы только с ОТКРЫТЫМИ комментариями..."
        )
    except Exception as e:
        print(f"❌ Не удалось отправить первое сообщение: {e}")
        return False

    for channel_key in ["cyber", "ai"]:
        emoji = "🔐" if channel_key == "cyber" else "🤖"
        name = "CyberGuardianSec" if channel_key == "cyber" else "AI Navigator"

        try:
            channels = await discover_channels(channel_key, max_new=3)
        except Exception as e:
            print(f"⚠️ Ошибка поиска каналов: {e}")
            channels = []

        if not channels:
            try:
                await bot.send_message(
                    target,
                    f"{emoji} <b>{name}</b>\n\n"
                    "😔 Каналов с открытыми комментариями не найдено.\n"
                    "<i>Попробуй позже или добавь каналы в белый список.</i>"
                )
            except:
                pass
            continue

        for ch in channels:
            header = f"{emoji} <b>{name}</b> → <a href=\"{ch['url']}\">{ch['title']}</a>\n"
            header += "✅ Комментарии открыты\n"
            header += f"\n📄 <i>Последний пост:</i>\n{ch['last_post'][:250]}\n"

            try:
                variants = await generate_comment_variants(ch['last_post'], channel_key)
            except Exception as e:
                print(f"⚠️ Ошибка генерации вариантов: {e}")
                variants = []

            if variants:
                header += "\n💬 <b>Варианты комментариев:</b>\n\n"
                for i, v in enumerate(variants, 1):
                    header += f"<b>{i}.</b> {v}\n\n"
            else:
                header += "\n💬 <i>Не удалось сгенерировать комментарии.</i>\n"

            header += (
                "\n📌 <b>Правила:</b>\n"
                "• Публикуй от имени канала\n"
                "• Без ссылок на свой канал\n"
                "• Выбери один из вариантов"
            )

            try:
                await bot.send_message(target, header, disable_web_page_preview=True)
                await asyncio.sleep(1)
            except Exception as e:
                print(f"⚠️ Ошибка отправки: {e}")

    try:
        await bot.send_message(target, "✅ Дайджест завершён")
    except:
        pass

    print("✅ Дайджесты отправлены")
    return True
