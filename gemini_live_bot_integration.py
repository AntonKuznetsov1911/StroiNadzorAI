"""
Интеграция Gemini Live API с Telegram ботом

Позволяет прорабам общаться с ботом голосом в реальном времени
"""

import logging
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from io import BytesIO
import asyncio

from gemini_live_api import TelegramVoiceAssistant, is_gemini_live_available

logger = logging.getLogger(__name__)

# Глобальный ассистент
voice_assistant: Optional[TelegramVoiceAssistant] = None

# Состояния разговора
VOICE_CONVERSATION = 1


def init_voice_assistant() -> bool:
    """Инициализация голосового ассистента"""
    global voice_assistant

    if not is_gemini_live_available():
        logger.warning("⚠️ GOOGLE_API_KEY не найден, Gemini Live API недоступен")
        return False

    try:
        voice_assistant = TelegramVoiceAssistant()
        logger.info("✅ Голосовой ассистент Gemini Live API инициализирован")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации голосового ассистента: {e}")
        return False


# ============================================================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================================================

async def start_voice_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /voice_chat - Начать голосовой разговор

    Использование: /voice_chat
    """
    if not voice_assistant:
        await update.message.reply_text(
            "❌ Голосовой ассистент недоступен.\n"
            "Требуется настроить GOOGLE_API_KEY."
        )
        return ConversationHandler.END

    user_id = update.effective_user.id

    # Callback для отправки аудио ответа пользователю
    async def send_voice_response(audio_bytes: bytes):
        """Отправить голосовой ответ пользователю"""
        try:
            audio_file = BytesIO(audio_bytes)
            audio_file.name = "response.ogg"

            await update.message.reply_voice(
                voice=audio_file,
                caption="🔊 Gemini Live"
            )
        except Exception as e:
            logger.error(f"❌ Ошибка отправки голосового ответа: {e}")

    # Запускаем голосовую сессию
    success = await voice_assistant.start_conversation(
        user_id=user_id,
        on_audio_ready=send_voice_response
    )

    if success:
        # Отправляем приветствие голосом
        session = voice_assistant.active_sessions.get(user_id)
        if session:
            # Даём время на установку WebSocket соединения
            await asyncio.sleep(1)

            # Бот поздоровается голосом
            await session.send_text(
                "Привет! Я твой голосовой помощник по строительству. "
                "Я готов ответить на вопросы по нормативам, безопасности и расчётам. "
                "Что тебя интересует?"
            )

        # Показываем UI с кнопкой завершения
        keyboard = [
            [InlineKeyboardButton("🛑 Завершить разговор", callback_data="stop_voice_chat")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🎤 **ГОЛОСОВОЙ АССИСТЕНТ ЗАПУЩЕН**\n\n"
            "🔊 Слушаю приветствие...\n\n"
            "Теперь вы можете:\n"
            "• 🎤 Отправлять голосовые сообщения\n"
            "• 📸 Отправлять фото с вопросами\n"
            "• 💬 Писать текстом\n\n"
            "Я отвечу вам голосом в режиме реального времени.\n\n"
            "_✨ Gemini Live API - низкая задержка < 500ms_",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

        return VOICE_CONVERSATION
    else:
        await update.message.reply_text(
            "❌ Не удалось запустить голосовую сессию.\n"
            "Попробуйте позже."
        )
        return ConversationHandler.END


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка голосового сообщения в Live режиме
    """
    if not voice_assistant:
        await update.message.reply_text("❌ Голосовой ассистент недоступен")
        return VOICE_CONVERSATION

    user_id = update.effective_user.id

    try:
        # Показываем индикатор набора
        await update.message.chat.send_action("record_voice")

        # Получаем голосовое сообщение
        voice = update.message.voice
        voice_file = await voice.get_file()

        # Скачиваем аудио
        audio_bytes = await voice_file.download_as_bytearray()

        # Отправляем в Gemini Live API
        success = await voice_assistant.process_voice(
            user_id=user_id,
            audio_bytes=bytes(audio_bytes),
            mime_type=voice.mime_type
        )

        if success:
            # Ответ придёт через callback on_audio_ready
            logger.info(f"✅ Голосовое сообщение обработано для пользователя {user_id}")
        else:
            await update.message.reply_text(
                "❌ Ошибка обработки голосового сообщения.\n"
                "Попробуйте ещё раз или перезапустите разговор с /voice_chat"
            )

        return VOICE_CONVERSATION

    except Exception as e:
        logger.error(f"❌ Ошибка обработки голосового сообщения: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        return VOICE_CONVERSATION


async def handle_voice_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка текстового сообщения в Live режиме
    """
    if not voice_assistant:
        await update.message.reply_text("❌ Голосовой ассистент недоступен")
        return VOICE_CONVERSATION

    user_id = update.effective_user.id
    text = update.message.text

    try:
        await update.message.chat.send_action("record_voice")

        # Получаем активную сессию
        session = voice_assistant.active_sessions.get(user_id)

        if session:
            # Отправляем текст в Live режиме
            await session.send_text(text)

            # Ответ придёт голосом через callback
            logger.info(f"✅ Текст обработан для пользователя {user_id}")
        else:
            await update.message.reply_text(
                "⚠️ Голосовая сессия не активна.\n"
                "Запустите её командой /voice_chat"
            )

        return VOICE_CONVERSATION

    except Exception as e:
        logger.error(f"❌ Ошибка обработки текста: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        return VOICE_CONVERSATION


async def handle_voice_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка фото в Live режиме (мультимодальность)
    """
    if not voice_assistant:
        await update.message.reply_text("❌ Голосовой ассистент недоступен")
        return VOICE_CONVERSATION

    user_id = update.effective_user.id

    try:
        await update.message.chat.send_action("record_voice")

        # Получаем фото
        photo = update.message.photo[-1]  # Самое большое фото
        photo_file = await photo.get_file()
        image_bytes = await photo_file.download_as_bytearray()

        # Получаем подпись (если есть)
        caption = update.message.caption or "Что ты видишь на этом фото? Проверь на нарушения."

        # Отправляем в Live сессию
        success = await voice_assistant.process_image(
            user_id=user_id,
            image_bytes=bytes(image_bytes),
            caption=caption
        )

        if success:
            # Ответ придёт голосом
            logger.info(f"✅ Фото обработано для пользователя {user_id}")
        else:
            await update.message.reply_text(
                "❌ Ошибка обработки фото.\n"
                "Попробуйте ещё раз."
            )

        return VOICE_CONVERSATION

    except Exception as e:
        logger.error(f"❌ Ошибка обработки фото: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        return VOICE_CONVERSATION


async def stop_voice_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Остановка голосового разговора
    """
    user_id = update.effective_user.id

    if voice_assistant:
        # Получаем статистику перед остановкой
        stats = voice_assistant.get_session_stats(user_id)

        # Останавливаем сессию
        success = await voice_assistant.stop_conversation(user_id)

        if success and stats:
            await update.effective_message.reply_text(
                f"🛑 **Голосовой разговор завершён**\n\n"
                f"📊 **Статистика сессии:**\n"
                f"• Отправлено сообщений: {stats.get('messages_sent', 0)}\n"
                f"• Получено сообщений: {stats.get('messages_received', 0)}\n"
                f"• Аудио фрагментов отправлено: {stats.get('audio_chunks_sent', 0)}\n"
                f"• Аудио фрагментов получено: {stats.get('audio_chunks_received', 0)}\n"
                f"• Ошибок: {stats.get('errors', 0)}\n\n"
                f"_✨ Спасибо за использование Gemini Live API_",
                parse_mode="Markdown"
            )
        else:
            await update.effective_message.reply_text(
                "🛑 Голосовой разговор завершён.\n"
                "Используйте /voice_chat для нового разговора."
            )
    else:
        await update.effective_message.reply_text("⚠️ Голосовой ассистент не был запущен")

    return ConversationHandler.END


async def cancel_voice_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена голосового разговора"""
    return await stop_voice_chat(update, context)


# ============================================================================
# CALLBACK ОБРАБОТЧИКИ
# ============================================================================

async def voice_chat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback кнопок"""
    query = update.callback_query
    await query.answer()

    if query.data == "stop_voice_chat":
        return await stop_voice_chat(update, context)

    return VOICE_CONVERSATION


# ============================================================================
# КОМАНДЫ ПОМОЩИ
# ============================================================================

async def voice_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /voice_help - Справка по голосовому ассистенту"""
    help_text = """🎤 **ГОЛОСОВОЙ АССИСТЕНТ - СПРАВКА**

**Что это такое?**
Gemini Live API позволяет общаться с ботом голосом в реальном времени с минимальной задержкой (< 500ms).

**Как использовать:**
1️⃣ Запустите разговор: `/voice_chat`
2️⃣ Отправляйте голосовые сообщения, фото или текст
3️⃣ Получайте голосовые ответы от бота
4️⃣ Завершите разговор кнопкой "Завершить"

**Возможности:**
• 🎤 Голосовые вопросы и ответы
• 📸 Отправка фото во время разговора
• 💬 Текстовые сообщения (ответ голосом)
• ⚡ Низкая задержка (< 500ms)
• 🔄 Мультимодальность (голос + фото + текст)
• 🎯 Контекст разговора сохраняется

**Примеры использования:**

**1. Быстрая консультация на объекте:**
🎤 "Какой защитный слой бетона для арматуры 16 миллиметров?"
🔊 Бот: "Минимальный защитный слой составляет 40 миллиметров согласно СП 63.13330.2018 пункт 10.3.2"

**2. Проверка безопасности с фото:**
📸 [Отправляете фото рабочего]
💬 "Проверь нарушения безопасности"
🔊 Бот: "ВНИМАНИЕ! ОПАСНОСТЬ! Обнаружено нарушение: рабочий без каски на высоте. Требуется немедленно остановить работы..."

**3. Расчёты материалов:**
🎤 "Сколько бетона нужно на плиту 6 на 8 метров толщиной 20 сантиметров?"
🔊 Бот: "Потребуется 9.6 кубических метров бетона. Рекомендую заказать 10 кубов с учётом запаса."

**4. Проверка нормативов:**
🎤 "Какая марка бетона для фундамента в Москве?"
🔊 Бот: "Для Москвы рекомендуется бетон не ниже М300 класса B22.5 с морозостойкостью F200 согласно СП 22.13330.2016"

**Преимущества для прораба:**
✅ Руки свободны (в каске и перчатках)
✅ Быстрые ответы прямо на объекте
✅ Можно показать фото и получить анализ голосом
✅ Нет необходимости печатать
✅ Профессиональные консультации 24/7

**Команды:**
• `/voice_chat` - Начать разговор
• `/voice_help` - Эта справка
• Кнопка "Завершить" - Закончить разговор

**Системные требования:**
• GOOGLE_API_KEY должен быть настроен
• Интернет соединение
• Telegram с поддержкой голосовых сообщений

_✨ Powered by Gemini Live API_
"""

    await update.message.reply_text(help_text, parse_mode="Markdown")


# ============================================================================
# РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ
# ============================================================================

def register_voice_assistant_handlers(application):
    """
    Регистрация обработчиков голосового ассистента

    Args:
        application: Telegram Application
    """
    from telegram.ext import (
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        ConversationHandler,
        filters
    )

    # Conversation Handler для голосового чата
    voice_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("voice_chat", start_voice_chat_command)
        ],
        states={
            VOICE_CONVERSATION: [
                MessageHandler(filters.VOICE, handle_voice_message),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_voice_text),
                MessageHandler(filters.PHOTO, handle_voice_photo),
                CallbackQueryHandler(voice_chat_callback),
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_voice_chat),
            CommandHandler("stop", stop_voice_chat),
        ],
        name="voice_chat_conversation",
        persistent=False
    )

    application.add_handler(voice_conv_handler)
    application.add_handler(CommandHandler("voice_help", voice_help_command))

    logger.info("✅ Обработчики голосового ассистента зарегистрированы")


# ============================================================================
# УТИЛИТЫ
# ============================================================================

async def cleanup_inactive_voice_sessions():
    """Очистка неактивных голосовых сессий (запускать периодически)"""
    if voice_assistant:
        await voice_assistant.cleanup_inactive_sessions(max_idle_minutes=5)
