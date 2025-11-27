"""
Модуль для обработки голосовых сообщений
Использует OpenAI Whisper API для распознавания речи
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from openai import OpenAI

logger = logging.getLogger(__name__)

# Инициализация клиентов (опционально)
openai_client = None
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if OPENAI_API_KEY and OPENAI_API_KEY.startswith('sk-'):
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("✅ OpenAI клиент инициализирован для распознавания голоса")
    except Exception as e:
        logger.warning(f"⚠️ OpenAI клиент не инициализирован: {e}")
else:
    logger.info("ℹ️ OpenAI API key не найден. Голосовые сообщения отключены (используйте только Claude API)")

# Папка для временных голосовых файлов
VOICE_TEMP_DIR = Path("voice_temp")
VOICE_TEMP_DIR.mkdir(exist_ok=True)


async def transcribe_voice(voice_file_path: str) -> dict:
    """
    Распознаёт голосовое сообщение в текст

    Args:
        voice_file_path: путь к голосовому файлу

    Returns:
        dict: {"success": bool, "text": str, "error": str}
    """
    if not openai_client:
        return {
            "success": False,
            "text": "",
            "error": "OpenAI API не настроен. Добавьте OPENAI_API_KEY в .env"
        }

    try:
        logger.info(f"🎤 Начинаем распознавание голоса: {voice_file_path}")

        # Открываем аудиофайл
        with open(voice_file_path, "rb") as audio_file:
            # Используем Whisper API
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ru"  # Русский язык
            )

        text = transcript.text.strip()
        logger.info(f"✅ Голос распознан: '{text[:50]}...'")

        return {
            "success": True,
            "text": text,
            "error": ""
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
    Полная обработка голосового сообщения

    Args:
        bot: экземпляр бота
        voice_file_id: ID голосового файла в Telegram
        user_id: ID пользователя

    Returns:
        dict: {"success": bool, "text": str, "error": str}
    """
    voice_file_path = None

    try:
        # Скачиваем голосовой файл
        voice_file_path = await download_voice_file(bot, voice_file_id, user_id)

        # Распознаём речь
        result = await transcribe_voice(voice_file_path)

        return result

    except Exception as e:
        logger.error(f"❌ Ошибка обработки голосового сообщения: {e}")
        return {
            "success": False,
            "text": "",
            "error": str(e)
        }

    finally:
        # Удаляем временный файл
        if voice_file_path and os.path.exists(voice_file_path):
            try:
                os.remove(voice_file_path)
                logger.info(f"🗑️ Временный файл удалён: {voice_file_path}")
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

        for file_path in VOICE_TEMP_DIR.glob("voice_*.ogg"):
            file_age_hours = (current_time - file_path.stat().st_mtime) / 3600

            if file_age_hours > max_age_hours:
                file_path.unlink()
                deleted_count += 1

        if deleted_count > 0:
            logger.info(f"🗑️ Удалено {deleted_count} старых голосовых файлов")

    except Exception as e:
        logger.warning(f"⚠️ Ошибка очистки старых файлов: {e}")
