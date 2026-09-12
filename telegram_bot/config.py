import os

# === Токены и ключи ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "8959872205:AAEYODqzyx_CG4PTGneoBCoBOVzMlVX2vRo")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
PROVOD_API_KEY = os.getenv("PROVOD_API_KEY", "sk_572d6f9c130ad10c5cfc7a6d48ab8421197328195c52278a")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "nsag1sPRpOnRupyvRMm6A5cZbZJgvuSfpX1DeFfFrOYksOq5XJMgpZSY")
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "sk_IO2JusirCuHRbVzBfZ6EEoDUkcjyRqU6")

# === Модель (с префиксом провайдера!) ===
GEMINI_MODEL = "google/gemini-3.5-flash"

# === Пути ===
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

VIDEO_PIPELINE_URL = os.getenv("VIDEO_PIPELINE_URL", "https://example.com")

# === Профили каналов ===
CHANNELS = {
    "cyber": {
        "name": "CyberGuardianSec",
        "telegram_channel": "@CyberGuardianSec",
        "topics": ["фишинг", "утечки данных", "VPN", "пароли", "кибератаки",
                   "социальная инженерия", "защита аккаунтов", "мошенничество"],
        "style": "экспертный, спокойный, с аналогиями из жизни, без паники",
        "prompt_prefix": "Ты — эксперт по кибербезопасности. Пиши понятно для обычных людей. Давай практические советы.",
        "schedule": ["10:00", "19:00"],
    },
    "ai": {
        "name": "AI Navigator",
        "telegram_channel": "@ainavigatorErgo",
        "topics": ["ChatGPT", "Midjourney", "нейросети для бизнеса",
                   "автоматизация", "AI-инструменты", "промпты", "GPT-агенты"],
        "style": "дружелюбный, практичный, с примерами и кейсами",
        "prompt_prefix": "Ты — эксперт по нейросетям и автоматизации. Пиши для предпринимателей и специалистов. Давай конкретные инструменты.",
        "schedule": ["10:00", "19:00"],
    },
}

# === Рубрики по дням недели (0=Пн, 6=Вс) ===
RUBRICS = {
    0: {
        "key": "threat",
        "name": "🔥 Угроза недели",
        "format": "post",
        "task": "Разбери свежую утечку, атаку или уязвимость. Объясни, кому угрожает и что делать.",
    },
    1: {
        "key": "tool",
        "name": "🛠️ Инструмент дня",
        "format": "post",
        "task": "Обзор одного инструмента (VPN, менеджер паролей, AI-сервис). Плюсы, минусы, для кого подходит.",
    },
    2: {
        "key": "scam",
        "name": "🎣 Разбор скама",
        "format": "poll",
        "task": "Разбери конкретную мошенническую схему. Покажи, как её распознать.",
    },
    3: {
        "key": "news",
        "name": "📰 Новость + комментарий",
        "format": "post",
        "task": "Возьми свежую новость из ниши. Дай экспертный комментарий и вывод.",
    },
    4: {
        "key": "checklist",
        "name": "✅ Чек-лист",
        "format": "post",
        "task": "Пошаговая инструкция из 5–7 пунктов. Конкретные действия.",
    },
    5: {
        "key": "myth",
        "name": "🧠 Миф vs Реальность",
        "format": "longread",
        "task": "Развенчай популярный миф. Объясни, почему это не так, и что на самом деле.",
    },
    6: {
        "key": "free",
        "name": "🎯 Свободная тема",
        "format": "post",
        "task": "Выбери самую актуальную и интересную тему недели. Свободный формат.",
    },
}

# === Расписание ===
DEFAULT_SCHEDULE = ["10:00", "19:00"]
TIMEZONE = "Europe/Moscow"
