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

TG_LINKS = {
    "cyber": "https://t.me/CyberGuardianSec",
    "ai": "https://t.me/ainavigatorErgo",
}

# === PROVOD IMAGE (Nano Banana Pro) ===
PROVOD_IMAGE_MODEL = os.getenv("PROVOD_IMAGE_MODEL", "google/gemini-3-pro-image-preview")
PROVOD_IMAGE_URL = "https://api.provod.ai/v1/images/generations"

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

CHANNELS = {
    "cyber": {
        "name": "CyberGuardianSec",
        "telegram_channel": "@CyberGuardianSec",
        "vk_group": "cyberguardiansec",
        "author": {
            "name": "Егор",
            "role": "автор канала, эксперт по кибербезопасности",
            "experience": "5 лет в теме защиты данных",
            "personal_touch": "сам сталкивался с фишингом и утечками",
        },
        "topics": [
            "фишинг", "утечки данных", "VPN", "пароли", "кибератаки",
            "социальная инженерия", "защита аккаунтов", "мошенничество",
            "двухфакторная аутентификация", "менеджеры паролей", "фишинговые письма",
            "взлом email", "защита смартфона", "безопасность Wi-Fi",
            "мошенники в Telegram", "поддельные сайты", "криптомошенничество",
            "защита детей в интернете", "утечка паролей", "вредоносное ПО",
        ],
        "prompt_prefix": "Ты — Егор, автор Telegram-канала CyberGuardianSec. Пишешь от первого лица, как живой эксперт по кибербезопасности. Дружелюбный, но серьёзный. Объясняешь сложное простыми словами.",
    },
    "ai": {
        "name": "AI Navigator",
        "telegram_channel": "@ainavigatorErgo",
        "vk_group": "ainavigatorpro",
        "author": {
            "name": "Егор",
            "role": "автор канала, практик в сфере AI",
            "experience": "3 года автоматизирую бизнес с помощью нейросетей",
            "personal_touch": "сам тестирую каждый инструмент, о котором пишу",
        },
        "topics": [
            "ChatGPT", "Midjourney", "нейросети для бизнеса", "автоматизация",
            "AI-инструменты", "промпты", "GPT-агенты", "Claude", "Gemini",
            "нейросети для маркетинга", "нейросети для продаж", "нейросети для контента",
            "автоматизация рутины", "AI-ассистенты", "нейросети для видео",
            "нейросети для дизайна", "обучение нейросетей", "бесплатные AI",
            "промпт-инжиниринг", "AI-стартапы",
        ],
        "prompt_prefix": "Ты — Егор, автор Telegram-канала AI Navigator. Пишешь от первого лица, как практик, который сам тестирует AI-инструменты. Дружелюбный, делишься опытом, даёшь кейсы и цифры.",
    },
}

RUBRICS_CYBER = {
    0: {"key": "threat", "name": "🔥 Угроза недели", "format": "post"},
    1: {"key": "tool", "name": "🛠️ Инструмент дня", "format": "post"},
    2: {"key": "tips", "name": "💡 Советы по защите", "format": "post"},
    3: {"key": "news", "name": "📰 Новость + комментарий", "format": "post"},
    4: {"key": "checklist", "name": "✅ Чек-лист", "format": "post"},
    5: {"key": "myth", "name": "🧠 Миф vs Реальность", "format": "longread"},
    6: {"key": "free", "name": "🎯 Свободная тема", "format": "post"},
}

RUBRICS_AI = {
    0: {"key": "ai_news", "name": "🔥 AI-новость недели", "format": "post"},
    1: {"key": "ai_tool", "name": "🛠️ AI-инструмент дня", "format": "post"},
    2: {"key": "ai_case", "name": "🎯 Кейс автоматизации", "format": "post"},
    3: {"key": "ai_news_comment", "name": "📰 Новость + комментарий", "format": "post"},
    4: {"key": "ai_checklist", "name": "✅ Чек-лист по AI", "format": "post"},
    5: {"key": "ai_myth", "name": "🧠 Миф vs Реальность", "format": "longread"},
    6: {"key": "ai_free", "name": "🎯 Свободная тема", "format": "post"},
}

BRAND_HASHTAGS = {"cyber": "#CyberGuardianSec", "ai": "#AINavigator"}
RUBRIC_HASHTAGS = {
    "cyber": {"threat": "#угроза", "tool": "#инструмент", "tips": "#совет",
              "news": "#новость", "checklist": "#чеклист", "myth": "#миф", "free": "#разбор"},
    "ai": {"ai_news": "#AIновость", "ai_tool": "#AIинструмент", "ai_case": "#AIкейс",
           "ai_news_comment": "#AIновость", "ai_checklist": "#AIчеклист",
           "ai_myth": "#AIмиф", "ai_free": "#AIразбор"},
}
GENERAL_HASHTAGS = {"cyber": "#кибербезопасность", "ai": "#нейросети"}

TOPIC_HASHTAG_POOL = {
    "cyber": [
        "#фишинг", "#защитаданных", "#приватность", "#пароли", "#VPN",
        "#антивирус", "#2FA", "#менеджерпаролей", "#утечка", "#хакеры",
        "#мошенники", "#безопасность", "#защитааккаунтов", "#шифрование",
        "#безопасныйинтернет", "#цифроваяграмотность", "#защитадетей",
        "#социальнаяинженерия", "#взлом", "#поддельныесайты",
        "#криптомошенничество", "#безопасностьсети", "#резервноекипирование",
        "#защитабанковскихкарт", "#спам", "#вредоносноеПО", "#шпионскоеПО",
        "#уязвимости", "#обновления", "#безопасностьприложений",
    ],
    "ai": [
        "#ChatGPT", "#Midjourney", "#промпты", "#промптинг", "#автоматизация",
        "#AIинструменты", "#нейросетидлябизнеса", "#GPTагенты", "#Claude",
        "#Gemini", "#DALLE", "#StableDiffusion", "#AIдлямаркетинга",
        "#AIдляпродаж", "#AIдляконтента", "#AIассистент", "#промптинжиниринг",
        "#AIстартап", "#машинноеобучение", "#AIдляфрилансеров",
        "#AIдлямалогобизнеса", "#бесплатныеAI", "#локальныенейросети",
        "#AIтренды", "#цифроваятрансформация", "#ноукод", "#AIворкфлоу",
        "#генерацияизображений", "#генерациятекста", "#AIвидео",
    ],
}

PALETTES = {
    "cyber": [
        {"bg_top": (8, 15, 40), "bg_bottom": (15, 40, 75), "accent": (0, 255, 150)},
        {"bg_top": (5, 5, 15), "bg_bottom": (10, 20, 50), "accent": (0, 200, 255)},
        {"bg_top": (15, 15, 20), "bg_bottom": (30, 40, 40), "accent": (100, 255, 100)},
        {"bg_top": (10, 8, 8), "bg_bottom": (30, 20, 10), "accent": (255, 150, 50)},
        {"bg_top": (8, 20, 30), "bg_bottom": (15, 45, 55), "accent": (0, 230, 200)},
    ],
    "ai": [
        {"bg_top": (30, 8, 50), "bg_bottom": (60, 15, 85), "accent": (0, 255, 130)},
        {"bg_top": (5, 10, 15), "bg_bottom": (10, 25, 35), "accent": (0, 220, 220)},
        {"bg_top": (10, 15, 40), "bg_bottom": (25, 30, 60), "accent": (255, 200, 80)},
        {"bg_top": (35, 10, 55), "bg_bottom": (70, 20, 80), "accent": (255, 100, 180)},
        {"bg_top": (12, 12, 25), "bg_bottom": (25, 30, 60), "accent": (100, 180, 255)},
    ],
}

POST_HOOKS = [
    "диалог: короткая реплика. Пример: «— Ты сменил пароль? — Да, на qwerty12345. — Ну ты и...»",
    "цитата: слова знакомого. Пример: «Мой знакомый сказал: “Зачем мне VPN?” — и через месяц его взломали».",
    "цифра: удивительный факт. Пример: «73% людей используют один пароль на всех сайтах. Ты в их числе?»",
    "мини-история: реальный момент. Пример: «Вчера мне позвонила Лена. Голос дрожал. Её развели на 150 тысяч за час».",
]

POST_CLOSINGS = [
    "вопрос-вызов: «А ты бы заметил подвох? Напиши в комментариях».",
    "мини-тест: «Проверь себя: когда последний раз менял пароль от почты?».",
    "просьба поделиться: «Перешли это родителям. Они — главная цель мошенников».",
    "мнение: «А ты как думаешь? Напиши в комментариях, я читаю всё».",
]

POST_TEMPLATES = ["story", "breakdown", "checklist", "myth"]
CARD_TEMPLATES = ["classic", "gradient", "accent", "bottom_up", "magazine"]

RUBRICS = RUBRICS_CYBER
DEFAULT_SCHEDULE = ["10:00", "19:00"]
TIMEZONE = "Europe/Moscow"
