"""
Сохранение расчётов калькуляторов v3.6
Позволяет сохранять результаты расчётов для повторного использования
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import json
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Папка для сохранённых расчётов
SAVED_CALCS_DIR = Path("saved_calculations")
SAVED_CALCS_DIR.mkdir(exist_ok=True)


# ========================================
# ТИПЫ КАЛЬКУЛЯТОРОВ
# ========================================

CALCULATOR_NAMES = {
    "concrete": "🏗️ Бетон",
    "reinforcement": "🔧 Арматура",
    "formwork": "📐 Опалубка",
    "electrical": "⚡ Электроснабжение",
    "water": "💧 Водоснабжение",
    "winter_heating": "❄️ Зимний прогрев"
}


# ========================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С СОХРАНЁННЫМИ РАСЧЁТАМИ
# ========================================

def get_user_saved_file(user_id: int) -> Path:
    """Получить путь к файлу сохранённых расчётов пользователя"""
    return SAVED_CALCS_DIR / f"user_{user_id}_calcs.json"


def load_saved_calculations(user_id: int) -> list:
    """Загрузить сохранённые расчёты пользователя"""
    saved_file = get_user_saved_file(user_id)

    if not saved_file.exists():
        return []

    try:
        with open(saved_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки расчётов пользователя {user_id}: {e}")
        return []


def save_calculation(user_id: int, calc_type: str, name: str, parameters: dict, result: str) -> bool:
    """
    Сохранить расчёт

    Args:
        user_id: ID пользователя
        calc_type: Тип калькулятора (concrete, reinforcement и т.д.)
        name: Название расчёта от пользователя
        parameters: Параметры расчёта
        result: Результат расчёта

    Returns:
        True если успешно сохранено
    """
    saved_file = get_user_saved_file(user_id)
    saved_calcs = load_saved_calculations(user_id)

    # Создаём новый расчёт
    new_calc = {
        "id": len(saved_calcs) + 1,
        "type": calc_type,
        "name": name,
        "parameters": parameters,
        "result": result,
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M")
    }

    saved_calcs.append(new_calc)

    try:
        with open(saved_file, 'w', encoding='utf-8') as f:
            json.dump(saved_calcs, f, ensure_ascii=False, indent=2)
        logger.info(f"Расчёт '{name}' сохранён для пользователя {user_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения расчёта: {e}")
        return False


def get_saved_calculation(user_id: int, calc_id: int) -> dict:
    """Получить сохранённый расчёт по ID"""
    saved_calcs = load_saved_calculations(user_id)

    for calc in saved_calcs:
        if calc.get('id') == calc_id:
            return calc

    return None


def delete_saved_calculation(user_id: int, calc_id: int) -> bool:
    """Удалить сохранённый расчёт"""
    saved_file = get_user_saved_file(user_id)
    saved_calcs = load_saved_calculations(user_id)

    # Фильтруем список, удаляя расчёт с нужным ID
    new_calcs = [calc for calc in saved_calcs if calc.get('id') != calc_id]

    if len(new_calcs) == len(saved_calcs):
        return False  # Расчёт не найден

    try:
        with open(saved_file, 'w', encoding='utf-8') as f:
            json.dump(new_calcs, f, ensure_ascii=False, indent=2)
        logger.info(f"Расчёт #{calc_id} удалён для пользователя {user_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка удаления расчёта: {e}")
        return False


def get_calculations_by_type(user_id: int, calc_type: str) -> list:
    """Получить все сохранённые расчёты определённого типа"""
    saved_calcs = load_saved_calculations(user_id)
    return [calc for calc in saved_calcs if calc.get('type') == calc_type]


def format_calculation_summary(calc: dict) -> str:
    """Форматировать краткую информацию о расчёте"""
    calc_type = calc.get('type', 'unknown')
    name = calc.get('name', 'Без названия')
    timestamp = calc.get('timestamp', 'Неизвестно')
    calc_id = calc.get('id', 0)

    type_icon = CALCULATOR_NAMES.get(calc_type, "📊")

    text = f"**#{calc_id}** {type_icon} **{name}**\n"
    text += f"_{timestamp}_"

    return text


def format_calculation_details(calc: dict) -> str:
    """Форматировать подробную информацию о расчёте"""
    calc_type = calc.get('type', 'unknown')
    name = calc.get('name', 'Без названия')
    timestamp = calc.get('timestamp', 'Неизвестно')
    parameters = calc.get('parameters', {})
    result = calc.get('result', 'Нет результата')

    type_name = CALCULATOR_NAMES.get(calc_type, "Неизвестный калькулятор")

    text = f"{type_name}\n"
    text += f"**{name}**\n\n"
    text += f"_Сохранено: {timestamp}_\n\n"

    # Параметры
    text += "**📋 Параметры:**\n"
    for key, value in parameters.items():
        # Форматируем ключи
        key_formatted = key.replace('_', ' ').capitalize()
        text += f"• {key_formatted}: {value}\n"

    text += f"\n{result}"

    return text


# ========================================
# КОМАНДЫ
# ========================================

async def saved_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /saved - показать сохранённые расчёты"""
    user_id = update.effective_user.id

    saved_calcs = load_saved_calculations(user_id)

    if not saved_calcs:
        await update.message.reply_text(
            "📂 **СОХРАНЁННЫЕ РАСЧЁТЫ**\n\n"
            "У вас пока нет сохранённых расчётов.\n\n"
            "💡 **Как сохранить расчёт:**\n"
            "1. Используйте любой калькулятор (/calculators)\n"
            "2. После получения результата нажмите кнопку **'💾 Сохранить'**\n"
            "3. Введите название расчёта\n"
            "4. Расчёт появится в этом списке!",
            parse_mode='Markdown'
        )
        return

    # Группируем по типам
    by_type = {}
    for calc in saved_calcs:
        calc_type = calc.get('type', 'unknown')
        if calc_type not in by_type:
            by_type[calc_type] = []
        by_type[calc_type].append(calc)

    text = f"📂 **СОХРАНЁННЫЕ РАСЧЁТЫ** ({len(saved_calcs)})\n\n"

    # Показываем по категориям
    for calc_type, calcs in by_type.items():
        type_name = CALCULATOR_NAMES.get(calc_type, "Другое")
        text += f"**{type_name}** ({len(calcs)}):\n"

        for calc in calcs[:3]:  # Показываем первые 3
            calc_id = calc.get('id')
            name = calc.get('name', 'Без названия')
            text += f"• #{calc_id} {name}\n"

        if len(calcs) > 3:
            text += f"_... и ещё {len(calcs) - 3}_\n"

        text += "\n"

    # Кнопки
    keyboard = [
        [InlineKeyboardButton("📋 Все расчёты", callback_data="saved_all")],
        [InlineKeyboardButton("🔍 По типу калькулятора", callback_data="saved_by_type")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ========================================
# ОБРАБОТЧИКИ CALLBACK
# ========================================

async def handle_saved_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки сохранённых расчётов"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    # Показать все расчёты
    if data == "saved_all":
        saved_calcs = load_saved_calculations(user_id)

        if not saved_calcs:
            await query.edit_message_text("📂 Нет сохранённых расчётов")
            return

        # Кнопки для каждого расчёта
        keyboard = []
        for calc in saved_calcs[:10]:  # Максимум 10
            calc_id = calc.get('id')
            name = calc.get('name', 'Без названия')
            calc_type = calc.get('type', 'unknown')
            icon = CALCULATOR_NAMES.get(calc_type, "📊").split()[0]

            keyboard.append([InlineKeyboardButton(
                f"{icon} #{calc_id} {name}",
                callback_data=f"saved_view_{calc_id}"
            )])

        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="saved_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"📂 **ВСЕ РАСЧЁТЫ** ({len(saved_calcs)})\n\n"
            "Выберите расчёт для просмотра:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    # Показать по типу
    elif data == "saved_by_type":
        keyboard = []

        for calc_type, type_name in CALCULATOR_NAMES.items():
            calcs = get_calculations_by_type(user_id, calc_type)
            if calcs:
                keyboard.append([InlineKeyboardButton(
                    f"{type_name} ({len(calcs)})",
                    callback_data=f"saved_type_{calc_type}"
                )])

        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="saved_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "🔍 **РАСЧЁТЫ ПО ТИПАМ**\n\n"
            "Выберите тип калькулятора:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    # Назад к главному меню
    elif data == "saved_back":
        saved_calcs = load_saved_calculations(user_id)

        # Группируем по типам
        by_type = {}
        for calc in saved_calcs:
            calc_type = calc.get('type', 'unknown')
            if calc_type not in by_type:
                by_type[calc_type] = []
            by_type[calc_type].append(calc)

        text = f"📂 **СОХРАНЁННЫЕ РАСЧЁТЫ** ({len(saved_calcs)})\n\n"

        for calc_type, calcs in by_type.items():
            type_name = CALCULATOR_NAMES.get(calc_type, "Другое")
            text += f"**{type_name}** ({len(calcs)})\n"

        keyboard = [
            [InlineKeyboardButton("📋 Все расчёты", callback_data="saved_all")],
            [InlineKeyboardButton("🔍 По типу калькулятора", callback_data="saved_by_type")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    # Просмотр расчётов конкретного типа
    elif data.startswith("saved_type_"):
        calc_type = data.replace("saved_type_", "")
        calcs = get_calculations_by_type(user_id, calc_type)

        type_name = CALCULATOR_NAMES.get(calc_type, "Расчёты")

        keyboard = []
        for calc in calcs:
            calc_id = calc.get('id')
            name = calc.get('name', 'Без названия')

            keyboard.append([InlineKeyboardButton(
                f"#{calc_id} {name}",
                callback_data=f"saved_view_{calc_id}"
            )])

        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="saved_by_type")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"{type_name}\n\n"
            f"**Сохранено расчётов:** {len(calcs)}\n\n"
            "Выберите расчёт:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    # Просмотр конкретного расчёта
    elif data.startswith("saved_view_"):
        calc_id = int(data.replace("saved_view_", ""))
        calc = get_saved_calculation(user_id, calc_id)

        if not calc:
            await query.edit_message_text("❌ Расчёт не найден")
            return

        details = format_calculation_details(calc)

        keyboard = [
            [InlineKeyboardButton("🗑️ Удалить", callback_data=f"saved_delete_{calc_id}")],
            [InlineKeyboardButton("⬅️ Назад к списку", callback_data="saved_all")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            details,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    # Удаление расчёта
    elif data.startswith("saved_delete_"):
        calc_id = int(data.replace("saved_delete_", ""))

        # Кнопки подтверждения
        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить", callback_data=f"saved_delete_confirm_{calc_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data=f"saved_view_{calc_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "⚠️ **УДАЛЕНИЕ РАСЧЁТА**\n\n"
            "Вы уверены, что хотите удалить этот расчёт?\n\n"
            "Это действие необратимо!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    # Подтверждение удаления
    elif data.startswith("saved_delete_confirm_"):
        calc_id = int(data.replace("saved_delete_confirm_", ""))

        success = delete_saved_calculation(user_id, calc_id)

        if success:
            await query.edit_message_text(
                "✅ **Расчёт удалён**\n\n"
                "Используйте /saved для просмотра оставшихся расчётов.",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "❌ Ошибка удаления расчёта"
            )
