import requests
import time
from config import OPENAI_API_KEY, OPENAI_BASE_URL, GEMINI_MODEL

class Scriptwriter:
    def run(self, topic, research):
        url = f"{OPENAI_BASE_URL}/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        prompt = f"""
Ты — сценарист YouTube-канала по кибербезопасности. Напиши живой сценарий на 10–12 минут на тему: {topic}

Исследование: {research}

Структура:
1. ХУК (0:00–0:40) — шокирующий факт.
2. ВВЕДЕНИЕ (0:40–2:00) — личная история.
3. ОСНОВНАЯ ЧАСТЬ (2:00–8:00) — 4–6 блоков с вопросами, аналогиями, советами.
4. ПРИМЕР ИЗ ЖИЗНИ (8:00–9:00).
5. ЧЕК-ЛИСТ (9:00–10:00).
6. ЗАКЛЮЧЕНИЕ (10:00–12:00) — итог, призыв подписаться.

Стиль: обращение на «ты», разговорные слова, личные вставки, без паники.
Выход: текст с тайм-кодами в квадратных скобках.
"""
        payload = {"model": GEMINI_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.85}
        last_error = None
        for attempt in range(5):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=120)
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                elif response.status_code in [503, 429, 500, 502]:
                    wait = 2 ** attempt
                    print(f"⚠️ Scriptwriter: сервер вернул {response.status_code}, повтор через {wait} сек...")
                    time.sleep(wait)
                    continue
                else:
                    raise Exception(f"Scriptwriter API error: {response.status_code}")
            except requests.exceptions.Timeout:
                last_error = "Таймаут"
                wait = 2 ** attempt
                print(f"⚠️ Scriptwriter: таймаут, повтор через {wait} сек...")
                time.sleep(wait)
                continue
            except requests.exceptions.ConnectionError as e:
                last_error = str(e)
                wait = 2 ** attempt
                print(f"⚠️ Scriptwriter: ошибка соединения, повтор через {wait} сек...")
                time.sleep(wait)
                continue
        raise Exception(f"Scriptwriter: не удалось получить ответ после 5 попыток. Последняя ошибка: {last_error}")
