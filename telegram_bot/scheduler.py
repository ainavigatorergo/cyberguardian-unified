import json
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.types import FSInputFile

from config import CHANNELS, DATA_DIR, RUBRICS_CYBER, RUBRICS_AI
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

    # === РАЗНЫЕ РУБРИКИ ДЛЯ КАЖДОГО КАНАЛА ===
    if channel_key == "cyber":
        rubric = RUBRICS_CYBER.get(weekday, RUBRICS_CYBER[6])
    else:
        rubric = RUBRICS_AI.get(weekday, RUBRICS_AI[6])

    print(f"\n{emoji} === Публикация: {channel_key} | {rubric['name']} ===")

    used_data = load_used_topics()
    used_list = used_data.get(channel_key, [])
    available_topics = [t for t in profile["topics"] if t not in used_list]

    if not available_topics:
        print(f"⚠️ Темы закончились, генерирую новые...")
        try:
            available_topics = await generate_ideas(channel_key, count=15)
        except Exception as e:
            print(f"❌ {e}")
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

        if fmt == "poll":
            poll_data = await generate_poll(topic, channel_key)
            await bot.send_poll(
                chat_id=profile["telegram_channel"],
                question=f"{rubric['name']}: {poll_data['question']}",
                options=poll_data["options"],
                is_anonymous=True,
            )
            print(f"🎉 Опрос опубликован")
            increment_post_count()

        elif fmt == "longread":
            post_text = await generate_longread(topic, channel_key, rubric)
            if len(post_text) > 4096:
                post_text = post_text[:4090] + "..."
            await bot.send_message(profile["telegram_channel"], post_text)
            print(f"🎉 Лонгрид опубликован (без фото)")
            increment_post_count()
            print("📤 Публикую в VK...")
            await publish_to_vk(channel_key, post_text)

        else:
            print("⏳ Генерирую пост...")
            post_text, parsed = await generate_post(topic, channel_key, rubric)
            print(f"✅ Текст готов ({len(post_text)} символов)")

            # Логика: длинный → без фото, короткий → с фото
            image_path = None
            if len(post_text) <= 1024:
                print(f"🎨 Текст короткий ({len(post_text)}) — создаю карточку")
                image_path = await generate_image(parsed, channel_key)
                if image_path and os.path.exists(image_path):
                    photo = FSInputFile(image_path)
                    await bot.send_photo(profile["telegram_channel"], photo, caption=post_text)
                else:
                    await bot.send_message(profile["telegram_channel"], post_text)
            else:
                print(f"📝 Текст длинный ({len(post_text)}) — публикую без фото")
                await bot.send_message(profile["telegram_channel"], post_text)

            print(f"🎉 Пост опубликован в Telegram")
            increment_post_count()

            print("📤 Публикую в VK...")
            await publish_to_vk(channel_key, post_text, image_path)

        used_data = load_used_topics()
        used_data.setdefault(channel_key, []).append(topic)
        save_used_topics(used_data)

    except Exception as e:
        print(f"❌ Ошибка публикации: {e}\n")


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
    print("✅ Планировщик запущен")
    print("   cyber: 10/19 МСК, ai: 11/20 МСК")
    print("   статистика: 23:00, отчёт: вс 20:00, мониторинг: каждый час")
