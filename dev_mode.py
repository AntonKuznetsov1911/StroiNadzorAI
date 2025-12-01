"""
Режим разработчика - отправка запросов на изменение кода
Версия 3.0 - С кнопкой "Запушить на git"
"""

import os
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters

logger = logging.getLogger(__name__)

# ID разработчика
DEVELOPER_ID = None

# Состояния
WAITING_FOR_CHANGE_REQUEST = 1


def is_developer(user_id: int) -> bool:
    """Проверяет, является ли пользователь разработчиком"""
    return DEVELOPER_ID is not None and user_id == DEVELOPER_ID

# Путь к проекту
PROJECT_PATH = Path(__file__).parent

# Проверка наличия git
GIT_AVAILABLE = False
try:
    result = subprocess.run(
        ["git", "--version"],
        capture_output=True,
        timeout=5
    )
    GIT_AVAILABLE = (result.returncode == 0)
    if GIT_AVAILABLE:
        logger.info("✅ Git доступен - кнопка автопуша будет показана")
    else:
        logger.warning("⚠️ Git не найден - работаем без автопуша")
except Exception as e:
    logger.warning(f"⚠️ Git не доступен: {e}")
    GIT_AVAILABLE = False


async def dev_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /dev - вход в режим разработчика"""
    user_id = update.effective_user.id

    global DEVELOPER_ID
    if DEVELOPER_ID is None:
        DEVELOPER_ID = user_id
        logger.info(f"✅ Developer ID установлен: {user_id}")

    if user_id != DEVELOPER_ID:
        await update.message.reply_text("❌ У вас нет доступа к режиму разработчика")
        return ConversationHandler.END

    await update.message.reply_text(
        "🔧 РЕЖИМ РАЗРАБОТЧИКА АКТИВИРОВАН\n\n"
        "Опишите что нужно изменить/исправить/добавить.\n\n"
        "Примеры:\n"
        "• Измени модель на claude-opus\n"
        "• Добавь калькулятор арматуры\n"
        "• Исправь ошибку в шаблоне\n\n"
        "После анализа появится кнопка для применения изменений.\n\n"
        "Для выхода: /cancel"
    )

    return WAITING_FOR_CHANGE_REQUEST


async def process_change_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка запроса на изменение кода"""
    user_id = update.effective_user.id

    if user_id != DEVELOPER_ID:
        return ConversationHandler.END

    request = update.message.text

    status_msg = await update.message.reply_text(
        f"⏳ Анализирую запрос...\n\nВаш запрос: {request}"
    )

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        # Промпт для Claude с форматом изменений
        analysis_prompt = f"""Ты - ассистент разработчика Telegram бота на Python.

Проект: Telegram бот СтройНадзорAI
Путь: {PROJECT_PATH}

Основные файлы:
- bot.py - главный файл
- document_handlers.py - обработчики документов
- document_templates.py - шаблоны
- calculator_handlers.py - калькуляторы
- calculators.py - логика расчётов
- role_modes.py - режимы ролей
- suggestions.py - предложения пользователей
- dev_mode.py - этот файл

Запрос: {request}

Проанализируй и верни изменения В ТОЧНОМ ФОРМАТЕ:

FILE: filename.py
ACTION: edit/create
OLD: |
старый код для замены (точный!)
|
NEW: |
новый код
|
---

Важно:
- Для ACTION=edit укажи ТОЧНЫЙ старый код
- Можно несколько блоков через ---
- Если не можешь - напиши "MANUAL" и дай инструкции"""

        response = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": analysis_prompt}]
        )

        analysis = response.content[0].text

        # Сохраняем в context для кнопки
        context.user_data['dev_analysis'] = analysis
        context.user_data['dev_request'] = request

        # Логируем
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
            with open(PROJECT_PATH / "dev_requests.log", "a", encoding="utf-8") as f:
                f.write(log_entry)
            logger.info(f"📝 Запрос залогирован")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка логирования: {e}")

        # Отправляем результат с кнопкой
        MAX_LENGTH = 4000
        header = f"✅ АНАЛИЗ ЗАВЕРШЁН\n\nЗапрос: {request}\n\n"
        full_text = header + analysis

        # Создаём кнопки - показываем "Запушить на git" только если git доступен
        keyboard = []
        if GIT_AVAILABLE:
            keyboard.append([InlineKeyboardButton("📤 Запушить на git", callback_data="dev_push_to_git")])
        keyboard.append([InlineKeyboardButton("❌ Закрыть", callback_data="dev_cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        if len(full_text) <= MAX_LENGTH:
            await status_msg.edit_text(full_text, reply_markup=reply_markup)
        else:
            # Отправляем по частям
            await status_msg.edit_text(header + "Результат анализа отправляю частями...")

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

            for i, part in enumerate(parts, 1):
                await update.message.reply_text(f"📋 Часть {i}/{len(parts)}:\n\n{part}")

            # Последнее сообщение с кнопкой
            if GIT_AVAILABLE:
                button_text = "✅ Анализ завершён!\n\nНажмите кнопку чтобы применить изменения и запушить в git:"
            else:
                button_text = "✅ Анализ завершён!\n\n⚠️ Git недоступен - примените изменения вручную."

            await update.message.reply_text(button_text, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Ошибка в dev_mode: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ Произошла ошибка:\n\n{str(e)}\n\n"
            "Попробуйте ещё раз."
        )

    return WAITING_FOR_CHANGE_REQUEST


async def push_to_git_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Запушить на git'"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if user_id != DEVELOPER_ID:
        await query.edit_message_text("❌ Нет доступа")
        return WAITING_FOR_CHANGE_REQUEST

    # Получаем сохранённый анализ
    analysis = context.user_data.get('dev_analysis')
    request = context.user_data.get('dev_request', 'dev change')

    if not analysis:
        await query.edit_message_text("❌ Анализ не найден. Попробуйте снова.")
        return WAITING_FOR_CHANGE_REQUEST

    status_msg = await query.edit_message_text("⏳ Применяю изменения...")

    try:
        # Парсим блоки изменений
        applied_changes = []
        blocks = analysis.split("---")

        for block in blocks:
            if "FILE:" not in block:
                continue

            lines = block.strip().split("\n")
            file_name = None
            action = None
            old_code_section = False
            new_code_section = False
            old_code = []
            new_code = []

            for line in lines:
                if line.startswith("FILE:"):
                    file_name = line.replace("FILE:", "").strip()
                elif line.startswith("ACTION:"):
                    action = line.replace("ACTION:", "").strip().lower()
                elif line.strip() == "OLD: |":
                    old_code_section = True
                    new_code_section = False
                elif line.strip() == "NEW: |":
                    old_code_section = False
                    new_code_section = True
                elif line.strip() == "|":
                    old_code_section = False
                    new_code_section = False
                elif old_code_section:
                    old_code.append(line)
                elif new_code_section:
                    new_code.append(line)

            if not file_name or not action:
                continue

            file_path = PROJECT_PATH / file_name

            try:
                if action == "edit":
                    if not old_code or not new_code:
                        applied_changes.append(f"⚠️ {file_name} - нет кода")
                        continue

                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    old_str = "\n".join(old_code)
                    new_str = "\n".join(new_code)

                    if old_str in content:
                        content = content.replace(old_str, new_str, 1)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        applied_changes.append(f"✅ {file_name} - изменено")
                    else:
                        applied_changes.append(f"⚠️ {file_name} - старый код не найден")

                elif action == "create":
                    if not new_code:
                        continue
                    new_str = "\n".join(new_code)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_str)
                    applied_changes.append(f"✅ {file_name} - создан")

            except Exception as e:
                applied_changes.append(f"❌ {file_name} - {str(e)[:50]}")

        if not applied_changes:
            await status_msg.edit_text(
                "⚠️ Не удалось применить изменения автоматически.\n\n"
                "Проверьте формат ответа Claude или примените вручную."
            )
            return WAITING_FOR_CHANGE_REQUEST

        changes_summary = "\n".join(applied_changes)

        await status_msg.edit_text(
            f"✅ Изменения применены:\n{changes_summary}\n\n"
            "⏳ Делаю git commit..."
        )

        # Git операции
        try:
            # git add
            subprocess.run(
                ["git", "-C", str(PROJECT_PATH), "add", "."],
                check=True,
                capture_output=True,
                text=True,
                timeout=10
            )

            # git commit
            commit_msg = f"Dev: {request[:80]}"
            subprocess.run(
                ["git", "-C", str(PROJECT_PATH), "commit", "-m", commit_msg],
                check=True,
                capture_output=True,
                text=True,
                timeout=10
            )

            # git push
            subprocess.run(
                ["git", "-C", str(PROJECT_PATH), "push", "origin", "main"],
                check=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            await status_msg.edit_text(
                f"✅ ГОТОВО!\n\n"
                f"Изменения:\n{changes_summary}\n\n"
                f"Commit: {commit_msg}\n"
                f"Статус: Запушено в GitHub ✓\n\n"
                f"⏳ Railway деплоит (1-2 мин)...\n\n"
                f"Можете отправить новый запрос или /cancel"
            )

        except subprocess.CalledProcessError as e:
            error = e.stderr if hasattr(e, 'stderr') else str(e)
            await status_msg.edit_text(
                f"⚠️ Изменения применены, но git failed:\n\n"
                f"{changes_summary}\n\n"
                f"Ошибка: {error[:200]}"
            )

    except Exception as e:
        logger.error(f"Ошибка применения: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ Ошибка:\n\n{str(e)[:500]}\n\n"
            "Попробуйте применить изменения вручную."
        )

    return WAITING_FOR_CHANGE_REQUEST


async def dev_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Отменить'"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "❌ Применение отменено.\n\n"
        "Отправьте новый запрос или /cancel для выхода."
    )

    return WAITING_FOR_CHANGE_REQUEST


async def cancel_dev_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выход из режима разработчика"""
    await update.message.reply_text(
        "👋 Режим разработчика деактивирован.\n\n"
        "Для повторного входа: /dev"
    )
    return ConversationHandler.END


def create_dev_mode_handler():
    """Создаёт ConversationHandler для режима разработчика"""
    return ConversationHandler(
        entry_points=[CommandHandler("dev", dev_command)],
        states={
            WAITING_FOR_CHANGE_REQUEST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_change_request),
                CallbackQueryHandler(push_to_git_callback, pattern="^dev_push_to_git$"),
                CallbackQueryHandler(dev_cancel_callback, pattern="^dev_cancel$")
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_dev_mode)],
        per_chat=True,
        per_user=True
    )
