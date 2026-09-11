import json
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.types import FSInputFile

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
    emoji = "🔐" if channel_key == "cyber" else "🤖"

    print(f"\n{emoji} === Публикация для канала: {channel_key} ({profile['name']}) ===")

    used = load_json("used_topics.json", {"cyber": [], "ai": []})
    available = [t for t in profile["topics"] if t not in used.get(channel_key, [])]
    if not available:
        print(f"⚠️ Все темы для {channel_key} использованы")
        return

    topic = available[0]
    print(f"📝 Тема: {topic}")

    try:
        print("⏳ Генерирую текст...")
        post_text = await generate_post(topic, channel_key)
        print(f"✅ Текст готов ({len(post_text)} символов)")

        print("🎨 Генерирую картинку...")
        image_path = await generate_image(topic, channel_key)
        print(f"✅ Картинка: {image_path}")

        # Отправляем фото с подписью (одно сообщение)
        # Если текст длиннее 1024 — обрезаем и отправляем отдельно
        if len(post_text) <= 1024:
            if image_path.startswith("http"):
                # Fallback: URL картинки
                await bot.send_photo(profile["telegram_channel"], image_path, caption=post_text)
            else:
                # Локальный файл
                photo = FSInputFile(image_path)
                await bot.send_photo(profile["telegram_channel"], photo, caption=post_text)
            print(f"🎉 Опубликовано в {profile['telegram_channel']}")
        else:
            # Если текст длиннее — отправляем фото и текст отдельно
            if image_path.startswith("http"):
                await bot.send_photo(profile["telegram_channel"], image_path)
            else:
                photo = FSInputFile(image_path)
                await bot.send_photo(profile["telegram_channel"], photo)
            await bot.send_message(profile["telegram_channel"], post_text)
            print(f"🎉 Опубликовано (фото + текст) в {profile['telegram_channel']}")

        used.setdefault(channel_key, []).append(topic)
        save_json("used_topics.json", used)

    except Exception as e:
        print(f"❌ Ошибка публикации для {channel_key}: {e}\n")


def start_scheduler(bot):
    scheduler.add_job(publish_post, "cron", hour=10, minute=0,
                      args=[bot, "cyber"], id="cyber_morning")
    scheduler.add_job(publish_post, "cron", hour=19, minute=0,
                      args=[bot, "cyber"], id="cyber_evening")
    scheduler.add_job(publish_post, "cron", hour=11, minute=0,
                      args=[bot, "ai"], id="ai_morning")
    scheduler.add_job(publish_post, "cron", hour=20, minute=0,
                      args=[bot, "ai"], id="ai_evening")

    scheduler.start()
    print("✅ Планировщик запущен: cyber 10/19, ai 11/20 МСК")
