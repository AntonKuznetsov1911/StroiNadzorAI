"""
Режим разработчика - ЛОКАЛЬНАЯ ВЕРСИЯ с автоматическим push
Версия 3.0 - Для локальной разработки (требует git)

ИСПОЛЬЗОВАНИЕ:
1. Запускайте бота локально на компьютере
2. /dev - активация режима
3. Описываете изменение
4. Бот автоматически:
   - Анализирует запрос
   - Применяет изменения в файлах
   - Делает git commit и push
   - Railway автоматически деплоит
"""

import os
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

logger = logging.getLogger(__name__)

# ID разработчика
DEVELOPER_ID = None

# Состояния
WAITING_FOR_CHANGE_REQUEST = 1

# Путь к проекту
PROJECT_PATH = Path(__file__).parent


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
        "🔧 РЕЖИМ РАЗРАБОТЧИКА АКТИВИРОВАН (ЛОКАЛЬНАЯ ВЕРСИЯ)\n\n"
        "Теперь вы можете писать что нужно изменить.\n\n"
        "Примеры запросов:\n"
        "• Измени модель на claude-sonnet-4\n"
        "• Добавь новый калькулятор арматуры\n"
        "• Исправь ошибку в шаблоне акта\n"
        "• Удали кнопку из меню\n\n"
        "⚡ БОТ АВТОМАТИЧЕСКИ:\n"
        "1. Проанализирует запрос через Claude\n"
        "2. Применит изменения в файлах\n"
        "3. Сделает git commit и push\n"
        "4. Railway автоматически задеплоит\n\n"
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

        # Шаг 1: Анализ запроса
        analysis_prompt = f"""Ты - ассистент разработчика Telegram бота на Python.

Проект находится в: {PROJECT_PATH}

Основные файлы:
- bot.py - главный файл, handlers
- document_handlers.py - обработчики документов
- document_templates.py - шаблоны документов
- calculator_handlers.py - обработчики калькуляторов
- calculators.py - логика расчётов
- role_modes.py - режимы по ролям
- dev_mode.py - режим разработчика (облачный)
- dev_mode_local.py - этот файл (локальный с git)

Запрос: {request}

Проанализируй и верни ТОЧНЫЙ план изменений в формате:

FILE: filename.py
ACTION: edit/create
OLD: |точный код для замены (для edit)|
NEW: |новый код|
---

Можешь вернуть несколько блоков для разных файлов.
Для ACTION=edit укажи ТОЧНЫЙ старый код для поиска."""

        response = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": analysis_prompt}]
        )

        analysis = response.content[0].text

        await status_msg.edit_text(
            f"📋 Анализ получен\n\nЗапрос: {request}\n\n⏳ Применяю изменения..."
        )

        # Шаг 2: Парсинг и применение изменений
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
                elif line.startswith("OLD:"):
                    old_code_section = True
                    new_code_section = False
                    # Убираем первую строку если там |
                    if "|" in line:
                        continue
                elif line.startswith("NEW:"):
                    old_code_section = False
                    new_code_section = True
                    if "|" in line:
                        continue
                elif old_code_section:
                    if line == "|":
                        old_code_section = False
                    else:
                        old_code.append(line)
                elif new_code_section:
                    if line == "|":
                        new_code_section = False
                    else:
                        new_code.append(line)

            if not file_name or not action:
                continue

            file_path = PROJECT_PATH / file_name

            try:
                if action == "edit":
                    if not old_code or not new_code:
                        applied_changes.append(f"⚠️ {file_name} - нет кода для замены")
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
                        applied_changes.append(f"⚠️ {file_name} - нет кода для создания")
                        continue

                    new_str = "\n".join(new_code)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_str)

                    applied_changes.append(f"✅ {file_name} - создан")

            except Exception as e:
                applied_changes.append(f"❌ {file_name} - ошибка: {e}")

        if not applied_changes:
            await status_msg.edit_text(
                "⚠️ Не удалось применить изменения автоматически.\n\n"
                f"Анализ:\n{analysis[:1000]}...\n\n"
                "Попробуйте переформулировать запрос."
            )
            return WAITING_FOR_CHANGE_REQUEST

        changes_summary = "\n".join(applied_changes)

        await status_msg.edit_text(
            f"✅ Изменения применены:\n{changes_summary}\n\n"
            "⏳ Делаю git commit..."
        )

        # Шаг 3: Git commit и push
        try:
            # Git add
            subprocess.run(
                ["git", "-C", str(PROJECT_PATH), "add", "."],
                check=True,
                capture_output=True,
                text=True
            )

            # Git commit
            commit_msg = f"Dev mode: {request[:80]}"
            result = subprocess.run(
                ["git", "-C", str(PROJECT_PATH), "commit", "-m", commit_msg],
                check=True,
                capture_output=True,
                text=True
            )

            # Git push
            subprocess.run(
                ["git", "-C", str(PROJECT_PATH), "push", "origin", "main"],
                check=True,
                capture_output=True,
                text=True
            )

            # Логируем в файл
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"""
{'='*80}
ДАТА: {timestamp}
ЗАПРОС: {request}
ИЗМЕНЕНИЯ: {changes_summary}
КОММИТ: {commit_msg}
СТАТУС: Запушено в GitHub, Railway деплоит...
{'='*80}

"""
            with open(PROJECT_PATH / "dev_requests.log", "a", encoding="utf-8") as f:
                f.write(log_entry)

            await status_msg.edit_text(
                f"✅ ГОТОВО!\n\n"
                f"Применённые изменения:\n{changes_summary}\n\n"
                f"Git commit: {commit_msg}\n"
                f"Статус: Запушено в GitHub ✓\n\n"
                f"⏳ Railway автоматически деплоит изменения...\n"
                f"Обычно это занимает 1-2 минуты.\n\n"
                f"Можете отправить новый запрос или /cancel для выхода."
            )

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if hasattr(e, 'stderr') else str(e)

            await status_msg.edit_text(
                f"⚠️ Изменения применены локально, но не удалось запушить:\n\n"
                f"{changes_summary}\n\n"
                f"Ошибка git: {error_msg}\n\n"
                f"Проверьте git статус вручную."
            )

    except Exception as e:
        logger.error(f"Ошибка в dev_mode_local: {e}", exc_info=True)
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
