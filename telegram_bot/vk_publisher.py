import aiohttp
import os
from config import VK_TOKENS, VK_GROUP_IDS

VK_API_URL = "https://api.vk.com/method/"
VK_API_VERSION = "5.199"


async def _upload_photo(image_path, token, group_id):
    """Загружает фото на сервер VK. Возвращает attachment."""
    print(f"   📷 [VK] Загружаю фото: {image_path}")
    async with aiohttp.ClientSession() as session:
        # 1. Получаем сервер для загрузки
        params = {
            "access_token": token,
            "v": VK_API_VERSION,
            "group_id": group_id,
        }
        async with session.get(f"{VK_API_URL}photos.getWallUploadServer", params=params) as resp:
            data = await resp.json()
            if "error" in data:
                err = data["error"]
                print(f"   ❌ [VK] getWallUploadServer error: {err.get('error_code')} — {err.get('error_msg')}")
                raise Exception(f"getWallUploadServer: {err}")
            upload_url = data["response"]["upload_url"]
            print(f"   ✅ [VK] Сервер получен")

        # 2. Загружаем файл
        with open(image_path, "rb") as f:
            form = aiohttp.FormData()
            form.add_field("photo", f, filename="image.png", content_type="image/png")
            async with session.post(upload_url, data=form) as resp:
                upload_data = await resp.json()

        if "photo" not in upload_data:
            print(f"   ❌ [VK] Загрузка фото: {upload_data}")
            raise Exception(f"upload: {upload_data}")
        print(f"   ✅ [VK] Фото загружено на сервер")

        # 3. Сохраняем фото
        params = {
            "access_token": token,
            "v": VK_API_VERSION,
            "group_id": group_id,
            "server": upload_data["server"],
            "photo": upload_data["photo"],
            "hash": upload_data["hash"],
        }
        async with session.get(f"{VK_API_URL}photos.saveWallPhoto", params=params) as resp:
            save_data = await resp.json()
            if "error" in save_data:
                err = save_data["error"]
                print(f"   ❌ [VK] saveWallPhoto error: {err.get('error_code')} — {err.get('error_msg')}")
                raise Exception(f"saveWallPhoto: {err}")
            photo = save_data["response"][0]
            attachment = f"photo{photo['owner_id']}_{photo['id']}"
            print(f"   ✅ [VK] Фото сохранено: {attachment}")
            return attachment


async def publish_to_vk(channel_key, text, image_path=None):
    """Публикует пост в VK-сообщество."""
    print(f"\n{'='*50}")
    print(f"📤 [VK] Публикация в {channel_key}")
    print(f"{'='*50}")

    token = VK_TOKENS.get(channel_key)
    group_id = VK_GROUP_IDS.get(channel_key)

    if not token:
        print(f"❌ [VK] Нет токена для {channel_key}")
        return False
    if not group_id:
        print(f"❌ [VK] Нет group_id для {channel_key}")
        return False

    print(f"   🔑 Токен: {token[:20]}...")
    print(f"   🆔 Group ID: {group_id}")
    print(f"   📝 Текст: {len(text)} символов")
    print(f"   📷 Картинка: {image_path}")

    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "access_token": token,
                "v": VK_API_VERSION,
                "owner_id": -group_id,
                "from_group": 1,
                "message": text,
            }

            # Загружаем фото, если есть
            if image_path and not image_path.startswith("http") and os.path.exists(image_path):
                try:
                    attachment = await _upload_photo(image_path, token, group_id)
                    params["attachments"] = attachment
                    print(f"   ✅ [VK] Фото готово: {attachment}")
                except Exception as e:
                    print(f"   ⚠️ [VK] Не удалось загрузить фото: {e}")
                    print(f"   ℹ️ [VK] Публикую БЕЗ фото")
            else:
                print(f"   ℹ️ [VK] Фото нет или это URL — публикую без фото")

            # Публикуем пост
            print(f"   📤 [VK] Отправляю wall.post...")
            async with session.post(f"{VK_API_URL}wall.post", data=params) as resp:
                result = await resp.json()
                if "error" in result:
                    err = result["error"]
                    print(f"   ❌ [VK] wall.post error: {err.get('error_code')} — {err.get('error_msg')}")
                    return False
                post_id = result["response"]["post_id"]
                print(f"   ✅ [VK] Опубликовано! post_id: {post_id}")
                print(f"   🔗 https://vk.com/wall-{group_id}_{post_id}")
                return True

    except Exception as e:
        print(f"   ❌ [VK] Общая ошибка: {e}")
        return False
