import requests
import time
from config import OPENAI_API_KEY, OPENAI_BASE_URL, GEMINI_MODEL

class ResearchAgent:
    def run(self, topic):
        url = f"{OPENAI_BASE_URL}/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        prompt = f"""
Ты — исследователь киберугроз. Собери по теме «{topic}» данные для сценария.

Собери:
1. Шокирующий факт (крючок).
2. 2–3 сценария угрозы.
3. 3–5 действий для защиты.
4. Один миф, который развенчаем.
5. Запоминающийся вывод.

Формат:
КРЮЧОК: ...
УГРОЗЫ: ...
ЧЕК-ЛИСТ: ...
МИФ: ...
ВЫВОД: ...
"""
        payload = {"model": GEMINI_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}
        last_error = None
        for attempt in range(5):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=120)
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                elif response.status_code in [503, 429, 500, 502]:
                    wait = 2 ** attempt
                    print(f"⚠️ Сервер вернул {response.status_code}, повтор через {wait} сек...")
                    time.sleep(wait)
                    continue
                else:
                    raise Exception(f"Research API error: {response.status_code} - {response.text}")
            except requests.exceptions.Timeout:
                last_error = "Таймаут"
                wait = 2 ** attempt
                print(f"⚠️ Таймаут, повтор через {wait} сек...")
                time.sleep(wait)
                continue
            except requests.exceptions.ConnectionError as e:
                last_error = str(e)
                wait = 2 ** attempt
                print(f"⚠️ Ошибка соединения, повтор через {wait} сек...")
                time.sleep(wait)
                continue
        raise Exception(f"ResearchAgent: не удалось получить ответ после 5 попыток. Последняя ошибка: {last_error}")
