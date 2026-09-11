import requests
import time
from config import OPENAI_API_KEY, OPENAI_BASE_URL, GEMINI_MODEL

class PlatformAdapter:
    def run(self, script, platform="youtube"):
        url = f"{OPENAI_BASE_URL}/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        prompt = f"""
Ты — адаптер контента. Переработай сценарий для платформы {platform}.

Исходный сценарий: {script}

YouTube: полная версия (10–12 мин).
Shorts/TikTok: сократи до 15–60 секунд, динамичный монтаж, текст в кадре.
VK: адаптируй для поста в сообществе: короткий текст, заголовок, ссылка на видео.

Дай итоговый адаптированный контент.
"""
        payload = {"model": GEMINI_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.8}
        last_error = None
        for attempt in range(3):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=120)
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                elif response.status_code in [503, 429, 500, 502]:
                    wait = 2 ** attempt
                    print(f"⚠️ Adapter: сервер вернул {response.status_code}, повтор через {wait} сек...")
                    time.sleep(wait)
                    continue
                else:
                    raise Exception(f"Adapter API error: {response.status_code}")
            except requests.exceptions.Timeout:
                last_error = "Таймаут"
                wait = 2 ** attempt
                print(f"⚠️ Adapter: таймаут, повтор через {wait} сек...")
                time.sleep(wait)
                continue
            except requests.exceptions.ConnectionError as e:
                last_error = str(e)
                wait = 2 ** attempt
                print(f"⚠️ Adapter: ошибка соединения, повтор через {wait} сек...")
                time.sleep(wait)
                continue
        return f"Ошибка адаптации для {platform}: {last_error}"
