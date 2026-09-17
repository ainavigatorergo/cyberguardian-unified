import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, FSInputFile
)
from flask import Flask, request
import threading

from config import BOT_TOKEN, CHANNELS, TG_LINKS
from generator import (
    generate_post, generate_image, generate_ideas,
    generate_article_cover, generate_vk_version,
)
from scheduler import start_scheduler
from comment_assistant import send_daily_digest, save_admin_chat_id
from analytics import send_stats_now, increment_post_count
from api_monitor import get_api_status
from vk_publisher import publish_to_vk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
app = Flask(__name__)


class PostFlow(StatesGroup):
    entering_topic = State()
    approving = State()


class CoverFlow(StatesGroup):
    entering_title = State()
    choosing_channel = State()


def bottom_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🏠 Главное меню")]],
        resize_keyboard=True, is_persistent=True
    )


def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создать пост", callback_data="menu_create")],
        [InlineKeyboardButton(text="💡 Идеи тем", callback_data="menu_ideas"),
         InlineKeyboardButton(text="📊 Аналитика", callback_data="menu_analytics")],
        [InlineKeyboardButton(text="🔔 Дайджест", callback_data="menu_digest"),
         InlineKeyboardButton(text="🔍 Статус API", callback_data="menu_api")],
        [InlineKeyboardButton(text="🖼 Обложка для статьи", callback_data="menu_cover")],
        [InlineKeyboardButton(text="📢 Опубликовать вручную", callback_data="menu_manual")],
    ])


def channels_inline(action="ch"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 CyberGuardianSec", callback_data=f"{action}_cyber"),
         InlineKeyboardButton(text="🤖 AI Navigator", callback_data=f"{action}_ai")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_back")]
    ])


def ideas_inline(channel_key, ideas):
    buttons = []
    for i, idea in enumerate(ideas):
        buttons.append([InlineKeyboardButton(text=f"💡 {idea[:50]}", callback_data=f"useidea_{channel_key}_{i}")])
    buttons.append([InlineKeyboardButton(text="🔄 Ещё идеи", callback_data=f"moreideas_{channel_key}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def approve_inline():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ В TG + VK", callback_data="approve_publish"),
         InlineKeyboardButton(text="📱 Только TG", callback_data="approve_publish_tg")],
        [InlineKeyboardButton(text="🔄 Перегенерировать", callback_data="approve_regen"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_preview")],
    ])


async def _send_preview(chat_id, post_text, image_path, channel_key, reply_markup=None):
    if reply_markup is None:
        reply_markup = approve_inline()
    preview = post_text[:3900] + "..." if len(post_text) > 3900 else post_text
    if image_path and os.path.exists(image_path) and len(post_text) <= 1024:
        photo = FSInputFile(image_path)
        await bot.send_photo(chat_id, photo, caption=f"📄 <b>Превью:</b>\n\n{preview}", reply_markup=reply_markup)
    else:
        await bot.send_message(chat_id, f"📄 <b>Превью:</b>\n\n{preview}", reply_markup=reply_markup)


def _format_vk_post(vk_text, channel_key, tg_message_id):
    """Приводит VK-текст к формату: тело → ссылка → хештеги одной строкой."""
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


async def _publish_vk_now(channel_key, post_text, image_path, tg_message_id):
    """VK сразу после TG: короткая версия + карточка + ссылка на TG-пост."""
    print(f"\n{'='*50}")
    print(f"⏳ [VK] Публикация ({channel_key})")
    print(f"{'='*50}")
    try:
        print(f"📝 [VK] Генерирую VK-версию...")
        vk_text = await generate_vk_version(post_text, channel_key)
        print(f"✅ [VK] VK-версия: {len(vk_text)} символов")
        print(f"   Превью: {vk_text[:150]}...")

        if not image_path or not os.path.exists(image_path):
            print(f"🎨 [VK] Карточки нет, генерирую новую...")
            first_line = vk_text.split("\n")[0][:60] if vk_text else channel_key
            parsed_vk = {"title": first_line, "bullets": [], "intro": "",
                         "details": "", "bonus": "", "question": "", "hashtags": ""}
            image_path = await generate_image(parsed_vk, channel_key)
            print(f"🎨 [VK] Карточка для VK: {image_path}")
        else:
            print(f"📷 [VK] Использую карточку из TG: {image_path}")

        vk_text = _format_vk_post(vk_text, channel_key, tg_message_id)
        print(f"📋 [VK] Финальный текст ({len(vk_text)} символов):")
        print(f"---")
        print(vk_text)
        print(f"---")

        print(f"📤 [VK] Отправляю в VK (фото: {bool(image_path and os.path.exists(image_path))})...")
        result = await publish_to_vk(channel_key, vk_text, image_path)
        if result:
            print(f"✅ [VK] Успешно опубликовано ({channel_key})")
        else:
            print(f"⚠️ [VK] publish_to_vk вернул False")
    except Exception as e:
        print(f"❌ [VK] Ошибка: {e}")
        import traceback
        traceback.print_exc()


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    try:
        save_admin_chat_id(message.chat.id)
    except:
        pass
    await message.answer(
        "👋 Привет! Я бот для двух каналов:\n"
        "🔐 <b>CyberGuardianSec</b>\n🤖 <b>AI Navigator</b>\n\n"
        "Выбери действие 👇",
        reply_markup=bottom_menu()
    )
    await message.answer("Главное меню:", reply_markup=main_menu())


@dp.message(F.text == "🏠 Главное меню")
async def bottom_menu_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Главное меню:", reply_markup=main_menu())


@dp.callback_query(F.data == "menu_cover")
async def menu_cover(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(CoverFlow.entering_title)
    try:
        await callback.message.edit_text(
            "🖼 <b>Обложка для статьи</b>\n\n"
            "✏️ Напиши заголовок статьи.\n"
            "Найду фото на Pexels, добавлю заголовок и брендинг.\n\n"
            "<i>Пример: Промпт-инжиниринг: как получать от ChatGPT то, что нужно</i>"
        )
    except:
        await callback.message.delete()
        await callback.message.answer("✏️ Напиши заголовок статьи:")
    await callback.answer()


@dp.message(CoverFlow.entering_title)
async def handle_cover_title(message: types.Message, state: FSMContext):
    await state.update_data(cover_title=message.text.strip())
    await state.set_state(CoverFlow.choosing_channel)
    await message.answer("Выбери канал:", reply_markup=channels_inline("coverch"))


@dp.callback_query(F.data.startswith("coverch_"), CoverFlow.choosing_channel)
async def handle_cover_channel(callback: types.CallbackQuery, state: FSMContext):
    channel_key = callback.data.replace("coverch_", "")
    if channel_key not in CHANNELS:
        return
    data = await state.get_data()
    title = data.get("cover_title", "")
    emoji = "🔐" if channel_key == "cyber" else "🤖"
    await callback.answer()
    try:
        await callback.message.edit_text(f"{emoji} Генерирую обложку... ⏳")
    except:
        pass
    try:
        path = await generate_article_cover(title, channel_key)
        if path and os.path.exists(path):
            photo = FSInputFile(path)
            await callback.message.answer_photo(
                photo,
                caption=f"🖼 <b>Обложка готова</b>\n\nКанал: {CHANNELS[channel_key]['name']}\nЗаголовок: {title}\n\nСкачай и вставь в статью в Telegra.ph."
            )
        else:
            await callback.message.answer("❌ Не удалось создать обложку.")
    except Exception as e:
        await callback.message.answer(f"❌ {e}")
    await state.clear()


@dp.message(Command("digest"))
async def cmd_digest(message: types.Message):
    await message.answer("🔍 Ищу каналы...")
    try:
        r = await send_daily_digest(bot)
        await message.answer("✅ Отправлено" if r else "⚠️ Не удалось")
    except Exception as e:
        await message.answer(f"❌ {e}")


@dp.callback_query(F.data == "menu_digest")
async def menu_digest(callback: types.CallbackQuery):
    await callback.message.edit_text("🔍 Ищу каналы...")
    await callback.answer()
    try:
        r = await send_daily_digest(bot)
        await callback.message.answer("✅ Отправлено" if r else "⚠️ Не удалось")
    except Exception as e:
        await callback.message.answer(f"❌ {e}")


@dp.callback_query(F.data == "menu_analytics")
async def menu_analytics(callback: types.CallbackQuery):
    await callback.message.edit_text("📊 Собираю статистику...")
    await callback.answer()
    try:
        await send_stats_now(bot)
        await callback.message.answer("✅ Отправлено")
    except Exception as e:
        await callback.message.answer(f"❌ {e}")


@dp.callback_query(F.data == "menu_api")
async def menu_api(callback: types.CallbackQuery):
    await callback.message.edit_text("🔍 Проверяю API...")
    await callback.answer()
    try:
        await get_api_status(bot)
        await callback.message.answer("✅ Отправлено")
    except Exception as e:
        await callback.message.answer(f"❌ {e}")


@dp.callback_query(F.data == "menu_back")
async def menu_back(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        if callback.message.caption:
            await callback.message.delete()
            await callback.message.answer("👋 Главное меню:", reply_markup=main_menu())
        else:
            await callback.message.edit_text("👋 Главное меню:", reply_markup=main_menu())
    except:
        await callback.message.answer("👋 Главное меню:", reply_markup=main_menu())
    await callback.answer()


@dp.callback_query(F.data == "cancel_preview")
async def cancel_preview(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer("❌ Отменено.", reply_markup=main_menu())
    await callback.answer()


@dp.callback_query(F.data == "menu_ideas")
async def menu_ideas(callback: types.CallbackQuery):
    try:
        await callback.message.edit_text("Выбери канал:", reply_markup=channels_inline("idea"))
    except:
        await callback.message.delete()
        await callback.message.answer("Выбери канал:", reply_markup=channels_inline("idea"))
    await callback.answer()


@dp.callback_query(F.data.startswith("idea_"))
async def show_ideas(callback: types.CallbackQuery, state: FSMContext):
    channel_key = callback.data.replace("idea_", "")
    if channel_key not in CHANNELS:
        return
    emoji = "🔐" if channel_key == "cyber" else "🤖"
    try:
        await callback.message.edit_text(f"{emoji} Генерирую...")
    except:
        pass
    await callback.answer()
    try:
        ideas = await generate_ideas(channel_key, count=5)
        await state.update_data(ideas=ideas, idea_channel=channel_key)
        try:
            await callback.message.edit_text(f"{emoji} <b>Идеи:</b>", reply_markup=ideas_inline(channel_key, ideas))
        except:
            await callback.message.delete()
            await callback.message.answer(f"{emoji} <b>Идеи:</b>", reply_markup=ideas_inline(channel_key, ideas))
    except Exception as e:
        await callback.message.answer(f"❌ {e}", reply_markup=main_menu())


@dp.callback_query(F.data.startswith("moreideas_"))
async def more_ideas(callback: types.CallbackQuery, state: FSMContext):
    channel_key = callback.data.replace("moreideas_", "")
    emoji = "🔐" if channel_key == "cyber" else "🤖"
    try:
        await callback.message.edit_text(f"{emoji} Генерирую...")
    except:
        pass
    await callback.answer()
    try:
        ideas = await generate_ideas(channel_key, count=5)
        await state.update_data(ideas=ideas, idea_channel=channel_key)
        try:
            await callback.message.edit_text(f"{emoji} <b>Ещё:</b>", reply_markup=ideas_inline(channel_key, ideas))
        except:
            await callback.message.delete()
            await callback.message.answer(f"{emoji} <b>Ещё:</b>", reply_markup=ideas_inline(channel_key, ideas))
    except Exception as e:
        await callback.message.answer(f"❌ {e}", reply_markup=main_menu())


@dp.callback_query(F.data.startswith("useidea_"))
async def use_idea(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    channel_key, idx = parts[1], int(parts[2])
    data = await state.get_data()
    ideas = data.get("ideas", [])
    if idx >= len(ideas):
        return
    topic = ideas[idx]
    emoji = "🔐" if channel_key == "cyber" else "🤖"
    await state.update_data(channel_key=channel_key)
    await callback.answer()
    try:
        await callback.message.edit_text(f"{emoji} Генерирую: <i>{topic}</i>...")
    except:
        pass
    chat_id = callback.message.chat.id
    try:
        post_text, parsed = await generate_post(topic, channel_key)
        image_path = await generate_image(parsed, channel_key)
        await state.update_data(topic=topic, post_text=post_text, image_url=image_path, channel_key=channel_key)
        await state.set_state(PostFlow.approving)
        try:
            await callback.message.delete()
        except:
            pass
        await _send_preview(chat_id, post_text, image_path, channel_key)
    except Exception as e:
        await bot.send_message(chat_id, f"❌ {e}", reply_markup=main_menu())
        await state.clear()


@dp.callback_query(F.data == "menu_create")
async def menu_create(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(PostFlow.entering_topic)
    try:
        await callback.message.edit_text("Выбери канал:", reply_markup=channels_inline("ch"))
    except:
        await callback.message.delete()
        await callback.message.answer("Выбери канал:", reply_markup=channels_inline("ch"))
    await callback.answer()


@dp.callback_query(F.data.startswith("ch_"))
async def choose_channel(callback: types.CallbackQuery, state: FSMContext):
    channel_key = callback.data.replace("ch_", "")
    if channel_key not in CHANNELS:
        return
    profile = CHANNELS[channel_key]
    emoji = "🔐" if channel_key == "cyber" else "🤖"
    await state.update_data(channel_key=channel_key)
    await state.set_state(PostFlow.entering_topic)
    text = f"{emoji} Канал: <b>{profile['name']}</b>\n\n✏️ Напиши тему поста."
    try:
        await callback.message.edit_text(text)
    except:
        await callback.message.delete()
        await callback.message.answer(text)
    await callback.answer()


@dp.message(PostFlow.entering_topic)
async def handle_topic(message: types.Message, state: FSMContext):
    topic = message.text.strip()
    data = await state.get_data()
    channel_key = data.get("channel_key", "cyber")
    profile = CHANNELS[channel_key]
    emoji = "🔐" if channel_key == "cyber" else "🤖"
    await message.answer(f"⏳ Генерирую для {emoji} <b>{profile['name']}</b>...")
    try:
        post_text, parsed = await generate_post(topic, channel_key)
        image_path = await generate_image(parsed, channel_key)
        await state.update_data(topic=topic, post_text=post_text, image_url=image_path)
        await state.set_state(PostFlow.approving)
        await _send_preview(message.chat.id, post_text, image_path, channel_key)
    except Exception as e:
        await message.answer(f"❌ {e}", reply_markup=main_menu())
        await state.clear()


@dp.callback_query(F.data == "approve_publish", PostFlow.approving)
async def approve_publish(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    channel_key = data.get("channel_key", "cyber")
    post_text = data.get("post_text", "")
    image_path = data.get("image_url", "")
    profile = CHANNELS[channel_key]
    try:
        tg_message = None
        if image_path and os.path.exists(image_path) and len(post_text) <= 1024:
            photo = FSInputFile(image_path)
            tg_message = await bot.send_photo(profile["telegram_channel"], photo, caption=post_text)
        else:
            tg_message = await bot.send_message(profile["telegram_channel"], post_text)
        increment_post_count()
        try:
            await callback.message.delete()
        except:
            pass
        # VK синхронно — ждём результата
        await _publish_vk_now(channel_key, post_text, image_path, tg_message.message_id)
        await callback.message.answer(
            f"✅ Опубликовано в TG + VK ({profile['name']})",
            reply_markup=main_menu()
        )
    except Exception as e:
        await callback.message.answer(f"❌ {e}", reply_markup=main_menu())
    await state.clear()
    await callback.answer()


@dp.callback_query(F.data == "approve_publish_tg", PostFlow.approving)
async def approve_publish_tg(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    channel_key = data.get("channel_key", "cyber")
    post_text = data.get("post_text", "")
    image_path = data.get("image_url", "")
    profile = CHANNELS[channel_key]
    try:
        if image_path and os.path.exists(image_path) and len(post_text) <= 1024:
            photo = FSInputFile(image_path)
            await bot.send_photo(profile["telegram_channel"], photo, caption=post_text)
        else:
            await bot.send_message(profile["telegram_channel"], post_text)
        increment_post_count()
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(f"📱 TG ({profile['name']})", reply_markup=main_menu())
    except Exception as e:
        await callback.message.answer(f"❌ {e}", reply_markup=main_menu())
    await state.clear()
    await callback.answer()


@dp.callback_query(F.data == "approve_regen", PostFlow.approving)
async def approve_regen(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    topic = data.get("topic", "")
    channel_key = data.get("channel_key", "cyber")
    emoji = "🔐" if channel_key == "cyber" else "🤖"
    chat_id = callback.message.chat.id
    try:
        await callback.message.edit_caption(caption=f"{emoji} Генерирую заново...")
    except:
        try:
            await callback.message.edit_text(f"{emoji} Генерирую заново...")
        except:
            pass
    await callback.answer()
    try:
        post_text, parsed = await generate_post(topic, channel_key)
        image_path = await generate_image(parsed, channel_key)
        await state.update_data(post_text=post_text, image_url=image_path)
        try:
            await callback.message.delete()
        except:
            pass
        await _send_preview(chat_id, post_text, image_path, channel_key)
    except Exception as e:
        await bot.send_message(chat_id, f"❌ {e}", reply_markup=main_menu())
        await state.clear()


@dp.callback_query(F.data == "menu_manual")
async def menu_manual(callback: types.CallbackQuery):
    text = "Отправь: <code>текст | канал</code>\n\nПример: <code>Как защитить пароль | cyber</code>"
    try:
        await callback.message.edit_text(text, reply_markup=main_menu())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=main_menu())
    await callback.answer()


@dp.message(F.text.contains("|"))
async def handle_manual_post(message: types.Message):
    parts = [p.strip() for p in message.text.split("|", 1)]
    if len(parts) != 2:
        return
    text, channel_key = parts
    channel_key = channel_key.lower()
    if channel_key not in CHANNELS:
        return
    try:
        await bot.send_message(CHANNELS[channel_key]["telegram_channel"], text)
        increment_post_count()
        await message.answer("✅ Опубликовано", reply_markup=main_menu())
    except Exception as e:
        await message.answer(f"❌ {e}")


@app.route("/")
def health():
    return "OK", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    update = types.Update.model_validate(request.json, context={"bot": bot})
    asyncio.run(dp.feed_update(bot, update))
    return "OK", 200


def run_flask():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


async def main():
    logger.info("🚀 Бот запущен")
    start_scheduler(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
