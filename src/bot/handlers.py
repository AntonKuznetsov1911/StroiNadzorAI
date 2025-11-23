"""
Telegram Bot Handlers
Все обработчики команд и сообщений
"""

import logging
import base64
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from telegram.constants import ParseMode
from sqlalchemy.orm import Session

from config.settings import settings
from src.database import get_db
from src.database.models import User, Request, RequestType, UserRole, DefectSeverity
from src.services.rate_limiter import get_rate_limiter
from src.services.openai_service import get_openai_service
from src.services.pdf_service import get_pdf_service
from src.cache import get_cache
from src.utils.helpers import (
    extract_regulations, calculate_defect_severity,
    extract_defect_type, get_severity_emoji, get_severity_text_ru
)

logger = logging.getLogger(__name__)

# Сервисы
rate_limiter = get_rate_limiter()
openai_service = get_openai_service()
pdf_service = get_pdf_service()
cache = get_cache()


# === UTILITY FUNCTIONS ===

def get_or_create_user(db: Session, telegram_user) -> User:
    """
    Получить или создать пользователя

    Args:
        db: Database session
        telegram_user: Telegram user object

    Returns:
        User: User object
    """
    user = db.query(User).filter(User.telegram_id == telegram_user.id).first()

    if not user:
        user = User(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"New user created: {user.telegram_id}")
    else:
        # Обновляем последнюю активность
        user.last_activity = datetime.utcnow()
        db.commit()

    return user


def check_rate_limit(user: User) -> tuple[bool, Optional[str]]:
    """
    Проверка rate limit

    Args:
        user: User object

    Returns:
        tuple[bool, Optional[str]]: (allowed, error_message)
    """
    allowed, wait_time = rate_limiter.check_rate_limit(user)

    if not allowed:
        minutes = wait_time // 60
        message = f"⏱ Превышен лимит запросов. Подожди {minutes} минут."

        if user.role == UserRole.USER:
            message += "\n\n💎 Хочешь больше запросов? Обновись до Premium!"

        return False, message

    return True, None


# === COMMAND HANDLERS ===

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    db: Session = next(get_db())
    try:
        user = get_or_create_user(db, update.effective_user)

        welcome_message = f"""👋 Здравствуйте, {user.first_name}!

Я - **AI консультант ТехНадзор** по строительным нормативам (v{settings.APP_VERSION}).

🔍 **Мои возможности:**

📸 **Анализ фотографий**
   • Отправьте фото дефекта
   • Я определю тип, критичность
   • Дам рекомендации по нормативам

💬 **Консультации**
   • Задайте вопрос по СП, ГОСТ, СНиП
   • Получите ответ со ссылками

🎤 **Голосовые сообщения**
   • Отправьте голосовое сообщение
   • Я распознаю и отвечу на вопрос

📄 **PDF Отчеты**
   • Генерация профессиональных отчетов
   • С фотографиями и рекомендациями

📍 **Геолокация**
   • Привязка дефектов к местоположению
   • История проверок по адресам

📋 **Команды:**
/start - Это сообщение
/help - Подробная справка
/regulations - Список нормативов
/stats - Ваша статистика
/projects - Мои проекты
/report - Создать PDF отчет

**Ваш статус:** {user.role.value.upper()}
**Запросов сегодня:** {rate_limiter.get_remaining_requests(user)} доступно

Попробуйте отправить фото дефекта или задать вопрос! 👇"""

        keyboard = [
            [InlineKeyboardButton("📚 Список нормативов", callback_data="regulations")],
            [InlineKeyboardButton("💡 Примеры вопросов", callback_data="examples")],
            [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")],
            [InlineKeyboardButton("ℹ️ Справка", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    finally:
        db.close()


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """📖 **Подробная справка**

**1️⃣ Анализ фотографий:**
   • Отправьте фото дефекта
   • Можно добавить подпись с вопросом
   • Я проанализирую изображение и дам рекомендации

**2️⃣ Вопросы по нормативам:**
   • Напишите вопрос в чат
   • Например: "Требования к бетону B25?"
   • Получите профессиональный ответ

**3️⃣ Голосовые сообщения:**
   • Отправьте голосовое сообщение
   • Я распознаю речь и отвечу на вопрос
   • Удобно на стройплощадке!

**4️⃣ PDF Отчеты:**
   • Используйте /report после анализа
   • Получите профессиональный PDF отчет
   • С фотографиями и рекомендациями

**5️⃣ Проекты:**
   • Создавайте проекты через /projects
   • Группируйте дефекты по объектам
   • Совместная работа с командой

**6️⃣ Геолокация:**
   • Отправьте геопозицию с фото
   • Дефекты привяжутся к карте
   • История проверок по адресам

**База знаний:**
• 13 строительных нормативов
• СП (Своды Правил)
• ГОСТ (ГОСТы)
• СНиП (Строительные Нормы и Правила)

**Примеры вопросов:**
📌 Какие требования к прочности бетона класса B25?
📌 Допустимая ширина трещины в несущей стене?
📌 Как проверить качество сварного шва?
📌 Требования к гидроизоляции фундамента?

Есть вопросы? Просто напишите! 💬"""

    if update.callback_query:
        await update.callback_query.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def regulations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /regulations"""
    from src.utils.helpers import REGULATIONS

    text = "📚 **Доступные нормативы:**\n\n"

    for code, title in REGULATIONS.items():
        text += f"📄 **{code}**\n   _{title}_\n\n"

    text += "\nЗадайте вопрос по любому нормативу!"

    if update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats - статистика пользователя"""
    db: Session = next(get_db())
    try:
        user = get_or_create_user(db, update.effective_user)

        stats_text = f"""📊 **Ваша статистика**

👤 **Пользователь:** {user.first_name or user.username}
🆔 **Telegram ID:** {user.telegram_id}
⭐ **Статус:** {user.role.value.upper()}

📈 **Активность:**
• Всего запросов: {user.total_requests}
• Анализов фото: {user.total_photos}
• Голосовых: {user.total_voice}

⏰ **Даты:**
• Регистрация: {user.created_at.strftime('%d.%m.%Y')}
• Последняя активность: {user.last_activity.strftime('%d.%m.%Y %H:%M')}

⚡ **Лимиты сегодня:**
• Доступно запросов: {rate_limiter.get_remaining_requests(user)}
"""

        if user.role != UserRole.PREMIUM:
            stats_text += "\n💎 Хочешь больше запросов? Обновись до Premium!"

        if update.callback_query:
            await update.callback_query.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)

    finally:
        db.close()


async def examples_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /examples"""
    examples_text = """💡 **Примеры вопросов:**

**О бетоне:**
• Какие требования к прочности бетона класса B25?
• Допустимая ширина трещины в железобетоне?
• Методы контроля качества бетона по ГОСТ 10180-2012

**О конструкциях:**
• Требования к несущим стенам жилых домов
• Допустимые деформации перекрытий
• Как проверить качество кирпичной кладки?

**О дефектах:**
• Трещина шириной 0.3 мм - критична ли она?
• Как оценить степень коррозии арматуры?
• Что делать при обнаружении отслоения штукатурки?

**О контроле:**
• Как проверить качество сварных соединений?
• Методы контроля гидроизоляции подвала
• Требования к приемке скрытых работ

**О кровле:**
• Какой уклон нужен для металлочерепицы?
• Как рассчитать площадь кровли?
• Конструкция кровельного пирога для мансарды

**О теплоизоляции:**
• Какую толщину утеплителя выбрать для Москвы?
• Как рассчитать точку росы в стене?
• Какой утеплитель лучше для фасада?

Просто напишите свой вопрос или отправьте фото дефекта! 📸"""

    if update.callback_query:
        await update.callback_query.message.reply_text(examples_text, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(examples_text, parse_mode=ParseMode.MARKDOWN)


# === MESSAGE HANDLERS ===

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фотографий"""
    db: Session = next(get_db())
    try:
        user = get_or_create_user(db, update.effective_user)

        # Проверка rate limit
        allowed, error_msg = check_rate_limit(user)
        if not allowed:
            await update.message.reply_text(error_msg)
            return

        await update.message.reply_text("📸 Анализирую фотографию... Это может занять несколько секунд.")

        start_time = time.time()

        # Получаем фото
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')

        # Хеш фото для кеширования
        photo_hash = hashlib.md5(photo_bytes).hexdigest()

        # Получаем подпись
        caption = update.message.caption or ""

        # Проверяем кеш
        cache_key = cache.get_cache_key_for_photo(photo_hash, caption)
        cached_response = cache.get(cache_key)

        if cached_response:
            analysis = cached_response
            from_cache = True
            logger.info(f"Photo response from cache for user {user.telegram_id}")
        else:
            # Анализ через OpenAI
            analysis = await openai_service.analyze_photo(photo_base64, caption)
            from_cache = False

            # Сохраняем в кеш
            cache.set(cache_key, analysis)

        processing_time = time.time() - start_time

        # Извлекаем метаданные
        defect_type = extract_defect_type(analysis)
        severity = calculate_defect_severity(analysis)
        regulations = extract_regulations(analysis)

        # Сохраняем запрос в БД
        request = Request(
            user_id=user.id,
            request_type=RequestType.PHOTO,
            caption=caption,
            response_text=analysis,
            defect_type=defect_type,
            defect_severity=severity,
            mentioned_regulations=regulations,
            processing_time=processing_time,
            cached=from_cache
        )
        db.add(request)

        # Обновляем статистику пользователя
        user.total_requests += 1
        user.total_photos += 1
        db.commit()

        # Формируем ответ
        result = f"🔍 **Анализ фотографии:**\n\n{analysis}\n\n"

        if defect_type and severity:
            severity_emoji = get_severity_emoji(severity)
            severity_text = get_severity_text_ru(severity)
            result += f"**Тип дефекта:** {defect_type}\n"
            result += f"**Критичность:** {severity_emoji} {severity_text}\n\n"

        if regulations:
            result += "📚 **Упомянутые нормативы:**\n"
            for reg in regulations:
                result += f"• {reg}\n"
            result += "\n"

        result += f"⏰ Время анализа: {processing_time:.2f}с"
        if from_cache:
            result += " ⚡ (из кеша)"

        # Кнопка для генерации PDF отчета
        keyboard = [
            [InlineKeyboardButton("📄 Создать PDF отчет", callback_data=f"generate_pdf:{request.id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            result,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

        logger.info(f"Photo analyzed for user {user.telegram_id} in {processing_time:.2f}s")

    except Exception as e:
        logger.error(f"Error analyzing photo: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Ошибка при анализе фотографии: {str(e)}\n\nПопробуйте еще раз или обратитесь к администратору."
        )
    finally:
        db.close()


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    db: Session = next(get_db())
    try:
        user = get_or_create_user(db, update.effective_user)

        # Проверка rate limit
        allowed, error_msg = check_rate_limit(user)
        if not allowed:
            await update.message.reply_text(error_msg)
            return

        question = update.message.text

        await update.message.reply_text("🤔 Думаю над вашим вопросом...")

        start_time = time.time()

        # Проверяем кеш
        cache_key = cache.get_cache_key_for_question(question)
        cached_response = cache.get(cache_key)

        if cached_response:
            answer = cached_response
            from_cache = True
            logger.info(f"Text response from cache for user {user.telegram_id}")
        else:
            # Анализ через OpenAI
            answer = await openai_service.analyze_text_question(question)
            from_cache = False

            # Сохраняем в кеш
            cache.set(cache_key, answer)

        processing_time = time.time() - start_time

        # Извлекаем упомянутые нормативы
        regulations = extract_regulations(answer)

        # Сохраняем запрос в БД
        request = Request(
            user_id=user.id,
            request_type=RequestType.TEXT,
            message_text=question,
            response_text=answer,
            mentioned_regulations=regulations,
            processing_time=processing_time,
            cached=from_cache
        )
        db.add(request)

        # Обновляем статистику
        user.total_requests += 1
        db.commit()

        # Формируем ответ
        result = f"💬 **Ответ:**\n\n{answer}\n\n"

        if regulations:
            result += "📚 **Упомянутые нормативы:**\n"
            for reg in regulations:
                result += f"• {reg}\n"
            result += "\n"

        result += f"⏰ {processing_time:.2f}с"
        if from_cache:
            result += " ⚡"

        await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

        logger.info(f"Question answered for user {user.telegram_id} in {processing_time:.2f}s")

    except Exception as e:
        logger.error(f"Error answering question: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Ошибка при обработке вопроса: {str(e)}\n\nПопробуйте переформулировать вопрос."
        )
    finally:
        db.close()


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка голосовых сообщений"""
    if not settings.ENABLE_VOICE_MESSAGES:
        await update.message.reply_text("🔇 Голосовые сообщения временно недоступны.")
        return

    db: Session = next(get_db())
    try:
        user = get_or_create_user(db, update.effective_user)

        # Проверка rate limit
        allowed, error_msg = check_rate_limit(user)
        if not allowed:
            await update.message.reply_text(error_msg)
            return

        await update.message.reply_text("🎤 Распознаю голосовое сообщение...")

        # Скачиваем аудио
        voice = update.message.voice
        voice_file = await voice.get_file()

        # Сохраняем временно
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        audio_path = upload_dir / f"voice_{user.telegram_id}_{int(time.time())}.ogg"
        await voice_file.download_to_drive(str(audio_path))

        # Распознаем через Whisper API
        transcribed_text = await openai_service.transcribe_voice(str(audio_path))

        # Удаляем временный файл
        audio_path.unlink()

        # Отправляем распознанный текст
        await update.message.reply_text(f"📝 Распознано: \"{transcribed_text}\"\n\nОбрабатываю ваш вопрос...")

        # Обрабатываем как текстовый вопрос
        start_time = time.time()
        answer = await openai_service.analyze_text_question(transcribed_text)
        processing_time = time.time() - start_time

        # Сохраняем в БД
        request = Request(
            user_id=user.id,
            request_type=RequestType.VOICE,
            message_text=transcribed_text,
            response_text=answer,
            processing_time=processing_time
        )
        db.add(request)

        user.total_requests += 1
        user.total_voice += 1
        db.commit()

        # Отправляем ответ
        result = f"💬 **Ответ:**\n\n{answer}"
        await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

        logger.info(f"Voice message processed for user {user.telegram_id}")

    except Exception as e:
        logger.error(f"Error processing voice: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Ошибка при обработке голосового сообщения: {str(e)}"
        )
    finally:
        db.close()


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback кнопок"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "regulations":
        await regulations_command(update, context)
    elif data == "examples":
        await examples_command(update, context)
    elif data == "help":
        await help_command(update, context)
    elif data == "stats":
        await stats_command(update, context)
    elif data.startswith("generate_pdf:"):
        # Генерация PDF отчета
        request_id = int(data.split(":")[1])
        await generate_pdf_report(update, context, request_id)


async def generate_pdf_report(update: Update, context: ContextTypes.DEFAULT_TYPE, request_id: int):
    """Генерация PDF отчета"""
    if not settings.ENABLE_PDF_REPORTS:
        await update.callback_query.message.reply_text("📄 PDF отчеты временно недоступны.")
        return

    db: Session = next(get_db())
    try:
        await update.callback_query.message.reply_text("📄 Генерирую PDF отчет...")

        # Получаем запрос из БД
        request = db.query(Request).filter(Request.id == request_id).first()

        if not request:
            await update.callback_query.message.reply_text("❌ Запрос не найден.")
            return

        # Генерируем PDF
        pdf_path = pdf_service.generate_defect_report(
            title=f"Дефект #{request_id}",
            defect_type=request.defect_type or "Не определен",
            severity=request.defect_severity.value if request.defect_severity else "Не определена",
            analysis=request.response_text,
            recommendations="См. анализ выше",
            regulations=request.mentioned_regulations,
            user_name=request.user.first_name
        )

        # Отправляем PDF
        with open(pdf_path, 'rb') as pdf_file:
            await update.callback_query.message.reply_document(
                document=pdf_file,
                filename=f"defect_report_{request_id}.pdf",
                caption=f"📄 PDF отчет готов!\n\nДефект #{request_id}"
            )

        logger.info(f"PDF report sent for request {request_id}")

    except Exception as e:
        logger.error(f"Error generating PDF: {e}", exc_info=True)
        await update.callback_query.message.reply_text(f"❌ Ошибка генерации PDF: {str(e)}")
    finally:
        db.close()


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)


# === SETUP ===

def setup_handlers(application: Application):
    """
    Регистрация всех handlers

    Args:
        application: Telegram Application
    """
    # Команды
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("regulations", regulations_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("examples", examples_command))

    # Сообщения
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Callback кнопки
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Error handler
    application.add_error_handler(error_handler)

    logger.info("All handlers registered successfully")
