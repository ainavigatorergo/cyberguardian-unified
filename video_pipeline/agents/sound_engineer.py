import asyncio
import edge_tts
import os
from agents.speech_editor import SpeechEditor
from config import OUTPUT_BASE_DIR

class SoundEngineer:
    def __init__(self, platform="youtube"):
        self.platform = platform
        self.speech_editor = SpeechEditor()

    async def _generate_tts(self, text, output_path):
        voice = "ru-RU-DmitryNeural"
        await edge_tts.Communicate(text, voice).save(output_path)

    def run(self, script):
        clean_text = self.speech_editor.run(script, platform=self.platform)
        if not clean_text or len(clean_text) < 20:
            clean_text = "Текст для озвучки не найден."

        audio_dir = os.path.join(OUTPUT_BASE_DIR, "audio")
        os.makedirs(audio_dir, exist_ok=True)
        output_path = os.path.join(audio_dir, "audio.mp3")
        asyncio.run(self._generate_tts(clean_text, output_path))
        return output_path
