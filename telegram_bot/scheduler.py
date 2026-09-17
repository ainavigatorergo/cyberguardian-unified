import asyncio
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.types import FSInputFile

from config import CHANNELS, RUBRICS_CYBER, RUBRICS_AI, TG_LINKS
from generator import (
    generate_post, generate_image, generate_longread, generate_poll,
    is_topic_unique, load_used_topics, save_used_topics, generate_ideas,
    generate_vk_version,
)
from analytics import collect_daily_stats, send_weekly_report, increment_post_count
from api_monitor import check_all_apis
from vk_publisher import publish_to_vk

scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


async def _publish_vk(channel_key, post_text, image_path, tg_message_id):
    """VK сразу после TG: короткая версия + карточка + ссылка на TG-пост."""
    try:
        print(f"\n⏳ [VK] Начинаю публикацию ({channel_key})...")

        print(f"📝 [VK] Генерирую VK-версию...")
        vk_text = await generate_vk_version(post_text, channel_key)
        print(f"✅ [VK] VK-версия: {len(vk_text)} символов")
        print(f"   Превью: {vk_text[:150]}...")

        # Карточка для VK
        if not image_path or not os.path.exists(image_path):
            print(f"🎨 [VK] Карточки нет, генерирую новую...")
            first_line = vk_text.split("\n")[0][:60] if vk_text else channel_key
            parsed_vk = {"title": first_line, "bullets": [], "intro": "",
                         "details": "", "bonus": "", "question": "", "hashtags": ""}
            image_path = await generate_image(parsed_vk, channel_key)
            print(f"🎨 [VK] Карточка для VK: {image_path}")
        else:
            print(f"📷 [VK] Использую карточку из TG: {image_path}")

        # Ссылка на пост TG — ставим ПЕРЕД хештегами
        tg_link_base = TG_LINKS.get(channel_key, "")
        if tg_link_base and tg_message_id:
            tg_link = f"{tg_link_base}/{tg_message_id}"
            vk_text = vk_text.rstrip() + f"\n\n👉 Продолжение: {tg_link}"
            print(f"🔗 [VK] Добавил ссылку: {tg_link}")

        # Хештеги — только отсутствующие, все в одну строку
        brand_tag = "#CyberGuardianSec" if channel_key == "cyber" else "#AINavigator"
        general = "#кибербезопасность" if channel_key == "cyber" else "#нейросети"

        tags_to_add = []
        vk_lower = vk_text.lower()
        if brand_tag.lower() not in vk_lower:
            tags_to_add.append(brand_tag)
        if general.lower() not in vk_lower:
            tags_to_add.append(general)

        if tags_to_add:
            vk_text = vk_text.rstrip() + f"\n\n{' '.join(tags_to_add)}"
            print(f"🏷 [VK] Добавил хештеги: {' '.join(tags_to_add)}")

        print(f"📤 [VK] Отправляю в VK (фото: {bool(image_path and os.path.exists(image_path))})...")
        result = await publish_to_vk(channel_key, vk_text, image_path)
        if result:
            print(f"✅ [VK] Успешно опубликовано ({channel_key})")
        else:
            print(f"⚠️ [VK] publish_to_vk вернул False")
    except Exception as e:
        print(f"❌ [VK] Ошибка: {e}")


async def publish_rubric_post(bot, channel_key: str):
    profile = CHANNELS[channel_key]
    emoji = "🔐" if channel_key == "cyber" else "🤖"
    weekday = datetime.now().weekday()
    rubrics = RUBRICS_CYBER if channel_key == "cyber" else RUBRICS_AI
    rubric = rubrics.get(weekday, rubrics[6])
    print(f"\n{emoji} === {channel_key} | {rubric['name']} ===")

    used_data = load_used_topics()
    used_list = used_data.get(channel_key, [])
    available = [t for t in profile["topics"] if t not in used_list]

    if not available:
        try:
            available = await generate_ideas(channel_key, count=15)
        except:
            used_data[channel_key] = []
            save_used_topics(used_data)
            available = profile["topics"]

    topic = None
    for cand in available[:5]:
        if await is_topic_unique(cand, channel_key):
            topic = cand
            break
    if not topic: topic = available[0]
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
            increment_post_count()

        elif fmt == "longread":
            post_text = await generate_longread(topic, channel_key, rubric)
            if len(post_text) > 4096:
                post_text = post_text[:4090] + "..."
            msg = await bot.send_message(profile["telegram_channel"], post_text)
            increment_post_count()
            await _publish_vk(channel_key, post_text, None, msg.message_id)

        else:
            post_text, parsed = await generate_post(topic, channel_key, rubric)
            print(f"✅ Текст: {len(post_text)} символов")

            print("🎨 Создаю карточку...")
            image_path = await generate_image(parsed, channel_key)
            print(f"🎨 Карточка: {image_path}")

            tg_message = None
            if len(post_text) <= 1024 and image_path and os.path.exists(image_path):
                photo = FSInputFile(image_path)
                tg_message = await bot.send_photo(profile["telegram_channel"], photo, caption=post_text)
            else:
                tg_message = await bot.send_message(profile["telegram_channel"], post_text)
            increment_post_count()

            await _publish_vk(channel_key, post_text, image_path, tg_message.message_id)

        used_data = load_used_topics()
        used_data.setdefault(channel_key, []).append(topic)
        save_used_topics(used_data)

    except Exception as e:
        print(f"❌ Ошибка: {e}\n")


def start_scheduler(bot):
    scheduler.add_job(publish_rubric_post, "cron", hour=10, minute=0, args=[bot, "cyber"], id="cyber_morning")
    scheduler.add_job(publish_rubric_post, "cron", hour=19, minute=0, args=[bot, "cyber"], id="cyber_evening")
    scheduler.add_job(publish_rubric_post, "cron", hour=11, minute=0, args=[bot, "ai"], id="ai_morning")
    scheduler.add_job(publish_rubric_post, "cron", hour=20, minute=0, args=[bot, "ai"], id="ai_evening")
    scheduler.add_job(collect_daily_stats, "cron", hour=23, minute=0, args=[bot], id="daily_stats")
    scheduler.add_job(send_weekly_report, "cron", day_of_week="sun", hour=20, minute=0, args=[bot], id="weekly_report")
    scheduler.add_job(check_all_apis, "interval", hours=1, args=[bot], id="api_monitor")
    scheduler.start()
    print("✅ Планировщик: cyber 10/19, ai 11/20 МСК")
