import requests
import time
from config import OPENAI_API_KEY, OPENAI_BASE_URL, GEMINI_MODEL

class RulesChecker:
    def run(self, script):
        url = f"{OPENAI_BASE_URL}/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        prompt = f"""
Ты — модератор контента. Проверь сценарий на соответствие правилам YouTube, TikTok, VK.

Запрещено: кликбейт, паника, политика, оскорбления, призывы к незаконным действиям, спам.

Если нарушений нет, ответь: "ОК".
Если есть, укажи их и предложи исправления.

Сценарий: {script}
"""
        payload = {"model": GEMINI_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}
        last_error = None
        for attempt in range(3):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=120)
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                elif response.status_code in [503, 429, 500, 502]:
                    wait = 2 ** attempt
                    print(f"⚠️ Rules: сервер вернул {response.status_code}, повтор через {wait} сек...")
                    time.sleep(wait)
                    continue
                else:
                    raise Exception(f"Rules API error: {response.status_code}")
            except requests.exceptions.Timeout:
                last_error = "Таймаут"
                wait = 2 ** attempt
                print(f"⚠️ Rules: таймаут, повтор через {wait} сек...")
                time.sleep(wait)
                continue
            except requests.exceptions.ConnectionError as e:
                last_error = str(e)
                wait = 2 ** attempt
                print(f"⚠️ Rules: ошибка соединения, повтор через {wait} сек...")
                time.sleep(wait)
                continue
        return f"Ошибка проверки правил: {last_error}"
