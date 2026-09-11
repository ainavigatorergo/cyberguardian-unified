import os
import time
import requests
from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip
from config import AGNES_API_KEY, PEXELS_API_KEY, PIXABAY_API_KEY, OUTPUT_BASE_DIR

AGNES_API_URL = "https://apihub.agnes-ai.com/v1"


class VideoEditor:
    def __init__(self):
        self.agnes_key = AGNES_API_KEY
        self.pexels_key = PEXELS_API_KEY
        self.pixabay_key = PIXABAY_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.pexels.com/"
        })

    # ============================================================
    # AGNES AI — ГЕНЕРАЦИЯ КЛЮЧЕВЫХ СЦЕН
    # ============================================================

    def _agnes_create_task(self, prompt, duration=12):
        """Создаёт задачу на генерацию видео в Agnes AI."""
        url = f"{AGNES_API_URL}/videos"
        headers = {
            "Authorization": f"Bearer {self.agnes_key}",
            "Content-Type": "application/json"
        }
        num_frames = min(int(duration * 24), 441)
        num_frames = (num_frames // 8) * 8 + 1  # 8n+1

        payload = {
            "model": "agnes-video-v2.0",
            "prompt": prompt,
            "height": 768,
            "width": 1152,
            "num_frames": num_frames,
            "frame_rate": 24
        }
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code != 200:
            raise Exception(f"Agnes create error: {response.status_code} - {response.text}")
        data = response.json()
        return data.get("video_id") or data.get("id") or data.get("task_id")

    def _agnes_poll_result(self, video_id, max_wait=600):
        """Ждёт завершения генерации и возвращает URL видео."""
        url = f"https://apihub.agnes-ai.com/agnesapi?video_id={video_id}"
        start = time.time()
        while time.time() - start < max_wait:
            time.sleep(10)
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                continue
            data = response.json()
            status = data.get("status")
            print(f"   Agnes статус: {status}")
            if status == "completed":
                return data.get("video_url") or data.get("url")
            elif status == "failed":
                raise Exception(f"Agnes generation failed: {data}")
        raise Exception("Agnes: превышено время ожидания")

    def _download_file(self, url, filename):
        r = requests.get(url, stream=True, timeout=60)
        if r.status_code != 200:
            raise Exception(f"Download failed: {r.status_code}")
        with open(filename, "wb") as f:
            for chunk in r.iter_content(1024):
                if chunk:
                    f.write(chunk)
        return filename

    def _generate_agnes_clip(self, prompt, index, video_dir, duration=12):
        """Генерирует одну ключевую сцену через Agnes AI."""
        try:
            print(f"🎬 Agnes сцена #{index}: {prompt[:60]}...")
            video_id = self._agnes_create_task(prompt, duration=duration)
            print(f"   Задача создана: {video_id}")
            video_url = self._agnes_poll_result(video_id)
            if not video_url:
                return None
            path = os.path.join(video_dir, f"agnes_{index}.mp4")
            self._download_file(video_url, path)
            print(f"   ✅ Скачано: {path}")
            time.sleep(30)  # пауза для соблюдения RPM
            return path
        except Exception as e:
            print(f"   ⚠️ Agnes сцена #{index} не удалась: {e}")
            return None

    def _plan_scenes(self, script, budget_seconds=480):
        """Планирует, сколько секунд Agnes тратить на видео."""
        sentences = [s.strip() for s in script.replace('\n', ' ').split('.') if len(s.strip()) > 40]
        if not sentences:
            sentences = ["cyber security concept"]

        n_clips = budget_seconds // 12
        step = max(1, len(sentences) // n_clips)
        prompts = []
        for i in range(0, len(sentences), step):
            if len(prompts) >= n_clips:
                break
            prompt = sentences[i][:200]
            prompts.append(prompt)
        return prompts

    # ============================================================
    # PEXELS + PIXABAY — ФОНОВЫЙ ВИДЕОРЯД
    # ============================================================

    def _pexels_search(self, query, max_results=30):
        r = self.session.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": self.pexels_key},
            params={"query": query, "per_page": max_results}
        )
        if r.status_code != 200:
            return []
        data = r.json()
        links = []
        for v in data.get("videos", []):
            for vf in v.get("video_files", []):
                if vf.get("file_type") == "video/mp4" and vf.get("quality") in ["hd", "sd"]:
                    links.append(vf.get("link"))
                    break
        return links

    def _pixabay_search(self, query, max_results=30):
        """Pixabay API — резервный источник видео."""
        if not self.pixabay_key:
            return []
        url = "https://pixabay.com/api/videos/"
        params = {
            "key": self.pixabay_key,
            "q": query,
            "per_page": min(max_results, 200),
            "safesearch": "true"
        }
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code != 200:
                return []
            data = r.json()
            links = []
            for v in data.get("hits", []):
                video_info = v.get("videos", {})
                for quality in ["large", "medium", "small"]:
                    if quality in video_info and video_info[quality].get("url"):
                        links.append(video_info[quality]["url"])
                        break
            return links
        except Exception as e:
            print(f"⚠️ Pixabay error: {e}")
            return []

    def _download_stock_clip(self, url, path, retries=3):
        for attempt in range(retries):
            try:
                r = self.session.get(url, stream=True, timeout=30)
                if r.status_code == 200:
                    with open(path, "wb") as f:
                        for chunk in r.iter_content(1024):
                            if chunk:
                                f.write(chunk)
                    if os.path.getsize(path) > 100 * 1024:
                        return path
                time.sleep(2 ** attempt)
            except:
                continue
        raise Exception("Stock download failed")

    def _collect_stock_clips(self, script, video_dir, target_duration=600):
        """Собирает фоновые клипы с Pexels, при неудаче — с Pixabay."""
        words = script.replace('\n', ' ').split()[:5]
        q = " ".join(words) if words else "cyber security"
        queries = [q, "cyber security", "technology", "computer", "hacker", "network",
                   "digital", "coding", "data", "server", "internet", "phishing",
                   "malware", "firewall", "encryption", "cyber attack", "data breach"]

        all_links = []
        for query in queries:
            try:
                links = self._pexels_search(query, max_results=30)
                all_links.extend(links)
                if not links:
                    links = self._pixabay_search(query, max_results=30)
                    all_links.extend(links)
            except:
                continue
            if len(all_links) > 80:
                break

        clips = []
        total = 0
        for i, url in enumerate(all_links):
            if total >= target_duration:
                break
            try:
                path = os.path.join(video_dir, f"stock_{i}.mp4")
                self._download_stock_clip(url, path)
                clip = VideoFileClip(path)
                if clip.duration < 2.5:
                    continue
                clip = clip.resize(height=1080).crop(
                    x_center=clip.w / 2, y_center=clip.h / 2,
                    width=1920, height=1080
                )
                clips.append(clip)
                total += clip.duration
                print(f"   ✅ Stock клип {i}: {clip.duration:.1f}s (итого {total:.0f}s)")
            except Exception as e:
                print(f"   ⚠️ Stock клип {i} пропущен: {e}")
                continue
        return clips

    # ============================================================
    # ОСНОВНОЙ RUN — ГИБРИД
    # ============================================================

    def run(self, script, output_format='full', max_duration=60):
        video_dir = os.path.join(OUTPUT_BASE_DIR, "video")
        os.makedirs(video_dir, exist_ok=True)

        audio_path = os.path.join(OUTPUT_BASE_DIR, "audio", "audio.mp3")
        target_duration = 600
        if os.path.exists(audio_path):
            try:
                target_duration = AudioFileClip(audio_path).duration + 10
            except:
                pass

        # === 1. Agnes AI — ключевые сцены ===
        print("🎬 Генерация ключевых сцен через Agnes AI (до 500 сек)...")
        agnes_prompts = self._plan_scenes(script, budget_seconds=480)
        agnes_clips = []
        for i, prompt in enumerate(agnes_prompts):
            clip_path = self._generate_agnes_clip(prompt, i, video_dir, duration=12)
            if clip_path:
                try:
                    clip = VideoFileClip(clip_path)
                    clip = clip.resize(height=1080).crop(
                        x_center=clip.w / 2, y_center=clip.h / 2,
                        width=1920, height=1080
                    )
                    agnes_clips.append(clip)
                except Exception as e:
                    print(f"   ⚠️ Ошибка обработки Agnes клипа: {e}")

        # === 2. Стоки — фоновый видеоряд ===
        print("🎬 Сбор фоновых клипов (Pexels / Pixabay)...")
        stock_clips = self._collect_stock_clips(script, video_dir, target_duration)

        if not stock_clips and not agnes_clips:
            print("⚠️ Нет клипов для сборки")
            return None

        # === 3. Сборка финального видео ===
        print("🎬 Сборка финального видео...")
        if agnes_clips and stock_clips:
            final_clips = [agnes_clips[0]]  # хук
            n_agnes = len(agnes_clips) - 1
            n_stock = len(stock_clips)
            if n_agnes > 0:
                step = max(1, n_stock // (n_agnes + 1))
                agnes_idx = 1
                for i, clip in enumerate(stock_clips):
                    final_clips.append(clip)
                    if agnes_idx < len(agnes_clips) and (i + 1) % step == 0:
                        final_clips.append(agnes_clips[agnes_idx])
                        agnes_idx += 1
            else:
                final_clips.extend(stock_clips)
        else:
            final_clips = agnes_clips + stock_clips

        if not final_clips:
            return None

        final = concatenate_videoclips(final_clips, method="compose")

        if os.path.exists(audio_path):
            audio = AudioFileClip(audio_path)
            if final.duration < audio.duration:
                loop = final_clips.copy()
                while final.duration < audio.duration:
                    final = concatenate_videoclips([final] + loop, method="compose")
            final = final.subclip(0, audio.duration).set_audio(audio)

        if output_format == 'shorts' and final.duration > max_duration:
            final = final.subclip(0, max_duration)

        out = os.path.join(video_dir, f"video_{output_format}.mp4")
        final.write_videofile(
            out, codec="libx264", audio_codec="aac",
            verbose=False, logger=None
        )
        print(f"✅ Финальное видео сохранено: {out}")
        return out
