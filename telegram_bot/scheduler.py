import json
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.types import FSInputFile

from config import CHANNELS, DATA_DIR, RUBRICS
from generator import (
    generate_post, generate_image, generate_longread,
    generate_poll, is_topic_unique, load_used_topics, save_used_topics,
    generate_ideas
)
from analytics import collect_daily_stats, send_weekly_report, increment_post_count
from api_monitor import check_all_apis
from vk_publisher import publish_to_vk

scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


async def publish_rubric_post(bot, channel_key: str):
    profile = CHANNELS[channel_key]
    emoji = "🔐" if channel_key == "cyber" else "🤖"

    weekday = datetime.now().weekday()
    rubric = RUBRICS.get(weekday, RUBRICS[6])

    print(f"\n{emoji} === Публикация: {channel_key} | Рубрика: {rubric['name']} ===")

    used_data = load_used_topics()
    used_list = used_data.get(channel_key, [])
    available_topics = [t for t in profile["topics"] if t not in used_list]

    if not available_topics:
        print(f"⚠️ Темы закончились, генерирую новые через AI...")
        try:
            new_ideas = await generate_ideas(channel_key, count=15)
            available_topics = new_ideas
            print(f"✅ Получено {len(new_ideas)} новых тем")
        except Exception as e:
            print(f"❌ Не удалось получить новые темы: {e}")
            used_data[channel_key] = []
            save_used_topics(used_data)
            available_topics = profile["topics"]

    topic = None
    for candidate in available_topics[:5]:
        if await is_topic_unique(candidate, channel_key):
            topic = candidate
            break

    if not topic:
        topic = available_topics[0]

    print(f"📝 Тема: {topic}")

    try:
        fmt = rubric.get("format", "post")
        post_text = ""
        image_path = None

        if fmt == "poll":
            print("🗳️ Генерирую опрос (только Telegram)...")
            poll_data = await generate_poll(topic, channel_key)
            await bot.send_poll(
                chat_id=profile["telegram_channel"],
                question=f"{rubric['name']}: {poll_data['question']}",
                options=poll_data["options"],
                is_anonymous=True,
            )
            print(f"🎉 Опрос опубликован в Telegram")
            increment_post_count()

        elif fmt == "longread":
            print("📖 Генерирую лонгрид...")
            post_text = await generate_longread(topic, channel_key, rubric)
            if len(post_text) > 4096:
                post_text = post_text[:4090] + "..."
            await bot.send_message(profile["telegram_channel"], post_text)
            print(f"🎉 Лонгрид опубликован в Telegram")
            increment_post_count()

            print("📤 Публикую в VK...")
            await publish_to_vk(channel_key, post_text)

        else:
            print("⏳ Генерирую текст...")
            post_text = await generate_post(topic, channel_key, rubric)
            print(f"✅ Текст готов ({len(post_text)} символов)")

            print("🎨 Генерирую картинку...")
            image_path = await generate_image(topic, channel_key)

            tg_text = post_text[:1020] + "..." if len(post_text) > 1024 else post_text

            if image_path.startswith("http"):
                await bot.send_photo(profile["telegram_channel"], image_path, caption=tg_text)
            else:
                photo = FSInputFile(image_path)
                await bot.send_photo(profile["telegram_channel"], photo, caption=tg_text)
            print(f"🎉 Пост опубликован в Telegram")
            increment_post_count()

            print("📤 Публикую в VK...")
            await publish_to_vk(channel_key, post_text, image_path)

        used_data = load_used_topics()
        used_data.setdefault(channel_key, []).append(topic)
        save_used_topics(used_data)

    except Exception as e:
        print(f"❌ Ошибка публикации для {channel_key}: {e}\n")


def start_scheduler(bot):
    scheduler.add_job(publish_rubric_post, "cron", hour=10, minute=0,
                      args=[bot, "cyber"], id="cyber_morning")
    scheduler.add_job(publish_rubric_post, "cron", hour=19, minute=0,
                      args=[bot, "cyber"], id="cyber_evening")
    scheduler.add_job(publish_rubric_post, "cron", hour=11, minute=0,
                      args=[bot, "ai"], id="ai_morning")
    scheduler.add_job(publish_rubric_post, "cron", hour=20, minute=0,
                      args=[bot, "ai"], id="ai_evening")

    scheduler.add_job(collect_daily_stats, "cron", hour=23, minute=0,
                      args=[bot], id="daily_stats")

    scheduler.add_job(send_weekly_report, "cron", day_of_week="sun", hour=20, minute=0,
                      args=[bot], id="weekly_report")

    scheduler.add_job(check_all_apis, "interval", hours=1,
                      args=[bot], id="api_monitor")

    scheduler.start()
    print("✅ Планировщик запущен: cyber 10/19, ai 11/20 МСК (TG + VK)")
