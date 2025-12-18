"""
Модуль для обработки голосовых сообщений
Использует Google Gemini API для распознавания речи
"""

import os
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Папка для временных голосовых файлов
VOICE_TEMP_DIR = Path("voice_temp")
VOICE_TEMP_DIR.mkdir(exist_ok=True)

# Инициализация Gemini клиента
gemini_client = None
VOICE_ENABLED = False

try:
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        gemini_client = genai.Client(api_key=api_key)
        VOICE_ENABLED = True
        logger.info("✅ Голосовые сообщения включены (Gemini API)")
    else:
        logger.warning("⚠️ GEMINI_API_KEY не найден. Голосовые сообщения отключены.")
except ImportError:
    logger.warning("⚠️ google-genai не установлен. Голосовые сообщения отключены.")
except Exception as e:
    logger.error(f"❌ Ошибка инициализации Gemini для голоса: {e}")


async def transcribe_voice(voice_file_path: str) -> dict:
    """
    Распознаёт голосовое сообщение в текст через Gemini API

    Args:
        voice_file_path: путь к голосовому файлу (OGG/MP3/WAV)

    Returns:
        dict: {"success": bool, "text": str, "error": str}
    """
    if not VOICE_ENABLED or not gemini_client:
        return {
            "success": False,
            "text": "",
            "error": "Голосовые сообщения отключены. Добавьте GEMINI_API_KEY в переменные окружения."
        }

    try:
        logger.info(f"🎤 Распознавание голоса: {voice_file_path}")

        # Читаем аудио файл
        file_path = Path(voice_file_path)
        if not file_path.exists():
            return {
                "success": False,
                "text": "",
                "error": f"Файл не найден: {voice_file_path}"
            }

        # Загружаем файл в Gemini
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

        # Отправляем в Gemini для транскрипции
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
                                    "data": audio_data
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

        transcribed_text = await loop.run_in_executor(None, _transcribe)

        if transcribed_text:
            logger.info(f"✅ Голос распознан: {transcribed_text[:100]}...")
            return {
                "success": True,
                "text": transcribed_text.strip(),
                "error": ""
            }
        else:
            return {
                "success": False,
                "text": "",
                "error": "Не удалось распознать речь. Попробуйте говорить чётче."
            }

    except Exception as e:
        logger.error(f"❌ Ошибка распознавания голоса: {e}")
        return {
            "success": False,
            "text": "",
            "error": f"Ошибка распознавания: {str(e)}"
        }


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
        # Получаем информацию о файле
        file = await bot.get_file(file_id)

        # Генерируем уникальное имя файла
        timestamp = int(datetime.now().timestamp())
        file_path = VOICE_TEMP_DIR / f"voice_{user_id}_{timestamp}.ogg"

        # Скачиваем файл
        await file.download_to_drive(file_path)

        logger.info(f"✅ Голосовое сообщение скачано: {file_path}")
        return str(file_path)

    except Exception as e:
        logger.error(f"❌ Ошибка скачивания голосового файла: {e}")
        raise


async def process_voice_message(bot, voice_file_id: str, user_id: int) -> dict:
    """
    Полная обработка голосового сообщения:
    1. Скачивание из Telegram
    2. Распознавание через Gemini
    3. Очистка временного файла

    Args:
        bot: экземпляр бота
        voice_file_id: ID голосового файла в Telegram
        user_id: ID пользователя

    Returns:
        dict: {"success": bool, "text": str, "error": str}
    """
    if not VOICE_ENABLED:
        return {
            "success": False,
            "text": "",
            "error": "🎤 Голосовые сообщения отключены.\n\n"
                    "Для включения добавьте GEMINI_API_KEY в переменные окружения.\n"
                    "Получить ключ: https://aistudio.google.com/apikey"
        }

    file_path = None
    try:
        # 1. Скачиваем файл
        file_path = await download_voice_file(bot, voice_file_id, user_id)

        # 2. Распознаём речь
        result = await transcribe_voice(file_path)

        return result

    except Exception as e:
        logger.error(f"❌ Ошибка обработки голосового сообщения: {e}")
        return {
            "success": False,
            "text": "",
            "error": f"Ошибка обработки голосового сообщения: {str(e)}"
        }
    finally:
        # 3. Удаляем временный файл
        if file_path:
            try:
                Path(file_path).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"⚠️ Не удалось удалить временный файл: {e}")


def cleanup_old_voice_files(max_age_hours: int = 24):
    """
    Очищает старые временные голосовые файлы

    Args:
        max_age_hours: максимальный возраст файлов в часах
    """
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
        logger.warning(f"⚠️ Ошибка очистки старых файлов: {e}")


def is_voice_enabled() -> bool:
    """Проверить, включены ли голосовые сообщения"""
    return VOICE_ENABLED
