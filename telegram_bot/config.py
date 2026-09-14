import os

# === Токены и ключи ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "8959872205:AAEYODqzyx_CG4PTGneoBCoBOVzMlVX2vRo")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
PROVOD_API_KEY = os.getenv("PROVOD_API_KEY", "sk_572d6f9c130ad10c5cfc7a6d48ab8421197328195c52278a")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "nsag1sPRpOnRupyvRMm6A5cZbZJgvuSfpX1DeFfFrOYksOq5XJMgpZSY")
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "sk_IO2JusirCuHRbVzBfZ6EEoDUkcjyRqU6")

# === VK токены и ID групп ===
VK_TOKENS = {
    "cyber": os.getenv("VK_TOKEN_CYBER", "vk1.a.kPjS4OrhX2Vt5yMKw49l-p3l3bmE6uQoyPiDF4XpeTGstsUUNA3GY22YShf5evspiZGOddAtDCk5QSzCxFZc1UUfZxtdIl__Y5sYnZwJfZncsa8ybMmhf_eE-LWynH2mHhYh6RTD08P0FJpbIFcSlccQ3Mgs7-hyo-hUKHXDV2xOKezxEeXTwd8Lhv2tvyOhwEHWlQYJWAWw7YfQXL9Xpw"),
    "ai": os.getenv("VK_TOKEN_AI", "vk1.a.5oc-ybsZqzZ7A0GZOL8ihsDvhbJxd_AGuADu44PWMD_AsdWLf_0962b6_GRt4PvqW9Jo39uwznFV67pNYTK81tUSNKTNN_nexsWcjmjQ3MVEEFJCV-cHHGtoYNfFWrKLtwzLJs7zKy0673K7w4Iakvfiad_r-zeN8kcEQdQJ5HMXwqnMaclebSu40HfTfygHbt9NJIZh7lQMpIw2FxBy1A"),
}

VK_GROUP_IDS = {
    "cyber": int(os.getenv("VK_GROUP_CYBER", "241288592")),
    "ai": int(os.getenv("VK_GROUP_AI", "241416521")),
}

# === Модель ===
GEMINI_MODEL = "gemini-3.5-flash"

# === Пути ===
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

VIDEO_PIPELINE_URL = os.getenv("VIDEO_PIPELINE_URL", "https://example.com")

# === Профили каналов ===
CHANNELS = {
    "cyber": {
        "name": "CyberGuardianSec",
        "telegram_channel": "@CyberGuardianSec",
        "vk_group": "cyberguardiansec",
        "topics": [
            "фишинг", "утечки данных", "VPN", "пароли", "кибератаки",
            "социальная инженерия", "защита аккаунтов", "мошенничество",
            "двухфакторная аутентификация", "менеджеры паролей", "фишинговые письма",
            "взлом email", "защита смартфона", "безопасность Wi-Fi",
            "мошенники в Telegram", "поддельные сайты", "криптомошенничество",
            "защита детей в интернете", "утечка паролей", "вредоносное ПО",
            "программы-вымогатели", "DDoS-атаки", "уязвимости в приложениях",
            "безопасные платежи онлайн", "защита банковских карт", "фишинг в соцсетях",
            "поддельные приложения", "шпионское ПО", "защита данных на телефоне",
            "утечки через приложения", "взлом социальных сетей", "безопасность в мессенджерах",
            "защита от слежки", "приватность в интернете", "пароли для детей",
            "резервное копирование данных", "защита от спама", "онлайн-шопинг безопасность",
        ],
        "style": "экспертный, спокойный, с аналогиями из жизни, без паники",
        "prompt_prefix": "Ты — эксперт по кибербезопасности. Пиши понятно для обычных людей. Давай практические советы.",
        "schedule": ["10:00", "19:00"],
    },
    "ai": {
        "name": "AI Navigator",
        "telegram_channel": "@ainavigatorErgo",
        "vk_group": "ainavigatorpro",
        "topics": [
            "ChatGPT", "Midjourney", "нейросети для бизнеса",
            "автоматизация", "AI-инструменты", "промпты", "GPT-агенты",
            "Claude", "Gemini", "Stable Diffusion", "DALL-E",
            "нейросети для маркетинга", "нейросети для продаж",
            "нейросети для контента", "нейросети для аналитики",
            "автоматизация рутины", "AI-ассистенты", "голосовые нейросети",
            "нейросети для видео", "нейросети для дизайна", "нейросети для текста",
            "обучение нейросетей", "локальные нейросети", "бесплатные AI",
            "ChatGPT для работы", "GPT-4o", "AI в образовании",
            "AI в финансах", "AI в медицине", "AI в юриспруденции",
            "нейросети и этика", "будущее AI", "AI в повседневной жизни",
            "как заработать на нейросетях", "нейросети для фрилансеров",
            "нейросети для малого бизнеса", "нейросети и безопасность",
            "промпт-инжиниринг", "AI-стартапы", "тренды AI 2026",
        ],
        "style": "дружелюбный, практичный, с примерами и кейсами",
        "prompt_prefix": "Ты — эксперт по нейросетям и автоматизации. Пиши для предпринимателей и специалистов. Давай конкретные инструменты.",
        "schedule": ["10:00", "19:00"],
    },
}

# === Рубрики по дням недели (0=Пн, 6=Вс) ===
RUBRICS = {
    0: {"key": "threat", "name": "🔥 Угроза недели", "format": "post",
        "task": "Разбери свежую утечку, атаку или уязвимость. Объясни, кому угрожает и что делать."},
    1: {"key": "tool", "name": "🛠️ Инструмент дня", "format": "post",
        "task": "Обзор одного инструмента (VPN, менеджер паролей, AI-сервис). Плюсы, минусы, для кого подходит."},
    2: {"key": "scam", "name": "🎣 Разбор скама", "format": "poll",
        "task": "Разбери конкретную мошенническую схему. Покажи, как её распознать."},
    3: {"key": "news", "name": "📰 Новость + комментарий", "format": "post",
        "task": "Возьми свежую новость из ниши. Дай экспертный комментарий и вывод."},
    4: {"key": "checklist", "name": "✅ Чек-лист", "format": "post",
        "task": "Пошаговая инструкция из 5–7 пунктов. Конкретные действия."},
    5: {"key": "myth", "name": "🧠 Миф vs Реальность", "format": "longread",
        "task": "Развенчай популярный миф. Объясни, почему это не так, и что на самом деле."},
    6: {"key": "free", "name": "🎯 Свободная тема", "format": "post",
        "task": "Выбери самую актуальную и интересную тему недели. Свободный формат."},
}

# === Расписание ===
DEFAULT_SCHEDULE = ["10:00", "19:00"]
TIMEZONE = "Europe/Moscow"
