import asyncio
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.types import FSInputFile

from config import CHANNELS, RUBRICS_CYBER, RUBRICS_AI, TG_LINKS
from generator import (
    generate_post, generate_image, generate_longread, generate_poll,
    is_topic_unique, load_used_topics, save_used_topics, generate_ideas,
    generate_vk_version, generate_meme,
)
from analytics import collect_daily_stats, send_weekly_report, increment_post_count
from api_monitor import check_all_apis
from vk_publisher import publish_to_vk
from comment_assistant import get_admin_chat_id

scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


def _format_vk_post(vk_text, channel_key, tg_message_id):
    lines = vk_text.rstrip().split("\n")
    body_lines = []
    existing_tags = []
    for line in lines:
        stripped = line.strip()
        if stripped and all(w.startswith("#") for w in stripped.split() if w):
            existing_tags.extend(stripped.split())
        else:
            body_lines.append(line)

    brand_tag = "#CyberGuardianSec" if channel_key == "cyber" else "#AINavigator"
    general = "#кибербезопасность" if channel_key == "cyber" else "#нейросети"

    tags_all = existing_tags[:]
    existing_lower = [t.lower() for t in tags_all]
    if brand_tag.lower() not in existing_lower:
        tags_all.append(brand_tag)
    if general.lower() not in existing_lower:
        tags_all.append(general)

    seen, unique = set(), []
    for t in tags_all:
        tl = t.lower()
        if tl not in seen:
            seen.add(tl)
            unique.append(t)

    body = "\n".join(body_lines).strip()
    tg_link_base = TG_LINKS.get(channel_key, "")
    if tg_link_base and tg_message_id:
        body = body.rstrip() + f"\n\n👉 Продолжение: {tg_link_base}/{tg_message_id}"

    return body + "\n\n" + " ".join(unique)


async def _send_card_to_admin(bot, image_path, channel_key):
    if not image_path or not os.path.exists(image_path):
        return
    admin_id = get_admin_chat_id()
    if not admin_id:
        return
    try:
        photo = FSInputFile(image_path)
        channel_name = "CyberGuardianSec" if channel_key == "cyber" else "AI Navigator"
        await bot.send_photo(
            admin_id, photo,
            caption=f"🖼 <b>Карточка для VK</b> ({channel_name})\n\nСкачай и вставь в VK-пост вручную."
        )
        print(f"✅ [Admin] Карточка отправлена ({channel_key})")
    except Exception as e:
        print(f"⚠️ [Admin] {e}")


async def _publish_vk(bot, channel_key, post_text, image_path, tg_message_id):
    print(f"\n⏳ [VK] Публикация ({channel_key})...")
    try:
        vk_text = await generate_vk_version(post_text, channel_key)
        vk_text = _format_vk_post(vk_text, channel_key, tg_message_id)

        result = await publish_to_vk(channel_key, vk_text, None)
        if result:
            print(f"✅ [VK] Опубликовано ({channel_key})")
        else:
            print(f"⚠️ [VK] publish_to_vk вернул False")

        if image_path and os.path.exists(image_path):
            await _send_card_to_admin(bot, image_path, channel_key)
    except Exception as e:
        print(f"❌ [VK] Ошибка: {e}")


async def publish_rubric_post(bot, channel_key: str, is_series=False):
    profile = CHANNELS[channel_key]
    emoji = "🔐" if channel_key == "cyber" else "🤖"
    weekday = datetime.now().weekday()
    rubrics = RUBRICS_CYBER if channel_key == "cyber" else RUBRICS_AI
    rubric = rubrics.get(weekday, rubrics[6])
    print(f"\n{emoji} === {channel_key} | {rubric['name']} === {'(серия)' if is_series else ''}")

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

        # МЕМ
        if fmt == "meme":
            post_text = await generate_meme(topic, channel_key)
            parsed = {"title": "Мем дня", "intro": post_text[:200], "details": "", "bullets": [], "bonus": "", "question": "", "hashtags": "#мем", "numbers": []}
            image_path = await generate_image(parsed, channel_key, rubric)
            tg_message = await bot.send_photo(profile["telegram_channel"], FSInputFile(image_path), caption=post_text)
            increment_post_count()
            await _publish_vk(bot, channel_key, post_text, image_path, tg_message.message_id)

        elif fmt == "poll":
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
            await _publish_vk(bot, channel_key, post_text, None, msg.message_id)

        else:
            post_text, parsed = await generate_post(topic, channel_key, rubric, is_series=is_series)
            print(f"✅ Текст: {len(post_text)} символов")

            image_path = await generate_image(parsed, channel_key, rubric)
            print(f"🎨 Карточка: {image_path}")

            tg_message = None
            if len(post_text) <= 1024 and image_path and os.path.exists(image_path):
                tg_message = await bot.send_photo(profile["telegram_channel"], FSInputFile(image_path), caption=post_text)
            else:
                tg_message = await bot.send_message(profile["telegram_channel"], post_text)
            increment_post_count()

            await _publish_vk(bot, channel_key, post_text, image_path, tg_message.message_id)

        used_data = load_used_topics()
        used_data.setdefault(channel_key, []).append(topic)
        save_used_topics(used_data)

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


def start_scheduler(bot):
    # Cyber: 09:30 и 19:00 (вторник вечер — серия)
    scheduler.add_job(publish_rubric_post, "cron", hour=9, minute=30, args=[bot, "cyber", False], id="cyber_morning")
    scheduler.add_job(publish_rubric_post, "cron", hour=19, minute=0, args=[bot, "cyber", False], id="cyber_evening")
    # Cyber: серия — вторник 19:00
    scheduler.add_job(publish_rubric_post, "cron", day_of_week="tue", hour=19, minute=0, args=[bot, "cyber", True], id="cyber_series")

    # AI: 11:00 и 20:00 (вторник вечер — серия)
    scheduler.add_job(publish_rubric_post, "cron", hour=11, minute=0, args=[bot, "ai", False], id="ai_morning")
    scheduler.add_job(publish_rubric_post, "cron", hour=20, minute=0, args=[bot, "ai", False], id="ai_evening")
    scheduler.add_job(publish_rubric_post, "cron", day_of_week="tue", hour=20, minute=0, args=[bot, "ai", True], id="ai_series")

    # Мем дня: среда 14:00 (meme включён в RUBRICS для среды)
    scheduler.add_job(publish_rubric_post, "cron", day_of_week="wed", hour=14, minute=0, args=[bot, "cyber", False], id="cyber_meme")
    scheduler.add_job(publish_rubric_post, "cron", day_of_week="wed", hour=14, minute=0, args=[bot, "ai", False], id="ai_meme")

    scheduler.add_job(collect_daily_stats, "cron", hour=23, minute=0, args=[bot], id="daily_stats")
    scheduler.add_job(send_weekly_report, "cron", day_of_week="sun", hour=20, minute=0, args=[bot], id="weekly_report")
    scheduler.add_job(check_all_apis, "interval", hours=1, args=[bot], id="api_monitor")
    scheduler.start()
    print("✅ Планировщик запущен:")
    print("   Cyber: 09:30, 19:00 (вт — серия)")
    print("   AI: 11:00, 20:00 (вт — серия)")
    print("   Мем: среда 14:00 (оба канала)")
