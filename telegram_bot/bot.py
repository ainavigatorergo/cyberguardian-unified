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
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from flask import Flask, request
import threading

from config import BOT_TOKEN, CHANNELS
from generator import generate_post, generate_image, generate_ideas
from scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
app = Flask(__name__)


class PostFlow(StatesGroup):
    entering_topic = State()
    approving = State()


def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создать пост", callback_data="menu_create")],
        [
            InlineKeyboardButton(text="💡 Идеи тем", callback_data="menu_ideas"),
            InlineKeyboardButton(text="📊 Статус", callback_data="menu_status"),
        ],
        [InlineKeyboardButton(text="📢 Опубликовать вручную", callback_data="menu_manual")],
    ])


def channels_inline(action="ch"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔐 CyberGuardianSec", callback_data=f"{action}_cyber"),
            InlineKeyboardButton(text="🤖 AI Navigator", callback_data=f"{action}_ai"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_back")]
    ])


def ideas_inline(channel_key, ideas):
    buttons = []
    for i, idea in enumerate(ideas):
        buttons.append([InlineKeyboardButton(
            text=f"💡 {idea[:50]}",
            callback_data=f"useidea_{channel_key}_{i}"
        )])
    buttons.append([InlineKeyboardButton(text="🔄 Ещё идеи", callback_data=f"moreideas_{channel_key}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def approve_inline():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Опубликовать", callback_data="approve_publish"),
            InlineKeyboardButton(text="🔄 Перегенерировать", callback_data="approve_regen"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_back")]
    ])


async def _send_preview(message_or_callback, post_text, image_path, channel_key):
    """Отправляет превью с фото и подписью."""
    if len(post_text) > 1024:
        post_text = post_text[:1020] + "..."

    if image_path.startswith("http"):
        await message_or_callback.answer_photo(
            image_path,
            caption=f"📄 <b>Превью:</b>\n\n{post_text}",
            reply_markup=approve_inline()
        )
    else:
        photo = FSInputFile(image_path)
        await message_or_callback.answer_photo(
            photo,
            caption=f"📄 <b>Превью:</b>\n\n{post_text}",
            reply_markup=approve_inline()
        )


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Привет! Я бот для двух каналов:\n"
        "🔐 <b>CyberGuardianSec</b> — кибербезопасность\n"
        "🤖 <b>AI Navigator</b> — нейросети и автоматизация\n\n"
        "Выбери действие 👇",
        reply_markup=main_menu()
    )


@dp.callback_query(F.data == "menu_status")
async def menu_status(callback: types.CallbackQuery):
    status = "✅ <b>Бот работает</b>\n\n"
    status += f"📅 Время: <code>{datetime.now().strftime('%H:%M:%S')}</code>\n\n"
    for key, ch in CHANNELS.items():
        emoji = "🔐" if key == "cyber" else "🤖"
        status += f"{emoji} <b>{ch['name']}</b>\n   📍 {ch['telegram_channel']}\n\n"
    await callback.message.edit_text(status, reply_markup=main_menu())
    await callback.answer()


@dp.callback_query(F.data == "menu_back")
async def menu_back(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("👋 Главное меню:", reply_markup=main_menu())
    await callback.answer()


@dp.callback_query(F.data == "menu_ideas")
async def menu_ideas(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Выбери канал — я сгенерирую свежие идеи:",
        reply_markup=channels_inline("idea")
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("idea_"))
async def show_ideas(callback: types.CallbackQuery, state: FSMContext):
    channel_key = callback.data.replace("idea_", "")
    if channel_key not in CHANNELS:
        await callback.answer("Неизвестный канал")
        return

    emoji = "🔐" if channel_key == "cyber" else "🤖"
    await callback.message.edit_text(f"{emoji} Генерирую свежие идеи через AI... ⏳")
    await callback.answer()

    try:
        ideas = await generate_ideas(channel_key, count=5)
        await state.update_data(ideas=ideas, idea_channel=channel_key)
        text = f"{emoji} <b>Свежие идеи для «{CHANNELS[channel_key]['name']}»:</b>\n\nНажми на идею:"
        await callback.message.edit_text(text, reply_markup=ideas_inline(channel_key, ideas))
    except Exception as e:
        logger.error(f"Ошибка генерации идей: {e}")
        await callback.message.edit_text(f"❌ Ошибка: {e}", reply_markup=main_menu())


@dp.callback_query(F.data.startswith("moreideas_"))
async def more_ideas(callback: types.CallbackQuery, state: FSMContext):
    channel_key = callback.data.replace("moreideas_", "")
    emoji = "🔐" if channel_key == "cyber" else "🤖"
    await callback.message.edit_text(f"{emoji} Генерирую ещё идеи... ⏳")
    await callback.answer()

    try:
        ideas = await generate_ideas(channel_key, count=5)
        await state.update_data(ideas=ideas, idea_channel=channel_key)
        text = f"{emoji} <b>Ещё идеи для «{CHANNELS[channel_key]['name']}»:</b>\n\nНажми на идею:"
        await callback.message.edit_text(text, reply_markup=ideas_inline(channel_key, ideas))
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {e}", reply_markup=main_menu())


@dp.callback_query(F.data.startswith("useidea_"))
async def use_idea(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    channel_key = parts[1]
    idx = int(parts[2])

    data = await state.get_data()
    ideas = data.get("ideas", [])

    if idx >= len(ideas):
        await callback.answer("Идея не найдена")
        return

    topic = ideas[idx]
    emoji = "🔐" if channel_key == "cyber" else "🤖"
    profile = CHANNELS[channel_key]

    await callback.message.edit_text(f"{emoji} Генерирую пост на тему: <i>{topic}</i>... ⏳")
    await callback.answer()

    try:
        post_text = await generate_post(topic, channel_key)
        image_path = await generate_image(topic, channel_key)

        await state.update_data(
            topic=topic, post_text=post_text,
            image_url=image_path, channel_key=channel_key
        )
        await state.set_state(PostFlow.approving)

        await callback.message.delete()
        await _send_preview(callback.message, post_text, image_path, channel_key)
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {e}", reply_markup=main_menu())
        await state.clear()


@dp.callback_query(F.data == "menu_create")
async def menu_create(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(PostFlow.entering_topic)
    await callback.message.edit_text(
        "Выбери канал для нового поста:",
        reply_markup=channels_inline("ch")
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("ch_"))
async def choose_channel(callback: types.CallbackQuery, state: FSMContext):
    channel_key = callback.data.replace("ch_", "")
    if channel_key not in CHANNELS:
        await callback.answer("Неизвестный канал")
        return

    profile = CHANNELS[channel_key]
    emoji = "🔐" if channel_key == "cyber" else "🤖"

    await state.update_data(channel_key=channel_key)
    await state.set_state(PostFlow.entering_topic)
    await callback.message.edit_text(
        f"{emoji} Канал: <b>{profile['name']}</b>\n\n"
        f"✏️ Напиши тему поста.\n\n"
        f"<i>Примеры: {', '.join(profile['topics'][:3])}</i>"
    )
    await callback.answer()


@dp.message(PostFlow.entering_topic)
async def handle_topic(message: types.Message, state: FSMContext):
    topic = message.text.strip()
    data = await state.get_data()
    channel_key = data.get("channel_key", "cyber")
    profile = CHANNELS[channel_key]
    emoji = "🔐" if channel_key == "cyber" else "🤖"

    await message.answer(f"⏳ Генерирую пост для {emoji} <b>{profile['name']}</b>...")

    try:
        post_text = await generate_post(topic, channel_key)
        image_path = await generate_image(topic, channel_key)

        await state.update_data(topic=topic, post_text=post_text, image_url=image_path)
        await state.set_state(PostFlow.approving)

        await _send_preview(message, post_text, image_path, channel_key)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer(f"❌ Ошибка: {e}", reply_markup=main_menu())
        await state.clear()


@dp.callback_query(F.data == "approve_publish", PostFlow.approving)
async def approve_publish(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    channel_key = data.get("channel_key", "cyber")
    post_text = data.get("post_text", "")
    image_path = data.get("image_url", "")
    profile = CHANNELS[channel_key]

    try:
        # Обрезаем текст до 1024 символов
        if len(post_text) > 1024:
            post_text = post_text[:1020] + "..."

        if image_path.startswith("http"):
            await bot.send_photo(profile["telegram_channel"], image_path, caption=post_text)
        else:
            photo = FSInputFile(image_path)
            await bot.send_photo(profile["telegram_channel"], photo, caption=post_text)

        try:
            if callback.message.caption:
                await callback.message.edit_caption(caption="✅ Опубликовано!", reply_markup=None)
            else:
                await callback.message.edit_text(text="✅ Опубликовано!", reply_markup=None)
        except:
            pass

        await callback.message.answer(
            f"🎉 Пост опубликован в <b>{profile['name']}</b>",
            reply_markup=main_menu()
        )
    except Exception as e:
        logger.error(f"Ошибка публикации: {e}")
        await callback.message.answer(f"❌ Ошибка: {e}", reply_markup=main_menu())

    await state.clear()
    await callback.answer()


@dp.callback_query(F.data == "approve_regen", PostFlow.approving)
async def approve_regen(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    topic = data.get("topic", "")
    channel_key = data.get("channel_key", "cyber")

    await callback.message.edit_caption(caption="🔄 Генерирую заново... ⏳")

    try:
        post_text = await generate_post(topic, channel_key)
        image_path = await generate_image(topic, channel_key)
        await state.update_data(post_text=post_text, image_url=image_path)

        await callback.message.delete()
        await _send_preview(callback.message, post_text, image_path, channel_key)
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {e}", reply_markup=main_menu())
        await state.clear()

    await callback.answer()


@dp.callback_query(F.data == "menu_manual")
async def menu_manual(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Отправь текст в формате:\n\n"
        "<code>текст поста | канал</code>\n\n"
        "Пример: <code>Как защитить пароль | cyber</code>",
        reply_markup=main_menu()
    )
    await callback.answer()


@dp.message(F.text.contains("|"))
async def handle_manual_post(message: types.Message):
    parts = [p.strip() for p in message.text.split("|", 1)]
    if len(parts) != 2:
        await message.answer("❌ Неверный формат. Используй: текст | канал")
        return

    text, channel_key = parts
    channel_key = channel_key.lower()

    if channel_key not in CHANNELS:
        await message.answer(f"❌ Неизвестный канал: {channel_key}")
        return

    try:
        await bot.send_message(CHANNELS[channel_key]["telegram_channel"], text)
        await message.answer(
            f"✅ Опубликовано в <b>{CHANNELS[channel_key]['name']}</b>",
            reply_markup=main_menu()
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


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
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    asyncio.run(main())
