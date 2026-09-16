import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "8959872205:AAEYODqzyx_CG4PTGneoBCoBOVzMlVX2vRo")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
PROVOD_API_KEY = os.getenv("PROVOD_API_KEY", "sk_572d6f9c130ad10c5cfc7a6d48ab8421197328195c52278a")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "nsag1sPRpOnRupyvRMm6A5cZbZJgvuSfpX1DeFfFrOYksOq5XJMgpZSY")
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "sk_IO2JusirCuHRbVzBfZ6EEoDUkcjyRqU6")

VK_TOKENS = {
    "cyber": os.getenv("VK_TOKEN_CYBER", "vk1.a.kPjS4OrhX2Vt5yMKw49l-p3l3bmE6uQoyPiDF4XpeTGstsUUNA3GY22YShf5evspiZGOddAtDCk5QSzCxFZc1UUfZxtdIl__Y5sYnZwJfZncsa8ybMmhf_eE-LWynH2mHhYh6RTD08P0FJpbIFcSlccQ3Mgs7-hyo-hUKHXDV2xOKezxEeXTwd8Lhv2tvyOhwEHWlQYJWAWw7YfQXL9Xpw"),
    "ai": os.getenv("VK_TOKEN_AI", "vk1.a.5oc-ybsZqzZ7A0GZOL8ihsDvhbJxd_AGuADu44PWMD_AsdWLf_0962b6_GRt4PvqW9Jo39uwznFV67pNYTK81tUSNKTNN_nexsWcjmjQ3MVEEFJCV-cHHGtoYNfFWrKLtwzLJs7zKy0673K7w4Iakvfiad_r-zeN8kcEQdQJ5HMXwqnMaclebSu40HfTfygHbt9NJIZh7lQMpIw2FxBy1A"),
}

VK_GROUP_IDS = {
    "cyber": int(os.getenv("VK_GROUP_CYBER", "241288592")),
    "ai": int(os.getenv("VK_GROUP_AI", "241416521")),
}

GEMINI_MODEL = "gemini-3.5-flash"

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

VIDEO_PIPELINE_URL = os.getenv("VIDEO_PIPELINE_URL", "https://example.com")

# === ПРОФИЛИ КАНАЛОВ ===
CHANNELS = {
    "cyber": {
        "name": "CyberGuardianSec",
        "telegram_channel": "@CyberGuardianSec",
        "vk_group": "cyberguardiansec",
        "author": {
            "name": "Егор",
            "role": "автор канала, эксперт по кибербезопасности",
            "experience": "5 лет в теме защиты данных и корпоративной безопасности",
            "style": "спокойный, дружелюбный, с лёгкой иронией, без паники",
            "personal_touch": "сам сталкивался с фишингом, утечками и мошенниками",
        },
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
        "prompt_prefix": "Ты — Егор, автор Telegram-канала CyberGuardianSec. Пишешь от первого лица, как живой эксперт по кибербезопасности. Ты дружелюбный, но серьёзный, когда дело касается защиты данных. Умеешь объяснять сложное простыми словами и с лёгкой иронией.",
        "schedule": ["10:00", "19:00"],
    },
    "ai": {
        "name": "AI Navigator",
        "telegram_channel": "@ainavigatorErgo",
        "vk_group": "ainavigatorpro",
        "author": {
            "name": "Егор",
            "role": "автор канала, практик в сфере AI и автоматизации",
            "experience": "3 года автоматизирую бизнес-процессы с помощью нейросетей",
            "style": "дружелюбный, практичный, делюсь опытом и кейсами",
            "personal_touch": "сам тестирую каждый инструмент, о котором пишу",
        },
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
            "нейросети для малого бизнеса", "промпт-инжиниринг", "AI-стартапы",
            "тренды AI 2026",
        ],
        "style": "дружелюбный, практичный, с примерами и кейсами",
        "prompt_prefix": "Ты — Егор, автор Telegram-канала AI Navigator. Пишешь от первого лица, как практик, который сам тестирует AI-инструменты. Ты дружелюбный, делишься опытом, даёшь конкретные кейсы и цифры.",
        "schedule": ["10:00", "19:00"],
    },
}

# === РУБРИКИ ДЛЯ КИБЕР-КАНАЛА ===
RUBRICS_CYBER = {
    0: {"key": "threat", "name": "🔥 Угроза недели", "format": "post",
        "task": "Разбери свежую утечку, атаку или уязвимость от первого лица."},
    1: {"key": "tool", "name": "🛠️ Инструмент дня", "format": "post",
        "task": "Обзор инструмента защиты (VPN, менеджер паролей). Что тестировал, что понравилось."},
    2: {"key": "tips", "name": "💡 Советы по защите", "format": "post",
        "task": "Дай 3 практических совета по защите данных от первого лица."},
    3: {"key": "news", "name": "📰 Новость + комментарий", "format": "post",
        "task": "Возьми свежую новость из мира ИБ. Дай личный экспертный комментарий."},
    4: {"key": "checklist", "name": "✅ Чек-лист", "format": "post",
        "task": "Пошаговая инструкция по защите с личными советами."},
    5: {"key": "myth", "name": "🧠 Миф vs Реальность", "format": "longread",
        "task": "Развенчай миф о кибербезопасности от первого лица, с личным опытом."},
    6: {"key": "free", "name": "🎯 Свободная тема", "format": "post",
        "task": "Свободная тема с личным мнением."},
}

# === РУБРИКИ ДЛЯ AI-КАНАЛА ===
RUBRICS_AI = {
    0: {"key": "ai_news", "name": "🔥 AI-новость недели", "format": "post",
        "task": "Разбери свежую новость из мира AI. Что это значит для бизнеса."},
    1: {"key": "ai_tool", "name": "🛠️ AI-инструмент дня", "format": "post",
        "task": "Обзор AI-инструмента от первого лица: что тестировал, что понравилось."},
    2: {"key": "ai_case", "name": "🎯 Кейс автоматизации", "format": "post",
        "task": "Разбери реальный кейс автоматизации с помощью AI. С цифрами."},
    3: {"key": "ai_news_comment", "name": "📰 Новость + комментарий", "format": "post",
        "task": "Возьми свежую новость из мира AI. Дай личный комментарий."},
    4: {"key": "ai_checklist", "name": "✅ Чек-лист по AI", "format": "post",
        "task": "Пошаговая инструкция по внедрению AI-инструмента."},
    5: {"key": "ai_myth", "name": "🧠 Миф vs Реальность в AI", "format": "longread",
        "task": "Развенчай популярный миф о нейросетях."},
    6: {"key": "ai_free", "name": "🎯 Свободная тема", "format": "post",
        "task": "Свободная тема из мира AI."},
}

DEFAULT_SCHEDULE = ["10:00", "19:00"]
TIMEZONE = "Europe/Moscow"
