import json
import os
from datetime import datetime, timedelta
from config import DATA_DIR, CHANNELS

STATS_FILE = os.path.join(DATA_DIR, "stats.json")


def _load_stats():
    if not os.path.exists(STATS_FILE):
        return {"daily": [], "posts": 0, "started": datetime.now().isoformat()}
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"daily": [], "posts": 0, "started": datetime.now().isoformat()}


def _save_stats(data):
    try:
        os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Не удалось сохранить статистику: {e}")


def increment_post_count():
    """Увеличивает счётчик постов."""
    stats = _load_stats()
    stats["posts"] = stats.get("posts", 0) + 1
    _save_stats(stats)


async def collect_daily_stats(bot):
    """Собирает статистику по обоим каналам."""
    stats = _load_stats()
    today = datetime.now().strftime("%Y-%m-%d")

    daily_entry = {"date": today, "channels": {}}

    for key, channel in CHANNELS.items():
        try:
            count = await bot.get_chat_member_count(channel["telegram_channel"])
            daily_entry["channels"][key] = {
                "name": channel["name"],
                "subscribers": count,
            }
            print(f"📊 {channel['name']}: {count} подписчиков")
        except Exception as e:
            print(f"⚠️ Не удалось получить статистику {channel['name']}: {e}")
            daily_entry["channels"][key] = {
                "name": channel["name"],
                "subscribers": 0,
                "error": str(e),
            }

    stats["daily"].append(daily_entry)

    # Храним только последние 30 дней
    stats["daily"] = stats["daily"][-30:]
    _save_stats(stats)
    print(f"✅ Статистика за {today} сохранена")


async def send_weekly_report(bot):
    """Отправляет еженедельный отчёт."""
    from comment_assistant import get_admin_chat_id
    target = get_admin_chat_id()

    stats = _load_stats()
    daily = stats.get("daily", [])

    if len(daily) < 2:
        try:
            await bot.send_message(target, "📊 Отчёт: данных пока мало (нужно минимум 2 дня).")
        except:
            pass
        return

    # Берём первую и последнюю запись
    first = daily[0]
    last = daily[-1]

    report = "📊 <b>Еженедельный отчёт</b>\n"
    report += f"📅 {last['date']}\n\n"

    for key in ["cyber", "ai"]:
        emoji = "🔐" if key == "cyber" else "🤖"
        first_count = first["channels"].get(key, {}).get("subscribers", 0)
        last_count = last["channels"].get(key, {}).get("subscribers", 0)
        growth = last_count - first_count
        growth_str = f"+{growth}" if growth >= 0 else str(growth)

        name = CHANNELS[key]["name"]
        report += f"{emoji} <b>{name}</b>\n"
        report += f"   Подписчиков: <b>{last_count}</b>\n"
        report += f"   Прирост за неделю: <b>{growth_str}</b>\n\n"

    report += f"📝 Всего постов за всё время: <b>{stats.get('posts', 0)}</b>\n\n"

    # Прогноз
    total_growth = 0
    for key in ["cyber", "ai"]:
        first_count = first["channels"].get(key, {}).get("subscribers", 0)
        last_count = last["channels"].get(key, {}).get("subscribers", 0)
        total_growth += (last_count - first_count)

    if total_growth > 0:
        report += f"🚀 <b>Растём!</b> Средний прирост: <b>{total_growth // max(len(daily), 1)}</b> в день.\n"
    else:
        report += "⚠️ Прирост минимальный. Нужно больше активностей: комментарии, кросс-промо, каталоги.\n"

    try:
        await bot.send_message(target, report)
        print("✅ Еженедельный отчёт отправлен")
    except Exception as e:
        print(f"⚠️ Не удалось отправить отчёт: {e}")


async def send_stats_now(bot):
    """Ручной запрос статистики (по кнопке)."""
    from comment_assistant import get_admin_chat_id
    target = get_admin_chat_id()

    stats = _load_stats()
    daily = stats.get("daily", [])

    report = "📊 <b>Статистика каналов</b>\n\n"

    for key, channel in CHANNELS.items():
        emoji = "🔐" if key == "cyber" else "🤖"
        try:
            count = await bot.get_chat_member_count(channel["telegram_channel"])
            report += f"{emoji} <b>{channel['name']}</b>\n"
            report += f"   Подписчиков: <b>{count}</b>\n\n"
        except Exception as e:
            report += f"{emoji} <b>{channel['name']}</b>\n"
            report += f"   ⚠️ Ошибка: {e}\n\n"

    report += f"📝 Всего постов: <b>{stats.get('posts', 0)}</b>\n"
    report += f"📅 Дней наблюдений: <b>{len(daily)}</b>\n"

    try:
        await bot.send_message(target, report)
        return True
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        return False
