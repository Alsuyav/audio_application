import os

MODELS_DIR = "models"
# Модели Vosk
MODELS = {
    "en": {
        "name": "vosk-model-small-en-us-0.15",
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
        "path": os.path.join(MODELS_DIR, "vosk-model-small-en-us-0.15")
    },
    "ru": {
        "name": "vosk-model-small-ru-0.22",
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip",
        "path": os.path.join(MODELS_DIR, "vosk-model-small-ru-0.22")
    }
}



LOG_DIR = "logs"
LOG_FILE = "transcriptions.log"
LOG_PATH = os.path.join(LOG_DIR, LOG_FILE)

TEST_DIR = "test"
TEST_AUDIO_DIR = os.path.join(TEST_DIR, "audio")
