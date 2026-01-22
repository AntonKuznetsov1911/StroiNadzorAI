"""
Голосовой чат с OpenAI (Whisper + GPT + TTS)

Простая реализация голосового ассистента:
1. Whisper - распознавание речи
2. GPT-4 - генерация ответа
3. TTS - озвучка ответа

Работает на любом OPENAI_API_KEY (не требует бета-доступа)
"""

import logging
import subprocess
import tempfile
import os
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from io import BytesIO
import asyncio
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Состояние разговора
VOICE_CONVERSATION = 1

# OpenAI клиент
openai_client: Optional[OpenAI] = None

# Системный промпт для голосового ассистента
VOICE_SYSTEM_PROMPT = """Вы — голосовой ассистент-эксперт по строительству для России.

ВАЖНО - ВЫ ОТВЕЧАЕТЕ ГОЛОСОМ:
- Отвечайте КРАТКО (2-3 предложения максимум)
- Говорите простым языком, без сложных конструкций
- Называйте номера СП/ГОСТ коротко
- При опасности говорите чётко: "Внимание! Опасность!"

Вы помогаете прорабам на стройке - у них нет времени на длинные ответы.
Язык: русский."""


def init_realtime_assistant() -> bool:
    """Инициализация голосового ассистента"""
    global openai_client

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("⚠️ OPENAI_API_KEY не найден")
        return False

    try:
        openai_client = OpenAI(api_key=api_key)
        # Проверяем что клиент работает
        openai_client.models.list()
        logger.info("✅ OpenAI Voice Assistant инициализирован (Whisper + TTS)")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации OpenAI: {e}")
        return False


def is_openai_realtime_available() -> bool:
    """Проверка доступности"""
    return openai_client is not None


def convert_ogg_to_mp3(ogg_bytes: bytes) -> Optional[bytes]:
    """Конвертирует OGG в MP3 для Whisper"""
    try:
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as ogg_file:
            ogg_file.write(ogg_bytes)
            ogg_path = ogg_file.name

        mp3_path = ogg_path.replace('.ogg', '.mp3')

        result = subprocess.run(
            ['ffmpeg', '-y', '-i', ogg_path, '-acodec', 'libmp3lame', '-q:a', '4', mp3_path],
            capture_output=True,
            timeout=30
        )

        if result.returncode == 0 and os.path.exists(mp3_path):
            with open(mp3_path, 'rb') as f:
                mp3_bytes = f.read()
            os.unlink(ogg_path)
            os.unlink(mp3_path)
            return mp3_bytes

        os.unlink(ogg_path)
        return None

    except FileNotFoundError:
        logger.warning("⚠️ ffmpeg не установлен")
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка конвертации: {e}")
        return None


async def transcribe_audio(audio_bytes: bytes) -> Optional[str]:
    """Распознавание речи через Whisper"""
    if not openai_client:
        return None

    try:
        # Конвертируем в MP3
        mp3_bytes = convert_ogg_to_mp3(audio_bytes)
        if not mp3_bytes:
            logger.error("Не удалось конвертировать аудио")
            return None

        # Создаём временный файл
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
            f.write(mp3_bytes)
            temp_path = f.name

        # Отправляем в Whisper
        with open(temp_path, 'rb') as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ru"
            )

        os.unlink(temp_path)
        return transcript.text

    except Exception as e:
        logger.error(f"❌ Ошибка Whisper: {e}")
        return None


async def generate_response(user_message: str, context_messages: list = None) -> Optional[str]:
    """Генерация ответа через GPT"""
    if not openai_client:
        return None

    try:
        messages = [{"role": "system", "content": VOICE_SYSTEM_PROMPT}]

        # Добавляем контекст если есть
        if context_messages:
            messages.extend(context_messages[-6:])  # Последние 3 обмена

        messages.append({"role": "user", "content": user_message})

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Быстрая модель для голоса
            messages=messages,
            max_tokens=150,  # Короткие ответы для голоса
            temperature=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"❌ Ошибка GPT: {e}")
        return None


async def text_to_speech(text: str) -> Optional[bytes]:
    """Преобразование текста в речь через OpenAI TTS"""
    if not openai_client:
        return None

    try:
        response = openai_client.audio.speech.create(
            model="tts-1",
            voice="onyx",  # Мужской голос, подходит для строительства
            input=text,
            response_format="opus"
        )

        return response.content

    except Exception as e:
        logger.error(f"❌ Ошибка TTS: {e}")
        return None


# ============================================================================
# ОБРАБОТЧИКИ
# ============================================================================

async def start_realtime_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /realtime_chat - Начать голосовой разговор"""

    if not openai_client:
        await update.message.reply_text(
            "❌ Голосовой ассистент недоступен.\n"
            "Требуется OPENAI_API_KEY."
        )
        return ConversationHandler.END

    user_id = update.effective_user.id

    # Очищаем контекст
    context.user_data['voice_messages'] = []

    keyboard = [
        [InlineKeyboardButton("🛑 Завершить", callback_data="stop_realtime_chat")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎤 **ГОЛОСОВОЙ АССИСТЕНТ**\n\n"
        "Отправьте голосовое сообщение — я отвечу голосом!\n\n"
        "• 🎤 Говорите кратко и чётко\n"
        "• 💬 Можно писать текстом\n"
        "• 🔊 Ответ придёт голосом\n\n"
        "_Whisper + GPT-4 + TTS_",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

    return VOICE_CONVERSATION


async def start_realtime_chat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point через callback кнопки (для ConversationHandler)"""
    query = update.callback_query
    await query.answer("🎤 Запускаю голосовой чат...")

    if not openai_client:
        await query.edit_message_text(
            "❌ Голосовой ассистент недоступен.\n"
            "Требуется OPENAI_API_KEY."
        )
        return ConversationHandler.END

    # Очищаем контекст
    context.user_data['voice_messages'] = []

    keyboard = [
        [InlineKeyboardButton("🛑 Завершить", callback_data="stop_realtime_chat")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="🎤 **ГОЛОСОВОЙ АССИСТЕНТ**\n\n"
        "Отправьте голосовое сообщение — я отвечу голосом!\n\n"
        "• 🎤 Говорите кратко и чётко\n"
        "• 💬 Можно писать текстом\n"
        "• 🔊 Ответ придёт голосом\n\n"
        "_Whisper + GPT-4 + TTS_",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

    return VOICE_CONVERSATION


async def handle_realtime_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка голосового сообщения"""

    if not openai_client:
        await update.message.reply_text("❌ Ассистент недоступен")
        return VOICE_CONVERSATION

    try:
        # Показываем что обрабатываем
        processing_msg = await update.message.reply_text("🎧 Слушаю...")

        # Скачиваем голосовое
        voice = update.message.voice
        voice_file = await voice.get_file()
        ogg_bytes = await voice_file.download_as_bytearray()

        # 1. Распознаём речь
        await processing_msg.edit_text("🎤 Распознаю речь...")
        user_text = await transcribe_audio(bytes(ogg_bytes))

        if not user_text:
            await processing_msg.edit_text("❌ Не удалось распознать речь. Попробуйте ещё раз.")
            return VOICE_CONVERSATION

        # Показываем что сказал пользователь
        await processing_msg.edit_text(f"💬 Вы: _{user_text}_\n\n⏳ Думаю...", parse_mode="Markdown")

        # 2. Генерируем ответ
        voice_messages = context.user_data.get('voice_messages', [])
        bot_response = await generate_response(user_text, voice_messages)

        if not bot_response:
            await processing_msg.edit_text("❌ Ошибка генерации ответа.")
            return VOICE_CONVERSATION

        # Сохраняем в контекст
        voice_messages.append({"role": "user", "content": user_text})
        voice_messages.append({"role": "assistant", "content": bot_response})
        context.user_data['voice_messages'] = voice_messages

        # 3. Озвучиваем ответ
        await processing_msg.edit_text(f"💬 Вы: _{user_text}_\n\n🔊 Озвучиваю...", parse_mode="Markdown")
        audio_response = await text_to_speech(bot_response)

        # Удаляем сообщение о статусе
        await processing_msg.delete()

        if audio_response:
            # Отправляем голосовой ответ
            audio_file = BytesIO(audio_response)
            audio_file.name = "response.ogg"

            await update.message.reply_voice(
                voice=audio_file,
                caption=f"📝 _{bot_response}_",
                parse_mode="Markdown"
            )
        else:
            # Если TTS не сработал, отправляем текстом
            await update.message.reply_text(
                f"💬 Вы: _{user_text}_\n\n"
                f"🤖 **Ответ:**\n{bot_response}",
                parse_mode="Markdown"
            )

        return VOICE_CONVERSATION

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:100]}")
        return VOICE_CONVERSATION


async def handle_realtime_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового сообщения - тоже отвечаем голосом"""

    if not openai_client:
        await update.message.reply_text("❌ Ассистент недоступен")
        return VOICE_CONVERSATION

    try:
        user_text = update.message.text

        processing_msg = await update.message.reply_text("⏳ Думаю...")

        # Генерируем ответ
        voice_messages = context.user_data.get('voice_messages', [])
        bot_response = await generate_response(user_text, voice_messages)

        if not bot_response:
            await processing_msg.edit_text("❌ Ошибка генерации ответа.")
            return VOICE_CONVERSATION

        # Сохраняем в контекст
        voice_messages.append({"role": "user", "content": user_text})
        voice_messages.append({"role": "assistant", "content": bot_response})
        context.user_data['voice_messages'] = voice_messages

        # Озвучиваем
        await processing_msg.edit_text("🔊 Озвучиваю...")
        audio_response = await text_to_speech(bot_response)

        await processing_msg.delete()

        if audio_response:
            audio_file = BytesIO(audio_response)
            audio_file.name = "response.ogg"

            await update.message.reply_voice(
                voice=audio_file,
                caption=f"📝 _{bot_response}_",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"🤖 {bot_response}")

        return VOICE_CONVERSATION

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:100]}")
        return VOICE_CONVERSATION


async def stop_realtime_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение голосового чата"""

    voice_messages = context.user_data.get('voice_messages', [])
    exchanges = len(voice_messages) // 2

    context.user_data['voice_messages'] = []

    await update.effective_message.reply_text(
        f"🛑 **Голосовой чат завершён**\n\n"
        f"📊 Обменов: {exchanges}\n\n"
        f"Для нового чата: /realtime_chat",
        parse_mode="Markdown"
    )

    return ConversationHandler.END


async def cancel_realtime_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена"""
    return await stop_realtime_chat(update, context)


async def realtime_chat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback кнопок"""
    query = update.callback_query
    await query.answer()

    if query.data == "stop_realtime_chat":
        return await stop_realtime_chat(update, context)

    return VOICE_CONVERSATION


# ============================================================================
# СПРАВКА
# ============================================================================

async def realtime_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка по голосовому чату"""
    await update.message.reply_text(
        "🎤 **ГОЛОСОВОЙ АССИСТЕНТ**\n\n"
        "**Как работает:**\n"
        "1️⃣ Вы отправляете голосовое сообщение\n"
        "2️⃣ Whisper распознаёт речь\n"
        "3️⃣ GPT-4 генерирует ответ\n"
        "4️⃣ TTS озвучивает ответ\n\n"
        "**Команды:**\n"
        "• `/realtime_chat` - Начать\n"
        "• Кнопка \"Завершить\" - Закончить\n\n"
        "**Советы:**\n"
        "• Говорите чётко и кратко\n"
        "• Можно писать текстом — ответ голосом\n"
        "• Контекст сохраняется в рамках сессии",
        parse_mode="Markdown"
    )


# ============================================================================
# РЕГИСТРАЦИЯ
# ============================================================================

def register_realtime_assistant_handlers(application):
    """Регистрация обработчиков"""
    from telegram.ext import (
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        ConversationHandler,
        filters
    )

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("realtime_chat", start_realtime_chat_command),
            CallbackQueryHandler(start_realtime_chat_callback, pattern="^realtime_chat_start$")
        ],
        states={
            VOICE_CONVERSATION: [
                MessageHandler(filters.VOICE, handle_realtime_voice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_realtime_text),
                CallbackQueryHandler(realtime_chat_callback),
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_realtime_chat),
            CommandHandler("stop", stop_realtime_chat),
        ],
        name="voice_chat_conversation",
        persistent=False
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("realtime_help", realtime_help_command))

    logger.info("✅ Голосовой ассистент (Whisper+TTS) зарегистрирован")
