import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
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


# === КОМАНДЫ ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    text = (
        "👋 Привет! Я бот для двух каналов:\n"
        "🔐 @CyberGuardianSec — кибербезопасность\n"
        "🤖 @ainavigatorErgo — нейросети и автоматизация\n\n"
        "Команды:\n"
        "/status — статус сервисов\n"
        "/generate [тема] [канал] — создать пост\n"
        "/post [текст] [канал] — опубликовать\n"
        "/ideas [канал] — предложить темы"
    )
    await message.answer(text)


@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    status = "✅ Бот работает\n"
    status += f"📅 Время: {datetime.now().strftime('%H:%M:%S')}\n"
    status += f"📢 Каналов: {len(CHANNELS)}\n"
    for key, ch in CHANNELS.items():
        status += f"  • {ch['name']} ({ch['telegram_channel']})\n"
    await message.answer(status)


@dp.message(Command("generate"))
async def cmd_generate(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Использование: /generate [тема] [канал]\nКаналы: cyber, ai")
        return

    topic = args[1]
    channel_key = args[2].lower()

    if channel_key not in CHANNELS:
        await message.answer(f"❌ Неизвестный канал: {channel_key}. Доступны: {', '.join(CHANNELS.keys())}")
        return

    await message.answer(f"⏳ Генерирую пост для «{CHANNELS[channel_key]['name']}» на тему: {topic}...")

    try:
        post_text = await generate_post(topic, channel_key)
        image_url = await generate_image(topic)

        await message.answer(f"✅ Пост готов:\n\n{post_text}")
        if image_url:
            await message.answer_photo(image_url, caption="🖼️ Картинка к посту")
    except Exception as e:
        logger.error(f"Ошибка генерации: {e}")
        await message.answer(f"❌ Ошибка: {e}")


@dp.message(Command("post"))
async def cmd_post(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Использование: /post [текст] [канал]")
        return

    text = args[1]
    channel_key = args[2].lower()

    if channel_key not in CHANNELS:
        await message.answer(f"❌ Неизвестный канал: {channel_key}")
        return

    channel_id = CHANNELS[channel_key]["telegram_channel"]
    try:
        await bot.send_message(channel_id, text)
        await message.answer(f"✅ Опубликовано в {channel_id}")
    except Exception as e:
        logger.error(f"Ошибка публикации: {e}")
        await message.answer(f"❌ Ошибка: {e}")


@dp.message(Command("ideas"))
async def cmd_ideas(message: types.Message):
    args = message.text.split(maxsplit=1)
    channel_key = args[1].lower() if len(args) > 1 else "cyber"

    if channel_key not in CHANNELS:
        await message.answer(f"❌ Неизвестный канал: {channel_key}")
        return

    topics = CHANNELS[channel_key]["topics"]
    ideas = "\n".join([f"• {t}" for t in topics[:5]])
    await message.answer(f"💡 Идеи для «{CHANNELS[channel_key]['name']}»:\n\n{ideas}")


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
