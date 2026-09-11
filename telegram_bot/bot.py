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
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import threading

from config import BOT_TOKEN, CHANNELS
from generator import generate_post, generate_image
from scheduler import start_scheduler

# === Логирование ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Инициализация ===
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
app = Flask(__name__)


# === FSM состояния ===
class PostFlow(StatesGroup):
    entering_topic = State()
    approving = State()


# === Клавиатуры ===
def main_menu():
    """Главное inline-меню."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создать пост", callback_data="menu_create")],
        [
            InlineKeyboardButton(text="💡 Идеи тем", callback_data="menu_ideas"),
            InlineKeyboardButton(text="📊 Статус", callback_data="menu_status"),
        ],
        [InlineKeyboardButton(text="📢 Опубликовать вручную", callback_data="menu_manual")],
    ])
    return kb


def channels_inline():
    """Кнопки выбора канала."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔐 CyberGuardianSec", callback_data="ch_cyber"),
            InlineKeyboardButton(text="🤖 AI Navigator", callback_data="ch_ai"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_back")]
    ])
    return kb


def approve_inline():
    """Кнопки утверждения поста."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Опубликовать", callback_data="approve_publish"),
            InlineKeyboardButton(text="🔄 Перегенерировать", callback_data="approve_regen"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_back")]
    ])
    return kb


# === /start ===
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


# === МЕНЮ: СТАТУС ===
@dp.callback_query(F.data == "menu_status")
async def menu_status(callback: types.CallbackQuery):
    status = "✅ <b>Бот работает</b>\n\n"
    status += f"📅 Время: <code>{datetime.now().strftime('%H:%M:%S')}</code>\n"
    status += f"📢 Каналов: <b>{len(CHANNELS)}</b>\n\n"
    for key, ch in CHANNELS.items():
        emoji = "🔐" if key == "cyber" else "🤖"
        status += f"{emoji} <b>{ch['name']}</b>\n"
        status += f"   📍 {ch['telegram_channel']}\n"
        status += f"   📅 Постов в день: {len(ch['schedule'])}\n\n"
    await callback.message.edit_text(status, reply_markup=main_menu())
    await callback.answer()


# === МЕНЮ: ИДЕИ ===
@dp.callback_query(F.data == "menu_ideas")
async def menu_ideas(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Выбери канал, для которого нужны идеи:",
        reply_markup=channels_inline()
    )
    await callback.answer()


# === МЕНЮ: НАЗАД ===
@dp.callback_query(F.data == "menu_back")
async def menu_back(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "👋 Главное меню:",
        reply_markup=main_menu()
    )
    await callback.answer()


# === ВЫБОР КАНАЛА (для идей или создания поста) ===
@dp.callback_query(F.data.startswith("ch_"))
async def choose_channel(callback: types.CallbackQuery, state: FSMContext):
    channel_key = callback.data.replace("ch_", "")
    if channel_key not in CHANNELS:
        await callback.answer("Неизвестный канал")
        return

    profile = CHANNELS[channel_key]
    emoji = "🔐" if channel_key == "cyber" else "🤖"

    current_state = await state.get_state()

    if current_state == PostFlow.entering_topic.state:
        # Создание поста — переходим к вводу темы
        await state.update_data(channel_key=channel_key)
        await callback.message.edit_text(
            f"{emoji} Канал: <b>{profile['name']}</b>\n\n"
            f"✏️ Напиши тему поста.\n\n"
            f"<i>Примеры: {', '.join(profile['topics'][:3])}</i>"
        )
    else:
        # Просмотр идей
        ideas = "\n".join([f"• {t}" for t in profile["topics"][:10]])
        await callback.message.edit_text(
            f"{emoji} <b>Идеи для «{profile['name']}»:</b>\n\n{ideas}",
            reply_markup=main_menu()
        )
    await callback.answer()


# === МЕНЮ: СОЗДАТЬ ПОСТ ===
@dp.callback_query(F.data == "menu_create")
async def menu_create(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(PostFlow.entering_topic)
    await callback.message.edit_text(
        "Выбери канал для нового поста:",
        reply_markup=channels_inline()
    )
    await callback.answer()


# === ВВОД ТЕМЫ ===
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
        image_url = await generate_image(topic, channel_key)

        await state.update_data(topic=topic, post_text=post_text, image_url=image_url)
        await state.set_state(PostFlow.approving)

        if len(post_text) <= 1024:
            await message.answer_photo(
                image_url,
                caption=f"📄 <b>Превью поста:</b>\n\n{post_text}",
                reply_markup=approve_inline()
            )
        else:
            await message.answer_photo(image_url, caption="🖼️ Картинка к посту")
            await message.answer(
                f"📄 <b>Превью поста:</b>\n\n{post_text}",
                reply_markup=approve_inline()
            )
    except Exception as e:
        logger.error(f"Ошибка генерации: {e}")
        await message.answer(f"❌ Ошибка: {e}", reply_markup=main_menu())
        await state.clear()


# === УТВЕРЖДЕНИЕ: ОПУБЛИКОВАТЬ ===
@dp.callback_query(F.data == "approve_publish", PostFlow.approving)
async def approve_publish(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    channel_key = data.get("channel_key", "cyber")
    post_text = data.get("post_text", "")
    image_url = data.get("image_url", "")
    profile = CHANNELS[channel_key]

    try:
        if len(post_text) <= 1024 and image_url:
            await bot.send_photo(profile["telegram_channel"], image_url, caption=post_text)
        else:
            if image_url:
                await bot.send_photo(profile["telegram_channel"], image_url)
            await bot.send_message(profile["telegram_channel"], post_text)

        await callback.message.edit_caption(caption="✅ Опубликовано в канале!")
        await callback.message.answer(
            f"🎉 Пост опубликован в <b>{profile['name']}</b>",
            reply_markup=main_menu()
        )
    except Exception as e:
        logger.error(f"Ошибка публикации: {e}")
        await callback.message.answer(f"❌ Ошибка: {e}", reply_markup=main_menu())

    await state.clear()
    await callback.answer()


# === УТВЕРЖДЕНИЕ: ПЕРЕГЕНЕРИРОВАТЬ ===
@dp.callback_query(F.data == "approve_regen", PostFlow.approving)
async def approve_regen(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    topic = data.get("topic", "")
    channel_key = data.get("channel_key", "cyber")

    await callback.message.edit_caption(caption="🔄 Генерирую заново...")

    try:
        post_text = await generate_post(topic, channel_key)
        image_url = await generate_image(topic, channel_key)

        await state.update_data(post_text=post_text, image_url=image_url)

        await callback.message.delete()
        if len(post_text) <= 1024:
            await callback.message.answer_photo(
                image_url,
                caption=f"📄 <b>Новое превью:</b>\n\n{post_text}",
                reply_markup=approve_inline()
            )
        else:
            await callback.message.answer_photo(image_url, caption="🖼️ Картинка")
            await callback.message.answer(
                f"📄 <b>Новое превью:</b>\n\n{post_text}",
                reply_markup=approve_inline()
            )
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {e}", reply_markup=main_menu())
        await state.clear()

    await callback.answer()


# === МЕНЮ: ОПУБЛИКОВАТЬ ВРУЧНУЮ ===
@dp.callback_query(F.data == "menu_manual")
async def menu_manual(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Отправь текст в формате:\n\n"
        "<code>текст поста | канал</code>\n\n"
        "Пример:\n"
        "<code>Как защитить пароль | cyber</code>\n"
        "или\n"
        "<code>5 полезных промптов | ai</code>",
        reply_markup=main_menu()
    )
    await callback.answer()


# === РУЧНАЯ ПУБЛИКАЦИЯ ===
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


# === Команды для совместимости ===
@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    status = "✅ <b>Бот работает</b>\n\n"
    for key, ch in CHANNELS.items():
        emoji = "🔐" if key == "cyber" else "🤖"
        status += f"{emoji} <b>{ch['name']}</b> — {ch['telegram_channel']}\n"
    await message.answer(status, reply_markup=main_menu())


# === Flask для Render ===
@app.route("/")
def health():
    return "OK", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    update = types.Update.model_validate(request.json, context={"bot": bot})
    asyncio.run(dp.feed_update(bot, update))
    return "OK", 200


# === Запуск ===
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
