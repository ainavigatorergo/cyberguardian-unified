import requests
import time
from config import OPENAI_API_KEY, OPENAI_BASE_URL, GEMINI_MODEL

class SEOSpecialist:
    def run(self, topic, script):
        url = f"{OPENAI_BASE_URL}/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        prompt = f"""
Ты — SEO-эксперт. Для видео на тему «{topic}» создай:
1. 3 варианта названия (с цифрами, вопросами, обещанием пользы).
2. Описание (2–3 абзаца, чек-лист, призыв подписаться).
3. 15 тегов (широкие + узкие).

Выход:
НАЗВАНИЯ:
1. ...
2. ...
3. ...
ОПИСАНИЕ: ...
ТЕГИ: ...
"""
        payload = {"model": GEMINI_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.8}
        last_error = None
        for attempt in range(5):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=120)
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                elif response.status_code in [503, 429, 500, 502]:
                    wait = 2 ** attempt
                    print(f"⚠️ SEO: сервер вернул {response.status_code}, повтор через {wait} сек...")
                    time.sleep(wait)
                    continue
                else:
                    raise Exception(f"SEO API error: {response.status_code}")
            except requests.exceptions.Timeout:
                last_error = "Таймаут"
                wait = 2 ** attempt
                print(f"⚠️ SEO: таймаут, повтор через {wait} сек...")
                time.sleep(wait)
                continue
            except requests.exceptions.ConnectionError as e:
                last_error = str(e)
                wait = 2 ** attempt
                print(f"⚠️ SEO: ошибка соединения, повтор через {wait} сек...")
                time.sleep(wait)
                continue
        return f"SEO generation failed: {last_error}"
