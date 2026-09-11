import asyncio
import json
import os
import re
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import aiohttp
from config import DATA_DIR

# === Куда слать дайджест (твой юзернейм или ID) ===
ADMIN_USERNAME = "@kostaErgo"

# === Ключевые слова для поиска каналов ===
SEARCH_KEYWORDS = {
    "cyber": [
        "кибербезопасность", "cybersecurity", "инфобез", "infosec",
        "хакеры", "hacking", "утечки", "data breach", "уязвимость",
        "защита данных", "приватность", "VPN", "пароли", "фишинг",
    ],
    "ai": [
        "нейросети", "нейросеть", "AI", "artificial intelligence", "ChatGPT",
        "машинное обучение", "machine learning", "AI для бизнеса",
        "автоматизация", "промпты", "Midjourney", "GPT", "LLM",
    ],
}

# === Стартовый список известных каналов (seed) ===
SEED_CHANNELS = {
    "cyber": [
        "cybersecurity_ru", "infosecurity", "securitylab", "kaspersky",
        "positive_technologies", "bizone_ru", "cisoclub", "true_sec",
        "codeby_ru", "xakep_ru", "anti_malware", "cnews_ru",
    ],
    "ai": [
        "ai_news_ru", "neural_networks", "gpt_ru", "ai_art_ru",
        "openai_ru", "data_secrets", "aiconference", "neuro_ru",
        "ai_for_business", "gpt_chat_ru", "midjourney_ru", "stablediffusion_ru",
    ],
}

SEEN_FILE = os.path.join(DATA_DIR, "seen_channels.json")
POSTED_FILE = os.path.join(DATA_DIR, "commented_posts.json")


def _load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def _check_channel_web_preview(channel: str) -> dict:
    """Проверяет канал через t.me/s/ веб-превью."""
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
        if posts:
            last_post = re.sub(r'<[^>]+>', '', posts[-1])
            last_post = last_post[:300].replace("\n", " ")

        return {
            "title": title,
            "description": description,
            "last_post": last_post,
            "url": f"https://t.me/{channel}",
        }
    except Exception as e:
        print(f"⚠️ Ошибка проверки {channel}: {e}")
        return {}


def _matches_keywords(text: str, channel_key: str) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in SEARCH_KEYWORDS.get(channel_key, []))


async def discover_channels(channel_key: str, max_new: int = 5) -> list:
    """Автопоиск подходящих каналов."""
    seen = _load_json(SEEN_FILE, {"cyber": [], "ai": []})
    seen_list = seen.get(channel_key, [])

    candidates = list(set(SEED_CHANNELS.get(channel_key, [])))

    new_channels = []
    for ch in candidates:
        if ch in seen_list:
            continue

        info = await _check_channel_web_preview(ch)
        if not info:
            continue

        combined = f"{info['title']} {info['description']} {info['last_post']}"
        if _matches_keywords(combined, channel_key):
            new_channels.append({
                "channel": ch,
                "title": info["title"],
                "description": info["description"][:150],
                "last_post": info["last_post"][:200],
                "url": info["url"],
            })
            if len(new_channels) >= max_new:
                break

    return new_channels


async def send_daily_digest(bot):
    """Отправляет админу список каналов для комментирования по обоим каналам."""
    if not ADMIN_USERNAME:
        print("ℹ️ ADMIN_USERNAME не задан")
        return

    # === Дайджест для КИБЕР ===
    cyber_digest = "🔐 <b>Ассистент: CyberGuardianSec</b>\n"
    cyber_digest += "Куда зайти сегодня и оставить комментарий:\n\n"

    cyber_channels = await discover_channels("cyber", max_new=5)
    if cyber_channels:
        for ch in cyber_channels:
            cyber_digest += f"• <a href=\"{ch['url']}\">{ch['title']}</a>\n"
            if ch['last_post']:
                cyber_digest += f"  <i>{ch['last_post'][:150]}...</i>\n"
            cyber_digest += "\n"
    else:
        cyber_digest += "<i>Новых каналов не найдено</i>\n\n"

    cyber_digest += (
        "💡 <b>Правила:</b>\n"
        "• Без ссылок на свой канал\n"
        "• Полезный экспертный комментарий\n"
        "• 2–3 предложения\n\n"
        "✍️ Пришли мне текст поста — дам 3 варианта комментария."
    )

    # === Дайджест для AI ===
    ai_digest = "🤖 <b>Ассистент: AI Navigator</b>\n"
    ai_digest += "Куда зайти сегодня и оставить комментарий:\n\n"

    ai_channels = await discover_channels("ai", max_new=5)
    if ai_channels:
        for ch in ai_channels:
            ai_digest += f"• <a href=\"{ch['url']}\">{ch['title']}</a>\n"
            if ch['last_post']:
                ai_digest += f"  <i>{ch['last_post'][:150]}...</i>\n"
            ai_digest += "\n"
    else:
        ai_digest += "<i>Новых каналов не найдено</i>\n\n"

    ai_digest += (
        "💡 <b>Правила:</b>\n"
        "• Без ссылок на свой канал\n"
        "• Полезный экспертный комментарий\n"
        "• 2–3 предложения\n\n"
        "✍️ Пришли мне текст поста — дам 3 варианта комментария."
    )

    # Отправляем оба дайджеста
    try:
        # Сначала шапка
        await bot.send_message(
            ADMIN_USERNAME,
            "🔔 <b>Ежедневный дайджест для комментирования</b>\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            "Ниже — по 5 каналов для каждого направления. "
            "Зайди, оставь полезный комментарий — получишь органический трафик."
        )
        await asyncio.sleep(1)
        await bot.send_message(ADMIN_USERNAME, cyber_digest)
        await asyncio.sleep(1)
        await bot.send_message(ADMIN_USERNAME, ai_digest)
        print("✅ Дайджесты (cyber + ai) отправлены")
    except Exception as e:
        print(f"⚠️ Ошибка отправки: {e}")
        print("   Убедись, что ты написал боту /start первым!")


def start_comment_assistant(bot):
    """Запускает планировщик ассистента (2 раза в день)."""
    if not ADMIN_USERNAME:
        print("ℹ️ Ассистент комментирования отключён")
        return

    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    # Утро: 09:00 МСК
    scheduler.add_job(send_daily_digest, "cron", hour=9, minute=0, args=[bot])
    # Вечер: 17:00 МСК
    scheduler.add_job(send_daily_digest, "cron", hour=17, minute=0, args=[bot])
    scheduler.start()
    print("✅ Ассистент комментирования запущен (09:00 и 17:00 МСК)")
