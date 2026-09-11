import os
import streamlit as st
from agents.research_agent import ResearchAgent
from agents.scriptwriter import Scriptwriter
from agents.sound_engineer import SoundEngineer
from agents.video_editor import VideoEditor
from agents.seo_specialist import SEOSpecialist
from agents.rules_checker import RulesChecker
from agents.platform_adapter import PlatformAdapter
from config import OUTPUT_BASE_DIR

st.set_page_config(page_title="CyberGuardian Unified Studio", layout="wide")
st.title("🔥 CyberGuardian Unified — AI Video Studio")

# Выбор канала
channel = st.selectbox("📢 Канал", ["CyberGuardianSec (кибербезопасность)", "AI Navigator (нейросети)"])

# Ввод темы
topic = st.text_input("📝 Тема видео", placeholder="Например: Как защитить аккаунт от взлома")

# Настройки
col1, col2, col3 = st.columns(3)
with col1:
    video_format = st.radio("Формат видео", ["Полное (16:9)", "Короткое (9:16 для Shorts/TikTok)"], index=0)
with col2:
    platform = st.selectbox("Платформа", ["youtube", "shorts", "tiktok", "vk"], index=0)
with col3:
    speech_style = st.selectbox("Стиль речи", ["neutral", "energetic", "calm"], index=0)

if video_format == "Короткое (9:16 для Shorts/TikTok)":
    max_duration = st.slider("Максимальная длительность (сек)", 15, 60, 30, step=5)
else:
    max_duration = 0

if st.button("🚀 Создать видео") and topic:
    with st.spinner("🔍 Исследование..."):
        research = ResearchAgent().run(topic)
    with st.spinner("✍️ Сценарий..."):
        script = Scriptwriter().run(topic, research)
    with st.spinner("📏 Проверка правил..."):
        rules = RulesChecker().run(script)
        if "ОК" not in rules and "OK" not in rules:
            st.warning(f"⚠️ Возможные нарушения: {rules}")
            if not st.checkbox("Продолжить несмотря на предупреждение?"):
                st.stop()
    with st.spinner("🎙️ Озвучка..."):
        audio_agent = SoundEngineer(platform=platform)
        audio_path = audio_agent.run(script)
    with st.spinner("🎬 Видео (Agnes AI + стоки)..."):
        fmt = 'shorts' if video_format == "Короткое (9:16 для Shorts/TikTok)" else 'full'
        video_path = VideoEditor().run(script, output_format=fmt, max_duration=max_duration)
    with st.spinner("📊 SEO..."):
        seo = SEOSpecialist().run(topic, script)
    with st.spinner("🔄 Адаптация..."):
        adapted = PlatformAdapter().run(script, platform=platform)

    st.success("✅ Контент готов!")
    if video_path and os.path.exists(video_path):
        st.video(video_path)
        st.caption(f"📁 Видео сохранено: {video_path}")
    else:
        st.info("Видео не создано, но аудио и сценарий есть.")
    if audio_path and os.path.exists(audio_path):
        st.audio(audio_path)
        st.caption(f"📁 Аудио сохранено: {audio_path}")

    with st.expander("📄 Сценарий"):
        st.text(script)
    with st.expander("📊 SEO-метаданные"):
        st.text(seo)
    with st.expander("🔄 Адаптированный контент"):
        st.text(adapted)
    st.download_button("📥 Скачать сценарий", script, file_name="script.txt")
