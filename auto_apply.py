"""
Автоматическое применение изменений из ответов бота
Версия 1.0 - Кнопка "Применить изменения" после каждого ответа

ИСПОЛЬЗОВАНИЕ:
1. Задаёте вопрос боту: "Как изменить модель на claude-opus?"
2. Бот отвечает с кодом
3. Видите кнопку "🔧 Применить изменения"
4. Нажимаете - бот автоматически применяет код и пушит в git
"""

import os
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

PROJECT_PATH = Path(__file__).parent


def add_apply_button(reply_markup=None, message_id=None):
    """Добавляет кнопку 'Применить изменения' к клавиатуре"""

    apply_button = InlineKeyboardButton(
        "🔧 Применить изменения",
        callback_data=f"apply_changes_{message_id}" if message_id else "apply_changes"
    )

    if reply_markup and isinstance(reply_markup, InlineKeyboardMarkup):
        # Добавляем к существующей клавиатуре
        keyboard = reply_markup.inline_keyboard
        keyboard.append([apply_button])
        return InlineKeyboardMarkup(keyboard)
    else:
        # Создаём новую клавиатуру
        return InlineKeyboardMarkup([[apply_button]])


def should_show_apply_button(text: str) -> bool:
    """Определяет, нужно ли показывать кнопку применения изменений"""

    # Показываем кнопку если в тексте есть код или ключевые слова
    code_indicators = [
        "```",  # Markdown код
        "def ",  # Python функция
        "class ",  # Python класс
        "import ",  # Python импорт
        "async def",  # Async функция
        "from ",  # Python импорт
        ".py",  # Упоминание файла
        "bot.py",
        "document_handlers.py",
        "calculator",
        "Изменить",
        "изменить",
        "Добавить",
        "добавить",
        "Заменить",
        "заменить",
    ]

    return any(indicator in text for indicator in code_indicators)


async def handle_apply_changes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия кнопки 'Применить изменения'"""

    query = update.callback_query
    await query.answer()

    # Получаем текст сообщения на который нажали кнопку
    original_message_text = query.message.text or query.message.caption or ""

    # Проверяем что это локальная версия (есть git)
    try:
        subprocess.run(
            ["git", "--version"],
            check=True,
            capture_output=True,
            timeout=5
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        await query.edit_message_text(
            f"{original_message_text}\n\n"
            f"❌ Автоприменение доступно только в локальной версии бота.\n"
            f"На Railway используйте /dev для получения инструкций.",
            reply_markup=None
        )
        return

    # Отправляем статус
    status_msg = await query.message.reply_text(
        "⏳ Анализирую ответ и ищу код для применения..."
    )

    try:
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("XAI_API_KEY", base_url="https://api.x.ai/v1"))

        # Промпт для анализа ответа и извлечения кода
        analysis_prompt = f"""Ты - ассистент разработчика. Проанализируй ответ бота и извлеки из него КОД для применения.

ОТВЕТ БОТА:
{original_message_text}

ЗАДАЧА:
Найди в ответе код, который нужно применить к проекту.

Основные файлы проекта:
- bot.py - главный файл
- document_handlers.py - обработчики документов
- document_templates.py - шаблоны
- calculator_handlers.py - калькуляторы
- calculators.py - логика расчётов
- role_modes.py - режимы ролей

Верни план изменений в формате:

FILE: filename.py
ACTION: edit/create
OLD: |точный код для замены (для edit)|
NEW: |новый код|
---

ВАЖНО:
- Если в ответе НЕТ конкретного кода - верни: NO_CODE
- Для ACTION=edit укажи ТОЧНЫЙ старый код для поиска
- Можешь вернуть несколько блоков для разных файлов"""

        response = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": analysis_prompt}]
        )

        analysis = response.content[0].text

        # Проверяем что есть код
        if "NO_CODE" in analysis or "FILE:" not in analysis:
            await status_msg.edit_text(
                "⚠️ В ответе не найден конкретный код для применения.\n\n"
                "Попробуйте использовать /dev и описать изменение более конкретно."
            )
            return

        await status_msg.edit_text(
            "📋 Код найден, применяю изменения..."
        )

        # Применяем изменения (тот же код что в dev_mode_local.py)
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
                "Используйте /dev для ручного применения."
            )
            return

        changes_summary = "\n".join(applied_changes)

        await status_msg.edit_text(
            f"✅ Изменения применены:\n{changes_summary}\n\n"
            "⏳ Делаю git commit..."
        )

        # Git commit и push
        try:
            subprocess.run(
                ["git", "-C", str(PROJECT_PATH), "add", "."],
                check=True,
                capture_output=True,
                text=True
            )

            commit_msg = f"Auto-apply: {original_message_text[:60]}..."
            subprocess.run(
                ["git", "-C", str(PROJECT_PATH), "commit", "-m", commit_msg],
                check=True,
                capture_output=True,
                text=True
            )

            subprocess.run(
                ["git", "-C", str(PROJECT_PATH), "push", "origin", "main"],
                check=True,
                capture_output=True,
                text=True
            )

            # Логируем
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"""
{'='*80}
ДАТА: {timestamp}
МЕТОД: Auto-apply (кнопка)
ИСХОДНЫЙ ОТВЕТ: {original_message_text[:200]}...
ИЗМЕНЕНИЯ: {changes_summary}
КОММИТ: {commit_msg}
СТАТУС: Запушено в GitHub
{'='*80}

"""
            with open(PROJECT_PATH / "dev_requests.log", "a", encoding="utf-8") as f:
                f.write(log_entry)

            await status_msg.edit_text(
                f"✅ ГОТОВО!\n\n"
                f"Применённые изменения:\n{changes_summary}\n\n"
                f"Git commit: {commit_msg}\n"
                f"Статус: Запушено в GitHub ✓\n\n"
                f"⏳ Railway деплоит (1-2 минуты)..."
            )

            # Убираем кнопку из оригинального сообщения
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if hasattr(e, 'stderr') else str(e)

            await status_msg.edit_text(
                f"⚠️ Изменения применены локально, но не удалось запушить:\n\n"
                f"{changes_summary}\n\n"
                f"Ошибка git: {error_msg}"
            )

    except Exception as e:
        logger.error(f"Ошибка в auto_apply: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ Произошла ошибка:\n\n{str(e)}\n\n"
            "Попробуйте использовать /dev вместо автоприменения."
        )


async def send_message_with_apply_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    **kwargs
):
    """
    Отправляет сообщение с кнопкой 'Применить изменения' если в тексте есть код

    Использование:
        from auto_apply import send_message_with_apply_button

        await send_message_with_apply_button(
            update, context,
            "Вот код для изменения:\n\n```python\nprint('hello')\n```"
        )
    """

    # Проверяем нужна ли кнопка
    if should_show_apply_button(text):
        # Добавляем кнопку к существующей клавиатуре или создаём новую
        reply_markup = kwargs.get('reply_markup')
        kwargs['reply_markup'] = add_apply_button(reply_markup)

    # Отправляем сообщение
    if update.callback_query:
        return await update.callback_query.message.reply_text(text, **kwargs)
    else:
        return await update.message.reply_text(text, **kwargs)
