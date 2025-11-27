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
from src.services.claude_service import get_claude_service
from src.services.openai_service import get_openai_service  # Только для voice transcription
from src.services.pdf_service import get_pdf_service
from src.services.excel_service import get_excel_service
from src.cache import get_cache
from src.utils.helpers import (
    extract_regulations, calculate_defect_severity,
    extract_defect_type, get_severity_emoji, get_severity_text_ru
)

logger = logging.getLogger(__name__)

# Сервисы
rate_limiter = get_rate_limiter()
claude_service = get_claude_service()  # Основной AI сервис
openai_service = get_openai_service()  # Только для voice transcription (fallback)
pdf_service = get_pdf_service()
excel_service = get_excel_service()
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
/export - Экспорт данных в Excel
/premium - Информация о Premium

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

**🔬 НОВЫЕ ПРОДВИНУТЫЕ КОМАНДЫ:**

**7️⃣ /analyze - Детальный анализ:**
   • Инженерный анализ конструкций
   • Проверка по нормативам
   • Расчет несущей способности
   • Пример: `/analyze плита толщина=200мм класс=B25`

**8️⃣ /compare - Сравнение:**
   • Сравнение материалов/технологий
   • Плюсы и минусы
   • Стоимость и области применения
   • Пример: `/compare газобетон vs кирпич`

**9️⃣ /calculate - Расчеты:**
   • Строительные расчеты
   • Объемы материалов
   • Несущая способность
   • Пример: `/calculate бетон плита=6x4м толщина=200мм`

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


async def projects_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /projects - управление проектами"""
    db: Session = next(get_db())
    try:
        user = get_or_create_user(db, update.effective_user)

        from src.database.models import Project
        from sqlalchemy import func

        # Получаем проекты пользователя
        projects = db.query(Project).filter(
            Project.owner_id == user.id
        ).order_by(Project.created_at.desc()).all()

        if not projects:
            text = """📁 **Управление проектами**

У вас пока нет проектов.

Проекты помогают организовать работу:
• Группируйте дефекты по объектам
• Следите за прогрессом
• Работайте с командой

Хотите создать первый проект?"""

            keyboard = [
                [InlineKeyboardButton("➕ Создать проект", callback_data="create_project")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        else:
            text = "📁 **Ваши проекты:**\n\n"

            for project in projects:
                # Считаем дефекты в проекте
                defects_count = db.query(func.count(Request.id)).filter(
                    Request.project_id == project.id
                ).scalar()

                text += f"📂 **{project.name}**\n"
                text += f"   🏗️ {project.address or 'Адрес не указан'}\n"
                text += f"   📊 Дефектов: {defects_count}\n"
                text += f"   📅 {project.created_at.strftime('%d.%m.%Y')}\n\n"

            keyboard = [
                [InlineKeyboardButton("➕ Создать проект", callback_data="create_project")],
                [InlineKeyboardButton("📊 Статистика", callback_data="project_stats")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in projects command: {e}", exc_info=True)
        await update.message.reply_text("❌ Ошибка при получении проектов")
    finally:
        db.close()


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /export - экспорт данных в Excel"""
    db: Session = next(get_db())
    try:
        user = get_or_create_user(db, update.effective_user)

        # Проверяем, есть ли данные для экспорта
        requests_count = db.query(Request).filter(Request.user_id == user.id).count()

        if requests_count == 0:
            await update.message.reply_text(
                "📊 У вас пока нет данных для экспорта.\n\n"
                "Сначала отправьте фото или задайте вопросы!"
            )
            return

        text = f"""📊 **Экспорт данных**

Доступно для экспорта:
• Запросов: {requests_count}
• Период: с {user.created_at.strftime('%d.%m.%Y')}

Выберите что экспортировать:"""

        keyboard = [
            [InlineKeyboardButton("📋 Все запросы", callback_data="export_requests")],
            [InlineKeyboardButton("📸 Только фото", callback_data="export_photos")],
            [InlineKeyboardButton("💬 Только текст", callback_data="export_text")],
            [InlineKeyboardButton("📈 Статистика", callback_data="export_analytics")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in export command: {e}", exc_info=True)
        await update.message.reply_text("❌ Ошибка при подготовке экспорта")
    finally:
        db.close()


async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /premium - информация о Premium"""
    db: Session = next(get_db())
    try:
        user = get_or_create_user(db, update.effective_user)

        if user.role == UserRole.PREMIUM:
            text = """💎 **Premium статус активен!**

Ваши преимущества:
✅ 200 запросов в час (вместо 50)
✅ Приоритетная обработка
✅ Расширенная аналитика
✅ Экспорт в Excel без ограничений
✅ Командная работа над проектами
✅ Email-уведомления о дефектах
✅ Техническая поддержка 24/7

Спасибо, что выбрали Premium! 🎉"""
        else:
            text = """💎 **Upgrade to Premium**

**Базовый план (FREE):**
• 50 запросов в час
• Базовая аналитика
• Личные проекты

**Premium план:**
• ✨ 200 запросов в час
• ✨ Приоритетная обработка
• ✨ Расширенная аналитика
• ✨ Экспорт в Excel
• ✨ Командная работа
• ✨ Email-уведомления
• ✨ Техническая поддержка 24/7

**Стоимость:** 2990₽/месяц

Для подключения свяжитесь с @admin"""

            keyboard = [
                [InlineKeyboardButton("💳 Подключить Premium", url="https://t.me/admin")],
                [InlineKeyboardButton("📊 Сравнить планы", callback_data="compare_plans")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in premium command: {e}", exc_info=True)
        await update.message.reply_text("❌ Ошибка при получении информации о Premium")
    finally:
        db.close()


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /report - создать PDF отчет из последнего анализа"""
    db: Session = next(get_db())
    try:
        user = get_or_create_user(db, update.effective_user)

        # Получаем последний запрос с фото
        last_request = db.query(Request).filter(
            Request.user_id == user.id,
            Request.request_type == RequestType.PHOTO
        ).order_by(Request.created_at.desc()).first()

        if not last_request:
            await update.message.reply_text(
                "📄 У вас нет анализов фотографий для создания отчета.\n\n"
                "Сначала отправьте фото дефекта!"
            )
            return

        # Генерируем PDF
        await update.message.reply_text("📄 Генерирую PDF отчет...")

        pdf_path = pdf_service.generate_defect_report(
            title=f"Дефект #{last_request.id}",
            defect_type=last_request.defect_type or "Не определен",
            severity=last_request.defect_severity.value if last_request.defect_severity else "Не определена",
            analysis=last_request.response_text,
            recommendations="См. анализ выше",
            regulations=last_request.mentioned_regulations,
            user_name=user.first_name
        )

        # Отправляем PDF
        with open(pdf_path, 'rb') as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                filename=f"defect_report_{last_request.id}.pdf",
                caption=f"📄 PDF отчет по последнему анализу\n\nДефект #{last_request.id}"
            )

        logger.info(f"PDF report sent via /report command for user {user.telegram_id}")

    except Exception as e:
        logger.error(f"Error in report command: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ошибка при создании отчета: {str(e)}")
    finally:
        db.close()


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /admin - администраторские функции"""
    db: Session = next(get_db())
    try:
        user = get_or_create_user(db, update.effective_user)

        # Проверяем права администратора
        if user.role != UserRole.ADMIN:
            await update.message.reply_text("❌ У вас нет прав администратора")
            return

        from sqlalchemy import func
        from datetime import datetime, timedelta

        # Общая статистика
        total_users = db.query(func.count(User.id)).scalar()
        total_requests = db.query(func.count(Request.id)).scalar()

        # Статистика за сегодня
        today = datetime.utcnow().date()
        today_requests = db.query(func.count(Request.id)).filter(
            func.date(Request.created_at) == today
        ).scalar()

        # Новые пользователи за неделю
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_users_week = db.query(func.count(User.id)).filter(
            User.created_at >= week_ago
        ).scalar()

        # Cache hit rate
        total_cached = db.query(func.count(Request.id)).filter(Request.cached == True).scalar()
        cache_hit_rate = (total_cached / total_requests * 100) if total_requests > 0 else 0

        text = f"""👨‍💼 **Панель администратора**

📊 **Общая статистика:**
• Пользователей: {total_users}
• Всего запросов: {total_requests}
• Запросов сегодня: {today_requests}
• Новых за неделю: {new_users_week}

⚡ **Производительность:**
• Cache hit rate: {cache_hit_rate:.1f}%

🔗 **Ссылки:**
• Admin API: {settings.API_HOST}:{settings.API_PORT}
• API Docs: {settings.API_HOST}:{settings.API_PORT}/docs
"""

        keyboard = [
            [InlineKeyboardButton("📊 Детальная статистика", url=f"http://{settings.API_HOST}:{settings.API_PORT}/api/stats")],
            [InlineKeyboardButton("👥 Управление пользователями", url=f"http://{settings.API_HOST}:{settings.API_PORT}/api/users")],
            [InlineKeyboardButton("📈 Аналитика", url=f"http://{settings.API_HOST}:{settings.API_PORT}/api/analytics")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in admin command: {e}", exc_info=True)
        await update.message.reply_text("❌ Ошибка в панели администратора")
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
            # Анализ через Claude AI с RAG и контекстом
            analysis = await claude_service.analyze_photo(photo_base64, caption, user.id, db)
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
            # Анализ через Claude AI с RAG и контекстом
            answer = await claude_service.analyze_text_question(question, user.id, db)
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

        # Обрабатываем как текстовый вопрос через Claude AI
        start_time = time.time()
        answer = await claude_service.analyze_text_question(transcribed_text, user.id, db)
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
    elif data == "create_project":
        await update.callback_query.message.reply_text(
            "📝 Чтобы создать проект, отправьте название в формате:\n\n"
            "`/create_project Название объекта, адрес`"
        )
    elif data.startswith("export_"):
        # Экспорт данных
        export_type = data.split("_")[1]
        await handle_export(update, context, export_type)


async def handle_export(update: Update, context: ContextTypes.DEFAULT_TYPE, export_type: str):
    """Обработка экспорта данных"""
    db: Session = next(get_db())
    try:
        user = get_or_create_user(db, update.effective_user.id)

        await update.callback_query.message.reply_text("📊 Готовлю экспорт данных...")

        # Получаем данные в зависимости от типа
        if export_type == "requests":
            requests = db.query(Request).filter(Request.user_id == user.id).all()
            data = [{
                "ID": r.id,
                "Тип": r.request_type.value,
                "Дата": r.created_at.strftime('%d.%m.%Y %H:%M'),
                "Дефект": r.defect_type or "-",
                "Критичность": r.defect_severity.value if r.defect_severity else "-",
                "Время (с)": r.processing_time
            } for r in requests]
            filename = f"requests_{user.telegram_id}_{int(time.time())}.xlsx"

        elif export_type == "photos":
            requests = db.query(Request).filter(
                Request.user_id == user.id,
                Request.request_type == RequestType.PHOTO
            ).all()
            data = [{
                "ID": r.id,
                "Дата": r.created_at.strftime('%d.%m.%Y %H:%M'),
                "Дефект": r.defect_type or "-",
                "Критичность": r.defect_severity.value if r.defect_severity else "-",
                "Подпись": r.caption or "-"
            } for r in requests]
            filename = f"photos_{user.telegram_id}_{int(time.time())}.xlsx"

        elif export_type == "text":
            requests = db.query(Request).filter(
                Request.user_id == user.id,
                Request.request_type == RequestType.TEXT
            ).all()
            data = [{
                "ID": r.id,
                "Дата": r.created_at.strftime('%d.%m.%Y %H:%M'),
                "Вопрос": r.message_text[:100] + "..." if len(r.message_text) > 100 else r.message_text,
                "Время (с)": r.processing_time
            } for r in requests]
            filename = f"questions_{user.telegram_id}_{int(time.time())}.xlsx"

        elif export_type == "analytics":
            data = [{
                "Всего запросов": user.total_requests,
                "Анализов фото": user.total_photos,
                "Голосовых": user.total_voice,
                "Зарегистрирован": user.created_at.strftime('%d.%m.%Y'),
                "Последняя активность": user.last_activity.strftime('%d.%m.%Y %H:%M')
            }]
            filename = f"analytics_{user.telegram_id}_{int(time.time())}.xlsx"

        # Экспортируем в Excel
        excel_path = excel_service.export_requests(data, filename)

        # Отправляем файл
        with open(excel_path, 'rb') as excel_file:
            await update.callback_query.message.reply_document(
                document=excel_file,
                filename=filename,
                caption=f"📊 Экспорт данных готов!\n\nЗаписей: {len(data)}"
            )

        logger.info(f"Data exported for user {user.telegram_id}, type: {export_type}")

    except Exception as e:
        logger.error(f"Error exporting data: {e}", exc_info=True)
        await update.callback_query.message.reply_text(f"❌ Ошибка при экспорте: {str(e)}")
    finally:
        db.close()


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


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Детальный анализ конструкции по параметрам
    /analyze <тип конструкции> <параметры>
    """
    db = next(get_db())
    telegram_user = update.effective_user
    user = get_or_create_user(db, telegram_user)

    # Проверка rate limit
    allowed, error_message = check_rate_limit(user)
    if not allowed:
        await update.message.reply_text(error_message)
        return

    # Получаем параметры
    args = context.args
    if not args:
        help_text = """
🔍 **ДЕТАЛЬНЫЙ АНАЛИЗ КОНСТРУКЦИЙ**

**Как использовать:**
`/analyze <конструкция> <параметры>`

**Примеры:**

1. **Плита перекрытия:**
`/analyze плита толщина=200мм класс=B25 пролет=6м`

2. **Колонна:**
`/analyze колонна сечение=400x400 высота=3.5м нагрузка=500кН`

3. **Фундамент:**
`/analyze фундамент тип=ленточный глубина=1.8м грунт=суглинок`

4. **Стена:**
`/analyze стена материал=кирпич толщина=380мм высота=3м`

**Что получите:**
✅ Проверка по нормативам (СП, ГОСТ)
✅ Расчет несущей способности
✅ Выявление проблем и рисков
✅ Рекомендации по улучшению
"""
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
        return

    # Формируем вопрос для Claude
    analysis_request = " ".join(args)
    question = f"""Выполни ДЕТАЛЬНЫЙ ИНЖЕНЕРНЫЙ АНАЛИЗ конструкции:

{analysis_request}

Требуется:
1. 📋 ТЕХНИЧЕСКИЕ ХАРАКТЕРИСТИКИ - проверь все параметры по нормативам
2. 🔍 ПРОВЕРКА ПРОЧНОСТИ - расчеты несущей способности
3. ⚠️ ВЫЯВЛЕНИЕ РИСКОВ - потенциальные проблемы
4. 📐 СООТВЕТСТВИЕ СП/ГОСТ - конкретные пункты нормативов
5. 💡 РЕКОМЕНДАЦИИ - что улучшить/изменить

Дай развернутый ответ с расчетами и ссылками на нормативы."""

    # Обрабатываем через Claude
    await update.message.reply_text("🔍 Выполняю детальный инженерный анализ...")

    start_time = time.time()
    answer = await claude_service.analyze_text_question(question, user.id, db)
    processing_time = time.time() - start_time

    # Сохраняем в БД
    request = Request(
        user_id=user.id,
        request_type=RequestType.TEXT,
        message_text=analysis_request,
        response_text=answer,
        processing_time=processing_time
    )
    db.add(request)
    db.commit()

    # Отправляем результат
    await update.message.reply_text(
        answer,
        parse_mode=ParseMode.MARKDOWN
    )

    logger.info(f"Analysis completed for user {user.telegram_id} in {processing_time:.2f}s")


async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Сравнение материалов/технологий
    /compare <A> vs <B>
    """
    db = next(get_db())
    telegram_user = update.effective_user
    user = get_or_create_user(db, telegram_user)

    # Проверка rate limit
    allowed, error_message = check_rate_limit(user)
    if not allowed:
        await update.message.reply_text(error_message)
        return

    # Получаем параметры
    args = context.args
    if not args or 'vs' not in ' '.join(args).lower():
        help_text = """
⚖️ **СРАВНЕНИЕ МАТЕРИАЛОВ И ТЕХНОЛОГИЙ**

**Как использовать:**
`/compare <A> vs <B>`

**Примеры:**

1. **Материалы:**
`/compare газобетон vs кирпич`

2. **Технологии:**
`/compare монолит vs сборный железобетон`

3. **Системы:**
`/compare плитный фундамент vs ленточный`

4. **Отделка:**
`/compare штукатурка vs гипсокартон`

**Что получите:**
✅ Технические характеристики обоих вариантов
✅ Плюсы и минусы каждого
✅ Стоимость и трудозатраты
✅ Области применения
✅ Рекомендации по выбору
"""
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
        return

    # Формируем вопрос для Claude
    comparison_request = " ".join(args)
    question = f"""Сделай ПРОФЕССИОНАЛЬНОЕ СРАВНЕНИЕ:

{comparison_request}

Формат ответа:

**1️⃣ ПЕРВЫЙ ВАРИАНТ**
- Технические характеристики
- Плюсы
- Минусы
- Стоимость
- Области применения

**2️⃣ ВТОРОЙ ВАРИАНТ**
- Технические характеристики
- Плюсы
- Минусы
- Стоимость
- Области применения

**📊 СРАВНИТЕЛЬНАЯ ТАБЛИЦА**
| Параметр | Вариант 1 | Вариант 2 |

**💡 ИТОГОВЫЕ РЕКОМЕНДАЦИИ**
Когда выбрать первый, когда второй

Опирайся на СП, ГОСТ, СНиП и практический опыт."""

    # Обрабатываем через Claude
    await update.message.reply_text("⚖️ Провожу сравнительный анализ...")

    start_time = time.time()
    answer = await claude_service.analyze_text_question(question, user.id, db)
    processing_time = time.time() - start_time

    # Сохраняем в БД
    request = Request(
        user_id=user.id,
        request_type=RequestType.TEXT,
        message_text=comparison_request,
        response_text=answer,
        processing_time=processing_time
    )
    db.add(request)
    db.commit()

    # Отправляем результат
    await update.message.reply_text(
        answer,
        parse_mode=ParseMode.MARKDOWN
    )

    logger.info(f"Comparison completed for user {user.telegram_id} in {processing_time:.2f}s")


async def calculate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Строительные расчеты
    /calculate <тип расчета> <параметры>
    """
    db = next(get_db())
    telegram_user = update.effective_user
    user = get_or_create_user(db, telegram_user)

    # Проверка rate limit
    allowed, error_message = check_rate_limit(user)
    if not allowed:
        await update.message.reply_text(error_message)
        return

    # Получаем параметры
    args = context.args
    if not args:
        help_text = """
🧮 **СТРОИТЕЛЬНЫЕ РАСЧЕТЫ**

**Как использовать:**
`/calculate <тип расчета> <параметры>`

**Примеры:**

1. **Материалы:**
`/calculate кирпич стена=10м высота=3м толщина=0.38м`

2. **Бетон:**
`/calculate бетон плита=6x4м толщина=200мм`

3. **Арматура:**
`/calculate арматура балка=длина5м сечение=300x500`

4. **Нагрузка:**
`/calculate нагрузка перекрытие полезная=300кг/м2 собственная=400кг/м2`

5. **Теплопотери:**
`/calculate теплопотери стена=площадь100м2 материал=кирпич`

**Что получите:**
✅ Точные расчеты по формулам СП/ГОСТ
✅ Объемы материалов
✅ Несущая способность
✅ Стоимость (ориентировочная)
✅ Рекомендации
"""
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
        return

    # Формируем вопрос для Claude
    calculation_request = " ".join(args)
    question = f"""Выполни ИНЖЕНЕРНЫЙ РАСЧЕТ:

{calculation_request}

Требования к расчету:
1. 📐 ФОРМУЛЫ - укажи используемые формулы из СП/ГОСТ
2. 🔢 ПОДРОБНЫЕ ВЫЧИСЛЕНИЯ - покажи все шаги расчета
3. 📊 ИТОГОВЫЕ ЗНАЧЕНИЯ - конкретные числа с единицами измерения
4. ⚠️ ЗАПАС ПРОЧНОСТИ - проверка коэффициентов надежности
5. 💰 ПРИМЕРНАЯ СТОИМОСТЬ - если применимо
6. 📚 НОРМАТИВНАЯ БАЗА - ссылки на конкретные пункты СП

Расчет должен быть ТОЧНЫМ и ПРОВЕРЯЕМЫМ!"""

    # Обрабатываем через Claude
    await update.message.reply_text("🧮 Выполняю инженерные расчеты...")

    start_time = time.time()
    answer = await claude_service.analyze_text_question(question, user.id, db)
    processing_time = time.time() - start_time

    # Сохраняем в БД
    request = Request(
        user_id=user.id,
        request_type=RequestType.TEXT,
        message_text=calculation_request,
        response_text=answer,
        processing_time=processing_time
    )
    db.add(request)
    db.commit()

    # Отправляем результат
    await update.message.reply_text(
        answer,
        parse_mode=ParseMode.MARKDOWN
    )

    logger.info(f"Calculation completed for user {user.telegram_id} in {processing_time:.2f}s")


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
    application.add_handler(CommandHandler("projects", projects_command))
    application.add_handler(CommandHandler("export", export_command))
    application.add_handler(CommandHandler("premium", premium_command))
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CommandHandler("admin", admin_command))

    # Новые продвинутые команды
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(CommandHandler("compare", compare_command))
    application.add_handler(CommandHandler("calculate", calculate_command))

    # Сообщения
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Callback кнопки
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Error handler
    application.add_error_handler(error_handler)

    logger.info("All handlers registered successfully")
