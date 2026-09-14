import aiohttp
import os
from config import VK_TOKENS, VK_GROUP_IDS

VK_API_URL = "https://api.vk.com/method/"
VK_API_VERSION = "5.199"


async def _upload_photo(image_path, token, group_id):
    """Загружает фото на сервер VK и возвращает attachment."""
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
                raise Exception(f"getWallUploadServer error: {data['error']}")
            upload_url = data["response"]["upload_url"]

        # 2. Загружаем файл
        with open(image_path, "rb") as f:
            form = aiohttp.FormData()
            form.add_field("photo", f, filename="image.png", content_type="image/png")
            async with session.post(upload_url, data=form) as resp:
                upload_data = await resp.json()

        if "photo" not in upload_data:
            raise Exception(f"upload error: {upload_data}")

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
                raise Exception(f"saveWallPhoto error: {save_data['error']}")
            photo = save_data["response"][0]
            return f"photo{photo['owner_id']}_{photo['id']}"


async def publish_to_vk(channel_key, text, image_path=None):
    """
    Публикует пост в VK-сообщество.
    
    :param channel_key: "cyber" или "ai"
    :param text: текст поста
    :param image_path: путь к картинке (или URL)
    :return: True при успехе
    """
    token = VK_TOKENS.get(channel_key)
    group_id = VK_GROUP_IDS.get(channel_key)

    if not token or not group_id:
        print(f"⚠️ VK токен или group_id для {channel_key} не заданы")
        return False

    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "access_token": token,
                "v": VK_API_VERSION,
                "owner_id": -group_id,  # с минусом для сообщества
                "from_group": 1,
                "message": text,
            }

            # Загружаем фото, если есть
            if image_path and not image_path.startswith("http") and os.path.exists(image_path):
                try:
                    attachment = await _upload_photo(image_path, token, group_id)
                    params["attachments"] = attachment
                    print(f"   📷 Фото загружено в VK: {attachment}")
                except Exception as e:
                    print(f"   ⚠️ Не удалось загрузить фото в VK: {e}")

            async with session.post(f"{VK_API_URL}wall.post", data=params) as resp:
                result = await resp.json()
                if "error" in result:
                    err = result["error"]
                    print(f"❌ VK error: {err.get('error_msg', err)}")
                    return False
                post_id = result["response"]["post_id"]
                print(f"✅ Опубликовано в VK (post_id: {post_id})")
                return True

    except Exception as e:
        print(f"❌ Ошибка публикации в VK: {e}")
        return False
