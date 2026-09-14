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

# === ЧЁРНЫЙ СПИСОК (точное совпадение юзернейма) ===
BLACKLIST = [
    "cisoclub",
    "true_security",
    "true_sec",
    "infosec",
    "kiber_bez",
    "chatgpt_ru",
    "gpt_chat_ru",
    "ai_startups",
    "claude_ru",
    "gemini_ru",
    "chatgpt_ru_official",
    "security_alert",
    "cybersecurity_ru",
    "seeallochnaya",
    "syoloshchnaya",
    "ai_for_business",
    "data_security_ru",
    "itsec_news",
    "gpt4_ru",
    "ai_daily",
    "machinelearning",       # добавлено
    "machinelearning_ru",    # добавлено
    "machine_learning_news", # добавлено
]

# === СЛУЖЕБНЫЕ ФРАЗЫ ===
SERVICE_PHRASES = [
    "channel created",
    "channel name was changed",
    "channel photo changed",
    "channel description changed",
    "channel pinned",
    "channel is available for purchase",
    "available for purchase",
    "канал создан",
    "название канала изменено",
    "описание канала изменено",
    "канал доступен для покупки",
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

SEED_CHANNELS = {
    "cyber": [
        "positive_technologies", "bizone_ru", "codeby_ru", "xakep_ru",
        "anti_malware", "cnews_ru", "sec_ru", "bugbounty_ru",
        "pentestit", "in4security", "aciso_ru", "itsec_ru",
        "safe_zone_ru", "cyberpolice_ru", "antiphishing_ru",
        "cyber_news_ru", "security_week", "infosec_ru",
        "cyber_security_news", "hack_news",
        "kaspersky", "securitylab", "hacker_news_ru",
        "cyber_ru", "security_news_ru", "infosecurity",
    ],
    "ai": [
        "ai_news_ru", "neural_networks", "gpt_ru", "ai_art_ru",
        "openai_ru", "data_secrets", "aiconference", "neuro_ru",
        "midjourney_ru", "dl_ru",
        "deep_learning_ru", "prompt_engineering", "neuro_channel",
        "ai_machinelearning_big_data", "ai_discussions", "llm_ru",
        "ai_tools_ru", "neuro_news", "ai_practice", "gpt_news_ru",
        "ai_technologies", "neural_networks_ru",
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


def _normalize(s: str) -> str:
    return s.lower().strip().lstrip("@").strip()


def is_blacklisted(channel: str) -> bool:
    ch = _normalize(channel)
    return ch in [_normalize(b) for b in BLACKLIST]


def is_title_blacklisted(title: str) -> bool:
    t = _normalize(title)
    return t in [_normalize(b) for b in BLACKLIST]


def is_service_post(text: str) -> bool:
    if not text:
        return True
    text_lower = text.lower().strip()
    for phrase in SERVICE_PHRASES:
        if phrase in text_lower:
            return True
    if len(text_lower) < 60:
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

        posts = re.findall(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', html, re.DOTALL)
        last_post = ""
        for post_html in reversed(posts):
            cleaned = re.sub(r'<br\s*/?>', ' ', post_html)
            cleaned = re.sub(r'<[^>]+>', '', cleaned)
            cleaned = cleaned.replace("&nbsp;", " ").replace("&amp;", "&")
            cleaned = cleaned.strip()
            if not is_service_post(cleaned):
                last_post = cleaned[:400].replace("\n", " ")
                break

        return {
            "title": title,
            "description": description,
            "last_post": last_post,
            "url": f"https://t.me/{channel}",
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

Напиши ТРИ разных варианта комментария ИМЕННО К ЭТОМУ ПОСТУ.

Требования:
- 2–3 предложения каждый.
- Экспертный, полезный, по делу.
- Ссылайся на конкретику из поста.
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
    candidates = list(SEED_CHANNELS.get(channel_key, []))
    random.shuffle(candidates)

    new_channels = []
    checked = 0

    for ch in candidates:
        if len(new_channels) >= max_new:
            break
        if checked >= 25:
            break
        checked += 1

        if is_blacklisted(ch):
            print(f"   🚫 {ch} — в чёрном списке")
            continue

        info = await _check_channel_web_preview(ch)
        if not info:
            continue

        if is_title_blacklisted(info.get("title", "")):
            print(f"   🚫 {ch} — название в чёрном списке")
            continue

        if not info.get("last_post"):
            print(f"   ⏭️ {ch} — нет осмысленного поста")
            continue

        combined = f"{info['title']} {info['description']} {info['last_post']}"
        if _matches_keywords(combined, channel_key):
            new_channels.append({
                "channel": ch,
                "title": info["title"],
                "last_post": info["last_post"][:250],
                "url": info["url"],
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
            "🔍 Ищу подходящие каналы..."
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
                    f"{emoji} <b>{name}</b>\n\n😔 Каналы не найдены."
                )
            except:
                pass
            continue

        for ch in channels:
            header = f"{emoji} <b>{name}</b> → <a href=\"{ch['url']}\">{ch['title']}</a>\n"
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
                "• Проверь, открыты ли комментарии"
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
