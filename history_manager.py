"""
Управление историей диалогов v3.5
Улучшенный поиск по истории и экспорт в различные форматы
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import json
from pathlib import Path
from datetime import datetime
import io

logger = logging.getLogger(__name__)

# Папка для хранения истории
CONVERSATIONS_DIR = Path("user_conversations")
CONVERSATIONS_DIR.mkdir(exist_ok=True)


# ========================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ИСТОРИЕЙ
# ========================================

def get_user_history_file(user_id: int) -> Path:
    """Получить путь к файлу истории пользователя"""
    return CONVERSATIONS_DIR / f"user_{user_id}.json"


def load_user_history(user_id: int) -> list:
    """Загрузить историю пользователя"""
    history_file = get_user_history_file(user_id)

    if not history_file.exists():
        return []

    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки истории пользователя {user_id}: {e}")
        return []


def search_in_history(user_id: int, query: str, limit: int = 10) -> list:
    """
    Поиск в истории диалогов

    Args:
        user_id: ID пользователя
        query: Поисковый запрос
        limit: Максимальное количество результатов

    Returns:
        Список найденных сообщений
    """
    history = load_user_history(user_id)
    query_lower = query.lower()

    results = []

    for msg in history:
        # Ищем в вопросе пользователя
        if 'user' in msg and query_lower in msg['user'].lower():
            results.append({
                'type': 'user',
                'text': msg['user'],
                'answer': msg.get('assistant', ''),
                'timestamp': msg.get('timestamp', '')
            })

        # Ищем в ответе бота
        elif 'assistant' in msg and query_lower in msg['assistant'].lower():
            results.append({
                'type': 'assistant',
                'text': msg['assistant'],
                'question': msg.get('user', ''),
                'timestamp': msg.get('timestamp', '')
            })

        if len(results) >= limit:
            break

    return results


def get_history_stats(user_id: int) -> dict:
    """Получить статистику по истории пользователя"""
    history = load_user_history(user_id)

    total_messages = len(history)

    # Подсчёт по типам запросов (приблизительно)
    photo_count = sum(1 for msg in history if 'фото' in msg.get('user', '').lower() or 'изображ' in msg.get('user', '').lower())

    calculator_count = sum(1 for msg in history if any(word in msg.get('user', '').lower() for word in ['калькулятор', 'расчёт', 'бетон', 'арматур']))

    defect_count = sum(1 for msg in history if any(word in msg.get('user', '').lower() for word in ['дефект', 'трещин', 'коррозия', 'протечк']))

    # Дата первого и последнего сообщения
    first_date = history[0].get('timestamp', 'Неизвестно') if history else 'Нет данных'
    last_date = history[-1].get('timestamp', 'Неизвестно') if history else 'Нет данных'

    return {
        'total_messages': total_messages,
        'photo_requests': photo_count,
        'calculator_usage': calculator_count,
        'defect_queries': defect_count,
        'first_message': first_date,
        'last_message': last_date
    }


def export_history_to_text(user_id: int, format_type: str = 'txt') -> io.BytesIO:
    """
    Экспорт истории в текстовый формат

    Args:
        user_id: ID пользователя
        format_type: Формат экспорта ('txt' или 'md')

    Returns:
        BytesIO объект с содержимым файла
    """
    history = load_user_history(user_id)

    if format_type == 'md':
        content = export_to_markdown(history, user_id)
    else:
        content = export_to_txt(history, user_id)

    # Создаём BytesIO объект
    file_obj = io.BytesIO(content.encode('utf-8'))
    file_obj.name = f"history_{user_id}.{format_type}"

    return file_obj


def export_to_txt(history: list, user_id: int) -> str:
    """Экспорт в простой текстовый формат"""
    lines = []
    lines.append("=" * 80)
    lines.append(f"ИСТОРИЯ ДИАЛОГОВ - СтройНадзорAI")
    lines.append(f"Пользователь: {user_id}")
    lines.append(f"Дата экспорта: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    lines.append(f"Всего сообщений: {len(history)}")
    lines.append("=" * 80)
    lines.append("")

    for i, msg in enumerate(history, 1):
        timestamp = msg.get('timestamp', 'Неизвестно')
        user_msg = msg.get('user', '')
        assistant_msg = msg.get('assistant', '')

        lines.append(f"[{i}] {timestamp}")
        lines.append("-" * 80)
        lines.append(f"ВОПРОС:")
        lines.append(user_msg)
        lines.append("")
        lines.append(f"ОТВЕТ:")
        lines.append(assistant_msg)
        lines.append("")
        lines.append("=" * 80)
        lines.append("")

    return "\n".join(lines)


def export_to_markdown(history: list, user_id: int) -> str:
    """Экспорт в Markdown формат"""
    lines = []
    lines.append(f"# История диалогов - СтройНадзорAI")
    lines.append("")
    lines.append(f"**Пользователь:** {user_id}  ")
    lines.append(f"**Дата экспорта:** {datetime.now().strftime('%d.%m.%Y %H:%M')}  ")
    lines.append(f"**Всего сообщений:** {len(history)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, msg in enumerate(history, 1):
        timestamp = msg.get('timestamp', 'Неизвестно')
        user_msg = msg.get('user', '')
        assistant_msg = msg.get('assistant', '')

        lines.append(f"## Диалог #{i}")
        lines.append(f"*{timestamp}*")
        lines.append("")
        lines.append(f"### 👤 Вопрос:")
        lines.append(user_msg)
        lines.append("")
        lines.append(f"### 🤖 Ответ:")
        lines.append(assistant_msg)
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def get_recent_history(user_id: int, limit: int = 5) -> list:
    """Получить последние N сообщений из истории"""
    history = load_user_history(user_id)
    return history[-limit:] if history else []


def format_history_summary(user_id: int, limit: int = 5) -> str:
    """
    Сформировать краткое текстовое резюме истории пользователя.

    Args:
        user_id: ID пользователя.
        limit: Количество последних сообщений для вывода.

    Returns:
        Строка с кратким описанием последних диалогов или уведомление об отсутствии данных.
    """
    history = load_user_history(user_id)

    if not history:
        return "История диалогов пуста."

    recent = history[-limit:]
    summary_lines = [
        f"История пользователя {user_id}",
        f"Последние {len(recent)} диалог(ов):"
    ]

    for idx, msg in enumerate(recent, 1):
        timestamp = msg.get('timestamp', 'Неизвестно')
        user_msg = msg.get('user', '').strip() or '—'
        assistant_msg = msg.get('assistant', '').strip() or '—'

        user_preview = (user_msg[:120] + "...") if len(user_msg) > 120 else user_msg
        assistant_preview = (assistant_msg[:120] + "...") if len(assistant_msg) > 120 else assistant_msg

        summary_lines.append(f"{idx}. [{timestamp}]")
        summary_lines.append(f"   ❓ {user_preview}")
        summary_lines.append(f"   🤖 {assistant_preview}")

    summary_lines.append(f"Всего сообщений: {len(history)}")
    return "\n".join(summary_lines)


def clear_user_history(user_id: int) -> bool:
    """Очистить историю пользователя"""
    history_file = get_user_history_file(user_id)

    try:
        if history_file.exists():
            history_file.unlink()
            logger.info(f"История пользователя {user_id} очищена")
            return True
        return False
    except Exception as e:
        logger.error(f"Ошибка очистки истории: {e}")
        return False


# ========================================
# КОМАНДЫ ДЛЯ РАБОТЫ С ИСТОРИЕЙ
# ========================================

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /history - показать последние сообщения"""
    user_id = update.effective_user.id

    recent = get_recent_history(user_id, limit=5)

    if not recent:
        await update.message.reply_text(
            "📭 **История пуста**\n\n"
            "Вы ещё не задавали вопросов.\n"
            "Начните диалог, и история будет сохраняться автоматически!",
            parse_mode='Markdown'
        )
        return

    text = "📜 **ПОСЛЕДНИЕ 5 ДИАЛОГОВ**\n\n"

    for i, msg in enumerate(recent, 1):
        timestamp = msg.get('timestamp', 'Неизвестно')
        user_msg = msg.get('user', '')[:100]  # Первые 100 символов

        if len(msg.get('user', '')) > 100:
            user_msg += "..."

        text += f"**{i}.** _{timestamp}_\n"
        text += f"❓ {user_msg}\n\n"

    # Кнопки действий
    keyboard = [
        [InlineKeyboardButton("🔍 Поиск по истории", callback_data="hist_search")],
        [InlineKeyboardButton("📊 Статистика", callback_data="hist_stats")],
        [InlineKeyboardButton("💾 Экспорт истории", callback_data="hist_export")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats - показать статистику"""
    user_id = update.effective_user.id

    stats = get_history_stats(user_id)

    text = "📊 **СТАТИСТИКА ИСПОЛЬЗОВАНИЯ**\n\n"
    text += f"**Всего диалогов:** {stats['total_messages']}\n\n"
    text += f"**Анализ фотографий:** {stats['photo_requests']}\n"
    text += f"**Использование калькуляторов:** {stats['calculator_usage']}\n"
    text += f"**Вопросы о дефектах:** {stats['defect_queries']}\n\n"
    text += f"**Первое сообщение:** {stats['first_message']}\n"
    text += f"**Последнее сообщение:** {stats['last_message']}\n\n"
    text += "_Данные обновляются автоматически_"

    await update.message.reply_text(text, parse_mode='Markdown')


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /search <запрос> - поиск по истории"""
    user_id = update.effective_user.id

    # Проверяем наличие запроса
    if not context.args:
        await update.message.reply_text(
            "🔍 **ПОИСК ПО ИСТОРИИ**\n\n"
            "**Формат:** `/search запрос`\n\n"
            "**Примеры:**\n"
            "• `/search трещины`\n"
            "• `/search бетон B25`\n"
            "• `/search арматура`\n\n"
            "_Я найду все диалоги, содержащие эти слова_",
            parse_mode='Markdown'
        )
        return

    query = " ".join(context.args)
    results = search_in_history(user_id, query, limit=10)

    if not results:
        await update.message.reply_text(
            f"🔍 **Поиск: \"{query}\"**\n\n"
            "❌ Ничего не найдено.\n\n"
            "Попробуйте другие ключевые слова.",
            parse_mode='Markdown'
        )
        return

    text = f"🔍 **Найдено {len(results)} результат(ов) по запросу: \"{query}\"**\n\n"

    for i, result in enumerate(results[:5], 1):  # Показываем первые 5
        timestamp = result.get('timestamp', 'Неизвестно')

        if result['type'] == 'user':
            question = result['text'][:150]
            if len(result['text']) > 150:
                question += "..."

            text += f"**{i}.** _{timestamp}_\n"
            text += f"❓ {question}\n\n"
        else:
            answer = result['text'][:150]
            if len(result['text']) > 150:
                answer += "..."

            text += f"**{i}.** _{timestamp}_\n"
            text += f"🤖 {answer}\n\n"

    if len(results) > 5:
        text += f"\n_... и ещё {len(results) - 5} результат(ов)_\n"
        text += "Используйте /export для полного экспорта"

    await update.message.reply_text(text, parse_mode='Markdown')


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /export - экспорт истории"""
    user_id = update.effective_user.id

    # Кнопки выбора формата
    keyboard = [
        [InlineKeyboardButton("📄 TXT (простой текст)", callback_data="export_txt")],
        [InlineKeyboardButton("📝 Markdown (.md)", callback_data="export_md")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "💾 **ЭКСПОРТ ИСТОРИИ ДИАЛОГОВ**\n\n"
        "Выберите формат для экспорта:\n\n"
        "• **TXT** - простой текстовый файл\n"
        "• **Markdown** - форматированный текст с заголовками\n\n"
        "_История будет отправлена файлом_",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def clear_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /clear - очистить историю"""
    user_id = update.effective_user.id

    # Кнопка подтверждения
    keyboard = [
        [InlineKeyboardButton("✅ Да, очистить", callback_data="clear_confirm")],
        [InlineKeyboardButton("❌ Отмена", callback_data="clear_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚠️ **ОЧИСТКА ИСТОРИИ**\n\n"
        "Вы уверены, что хотите удалить всю историю диалогов?\n\n"
        "Это действие **необратимо**!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ========================================
# ОБРАБОТЧИКИ CALLBACK
# ========================================

async def handle_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки истории"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    # Статистика
    if data == "hist_stats":
        stats = get_history_stats(user_id)

        text = "📊 **СТАТИСТИКА ИСПОЛЬЗОВАНИЯ**\n\n"
        text += f"**Всего диалогов:** {stats['total_messages']}\n\n"
        text += f"**Анализ фотографий:** {stats['photo_requests']}\n"
        text += f"**Использование калькуляторов:** {stats['calculator_usage']}\n"
        text += f"**Вопросы о дефектах:** {stats['defect_queries']}\n\n"
        text += f"**Первое сообщение:** {stats['first_message']}\n"
        text += f"**Последнее сообщение:** {stats['last_message']}"

        await query.edit_message_text(text, parse_mode='Markdown')

    # Поиск
    elif data == "hist_search":
        await query.edit_message_text(
            "🔍 **ПОИСК ПО ИСТОРИИ**\n\n"
            "Используйте команду:\n"
            "`/search ваш запрос`\n\n"
            "**Примеры:**\n"
            "• `/search трещины`\n"
            "• `/search бетон`\n"
            "• `/search армирование`",
            parse_mode='Markdown'
        )

    # Экспорт
    elif data == "hist_export":
        keyboard = [
            [InlineKeyboardButton("📄 TXT", callback_data="export_txt")],
            [InlineKeyboardButton("📝 Markdown", callback_data="export_md")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "💾 **ЭКСПОРТ ИСТОРИИ**\n\n"
            "Выберите формат:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    # Экспорт в TXT
    elif data == "export_txt":
        await query.edit_message_text("⏳ Подготавливаю файл...")

        try:
            file_obj = export_history_to_text(user_id, 'txt')
            file_obj.seek(0)

            await query.message.reply_document(
                document=file_obj,
                filename=f"history_{user_id}.txt",
                caption="📄 История диалогов (TXT формат)"
            )

            await query.message.delete()
        except Exception as e:
            logger.error(f"Ошибка экспорта: {e}")
            await query.edit_message_text(
                f"❌ Ошибка экспорта: {str(e)}"
            )

    # Экспорт в Markdown
    elif data == "export_md":
        await query.edit_message_text("⏳ Подготавливаю файл...")

        try:
            file_obj = export_history_to_text(user_id, 'md')
            file_obj.seek(0)

            await query.message.reply_document(
                document=file_obj,
                filename=f"history_{user_id}.md",
                caption="📝 История диалогов (Markdown формат)"
            )

            await query.message.delete()
        except Exception as e:
            logger.error(f"Ошибка экспорта: {e}")
            await query.edit_message_text(
                f"❌ Ошибка экспорта: {str(e)}"
            )

    # Подтверждение очистки
    elif data == "clear_confirm":
        success = clear_user_history(user_id)

        if success:
            await query.edit_message_text(
                "✅ **История очищена**\n\n"
                "Все ваши диалоги удалены.",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "ℹ️ История уже пуста или не существует."
            )

    # Отмена очистки
    elif data == "clear_cancel":
        await query.edit_message_text(
            "❌ Очистка отменена.\n\n"
            "История сохранена."
        )


# ========================================
# АСИНХРОННЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С ИСТОРИЕЙ
# ========================================

async def get_user_history(user_id: int, limit: int = 10) -> list:
    """
    Асинхронно получить историю пользователя в формате для AI моделей

    Args:
        user_id: ID пользователя
        limit: Количество последних сообщений

    Returns:
        Список сообщений в формате [{"role": "user/assistant", "content": "..."}]
    """
    history = load_user_history(user_id)
    recent = history[-limit:] if history else []

    # Преобразуем в формат для AI моделей
    messages = []
    for msg in recent:
        if msg.get('user'):
            messages.append({"role": "user", "content": msg['user']})
        if msg.get('assistant'):
            messages.append({"role": "assistant", "content": msg['assistant']})

    return messages


async def add_message_to_history_async(user_id: int, role: str, content: str) -> bool:
    """
    Асинхронно добавить сообщение в историю пользователя

    Args:
        user_id: ID пользователя
        role: Роль ('user' или 'assistant')
        content: Текст сообщения

    Returns:
        True если сохранено успешно
    """
    try:
        history_file = get_user_history_file(user_id)
        history = load_user_history(user_id)

        timestamp = datetime.now().strftime('%d.%m.%Y %H:%M')

        # Если добавляем ответ assistant - добавляем к последнему сообщению
        if role == 'assistant' and history:
            # Если последнее сообщение только от user - добавляем assistant
            if 'assistant' not in history[-1]:
                history[-1]['assistant'] = content
            else:
                # Иначе создаём новую запись
                history.append({
                    'user': '',
                    'assistant': content,
                    'timestamp': timestamp
                })
        elif role == 'user':
            # Создаём новую запись с вопросом
            history.append({
                'user': content,
                'timestamp': timestamp
            })

        # Сохраняем
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения в историю: {e}")
        return False


def save_conversation(user_id: int, user_message: str, assistant_message: str) -> bool:
    """
    Сохранить пару вопрос-ответ в историю

    Args:
        user_id: ID пользователя
        user_message: Вопрос пользователя
        assistant_message: Ответ бота

    Returns:
        True если сохранено успешно
    """
    try:
        history_file = get_user_history_file(user_id)
        history = load_user_history(user_id)

        timestamp = datetime.now().strftime('%d.%m.%Y %H:%M')

        history.append({
            'user': user_message,
            'assistant': assistant_message,
            'timestamp': timestamp
        })

        # Ограничиваем историю последними 1000 сообщениями
        if len(history) > 1000:
            history = history[-1000:]

        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения беседы: {e}")
        return False
