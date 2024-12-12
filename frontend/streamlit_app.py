import streamlit as st
import requests

# URL базового API. Измените при необходимости.
API_URL = "http://backend:8003"

def modify_audio(file, speed, volume):
    url = f"{API_URL}/modify_audio"
    files = {"file": (file.name, file, "audio/wav")}
    data = {"speed": str(speed), "volume": str(volume)}
    try:
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        st.error(f"Ошибка при изменении аудио: {e}")
        return None

def transcribe_audio(file, lang_code):
    url = f"{API_URL}/transcribe_audio"
    files = {"file": (file.name, file, "audio/wav")}
    data = {"lang_code": lang_code}
    try:
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Ошибка при транскрипции аудио: {e}")
        return None

def main():
    st.set_page_config(page_title="Audio Processor", layout="wide")
    st.title("Audio Processor Application")

    tabs = st.tabs(["Modify Audio", "Transcribe Audio"])

    # Раздел 1: Modify Audio
    with tabs[0]:
        st.header("Изменение аудио")

        uploaded_file = st.file_uploader("Загрузите аудиофайл (WAV)", type=["wav"])

        speed = st.number_input("Коэффициент изменения скорости", min_value=0.1, max_value=3.0, value=1.0, step=0.1)
        volume = st.number_input("Коэффициент изменения громкости", min_value=0.1, max_value=3.0, value=1.0, step=0.1)

        if st.button("Изменить аудио"):
            if uploaded_file is not None:
                with st.spinner("Обработка аудио..."):
                    modified_audio = modify_audio(uploaded_file, speed, volume)
                    if modified_audio:
                        st.success("Аудио успешно изменено.")
                        st.download_button(
                            label="Скачать измененный аудиофайл",
                            data=modified_audio,
                            file_name="modified_audio.wav",
                            mime="audio/wav"
                        )
            else:
                st.warning("Пожалуйста, загрузите аудиофайл.")

    # Раздел 2: Transcribe Audio
    with tabs[1]:
        st.header("Транскрипция аудио")

        uploaded_file = st.file_uploader("Загрузите аудиофайл (WAV)", type=["wav"], key="transcribe")

        lang_code = st.selectbox("Выберите язык", options=["en", "ru"])

        if st.button("Транскрибировать"): 
            if uploaded_file is not None: 
                with st.spinner("Выполнение транскрипции..."): 
                    transcription = transcribe_audio(uploaded_file, lang_code) 
                    if transcription:
                        st.success("Транскрипция завершена.")
                        # Выводим текст по ключу "transcription"
                        st.write(transcription["transcription"]) 
                    else:
                        st.error("Транскрипция не удалась.")
            else: 
                st.warning("Пожалуйста, загрузите аудиофайл.")

if __name__ == "__main__":
    main()
