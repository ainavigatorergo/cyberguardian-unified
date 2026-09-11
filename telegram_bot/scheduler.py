import json
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import CHANNELS, DATA_DIR
from generator import generate_post, generate_image

scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


def load_json(filename, default):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def publish_post(bot, channel_key: str):
    profile = CHANNELS[channel_key]
    used = load_json("used_topics.json", {"cyber": [], "ai": []})

    # Берём тему, которой ещё не было
    available = [t for t in profile["topics"] if t not in used.get(channel_key, [])]
    if not available:
        print(f"⚠️ Все темы для {channel_key} использованы")
        return

    topic = available[0]
    print(f"📝 Публикация для {channel_key}: {topic}")

    try:
        post_text = await generate_post(topic, channel_key)
        image_url = await generate_image(topic, channel_key)

        # Отправляем фото + текст
        if len(post_text) <= 1024:
            await bot.send_photo(
                profile["telegram_channel"],
                image_url,
                caption=post_text,
            )
        else:
            await bot.send_photo(profile["telegram_channel"], image_url)
            await bot.send_message(profile["telegram_channel"], post_text)

        # Записываем тему в использованные
        used.setdefault(channel_key, []).append(topic)
        save_json("used_topics.json", used)
        print(f"✅ Опубликовано в {profile['telegram_channel']}")

    except Exception as e:
        print(f"❌ Ошибка публикации: {e}")


def start_scheduler(bot):
    # Для cyber — 10:00 и 19:00
    scheduler.add_job(
        publish_post, "cron", hour=10, minute=0,
        args=[bot, "cyber"], id="cyber_morning"
    )
    scheduler.add_job(
        publish_post, "cron", hour=19, minute=0,
        args=[bot, "cyber"], id="cyber_evening"
    )
    # Для ai — 11:00 и 20:00 (чтобы не совпадали)
    scheduler.add_job(
        publish_post, "cron", hour=11, minute=0,
        args=[bot, "ai"], id="ai_morning"
    )
    scheduler.add_job(
        publish_post, "cron", hour=20, minute=0,
        args=[bot, "ai"], id="ai_evening"
    )

    scheduler.start()
    print("✅ Планировщик запущен (4 поста в день)")
