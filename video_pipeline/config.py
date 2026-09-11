import os
from dotenv import load_dotenv
load_dotenv()

# === API ключи (читаем из переменных окружения) ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk_572d6f9c130ad10c5cfc7a6d48ab8421197328195c52278a")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.provod.ai/v1")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "nsag1sPRpOnRupyvRMm6A5cZbZJgvuSfpX1DeFfFrOYksOq5XJMgpZSY")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "57549284-857332cd57284ac77c2028400")
AGNES_API_KEY = os.getenv("AGNES_API_KEY", "sk-BSNQsJAA7uWMajEOqPdUAKCidfED7NiMSmWduXoHhLdf18Ji")

# === Путь для сохранения результатов ===
OUTPUT_BASE_DIR = os.getenv("OUTPUT_BASE_DIR", "/tmp/project_output")
os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_BASE_DIR, "audio"), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_BASE_DIR, "video"), exist_ok=True)

# === Для совместимости ===
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["OPENAI_BASE_URL"] = OPENAI_BASE_URL
os.environ["GEMINI_MODEL"] = GEMINI_MODEL
os.environ["PEXELS_API_KEY"] = PEXELS_API_KEY
os.environ["PIXABAY_API_KEY"] = PIXABAY_API_KEY
os.environ["AGNES_API_KEY"] = AGNES_API_KEY
os.environ["OUTPUT_BASE_DIR"] = OUTPUT_BASE_DIR
