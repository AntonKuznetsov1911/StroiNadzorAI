"""
Интеграция Gemini Live API V2 с Telegram ботом

Обновленная версия с:
- Официальным SDK от Google
- Function Calling для калькуляторов
- Улучшенной транскрипцией
"""

import logging
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from io import BytesIO
import asyncio

from gemini_live_api_v2 import GeminiLiveSessionV2, is_gemini_live_v2_available

# Импортируем распознавание голоса
try:
    from voice_handler import transcribe_voice, download_voice_file
    VOICE_RECOGNITION_AVAILABLE = True
except ImportError:
    VOICE_RECOGNITION_AVAILABLE = False

logger = logging.getLogger(__name__)

# Глобальные активные сессии
active_sessions_v2: Dict[int, GeminiLiveSessionV2] = {}

# Состояния разговора
VOICE_CONVERSATION = 1


# ============================================================================
# TELEGRAM VOICE ASSISTANT V2
# ============================================================================

class TelegramVoiceAssistantV2:
    """
    Голосовой ассистент V2 для Telegram

    Использует официальный SDK Google с Function Calling
    """

    def __init__(self):
        self.active_sessions: Dict[int, GeminiLiveSessionV2] = {}
        logger.info("🎤 Telegram Voice Assistant V2 инициализирован (SDK + Functions)")

    async def start_conversation(
        self,
        user_id: int,
        on_audio_ready: callable
    ) -> bool:
        """Начать голосовой разговор с Function Calling"""

        # Если уже есть активная сессия, остановим её
        if user_id in self.active_sessions:
            await self.stop_conversation(user_id)

        # Создаём новую сессию V2 с Function Calling
        session = GeminiLiveSessionV2(
            on_audio_received=on_audio_ready,
            enable_function_calling=True  # Включаем калькуляторы!
        )

        success = await session.start()

        if success:
            self.active_sessions[user_id] = session
            logger.info(f"✅ Голосовая сессия V2 запущена для пользователя {user_id} (Functions: ON)")
            return True
        else:
            logger.error(f"❌ Не удалось запустить сессию V2 для {user_id}")
            return False

    async def process_voice(
        self,
        user_id: int,
        audio_bytes: bytes,
        recognized_text: Optional[str] = None
    ) -> bool:
        """Обработка голосового сообщения"""
        session = self.active_sessions.get(user_id)

        if not session:
            logger.warning(f"⚠️ Нет активной сессии для пользователя {user_id}")
            return False

        return await session.send_audio(audio_bytes, user_message=recognized_text)

    async def process_image(
        self,
        user_id: int,
        image_bytes: bytes,
        caption: Optional[str] = None
    ) -> bool:
        """Обработка фото во время разговора"""
        session = self.active_sessions.get(user_id)

        if not session:
            logger.warning(f"⚠️ Нет активной сессии для пользователя {user_id}")
            return False

        # Отправляем подпись как текст
        if caption:
            return await session.send_text(f"[ФОТО] {caption}")

        return True

    async def stop_conversation(self, user_id: int) -> bool:
        """Остановить разговор"""
        session = self.active_sessions.get(user_id)

        if session:
            await session.stop()
            del self.active_sessions[user_id]
            logger.info(f"🛑 Сессия V2 остановлена для пользователя {user_id}")
            return True

        return False

    def get_session_stats(self, user_id: int) -> Optional[Dict]:
        """Получить статистику сессии"""
        session = self.active_sessions.get(user_id)
        return session.get_stats() if session else None

    def get_session_transcript(self, user_id: int) -> Optional[str]:
        """Получить транскрипцию"""
        session = self.active_sessions.get(user_id)
        return session.format_transcript() if session else None


# Глобальный экземпляр ассистента V2
voice_assistant_v2: Optional[TelegramVoiceAssistantV2] = None


def init_voice_assistant_v2() -> bool:
    """Инициализация голосового ассистента V2"""
    global voice_assistant_v2

    if not is_gemini_live_v2_available():
        logger.warning("⚠️ GOOGLE_API_KEY не найден или SDK не установлен")
        return False

    try:
        voice_assistant_v2 = TelegramVoiceAssistantV2()
        logger.info("✅ Голосовой ассистент V2 инициализирован (SDK + Function Calling)")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации голосового ассистента V2: {e}")
        return False


# ============================================================================
# КОМАНДЫ
# ============================================================================

async def start_voice_chat_command_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /voice_chat - запуск голосового ассистента V2"""

    if not voice_assistant_v2:
        await update.message.reply_text(
            "❌ Голосовой ассистент V2 недоступен.\n"
            "Требуется настроить GOOGLE_API_KEY и установить google-generativeai>=0.9.0"
        )
        return ConversationHandler.END

    user_id = update.effective_user.id

    # Callback для отправки аудио
    async def send_voice_response(audio_bytes: bytes):
        """Отправить голосовой ответ"""
        try:
            audio_file = BytesIO(audio_bytes)
            audio_file.name = "response.ogg"

            await update.message.reply_voice(
                voice=audio_file,
                caption="🔊 Gemini Live V2 (SDK)"
            )
        except Exception as e:
            logger.error(f"❌ Ошибка отправки голосового ответа: {e}")

    # Запускаем сессию
    success = await voice_assistant_v2.start_conversation(
        user_id=user_id,
        on_audio_ready=send_voice_response
    )

    if success:
        # Отправляем приветствие голосом
        session = voice_assistant_v2.active_sessions.get(user_id)
        if session:
            await asyncio.sleep(1)

            await session.send_text(
                "Привет! Я твой голосовой помощник по строительству с улучшенными функциями. "
                "Я могу рассчитать бетон и арматуру прямо во время разговора! "
                "Например, спроси: сколько бетона на плиту 6 на 8 метров толщиной 20 сантиметров?"
            )

        keyboard = [
            [InlineKeyboardButton("🛑 Завершить разговор", callback_data="stop_voice_chat")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🎤 **ГОЛОСОВОЙ АССИСТЕНТ V2 ЗАПУЩЕН**\n\n"
            "🔊 Слушаю приветствие...\n\n"
            "**✨ НОВЫЕ ВОЗМОЖНОСТИ:**\n"
            "🔧 **Function Calling** - автоматические расчёты:\n"
            "   • Расчёт бетона для плит, лент, столбов\n"
            "   • Расчёт арматуры\n"
            "   • Поиск по нормативам\n\n"
            "💬 **Попробуйте сказать:**\n"
            "   • \"Сколько бетона на плиту 6 на 8 метров 20 см?\"\n"
            "   • \"Рассчитай арматуру для плиты 10 на 10\"\n"
            "   • \"Найди защитный слой для арматуры\"\n\n"
            "📊 **Что можете:**\n"
            "• 🎤 Голосовые сообщения → голосовые ответы\n"
            "• 📸 Фото → голосовой анализ\n"
            "• 💬 Текст → голосовой ответ\n\n"
            "_✨ Gemini 2.5 Flash Native Audio + SDK + Functions_",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

        return VOICE_CONVERSATION
    else:
        await update.message.reply_text(
            "❌ Не удалось запустить голосовую сессию V2.\n"
            "Попробуйте позже."
        )
        return ConversationHandler.END


async def handle_voice_message_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка голосового сообщения в Live режиме V2"""

    if not voice_assistant_v2:
        await update.message.reply_text("❌ Голосовой ассистент V2 недоступен")
        return VOICE_CONVERSATION

    user_id = update.effective_user.id

    try:
        await update.message.chat.send_action("record_voice")

        # Получаем голос
        voice = update.message.voice
        voice_file = await voice.get_file()
        audio_bytes = await voice_file.download_as_bytearray()

        # Распознаём для транскрипции
        recognized_text = None
        if VOICE_RECOGNITION_AVAILABLE:
            try:
                file_path = await download_voice_file(
                    context.bot,
                    voice.file_id,
                    user_id
                )
                result = await transcribe_voice(file_path)
                if result.get("success"):
                    recognized_text = result.get("text")
                    logger.info(f"🎤 Распознано: {recognized_text[:100]}...")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось распознать: {e}")

        # Отправляем в Gemini Live V2 (с Function Calling!)
        success = await voice_assistant_v2.process_voice(
            user_id=user_id,
            audio_bytes=bytes(audio_bytes),
            recognized_text=recognized_text
        )

        if success:
            logger.info(f"✅ Голосовое сообщение обработано V2 для {user_id}")
        else:
            await update.message.reply_text(
                "❌ Ошибка обработки голоса.\n"
                "Попробуйте ещё раз или перезапустите с /voice_chat"
            )

        return VOICE_CONVERSATION

    except Exception as e:
        logger.error(f"❌ Ошибка обработки голоса V2: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        return VOICE_CONVERSATION


async def handle_voice_text_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текста в Live режиме V2"""

    if not voice_assistant_v2:
        await update.message.reply_text("❌ Голосовой ассистент V2 недоступен")
        return VOICE_CONVERSATION

    user_id = update.effective_user.id
    text = update.message.text

    try:
        await update.message.chat.send_action("record_voice")

        session = voice_assistant_v2.active_sessions.get(user_id)

        if session:
            await session.send_text(text)
            logger.info(f"✅ Текст обработан V2 для {user_id}")
        else:
            await update.message.reply_text(
                "⚠️ Голосовая сессия не активна.\n"
                "Запустите её командой /voice_chat"
            )

        return VOICE_CONVERSATION

    except Exception as e:
        logger.error(f"❌ Ошибка обработки текста V2: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        return VOICE_CONVERSATION


async def handle_voice_photo_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фото в Live режиме V2"""

    if not voice_assistant_v2:
        await update.message.reply_text("❌ Голосовой ассистент V2 недоступен")
        return VOICE_CONVERSATION

    user_id = update.effective_user.id

    try:
        await update.message.chat.send_action("record_voice")

        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        image_bytes = await photo_file.download_as_bytearray()

        caption = update.message.caption or "Проанализируй это фото на нарушения."

        success = await voice_assistant_v2.process_image(
            user_id=user_id,
            image_bytes=bytes(image_bytes),
            caption=caption
        )

        if success:
            logger.info(f"✅ Фото обработано V2 для {user_id}")
        else:
            await update.message.reply_text("❌ Ошибка обработки фото.")

        return VOICE_CONVERSATION

    except Exception as e:
        logger.error(f"❌ Ошибка обработки фото V2: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        return VOICE_CONVERSATION


async def stop_voice_chat_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Остановка голосового разговора V2"""

    user_id = update.effective_user.id

    if voice_assistant_v2:
        stats = voice_assistant_v2.get_session_stats(user_id)
        transcript = voice_assistant_v2.get_session_transcript(user_id)

        success = await voice_assistant_v2.stop_conversation(user_id)

        if success:
            # Отправляем статистику
            stats_msg = (
                f"🛑 **Голосовой разговор завершён** (SDK V2)\n\n"
                f"📊 **Статистика:**\n"
                f"• Отправлено сообщений: {stats.get('messages_sent', 0)}\n"
                f"• Получено сообщений: {stats.get('messages_received', 0)}\n"
                f"• Аудио фрагментов: {stats.get('audio_chunks_received', 0)}\n"
                f"• 🔧 **Функций вызвано: {stats.get('functions_called', 0)}**\n"
                f"• Ошибок: {stats.get('errors', 0)}\n\n"
                f"_✨ Gemini Live API V2 + Function Calling_"
            ) if stats else "🛑 Голосовой разговор завершён."

            await update.effective_message.reply_text(stats_msg, parse_mode="Markdown")

            # Отправляем транскрипцию
            if transcript:
                if len(transcript) > 4000:
                    parts = [transcript[i:i+4000] for i in range(0, len(transcript), 4000)]
                    for i, part in enumerate(parts):
                        await update.effective_message.reply_text(
                            f"📝 **Транскрипция (часть {i+1}/{len(parts)})**\n\n{part}",
                            parse_mode="Markdown"
                        )
                else:
                    await update.effective_message.reply_text(
                        transcript,
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


async def cancel_voice_chat_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена голосового разговора V2"""
    return await stop_voice_chat_v2(update, context)


# ============================================================================
# CALLBACK ОБРАБОТЧИКИ
# ============================================================================

async def voice_chat_callback_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback кнопок V2"""
    query = update.callback_query
    await query.answer()

    if query.data == "stop_voice_chat":
        return await stop_voice_chat_v2(update, context)

    return VOICE_CONVERSATION


# ============================================================================
# РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ
# ============================================================================

def register_voice_assistant_handlers_v2(application):
    """Регистрация обработчиков голосового ассистента V2"""
    from telegram.ext import (
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        ConversationHandler,
        filters
    )

    voice_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("voice_chat_v2", start_voice_chat_command_v2),
            CommandHandler("voice_chat", start_voice_chat_command_v2)  # Заменяем v1
        ],
        states={
            VOICE_CONVERSATION: [
                MessageHandler(filters.VOICE, handle_voice_message_v2),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_voice_text_v2),
                MessageHandler(filters.PHOTO, handle_voice_photo_v2),
                CallbackQueryHandler(voice_chat_callback_v2),
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_voice_chat_v2),
            CommandHandler("stop", stop_voice_chat_v2),
        ],
        name="voice_chat_v2_conversation",
        persistent=False
    )

    application.add_handler(voice_conv_handler)
    logger.info("✅ Обработчики голосового ассистента V2 зарегистрированы")
