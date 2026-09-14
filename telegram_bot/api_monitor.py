import aiohttp
from datetime import datetime
from config import PROVOD_API_KEY, PEXELS_API_KEY

PROVOD_URL = "https://api.provod.ai/v1/chat/completions"
PEXELS_URL = "https://api.pexels.com/videos/search"
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/test?width=64&height=64&nologo=true"

PROVOD_MODELS = ["gemini-3.5-flash", "gemini-2.5-flash"]


async def check_provod():
    """Проверяет provod.ai — короткий запрос."""
    async with aiohttp.ClientSession() as session:
        for model in PROVOD_MODELS:
            try:
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 5,
                }
                headers = {
                    "Authorization": f"Bearer {PROVOD_API_KEY}",
                    "Content-Type": "application/json",
                }
                async with session.post(PROVOD_URL, headers=headers, json=payload, timeout=30) as resp:
                    if resp.status == 200:
                        return True, model
            except:
                continue
    return False, None


async def check_pexels():
    """Проверяет Pexels."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": PEXELS_API_KEY}
            params = {"query": "test", "per_page": 1}
            async with session.get(PEXELS_URL, headers=headers, params=params, timeout=20) as resp:
                return resp.status == 200, resp.status
    except Exception as e:
        return False, str(e)


async def check_pollinations():
    """Проверяет Pollinations.ai."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(POLLINATIONS_URL, timeout=20) as resp:
                return resp.status == 200, resp.status
    except Exception as e:
        return False, str(e)


async def check_all_apis(bot, silent_if_ok=True):
    """
    Проверяет все API. Если что-то упало — присылает алерт админу.
    silent_if_ok: если True — при успехе ничего не пишет.
    """
    from comment_assistant import get_admin_chat_id
    target = get_admin_chat_id()

    results = {}

    # Provod
    provod_ok, provod_info = await check_provod()
    results["Provod.ai"] = (provod_ok, provod_info)

    # Pexels
    pexels_ok, pexels_info = await check_pexels()
    results["Pexels"] = (pexels_ok, pexels_info)

    # Pollinations
    poll_ok, poll_info = await check_pollinations()
    results["Pollinations"] = (poll_ok, poll_info)

    # Проверяем, всё ли ок
    all_ok = all(r[0] for r in results.values())

    if all_ok:
        print(f"✅ Все API работают ({datetime.now().strftime('%H:%M')})")
        if not silent_if_ok:
            msg = "✅ <b>Все API работают</b>\n\n"
            for name, (ok, info) in results.items():
                msg += f"• {name}: ✅ {info if isinstance(info, str) and len(str(info)) < 30 else 'OK'}\n"
            try:
                await bot.send_message(target, msg)
            except:
                pass
        return True

    # Что-то упало — алерт
    print(f"⚠️ Проблемы с API: {results}")

    msg = "⚠️ <b>Проблема с API!</b>\n"
    msg += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"

    for name, (ok, info) in results.items():
        if ok:
            msg += f"✅ {name}: работает\n"
        else:
            msg += f"❌ <b>{name}</b>: {info}\n"

    msg += "\n💡 Проверь логи Render или баланс."

    try:
        await bot.send_message(target, msg)
    except Exception as e:
        print(f"⚠️ Не удалось отправить алерт: {e}")

    return False


async def get_api_status(bot):
    """Показывает статус всех API (для кнопки)."""
    from comment_assistant import get_admin_chat_id
    target = get_admin_chat_id()

    provod_ok, provod_info = await check_provod()
    pexels_ok, pexels_info = await check_pexels()
    poll_ok, poll_info = await check_pollinations()

    msg = "🔍 <b>Статус API</b>\n\n"
    msg += f"{'✅' if provod_ok else '❌'} <b>Provod.ai</b>"
    if provod_ok:
        msg += f" — модель: <code>{provod_info}</code>\n"
    else:
        msg += f" — не отвечает\n"

    msg += f"{'✅' if pexels_ok else '❌'} <b>Pexels</b>"
    if pexels_ok:
        msg += " — работает\n"
    else:
        msg += f" — {pexels_info}\n"

    msg += f"{'✅' if poll_ok else '❌'} <b>Pollinations</b>"
    if poll_ok:
        msg += " — работает\n"
    else:
        msg += f" — {poll_info}\n"

    try:
        await bot.send_message(target, msg)
        return True
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        return False
