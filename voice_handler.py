"""
Модуль для обработки голосовых сообщений
Поддержка: OpenAI Whisper, Vosk (офлайн)
"""

import os
import logging
import asyncio
import json
import wave
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Папка для временных голосовых файлов
VOICE_TEMP_DIR = Path("voice_temp")
VOICE_TEMP_DIR.mkdir(exist_ok=True)

# Папка для Vosk моделей
VOSK_MODEL_DIR = Path("vosk_models")
VOSK_MODEL_DIR.mkdir(exist_ok=True)

# ========================================
# ИНИЦИАЛИЗАЦИЯ ДВИЖКОВ РАСПОЗНАВАНИЯ
# ========================================

# OpenAI клиент
openai_client = None
OPENAI_VOICE_ENABLED = False

# Vosk модель
vosk_model = None
VOSK_ENABLED = False

# Приоритет движков: 1) OpenAI Whisper  2) Vosk
VOICE_ENGINE = None  # "openai" или "vosk"


def init_openai_voice():
    """Инициализация OpenAI Whisper для голоса"""
    global openai_client, OPENAI_VOICE_ENABLED

    try:
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            openai_client = OpenAI(api_key=api_key)
            OPENAI_VOICE_ENABLED = True
            logger.info("✅ OpenAI Whisper инициализирован")
            return True
    except ImportError:
        logger.debug("openai не установлен")
    except Exception as e:
        logger.warning(f"Ошибка инициализации OpenAI: {e}")

    return False


def init_vosk():
    """Инициализация Vosk для офлайн распознавания"""
    global vosk_model, VOSK_ENABLED

    try:
        from vosk import Model, SetLogLevel

        # Отключаем лишние логи Vosk
        SetLogLevel(-1)

        # Ищем модель в папке vosk_models
        model_paths = [
            VOSK_MODEL_DIR / "vosk-model-small-ru-0.22",
            VOSK_MODEL_DIR / "vosk-model-ru-0.42",
            VOSK_MODEL_DIR / "model",
            Path("vosk-model-small-ru-0.22"),
            Path("vosk-model-ru"),
            Path("model"),
        ]

        for model_path in model_paths:
            if model_path.exists():
                vosk_model = Model(str(model_path))
                VOSK_ENABLED = True
                logger.info(f"✅ Vosk модель загружена: {model_path}")
                return True

        logger.warning(
            "⚠️ Vosk модель не найдена. Скачайте модель:\n"
            "   wget https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip\n"
            "   unzip vosk-model-small-ru-0.22.zip -d vosk_models/"
        )

    except ImportError:
        logger.debug("vosk не установлен (pip install vosk)")
    except Exception as e:
        logger.warning(f"Ошибка инициализации Vosk: {e}")

    return False


def init_voice_engine():
    """Инициализация движка распознавания голоса"""
    global VOICE_ENGINE

    # Пробуем OpenAI Whisper (приоритет - лучшее качество)
    if init_openai_voice():
        VOICE_ENGINE = "openai"
        logger.info("🎤 Голосовой движок: OpenAI Whisper")
        return True

    # Пробуем Vosk (офлайн fallback)
    if init_vosk():
        VOICE_ENGINE = "vosk"
        logger.info("🎤 Голосовой движок: Vosk (офлайн)")
        return True

    logger.warning("⚠️ Голосовые сообщения отключены (нет доступных движков)")
    return False


# Инициализируем при загрузке модуля
init_voice_engine()


# ========================================
# КОНВЕРТАЦИЯ АУДИО
# ========================================

def convert_ogg_to_wav(ogg_path: str) -> Optional[str]:
    """Конвертирует OGG в WAV для Vosk"""
    try:
        wav_path = ogg_path.replace('.ogg', '.wav')
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', ogg_path, '-ar', '16000', '-ac', '1', wav_path],
            capture_output=True,
            timeout=30
        )
        if result.returncode == 0 and Path(wav_path).exists():
            return wav_path
        return None
    except FileNotFoundError:
        logger.warning("ffmpeg не установлен")
        return None
    except Exception as e:
        logger.error(f"Ошибка конвертации: {e}")
        return None


def convert_ogg_to_mp3(ogg_path: str) -> Optional[str]:
    """Конвертирует OGG в MP3 для OpenAI"""
    try:
        mp3_path = ogg_path.replace('.ogg', '.mp3')
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', ogg_path, '-acodec', 'libmp3lame', '-q:a', '2', mp3_path],
            capture_output=True,
            timeout=30
        )
        if result.returncode == 0 and Path(mp3_path).exists():
            return mp3_path
        return None
    except FileNotFoundError:
        logger.warning("ffmpeg не установлен")
        return None
    except Exception as e:
        logger.error(f"Ошибка конвертации: {e}")
        return None


# ========================================
# РАСПОЗНАВАНИЕ ЧЕРЕЗ OPENAI WHISPER
# ========================================

async def transcribe_with_openai(audio_path: str) -> dict:
    """Распознавание через OpenAI Whisper API"""

    if not OPENAI_VOICE_ENABLED or not openai_client:
        return {"success": False, "text": "", "error": "OpenAI не инициализирован"}

    try:
        file_path = Path(audio_path)

        # Конвертируем OGG в MP3 если нужно (Whisper лучше работает с MP3)
        if file_path.suffix.lower() == '.ogg':
            mp3_path = convert_ogg_to_mp3(audio_path)
            if mp3_path:
                file_path = Path(mp3_path)
            # Если конвертация не удалась, пробуем с OGG

        loop = asyncio.get_event_loop()

        def _transcribe():
            with open(file_path, "rb") as audio_file:
                response = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ru",
                    response_format="text"
                )
            return response

        text = await loop.run_in_executor(None, _transcribe)

        # Удаляем временный MP3
        if str(file_path).endswith('.mp3') and file_path != Path(audio_path):
            try:
                file_path.unlink(missing_ok=True)
            except Exception:
                pass

        if text:
            return {"success": True, "text": text.strip(), "error": "", "engine": "openai"}
        else:
            return {"success": False, "text": "", "error": "Пустой ответ от Whisper"}

    except Exception as e:
        logger.error(f"Ошибка OpenAI Whisper: {e}")
        return {"success": False, "text": "", "error": str(e)}


# ========================================
# РАСПОЗНАВАНИЕ ЧЕРЕЗ VOSK
# ========================================

async def transcribe_with_vosk(audio_path: str) -> dict:
    """Распознавание через Vosk (офлайн)"""

    if not VOSK_ENABLED or not vosk_model:
        return {"success": False, "text": "", "error": "Vosk не инициализирован"}

    try:
        from vosk import KaldiRecognizer

        if audio_path.endswith('.ogg'):
            wav_path = convert_ogg_to_wav(audio_path)
            if not wav_path:
                return {"success": False, "text": "", "error": "Не удалось конвертировать аудио"}
        else:
            wav_path = audio_path

        loop = asyncio.get_event_loop()

        def _transcribe():
            wf = wave.open(wav_path, "rb")
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                return ""

            rec = KaldiRecognizer(vosk_model, wf.getframerate())
            rec.SetWords(True)

            results = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    part = json.loads(rec.Result())
                    if part.get('text'):
                        results.append(part['text'])

            final = json.loads(rec.FinalResult())
            if final.get('text'):
                results.append(final['text'])

            wf.close()
            return " ".join(results).strip()

        text = await loop.run_in_executor(None, _transcribe)

        if wav_path != audio_path:
            try:
                Path(wav_path).unlink(missing_ok=True)
            except Exception:
                pass

        if text:
            return {"success": True, "text": text, "error": "", "engine": "vosk"}
        else:
            return {"success": False, "text": "", "error": "Речь не распознана"}

    except Exception as e:
        logger.error(f"Ошибка Vosk: {e}")
        return {"success": False, "text": "", "error": str(e)}


# ========================================
# ОСНОВНЫЕ ФУНКЦИИ
# ========================================

async def transcribe_voice(voice_file_path: str) -> dict:
    """
    Распознаёт голосовое сообщение в текст

    Приоритет движков:
    1. OpenAI Whisper (лучшее качество)
    2. Vosk (офлайн fallback)
    """
    if not VOICE_ENGINE:
        return {
            "success": False, "text": "",
            "error": "Голосовые сообщения отключены. Нужен OPENAI_API_KEY или Vosk модель."
        }

    logger.info(f"🎤 Распознавание голоса ({VOICE_ENGINE}): {voice_file_path}")

    # Используем выбранный движок
    if VOICE_ENGINE == "openai":
        result = await transcribe_with_openai(voice_file_path)
        # Fallback на Vosk
        if not result["success"] and VOSK_ENABLED:
            logger.info("OpenAI не сработал, пробуем Vosk...")
            result = await transcribe_with_vosk(voice_file_path)

    elif VOICE_ENGINE == "vosk":
        result = await transcribe_with_vosk(voice_file_path)

    else:
        result = {"success": False, "text": "", "error": "Неизвестный движок"}

    if result["success"]:
        logger.info(f"✅ Распознано ({result.get('engine', '?')}): {result['text'][:100]}...")

    return result


async def download_voice_file(bot, file_id: str, user_id: int) -> str:
    """Скачивает голосовое сообщение из Telegram"""
    try:
        file = await bot.get_file(file_id)
        timestamp = int(datetime.now().timestamp())
        file_path = VOICE_TEMP_DIR / f"voice_{user_id}_{timestamp}.ogg"
        await file.download_to_drive(file_path)
        logger.info(f"✅ Голосовое сообщение скачано: {file_path}")
        return str(file_path)
    except Exception as e:
        logger.error(f"❌ Ошибка скачивания: {e}")
        raise


async def process_voice_message(bot, voice_file_id: str, user_id: int) -> dict:
    """Полная обработка голосового сообщения"""
    if not VOICE_ENGINE:
        return {
            "success": False, "text": "",
            "error": "🎤 Голосовые сообщения отключены.\n\n"
                    "Варианты включения:\n"
                    "1️⃣ OPENAI_API_KEY (лучшее качество)\n"
                    "2️⃣ Vosk модель (офлайн)"
        }

    file_path = None
    try:
        file_path = await download_voice_file(bot, voice_file_id, user_id)
        result = await transcribe_voice(file_path)
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка обработки голоса: {e}")
        return {"success": False, "text": "", "error": f"Ошибка: {str(e)}"}
    finally:
        if file_path:
            try:
                Path(file_path).unlink(missing_ok=True)
                Path(file_path.replace('.ogg', '.wav')).unlink(missing_ok=True)
                Path(file_path.replace('.ogg', '.mp3')).unlink(missing_ok=True)
            except Exception:
                pass


def cleanup_old_voice_files(max_age_hours: int = 24):
    """Очищает старые временные голосовые файлы"""
    try:
        current_time = datetime.now().timestamp()
        deleted_count = 0
        for file_path in VOICE_TEMP_DIR.glob("voice_*"):
            file_age_hours = (current_time - file_path.stat().st_mtime) / 3600
            if file_age_hours > max_age_hours:
                file_path.unlink()
                deleted_count += 1
        if deleted_count > 0:
            logger.info(f"🗑️ Удалено {deleted_count} старых голосовых файлов")
    except Exception as e:
        logger.warning(f"⚠️ Ошибка очистки: {e}")


def is_voice_enabled() -> bool:
    """Проверить, включены ли голосовые сообщения"""
    return VOICE_ENGINE is not None


def get_voice_engine() -> Optional[str]:
    """Получить текущий движок распознавания"""
    return VOICE_ENGINE
