import os

# === Токены и ключи ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "8959872205:AAEYODqzyx_CG4PTGneoBCoBOVzMlVX2vRo")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
PROVOD_API_KEY = os.getenv("PROVOD_API_KEY", "sk_572d6f9c130ad10c5cfc7a6d48ab8421197328195c52278a")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "nsag1sPRpOnRupyvRMm6A5cZbZJgvuSfpX1DeFfFrOYksOq5XJMgpZSY")

# === Пути ===
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# === URL видео-конвейера на Hugging Face ===
VIDEO_PIPELINE_URL = os.getenv("VIDEO_PIPELINE_URL", "https://твой-аккаунт-cyberguardian-studio.hf.space")

# === Профили каналов ===
CHANNELS = {
    "cyber": {
        "name": "CyberGuardianSec",
        "telegram_channel": "@CyberGuardianSec",
        "telegram_chat_id": None,
        "topics": ["фишинг", "утечки данных", "VPN", "пароли", "кибератаки",
                   "социальная инженерия", "защита аккаунтов", "мошенничество"],
        "style": "экспертный, спокойный, с аналогиями из жизни, без паники",
        "prompt_prefix": "Ты — эксперт по кибербезопасности. Пиши понятно для обычных людей. Давай практические советы.",
        "schedule": ["10:00", "19:00"],
    },
    "ai": {
        "name": "AI Navigator",
        "telegram_channel": "@ainavigatorErgo",
        "telegram_chat_id": None,
        "topics": ["ChatGPT", "Midjourney", "нейросети для бизнеса",
                   "автоматизация", "AI-инструменты", "промпты", "GPT-агенты"],
        "style": "дружелюбный, практичный, с примерами и кейсами",
        "prompt_prefix": "Ты — эксперт по нейросетям и автоматизации. Пиши для предпринимателей и специалистов. Давай конкретные инструменты.",
        "schedule": ["10:00", "19:00"],
    },
}

# === Расписание ===
DEFAULT_SCHEDULE = ["10:00", "19:00"]
TIMEZONE = "Europe/Moscow"
