"""
Режим разработчика - модификация кода бота через Telegram
Версия 1.0
"""

import os
import logging
import subprocess
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

logger = logging.getLogger(__name__)

# ID разработчика (укажите свой Telegram ID)
DEVELOPER_ID = None  # Будет установлен автоматически при первом использовании /dev

# Состояния для ConversationHandler
WAITING_FOR_CHANGE_REQUEST = 1

# Путь к проекту
PROJECT_PATH = Path(__file__).parent


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
        "🔧 **РЕЖИМ РАЗРАБОТЧИКА АКТИВИРОВАН**\n\n"
        "Теперь вы можете писать мне что нужно изменить/исправить/добавить в коде, и я это сделаю.\n\n"
        "**Примеры команд:**\n"
        "• _Измени цвет кнопок в главном меню на синий_\n"
        "• _Добавь новый калькулятор для расчета лестниц_\n"
        "• _Исправь ошибку в акте приёмки фундамента_\n"
        "• _Удали кнопку FAQ из главного меню_\n\n"
        "Опишите что нужно сделать, и я выполню изменения, закоммичу и отправлю в GitHub.\n\n"
        "Для выхода: /cancel",
        parse_mode="Markdown"
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
        "⏳ Анализирую запрос и ищу нужные файлы...\n\n"
        f"**Ваш запрос:** {request}",
        parse_mode="Markdown"
    )

    try:
        # Импортируем anthropic для работы с Claude
        from anthropic import Anthropic

        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        # Формируем промпт для Claude
        analysis_prompt = f"""Ты - ассистент разработчика Telegram бота на Python. Пользователь хочет внести изменение в код.

Проект находится в папке: {PROJECT_PATH}

Основные файлы проекта:
- bot.py - главный файл бота
- document_handlers.py - обработчики документов
- document_templates.py - шаблоны документов
- calculator_handlers.py - калькуляторы
- calculators.py - логика калькуляторов
- improvements_v3.py - дополнительные функции

Запрос пользователя: {request}

Проанализируй запрос и определи:
1. Какие файлы нужно изменить
2. Какие конкретно изменения нужно внести
3. Нужно ли создать новые файлы

Верни ответ в формате:
ФАЙЛЫ: [список файлов через запятую]
ДЕЙСТВИЕ: [краткое описание что делать]
ДЕТАЛИ: [подробная инструкция для выполнения]"""

        # Вызываем Claude для анализа
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            messages=[{"role": "user", "content": analysis_prompt}]
        )

        analysis = response.content[0].text

        # Отправляем анализ без markdown чтобы избежать ошибок парсинга
        await status_msg.edit_text(
            f"📋 Анализ запроса:\n\n{analysis}\n\n"
            "⏳ Выполняю изменения..."
        )

        # Теперь запрашиваем у Claude конкретный код для изменений
        code_prompt = f"""На основе анализа выше, сгенерируй конкретные изменения в коде.

Запрос пользователя: {request}

Анализ: {analysis}

Верни ТОЧНЫЕ изменения в формате:

FILE: имя_файла.py
ACTION: edit/create/delete
OLD_CODE: (для edit - старый код который нужно заменить)
NEW_CODE: (для edit/create - новый код)
---

Можешь вернуть несколько блоков для разных файлов."""

        code_response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            messages=[{"role": "user", "content": code_prompt}]
        )

        changes_text = code_response.content[0].text

        # Парсим изменения и применяем их
        applied_changes = []

        # Простой парсинг блоков изменений
        blocks = changes_text.split("---")

        for block in blocks:
            if "FILE:" not in block:
                continue

            lines = block.strip().split("\n")
            file_name = None
            action = None
            old_code = []
            new_code = []
            current_section = None

            for line in lines:
                if line.startswith("FILE:"):
                    file_name = line.replace("FILE:", "").strip()
                elif line.startswith("ACTION:"):
                    action = line.replace("ACTION:", "").strip()
                elif line.startswith("OLD_CODE:"):
                    current_section = "old"
                elif line.startswith("NEW_CODE:"):
                    current_section = "new"
                elif current_section == "old":
                    old_code.append(line)
                elif current_section == "new":
                    new_code.append(line)

            if file_name and action:
                file_path = PROJECT_PATH / file_name

                if action == "edit" and old_code and new_code:
                    # Читаем файл
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Заменяем
                    old_str = "\n".join(old_code)
                    new_str = "\n".join(new_code)

                    if old_str in content:
                        content = content.replace(old_str, new_str)

                        # Записываем обратно
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)

                        applied_changes.append(f"✅ {file_name} - изменено")
                    else:
                        applied_changes.append(f"⚠️ {file_name} - старый код не найден")

                elif action == "create" and new_code:
                    # Создаем новый файл
                    new_str = "\n".join(new_code)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_str)

                    applied_changes.append(f"✅ {file_name} - создан")

        if not applied_changes:
            await status_msg.edit_text(
                "⚠️ Не удалось применить изменения автоматически.\n\n"
                f"**Анализ:**\n{analysis}\n\n"
                f"**Предложенные изменения:**\n{changes_text[:500]}...\n\n"
                "Попробуйте переформулировать запрос более конкретно.",
                parse_mode="Markdown"
            )
            return WAITING_FOR_CHANGE_REQUEST

        changes_summary = "\n".join(applied_changes)

        await status_msg.edit_text(
            f"✅ **Изменения применены:**\n{changes_summary}\n\n"
            "⏳ Коммичу изменения...",
            parse_mode="Markdown"
        )

        # Git commit
        try:
            subprocess.run(
                ["git", "-C", str(PROJECT_PATH), "add", "."],
                check=True,
                capture_output=True
            )

            commit_msg = f"Dev mode: {request[:100]}"
            subprocess.run(
                ["git", "-C", str(PROJECT_PATH), "commit", "-m", commit_msg],
                check=True,
                capture_output=True
            )

            subprocess.run(
                ["git", "-C", str(PROJECT_PATH), "push", "origin", "main"],
                check=True,
                capture_output=True
            )

            await status_msg.edit_text(
                f"✅ **ГОТОВО!**\n\n"
                f"**Применённые изменения:**\n{changes_summary}\n\n"
                f"**Коммит:** {commit_msg}\n"
                "**Статус:** Отправлено в GitHub\n\n"
                "Можете отправить новый запрос или /cancel для выхода.",
                parse_mode="Markdown"
            )

        except subprocess.CalledProcessError as e:
            await status_msg.edit_text(
                f"⚠️ **Изменения применены, но не удалось отправить в Git:**\n\n"
                f"{changes_summary}\n\n"
                f"Ошибка: {e}",
                parse_mode="Markdown"
            )

    except Exception as e:
        logger.error(f"Ошибка в dev_mode: {e}")
        await status_msg.edit_text(
            f"❌ Произошла ошибка:\n\n{str(e)}\n\n"
            "Попробуйте ещё раз или переформулируйте запрос.",
            parse_mode="Markdown"
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
