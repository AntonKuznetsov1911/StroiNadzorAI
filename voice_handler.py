"""
Обработчик голосовых сообщений v3.1
Распознавание речи через OpenAI Whisper API
"""

import os
import logging
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
import anthropic

logger = logging.getLogger(__name__)

# Проверка доступности OpenAI для Whisper
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("⚠️ OpenAI не установлен. Установите: pip install openai")

# API ключ
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY and OPENAI_AVAILABLE:
    openai.api_key = OPENAI_API_KEY
    logger.info("✅ OpenAI Whisper API доступен для голосовых сообщений")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка голосовых сообщений

    1. Скачать голосовое сообщение
    2. Преобразовать в текст (Whisper API)
    3. Обработать как обычный текстовый вопрос
    4. Вернуть ответ
    """

    if not OPENAI_AVAILABLE or not OPENAI_API_KEY:
        await update.message.reply_text(
            "❌ **Голосовые сообщения временно недоступны**\n\n"
            "Причина: OpenAI Whisper API не настроен.\n\n"
            "Пожалуйста, отправьте ваш вопрос текстом.\n\n"
            "_Функция будет доступна в следующем обновлении._",
            parse_mode='Markdown'
        )
        return

    try:
        # Уведомляем пользователя
        processing_msg = await update.message.reply_text(
            "🎤 Обрабатываю голосовое сообщение...\n"
            "⏳ Распознаю речь..."
        )

        # Получаем файл голосового сообщения
        voice = update.message.voice
        voice_file = await voice.get_file()

        # Создаём временную папку если не существует
        temp_dir = Path("temp_voice")
        temp_dir.mkdir(exist_ok=True)

        # Скачиваем файл
        user_id = update.effective_user.id
        voice_path = temp_dir / f"voice_{user_id}_{voice.file_id}.ogg"
        await voice_file.download_to_drive(str(voice_path))

        logger.info(f"Голосовое сообщение скачано: {voice_path}")

        # Распознаём речь через Whisper API
        await processing_msg.edit_text(
            "🎤 Голосовое сообщение получено\n"
            "🔄 Распознаю текст..."
        )

        with open(voice_path, "rb") as audio_file:
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ru"  # Русский язык
            )

        recognized_text = transcript.text
        logger.info(f"Распознан текст: {recognized_text}")

        # Удаляем временный файл
        voice_path.unlink()

        # Показываем распознанный текст
        await processing_msg.edit_text(
            f"✅ **Распознано:**\n_{recognized_text}_\n\n"
            "💬 Отвечаю на ваш вопрос...",
            parse_mode='Markdown'
        )

        # Обрабатываем как текстовый вопрос
        # Удаляем сообщение о обработке и показываем распознанный текст
        await processing_msg.delete()

        # Показываем что распознали
        await update.message.reply_text(
            f"🎤 **Распознано:**\n_{recognized_text}_\n\n"
            "💬 Отвечаю на ваш вопрос...",
            parse_mode='Markdown'
        )

        # Теперь обрабатываем через handle_text, создавая временное обновление
        # Создаём фейковое текстовое сообщение для обработки
        from bot import handle_text

        # Заменяем текст в update на распознанный
        update.message.text = recognized_text

        # Вызываем стандартный обработчик текста
        await handle_text(update, context)

        logger.info(f"Голосовое сообщение обработано для пользователя {user_id}")

    except Exception as e:
        logger.error(f"Ошибка обработки голосового сообщения: {e}")
        await update.message.reply_text(
            f"❌ **Ошибка обработки голосового сообщения**\n\n"
            f"Причина: {str(e)}\n\n"
            "Попробуйте:\n"
            "• Записать более чёткое сообщение\n"
            "• Отправить вопрос текстом\n"
            "• Обратиться к администратору",
            parse_mode='Markdown'
        )


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка аудио файлов (отличаются от voice messages)
    Поддерживаются форматы: mp3, mp4, mpeg, mpga, m4a, wav, webm
    """

    if not OPENAI_AVAILABLE or not OPENAI_API_KEY:
        await update.message.reply_text(
            "❌ Аудио файлы не поддерживаются.\n"
            "Используйте голосовые сообщения или текст.",
            parse_mode='Markdown'
        )
        return

    try:
        processing_msg = await update.message.reply_text(
            "🎵 Обрабатываю аудио файл...\n"
            "⏳ Это может занять некоторое время..."
        )

        audio = update.message.audio
        audio_file = await audio.get_file()

        # Проверяем размер файла (лимит Whisper: 25 MB)
        if audio.file_size > 25 * 1024 * 1024:
            await processing_msg.edit_text(
                "❌ Файл слишком большой.\n"
                "Максимальный размер: 25 МБ"
            )
            return

        # Создаём временную папку
        temp_dir = Path("temp_audio")
        temp_dir.mkdir(exist_ok=True)

        user_id = update.effective_user.id
        # Определяем расширение файла
        file_ext = Path(audio.file_name).suffix if audio.file_name else ".mp3"
        audio_path = temp_dir / f"audio_{user_id}_{audio.file_id}{file_ext}"

        await audio_file.download_to_drive(str(audio_path))

        # Распознаём речь
        await processing_msg.edit_text(
            "🎵 Аудио файл получен\n"
            "🔄 Распознаю текст..."
        )

        with open(audio_path, "rb") as audio_file:
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ru"
            )

        recognized_text = transcript.text

        # Удаляем временный файл
        audio_path.unlink()

        # Показываем результат
        await processing_msg.edit_text(
            f"✅ **Распознано из аудио:**\n_{recognized_text}_\n\n"
            "💬 Отвечаю на ваш вопрос...",
            parse_mode='Markdown'
        )

        # Обрабатываем как текстовый вопрос
        await processing_msg.delete()

        await update.message.reply_text(
            f"🎵 **Распознано из аудио:**\n_{recognized_text}_\n\n"
            "💬 Отвечаю на ваш вопрос...",
            parse_mode='Markdown'
        )

        # Вызываем стандартный обработчик текста
        from bot import handle_text
        update.message.text = recognized_text
        await handle_text(update, context)

    except Exception as e:
        logger.error(f"Ошибка обработки аудио: {e}")
        await update.message.reply_text(
            f"❌ **Ошибка обработки аудио**\n\n{str(e)}",
            parse_mode='Markdown'
        )


# ========================================
# ИНФОРМАЦИЯ О ГОЛОСОВЫХ СООБЩЕНИЯХ
# ========================================

def get_voice_info():
    """Получить информацию о статусе голосовых сообщений"""
    if OPENAI_AVAILABLE and OPENAI_API_KEY:
        return (
            "✅ **Голосовые сообщения доступны**\n\n"
            "Вы можете отправить голосовое сообщение, и я:\n"
            "1. Распознаю вашу речь\n"
            "2. Отвечу на ваш вопрос\n\n"
            "**Поддерживаются:**\n"
            "• Голосовые сообщения Telegram\n"
            "• Аудио файлы (до 25 МБ)\n"
            "• Форматы: mp3, mp4, m4a, wav, webm\n\n"
            "**Технология:** OpenAI Whisper API\n"
            "**Язык:** Русский + Английский"
        )
    else:
        return (
            "⚠️ **Голосовые сообщения временно недоступны**\n\n"
            "Причина: OpenAI Whisper API не настроен\n\n"
            "Пожалуйста, используйте текстовые сообщения.\n"
            "Функция будет доступна в следующем обновлении."
        )
