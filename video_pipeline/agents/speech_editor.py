import requests
import time
from config import OPENAI_API_KEY, OPENAI_BASE_URL, GEMINI_MODEL

class SpeechEditor:
    def run(self, script, platform="youtube"):
        url = f"{OPENAI_BASE_URL}/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        prompt = f"""
Ты — редактор речи. Преобразуй сценарий в идеальный текст для озвучки.

Сценарий: {script}

Удали таймкоды, визуальные пометки, звёздочки, скобки.
Оставь только прямую речь.
Сделай предложения короткими (15–20 слов).
Разбей длинные фразы.
Замени сложные конструкции на простые.
Добавь естественные паузы.
Для {platform}: 'youtube' — нормальный темп, 'shorts/tiktok' — динамичный.

Выход: только текст для озвучки.
"""
        payload = {"model": GEMINI_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.6}
        last_error = None
        for attempt in range(5):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=120)
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                elif response.status_code in [503, 429, 500, 502]:
                    wait = 2 ** attempt
                    print(f"⚠️ SpeechEditor: сервер вернул {response.status_code}, повтор через {wait} сек...")
                    time.sleep(wait)
                    continue
                else:
                    raise Exception(f"SpeechEditor API error: {response.status_code}")
            except requests.exceptions.Timeout:
                last_error = "Таймаут"
                wait = 2 ** attempt
                print(f"⚠️ SpeechEditor: таймаут, повтор через {wait} сек...")
                time.sleep(wait)
                continue
            except requests.exceptions.ConnectionError as e:
                last_error = str(e)
                wait = 2 ** attempt
                print(f"⚠️ SpeechEditor: ошибка соединения, повтор через {wait} сек...")
                time.sleep(wait)
                continue
        raise Exception(f"SpeechEditor: не удалось получить ответ после 5 попыток. Последняя ошибка: {last_error}")
