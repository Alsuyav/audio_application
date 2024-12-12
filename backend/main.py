import os
import json
import shutil
import subprocess
import tempfile
import wave
import aiofiles
import requests
import logging

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydub import AudioSegment
from pydub.effects import speedup
from vosk import Model, KaldiRecognizer

from settings import (
    MODELS_DIR,
    MODELS,
    LOG_DIR,
    LOG_PATH
)

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("baclkend")

    
def download_and_extract_model(lang_code: str):
    """
    Скачивает и извлекает модель Vosk для распознавания речи по языковому коду.

    Если модель уже существует, то она не будет скачиваться и распаковываться снова.

    :param lang_code: Языковой код ('en' или 'ru')
    :raises ValueError: если языковой код не поддерживается
    :raises Exception: если происходит ошибка скачивания или распоковки модели
    """
    model_info = MODELS.get(lang_code)
    if not model_info:
        raise ValueError(f"Неподдерживаемый язык: {lang_code}")
    else:
        model_path = model_info.get("path")
        if not os.path.exists(model_path):
            os.makedirs(MODELS_DIR, exist_ok=True)
            try:
                zip_path = os.path.join(MODELS_DIR, f"{model_info.get('name')}.zip")
                logger.info(f"Скачивание модели Vosk для языка '{lang_code}'...")
                response = requests.get(model_info.get("url"), stream=True, timeout=10)
                with open(zip_path, "wb") as f:
                    shutil.copyfileobj(response.raw, f)
                logger.info(f"Распаковка модели '{model_info.get('name')}'...")
                import zipfile
                with zipfile.ZipFile(zip_path, 'r') as zipref:
                    zipref.extractall(MODELS_DIR)
                os.remove(zip_path)
                logger.info(f"Модель '{model_info.get('name')}' успешно установлена.")
            except Exception as e:
                logger.info(f"Ошибка скачивания или распоковки модели Vosk для языка '{lang_code}': {e}")
        else:
            logger.info(f"Модель '{model_info.get('name')}' уже существует.")

def load_models():
    """
    Загрузка всех доступных моделей Vosk для распознавания речи.

    Модели загружаются из интернета, если они еще не установлены,
    иначе они загружаются из local storage.

    :return: None
    """
    for lang_code in MODELS:
        download_and_extract_model(lang_code)
        model_path = MODELS.get(lang_code).get("path")
        try:
            loaded_models[lang_code] = Model(model_path)
            logger.info(f"Модель для языка '{lang_code}' загружена успешно.")
        except Exception as e:
            logger.info(f"Ошибка загрузки модели для языка '{lang_code}': {e}")


app = FastAPI(title="Audio Processing and Transcription API")
loaded_models = {}
load_models()
os.makedirs(LOG_DIR, exist_ok=True)

@app.get("/")
async def read_root():
    return {
        "message": "Добро пожаловать в Audio Processing and Transcription API",
        "endpoints": ["/modify_audio", "/transcribe_audio", "/health_check"]
    }

@app.get("/health_check")
async def health_check():
    return {"status": "OK"}

def remove_temp_files(*file_paths) -> None:
    for file_path in file_paths:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Файл удален: {file_path}")

def is_valid_wav_file(file: UploadFile) -> bool:
    # mime_type, _ = mimetypes.guess_type(file.filename)
    # return mime_type == "audio/wav"\
    return file.filename.lower().endswith('.wav')

@app.post("/modify_audio")
async def modify_audio(
    file: UploadFile = File(...),
    speed: float = Form(1.0),
    volume: float = Form(1.0),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> FileResponse:
    """
    Изменяет аудиофайл, изменяя его скорость и/или громкость.

    Args:
        file: Аудиофайл в формате WAV.
        speed: Коэффициент изменения скорости (1.0 - original speed, > 1.0 - faster, < 1.0 - slower).
        volume: Коэффициент изменения громкости (1.0 - original volume, > 1.0 - louder, < 1.0 - quieter).

    Returns:
        Измененный аудиофайл в формате WAV.

    Raises:
        HTTPException: Ошибка при обработке аудио.
    """
    if not is_valid_wav_file(file):
        raise HTTPException(status_code=400, detail="Файл должен быть в формате WAV.")

    temp_input_path = tempfile.mktemp(suffix='.wav')
    async with aiofiles.open(temp_input_path, 'wb') as temp_input:
        content = await file.read()
        await temp_input.write(content)

    try:
        audio = AudioSegment.from_wav(temp_input_path)

        if speed != 1.0:
            audio = speedup(audio, speed)

        if volume != 1.0:
            audio += 20 * (volume - 1.0)

        temp_output_path = tempfile.mktemp(suffix='.wav')
        audio.export(temp_output_path, format="wav")

        response = FileResponse(
            path=temp_output_path,
            media_type="audio/wav",
            filename=f"modified_{file.filename}"
        )

        return response
    except Exception as e:
        raise HTTPException(status_code=500, 
                            detail=f"Ошибка обработки аудио: {str(e)}")
    finally:
        background_tasks.add_task(remove_temp_files, temp_input_path, temp_output_path)

@app.post("/transcribe_audio")
async def transcribe_audio(
    file: UploadFile = File(...),
    lang_code: str = Form(..., regex="^(en|ru)$"),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> dict:
    """
    Транскрибирует аудиофайл с помощью Vosk.

    Args:
        file: Аудиофайл в формате WAV.
        lang_code: Код языка (en, ru).

    Returns:
        Словарь с транскрипцией.

    Raises:
        HTTPException: Ошибка при обработке аудио.
    """
    if not is_valid_wav_file(file):
        raise HTTPException(status_code=400, detail="Файл должен быть в формате WAV.")

    try:
        model = loaded_models[lang_code]
    except KeyError as k:
        raise HTTPException(status_code=400, detail="Поддерживаемые языки: 'en', 'ru'.") from k

    temp_input_path = tempfile.mktemp(suffix='.wav')
    async with aiofiles.open(temp_input_path, 'wb') as temp_input:
        content = await file.read()
        await temp_input.write(content)

    try:
        # Проверка и конвертация аудио в нужный формат
        with wave.open(temp_input_path, "rb") as wf:
            to_convert = wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE"
        if to_convert:
            converted_path = tempfile.mktemp(suffix='.wav')

            command = [
                "ffmpeg", "-i", temp_input_path,
                "-ac", "1",
                "-ar", "16000",
                "-f", "wav",
                converted_path, "-y"
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                raise RuntimeError(f"Ошибка при запуске FFmpeg: {result.stderr.decode().strip()}")
        else:
            converted_path = temp_input_path


        with wave.open(converted_path, "rb") as wf_converted:
            rec = KaldiRecognizer(model, wf_converted.getframerate())
            rec.SetWords(True)

            results = []
            while True:
                data = wf_converted.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = rec.Result()
                    results.append(json.loads(result))
            final_result = json.loads(rec.FinalResult())
            results.append(final_result)
            transcription = " ".join(res.get("text", "") for res in results)

            log_entry = {
                "filename": file.filename,
                "language": lang_code,
                "transcription": transcription
            }

            async with aiofiles.open(LOG_PATH, 'a', encoding='utf-8') as logfile:
                await logfile.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

            return {"transcription": transcription}

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке аудио: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка распознавания речи: {str(e)}")
    finally:
        background_tasks.add_task(remove_temp_files, temp_input_path, converted_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
