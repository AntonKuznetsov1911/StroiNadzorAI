"""
Модуль для обработки голосовых сообщений
ОТКЛЮЧЕНО: требует OpenAI Whisper API
"""

import os
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Голосовые сообщения отключены (требуется OpenAI API)
openai_client = None

logger.info("ℹ️ OpenAI API key не найден. Голосовые сообщения отключены (используйте только текст и изображения)")

# Папка для временных голосовых файлов
VOICE_TEMP_DIR = Path("voice_temp")
VOICE_TEMP_DIR.mkdir(exist_ok=True)


async def transcribe_voice(voice_file_path: str) -> dict:
    """
    Распознаёт голосовое сообщение в текст
    ОТКЛЮЧЕНО: требует OpenAI Whisper API

    Args:
        voice_file_path: путь к голосовому файлу

    Returns:
        dict: {"success": bool, "text": str, "error": str}
    """
    return {
        "success": False,
        "text": "",
        "error": "Голосовые сообщения отключены. Используйте текст или отправьте фото."
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
    ОТКЛЮЧЕНО: требует OpenAI Whisper API

    Args:
        bot: экземпляр бота
        voice_file_id: ID голосового файла в Telegram
        user_id: ID пользователя

    Returns:
        dict: {"success": bool, "text": str, "error": str}
    """
    return {
        "success": False,
        "text": "",
        "error": "Голосовые сообщения отключены. Пожалуйста, напишите текстом или отправьте фото."
    }


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
