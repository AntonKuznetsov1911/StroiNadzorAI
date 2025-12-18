"""
Модуль для обработки голосовых сообщений
Поддержка: Google Gemini API, Vosk (офлайн)
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

# Gemini клиент
gemini_client = None
GEMINI_VOICE_ENABLED = False

# Vosk модель
vosk_model = None
VOSK_ENABLED = False

# Приоритет движков: 1) Gemini  2) Vosk
VOICE_ENGINE = None  # "gemini" или "vosk"


def init_gemini_voice():
    """Инициализация Gemini для голоса"""
    global gemini_client, GEMINI_VOICE_ENABLED

    try:
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key:
            gemini_client = genai.Client(api_key=api_key)
            GEMINI_VOICE_ENABLED = True
            logger.info("✅ Gemini Voice инициализирован")
            return True
    except ImportError:
        logger.debug("google-genai не установлен")
    except Exception as e:
        logger.warning(f"Ошибка инициализации Gemini Voice: {e}")

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

    # Пробуем Gemini (приоритет)
    if init_gemini_voice():
        VOICE_ENGINE = "gemini"
        logger.info("🎤 Голосовой движок: Gemini API")
        return True

    # Пробуем Vosk (fallback)
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
    """
    Конвертирует OGG в WAV для Vosk

    Args:
        ogg_path: путь к OGG файлу

    Returns:
        путь к WAV файлу или None
    """
    try:
        wav_path = ogg_path.replace('.ogg', '.wav')

        # Используем ffmpeg для конвертации
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', ogg_path, '-ar', '16000', '-ac', '1', wav_path],
            capture_output=True,
            timeout=30
        )

        if result.returncode == 0 and Path(wav_path).exists():
            return wav_path

        logger.warning(f"ffmpeg вернул код {result.returncode}")
        return None

    except FileNotFoundError:
        logger.warning("ffmpeg не установлен. Установите: apt install ffmpeg")
        return None
    except Exception as e:
        logger.error(f"Ошибка конвертации аудио: {e}")
        return None


# ========================================
# РАСПОЗНАВАНИЕ ЧЕРЕЗ GEMINI
# ========================================

async def transcribe_with_gemini(audio_path: str) -> dict:
    """Распознавание через Gemini API"""

    if not GEMINI_VOICE_ENABLED or not gemini_client:
        return {"success": False, "text": "", "error": "Gemini не инициализирован"}

    try:
        import base64

        file_path = Path(audio_path)
        with open(file_path, "rb") as f:
            audio_data = f.read()

        # Определяем MIME тип
        suffix = file_path.suffix.lower()
        mime_types = {
            ".ogg": "audio/ogg",
            ".oga": "audio/ogg",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/mp4",
            ".webm": "audio/webm"
        }
        mime_type = mime_types.get(suffix, "audio/ogg")

        # Кодируем в base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        loop = asyncio.get_event_loop()

        def _transcribe():
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    {
                        "role": "user",
                        "parts": [
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": audio_base64
                                }
                            },
                            {
                                "text": "Расшифруй это голосовое сообщение на русском языке. "
                                       "Верни только текст сообщения без комментариев. "
                                       "Если речь неразборчива, напиши '[неразборчиво]'."
                            }
                        ]
                    }
                ]
            )
            return response.text if response.text else ""

        text = await loop.run_in_executor(None, _transcribe)

        if text:
            return {"success": True, "text": text.strip(), "error": "", "engine": "gemini"}
        else:
            return {"success": False, "text": "", "error": "Пустой ответ от Gemini"}

    except Exception as e:
        logger.error(f"Ошибка Gemini: {e}")
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

        # Конвертируем в WAV если нужно
        if audio_path.endswith('.ogg'):
            wav_path = convert_ogg_to_wav(audio_path)
            if not wav_path:
                return {"success": False, "text": "", "error": "Не удалось конвертировать аудио"}
        else:
            wav_path = audio_path

        loop = asyncio.get_event_loop()

        def _transcribe():
            wf = wave.open(wav_path, "rb")

            # Проверяем формат
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                return {"success": False, "text": "", "error": "Неподдерживаемый формат аудио"}

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

            # Финальный результат
            final = json.loads(rec.FinalResult())
            if final.get('text'):
                results.append(final['text'])

            wf.close()

            return " ".join(results).strip()

        text = await loop.run_in_executor(None, _transcribe)

        # Удаляем временный WAV
        if wav_path != audio_path:
            try:
                Path(wav_path).unlink(missing_ok=True)
            except:
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

    Автоматически выбирает движок:
    1. Gemini (если есть API ключ)
    2. Vosk (офлайн fallback)

    Args:
        voice_file_path: путь к голосовому файлу

    Returns:
        dict: {"success": bool, "text": str, "error": str, "engine": str}
    """
    if not VOICE_ENGINE:
        return {
            "success": False,
            "text": "",
            "error": "Голосовые сообщения отключены. Нужен GEMINI_API_KEY или Vosk модель."
        }

    logger.info(f"🎤 Распознавание голоса ({VOICE_ENGINE}): {voice_file_path}")

    # Используем выбранный движок
    if VOICE_ENGINE == "gemini":
        result = await transcribe_with_gemini(voice_file_path)

        # Если Gemini не сработал — пробуем Vosk
        if not result["success"] and VOSK_ENABLED:
            logger.info("Gemini не сработал, пробуем Vosk...")
            result = await transcribe_with_vosk(voice_file_path)

    elif VOICE_ENGINE == "vosk":
        result = await transcribe_with_vosk(voice_file_path)

    else:
        result = {"success": False, "text": "", "error": "Неизвестный движок"}

    if result["success"]:
        logger.info(f"✅ Распознано ({result.get('engine', '?')}): {result['text'][:100]}...")

    return result


async def download_voice_file(bot, file_id: str, user_id: int) -> str:
    """
    Скачивает голосовое сообщение из Telegram

    Args:
        bot: экземпляр бота
        file_id: ID файла в Telegram
        user_id: ID пользователя

    Returns:
        str: путь к скачанному файлу
    """
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
    """
    Полная обработка голосового сообщения

    Args:
        bot: экземпляр бота
        voice_file_id: ID голосового файла в Telegram
        user_id: ID пользователя

    Returns:
        dict: {"success": bool, "text": str, "error": str}
    """
    if not VOICE_ENGINE:
        return {
            "success": False,
            "text": "",
            "error": "🎤 Голосовые сообщения отключены.\n\n"
                    "Варианты включения:\n"
                    "1️⃣ Добавьте GEMINI_API_KEY (https://aistudio.google.com/apikey)\n"
                    "2️⃣ Установите Vosk: pip install vosk\n"
                    "   Скачайте модель: vosk-model-small-ru-0.22"
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
                # Удаляем и WAV если был создан
                wav_path = file_path.replace('.ogg', '.wav')
                Path(wav_path).unlink(missing_ok=True)
            except:
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
