"""
Интеграция OpenAI Realtime API с Telegram ботом

Позволяет прорабам общаться с ботом голосом в реальном времени
используя OpenAI вместо Gemini Live API
"""

import logging
import subprocess
import tempfile
import os
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from io import BytesIO
import asyncio

from openai_realtime_api import TelegramRealtimeAssistant, is_openai_realtime_available

logger = logging.getLogger(__name__)

# Глобальный ассистент
realtime_assistant: Optional[TelegramRealtimeAssistant] = None

# Состояния разговора
REALTIME_CONVERSATION = 1


def init_realtime_assistant() -> bool:
    """Инициализация Realtime ассистента"""
    global realtime_assistant

    if not is_openai_realtime_available():
        logger.warning("⚠️ OPENAI_API_KEY не найден, Realtime API недоступен")
        return False

    try:
        realtime_assistant = TelegramRealtimeAssistant()
        logger.info("✅ OpenAI Realtime ассистент инициализирован")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации: {e}")
        return False


def convert_ogg_to_pcm(ogg_bytes: bytes) -> Optional[bytes]:
    """Конвертирует OGG в PCM16 24kHz mono для OpenAI"""
    try:
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as ogg_file:
            ogg_file.write(ogg_bytes)
            ogg_path = ogg_file.name

        pcm_path = ogg_path.replace('.ogg', '.pcm')

        # Конвертируем через ffmpeg
        result = subprocess.run(
            [
                'ffmpeg', '-y', '-i', ogg_path,
                '-f', 's16le',  # PCM 16-bit signed little-endian
                '-acodec', 'pcm_s16le',
                '-ar', '24000',  # 24kHz для OpenAI Realtime
                '-ac', '1',  # mono
                pcm_path
            ],
            capture_output=True,
            timeout=30
        )

        if result.returncode == 0 and os.path.exists(pcm_path):
            with open(pcm_path, 'rb') as f:
                pcm_bytes = f.read()

            # Удаляем временные файлы
            os.unlink(ogg_path)
            os.unlink(pcm_path)

            return pcm_bytes

        os.unlink(ogg_path)
        return None

    except FileNotFoundError:
        logger.warning("⚠️ ffmpeg не установлен")
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка конвертации: {e}")
        return None


def convert_pcm_to_ogg(pcm_bytes: bytes) -> Optional[bytes]:
    """Конвертирует PCM16 24kHz в OGG для Telegram"""
    try:
        with tempfile.NamedTemporaryFile(suffix='.pcm', delete=False) as pcm_file:
            pcm_file.write(pcm_bytes)
            pcm_path = pcm_file.name

        ogg_path = pcm_path.replace('.pcm', '.ogg')

        # Конвертируем через ffmpeg
        result = subprocess.run(
            [
                'ffmpeg', '-y',
                '-f', 's16le',
                '-ar', '24000',
                '-ac', '1',
                '-i', pcm_path,
                '-c:a', 'libopus',
                '-b:a', '64k',
                ogg_path
            ],
            capture_output=True,
            timeout=30
        )

        if result.returncode == 0 and os.path.exists(ogg_path):
            with open(ogg_path, 'rb') as f:
                ogg_bytes = f.read()

            os.unlink(pcm_path)
            os.unlink(ogg_path)

            return ogg_bytes

        os.unlink(pcm_path)
        return None

    except FileNotFoundError:
        logger.warning("⚠️ ffmpeg не установлен")
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка конвертации: {e}")
        return None


# ============================================================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================================================

async def start_realtime_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /realtime_chat - Начать голосовой разговор через OpenAI

    Использование: /realtime_chat
    """
    if not realtime_assistant:
        await update.message.reply_text(
            "❌ Real-time ассистент недоступен.\n"
            "Требуется настроить OPENAI_API_KEY."
        )
        return ConversationHandler.END

    user_id = update.effective_user.id
    chat_id = update.message.chat_id

    # Callback для отправки аудио ответа
    async def send_voice_response(pcm_audio: bytes):
        """Конвертируем PCM в OGG и отправляем"""
        try:
            ogg_audio = convert_pcm_to_ogg(pcm_audio)

            if ogg_audio:
                audio_file = BytesIO(ogg_audio)
                audio_file.name = "response.ogg"

                await context.bot.send_voice(
                    chat_id=chat_id,
                    voice=audio_file,
                    caption="🔊 OpenAI Realtime"
                )
            else:
                logger.error("❌ Не удалось конвертировать аудио")

        except Exception as e:
            logger.error(f"❌ Ошибка отправки: {e}")

    # Callback для текстовой транскрипции
    async def send_transcript(text: str):
        """Отправляем транскрипцию как текст"""
        if text and len(text) > 10:  # Только если есть осмысленный текст
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"📝 _{text}_",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"❌ Ошибка отправки транскрипции: {e}")

    # Запускаем сессию
    success = await realtime_assistant.start_conversation(
        user_id=user_id,
        on_audio_ready=send_voice_response,
        on_text_ready=send_transcript
    )

    if success:
        # Даём время на установку соединения
        await asyncio.sleep(1)

        # Бот поздоровается
        session = realtime_assistant.active_sessions.get(user_id)
        if session:
            await session.send_text(
                "Привет! Я твой голосовой помощник по строительству. "
                "Готов ответить на вопросы по нормативам, безопасности и расчётам. "
                "Что тебя интересует?"
            )

        # UI с кнопкой завершения
        keyboard = [
            [InlineKeyboardButton("🛑 Завершить разговор", callback_data="stop_realtime_chat")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🎤 **ГОЛОСОВОЙ АССИСТЕНТ ЗАПУЩЕН**\n"
            "_(OpenAI Realtime API)_\n\n"
            "🔊 Слушаю приветствие...\n\n"
            "Теперь вы можете:\n"
            "• 🎤 Отправлять голосовые сообщения\n"
            "• 💬 Писать текстом\n\n"
            "Я отвечу вам голосом в режиме реального времени.\n\n"
            "_✨ Powered by OpenAI GPT-4o Realtime_",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

        return REALTIME_CONVERSATION
    else:
        await update.message.reply_text(
            "❌ Не удалось запустить голосовую сессию.\n"
            "Проверьте OPENAI_API_KEY и попробуйте позже."
        )
        return ConversationHandler.END


async def handle_realtime_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка голосового сообщения в Realtime режиме"""
    if not realtime_assistant:
        await update.message.reply_text("❌ Ассистент недоступен")
        return REALTIME_CONVERSATION

    user_id = update.effective_user.id

    try:
        await update.message.chat.send_action("record_voice")

        # Получаем голосовое сообщение
        voice = update.message.voice
        voice_file = await voice.get_file()
        ogg_bytes = await voice_file.download_as_bytearray()

        # Конвертируем в PCM для OpenAI
        pcm_audio = convert_ogg_to_pcm(bytes(ogg_bytes))

        if not pcm_audio:
            await update.message.reply_text(
                "❌ Не удалось обработать аудио.\n"
                "Убедитесь, что ffmpeg установлен."
            )
            return REALTIME_CONVERSATION

        # Отправляем в Realtime API
        success = await realtime_assistant.process_voice(
            user_id=user_id,
            audio_bytes=pcm_audio,
            commit=True
        )

        if success:
            logger.info(f"✅ Голосовое сообщение обработано для {user_id}")
        else:
            await update.message.reply_text(
                "❌ Ошибка обработки.\n"
                "Попробуйте ещё раз или перезапустите /realtime_chat"
            )

        return REALTIME_CONVERSATION

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        return REALTIME_CONVERSATION


async def handle_realtime_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового сообщения в Realtime режиме"""
    if not realtime_assistant:
        await update.message.reply_text("❌ Ассистент недоступен")
        return REALTIME_CONVERSATION

    user_id = update.effective_user.id
    text = update.message.text

    try:
        await update.message.chat.send_action("record_voice")

        success = await realtime_assistant.process_text(user_id, text)

        if success:
            logger.info(f"✅ Текст обработан для {user_id}")
        else:
            await update.message.reply_text(
                "⚠️ Сессия не активна.\n"
                "Запустите командой /realtime_chat"
            )

        return REALTIME_CONVERSATION

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        return REALTIME_CONVERSATION


async def stop_realtime_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Остановка Realtime разговора"""
    user_id = update.effective_user.id

    if realtime_assistant:
        stats = realtime_assistant.get_session_stats(user_id)
        transcript = realtime_assistant.get_session_transcript(user_id)

        success = await realtime_assistant.stop_conversation(user_id)

        if success:
            stats_msg = (
                f"🛑 **Голосовой разговор завершён**\n\n"
                f"📊 **Статистика сессии:**\n"
                f"• Отправлено: {stats.get('messages_sent', 0)}\n"
                f"• Получено: {stats.get('messages_received', 0)}\n"
                f"• Аудио отправлено: {stats.get('audio_chunks_sent', 0)}\n"
                f"• Аудио получено: {stats.get('audio_chunks_received', 0)}\n"
                f"• Ошибок: {stats.get('errors', 0)}\n\n"
                f"_✨ Powered by OpenAI Realtime API_"
            ) if stats else "🛑 Разговор завершён."

            await update.effective_message.reply_text(stats_msg, parse_mode="Markdown")

            # Транскрипция
            if transcript and len(transcript) > 30:
                if len(transcript) > 4000:
                    parts = [transcript[i:i+4000] for i in range(0, len(transcript), 4000)]
                    for i, part in enumerate(parts):
                        await update.effective_message.reply_text(
                            f"📝 Транскрипция ({i+1}/{len(parts)}):\n\n{part}",
                            parse_mode="Markdown"
                        )
                else:
                    await update.effective_message.reply_text(transcript, parse_mode="Markdown")
        else:
            await update.effective_message.reply_text("🛑 Разговор завершён.")
    else:
        await update.effective_message.reply_text("⚠️ Ассистент не был запущен")

    return ConversationHandler.END


async def cancel_realtime_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена разговора"""
    return await stop_realtime_chat(update, context)


# ============================================================================
# CALLBACK ОБРАБОТЧИКИ
# ============================================================================

async def realtime_chat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback кнопок"""
    query = update.callback_query
    await query.answer()

    if query.data == "stop_realtime_chat":
        return await stop_realtime_chat(update, context)

    return REALTIME_CONVERSATION


# ============================================================================
# СПРАВКА
# ============================================================================

async def realtime_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /realtime_help"""
    help_text = """🎤 **ГОЛОСОВОЙ АССИСТЕНТ (OpenAI Realtime)**

**Что это?**
Real-time голосовое общение с ботом через OpenAI GPT-4o.
Низкая задержка, высокое качество распознавания.

**Как использовать:**
1️⃣ Запустите: `/realtime_chat`
2️⃣ Отправляйте голосовые или текст
3️⃣ Получайте голосовые ответы
4️⃣ Завершите кнопкой "Завершить"

**Возможности:**
• 🎤 Голосовые вопросы → голосовые ответы
• 💬 Текст → голосовой ответ
• ⚡ Низкая задержка
• 📝 Автоматическая транскрипция
• 🎯 Контекст сохраняется

**Примеры:**
🎤 "Какой защитный слой для арматуры 16 мм?"
🎤 "Сколько бетона на плиту 6x8 метров?"
🎤 "Какая марка бетона для фундамента?"

**Команды:**
• `/realtime_chat` - Начать разговор
• `/realtime_help` - Эта справка

**Требования:**
• OPENAI_API_KEY
• ffmpeg (для конвертации аудио)

_✨ Powered by OpenAI GPT-4o Realtime API_
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")


# ============================================================================
# РЕГИСТРАЦИЯ
# ============================================================================

def register_realtime_assistant_handlers(application):
    """Регистрация обработчиков OpenAI Realtime"""
    from telegram.ext import (
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        ConversationHandler,
        filters
    )

    # ConversationHandler
    realtime_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("realtime_chat", start_realtime_chat_command)
        ],
        states={
            REALTIME_CONVERSATION: [
                MessageHandler(filters.VOICE, handle_realtime_voice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_realtime_text),
                CallbackQueryHandler(realtime_chat_callback),
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_realtime_chat),
            CommandHandler("stop", stop_realtime_chat),
        ],
        name="realtime_chat_conversation",
        persistent=False
    )

    application.add_handler(realtime_conv_handler)
    application.add_handler(CommandHandler("realtime_help", realtime_help_command))

    logger.info("✅ Обработчики OpenAI Realtime зарегистрированы")
