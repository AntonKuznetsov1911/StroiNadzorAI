"""
Режим разработчика - отправка запросов на изменение кода
Версия 2.0 - Упрощённая (без git, работает на любом хостинге)
"""

import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

logger = logging.getLogger(__name__)

# ID разработчика (укажите свой Telegram ID)
DEVELOPER_ID = None  # Будет установлен автоматически при первом использовании /dev

# Состояния для ConversationHandler
WAITING_FOR_CHANGE_REQUEST = 1


async def dev_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /dev - вход в режим разработчика"""
    user_id = update.effective_user.id

    # Устанавливаем DEVELOPER_ID при первом использовании
    global DEVELOPER_ID
    if DEVELOPER_ID is None:
        DEVELOPER_ID = user_id
        logger.info(f"✅ Developer ID установлен: {user_id}")

    # Проверка прав доступа
    if user_id != DEVELOPER_ID:
        await update.message.reply_text("❌ У вас нет доступа к режиму разработчика")
        return ConversationHandler.END

    await update.message.reply_text(
        "🔧 РЕЖИМ РАЗРАБОТЧИКА АКТИВИРОВАН\n\n"
        "Теперь вы можете писать мне что нужно изменить/исправить/добавить в коде.\n\n"
        "Примеры запросов:\n"
        "• Измени цвет кнопок в главном меню на синий\n"
        "• Добавь новый калькулятор для расчета лестниц\n"
        "• Исправь ошибку в акте приёмки фундамента\n"
        "• Удали кнопку FAQ из главного меню\n\n"
        "Я проанализирую ваш запрос, определю какие файлы нужно изменить и сгенерирую готовый код.\n"
        "Все запросы логируются в dev_requests.log\n\n"
        "Для выхода: /cancel"
    )

    return WAITING_FOR_CHANGE_REQUEST


async def process_change_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка запроса на изменение кода"""
    user_id = update.effective_user.id

    if user_id != DEVELOPER_ID:
        return ConversationHandler.END

    request = update.message.text

    # Отправляем сообщение о начале работы
    status_msg = await update.message.reply_text(
        f"⏳ Анализирую запрос...\n\nВаш запрос: {request}"
    )

    try:
        # Импортируем anthropic для работы с Claude
        from anthropic import Anthropic

        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        # Формируем промпт для Claude
        analysis_prompt = f"""Ты - ассистент разработчика Telegram бота на Python. Пользователь хочет внести изменение в код.

Основные файлы проекта:
- bot.py - главный файл бота, регистрация handlers
- document_handlers.py - обработчики документов (ConversationHandler)
- document_templates.py - шаблоны документов (словарь DOCUMENT_TEMPLATES)
- calculator_handlers.py - обработчики калькуляторов (ConversationHandler)
- calculators.py - логика калькуляторов (функции расчётов)
- improvements_v3.py - дополнительные функции
- role_modes.py - режимы работы по ролям
- dev_mode.py - этот файл (режим разработчика)

Запрос пользователя: {request}

Проанализируй запрос и создай подробный план изменений:
1. Какие файлы нужно изменить
2. Какие конкретно изменения нужно внести в каждый файл
3. Нужно ли создать новые файлы
4. Какой код нужно заменить (укажи точные строки)
5. Какой новый код нужно добавить

Верни детальный ответ с готовым кодом для каждого изменения."""

        # Вызываем Claude для анализа
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            messages=[{"role": "user", "content": analysis_prompt}]
        )

        analysis = response.content[0].text

        # Логируем запрос в файл
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"""
{'='*80}
ДАТА: {timestamp}
ЗАПРОС: {request}
АНАЛИЗ:
{analysis}
{'='*80}

"""

        try:
            with open("dev_requests.log", "a", encoding="utf-8") as f:
                f.write(log_entry)
            logger.info(f"📝 Запрос залогирован в dev_requests.log")
        except Exception as log_error:
            logger.warning(f"⚠️ Не удалось залогировать запрос: {log_error}")

        # Отправляем результат пользователю (разбиваем если длинный)
        MAX_LENGTH = 4000

        header = f"✅ АНАЛИЗ ЗАВЕРШЁН\n\nЗапрос: {request}\n\n"
        full_text = header + analysis

        if len(full_text) <= MAX_LENGTH:
            await status_msg.edit_text(full_text)
        else:
            # Отправляем заголовок
            await status_msg.edit_text(header + "Результат анализа отправляю следующими сообщениями...")

            # Разбиваем анализ на части
            parts = []
            current_part = ""

            for line in analysis.split("\n"):
                if len(current_part) + len(line) + 1 > MAX_LENGTH:
                    parts.append(current_part)
                    current_part = line + "\n"
                else:
                    current_part += line + "\n"

            if current_part:
                parts.append(current_part)

            # Отправляем части
            for i, part in enumerate(parts, 1):
                await update.message.reply_text(
                    f"📋 Часть {i}/{len(parts)}:\n\n{part}"
                )

        # Финальное сообщение
        await update.message.reply_text(
            "✅ Готово! Анализ завершён и сохранён в dev_requests.log\n\n"
            "Вы можете:\n"
            "• Отправить новый запрос\n"
            "• Использовать /cancel для выхода\n\n"
            "💡 Для применения изменений используйте предложенный код вручную или через IDE."
        )

    except Exception as e:
        logger.error(f"Ошибка в dev_mode: {e}")
        await status_msg.edit_text(
            f"❌ Произошла ошибка:\n\n{str(e)}\n\n"
            "Попробуйте ещё раз или переформулируйте запрос."
        )

    return WAITING_FOR_CHANGE_REQUEST


async def cancel_dev_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выход из режима разработчика"""
    await update.message.reply_text(
        "👋 Режим разработчика деактивирован.\n\n"
        "Для повторного входа используйте /dev"
    )
    return ConversationHandler.END


def create_dev_mode_handler():
    """Создаёт ConversationHandler для режима разработчика"""
    return ConversationHandler(
        entry_points=[CommandHandler("dev", dev_command)],
        states={
            WAITING_FOR_CHANGE_REQUEST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_change_request)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_dev_mode)],
        per_chat=True,
        per_user=True
    )
