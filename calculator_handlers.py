"""
Интерактивные обработчики для калькуляторов v3.1
ConversationHandler для пошагового ввода параметров
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
import logging

logger = logging.getLogger(__name__)

# Импортируем функции калькуляторов
try:
    from calculators import (
        calculate_concrete,
        calculate_reinforcement,
        calculate_formwork,
        calculate_electrical,
        calculate_water,
        calculate_winter_heating,
        format_calculator_result
    )
    CALCULATORS_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Модуль calculators недоступен")
    CALCULATORS_AVAILABLE = False


# ========================================
# СОСТОЯНИЯ CONVERSATIONHANDLER
# ========================================

# Калькулятор бетона
(CONCRETE_LENGTH, CONCRETE_WIDTH, CONCRETE_HEIGHT,
 CONCRETE_CLASS, CONCRETE_WASTAGE) = range(5)

# Калькулятор арматуры
(REBAR_LENGTH, REBAR_WIDTH, REBAR_HEIGHT, REBAR_DIAMETER,
 REBAR_SPACING, REBAR_TYPE) = range(5, 11)

# Калькулятор опалубки
(FORMWORK_AREA, FORMWORK_DURATION, FORMWORK_TYPE) = range(11, 14)

# Калькулятор электроснабжения
(ELEC_CRANE, ELEC_PUMP, ELEC_WELDER, ELEC_HEATER, ELEC_CABIN) = range(14, 19)

# Калькулятор водоснабжения
(WATER_WORKERS, WATER_BATCHES) = range(19, 21)

# Калькулятор зимнего прогрева
(WINTER_VOLUME, WINTER_TEMP, WINTER_METHOD) = range(21, 24)


# ========================================
# КАЛЬКУЛЯТОР БЕТОНА - ConversationHandler
# ========================================

async def concrete_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора бетона"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🏗️ **КАЛЬКУЛЯТОР БЕТОНА**\n\n"
            "Шаг 1 из 5\n\n"
            "Введите **длину** элемента в метрах:\n\n"
            "_Например: 10 или 10.5_\n\n"
            "Для отмены введите /cancel",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "🏗️ **КАЛЬКУЛЯТОР БЕТОНА**\n\n"
            "Шаг 1 из 5\n\n"
            "Введите **длину** элемента в метрах:\n\n"
            "_Например: 10 или 10.5_\n\n"
            "Для отмены введите /cancel",
            parse_mode='Markdown'
        )

    return CONCRETE_LENGTH


async def concrete_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить длину и запросить ширину"""
    try:
        length = float(update.message.text.replace(',', '.'))
        if length <= 0 or length > 1000:
            await update.message.reply_text(
                "❌ Длина должна быть от 0 до 1000 метров.\n"
                "Попробуйте ещё раз:"
            )
            return CONCRETE_LENGTH

        context.user_data['concrete_length'] = length

        await update.message.reply_text(
            f"✅ Длина: {length} м\n\n"
            "🏗️ Шаг 2 из 5\n\n"
            "Введите **ширину** элемента в метрах:\n\n"
            "_Например: 8 или 8.5_",
            parse_mode='Markdown'
        )
        return CONCRETE_WIDTH

    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите число.\n"
            "Например: 10 или 10.5"
        )
        return CONCRETE_LENGTH


async def concrete_width(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить ширину и запросить высоту"""
    try:
        width = float(update.message.text.replace(',', '.'))
        if width <= 0 or width > 1000:
            await update.message.reply_text(
                "❌ Ширина должна быть от 0 до 1000 метров.\n"
                "Попробуйте ещё раз:"
            )
            return CONCRETE_WIDTH

        context.user_data['concrete_width'] = width

        await update.message.reply_text(
            f"✅ Ширина: {width} м\n\n"
            "🏗️ Шаг 3 из 5\n\n"
            "Введите **высоту (толщину)** элемента в метрах:\n\n"
            "_Например: 0.2 (для плиты 20 см)_",
            parse_mode='Markdown'
        )
        return CONCRETE_HEIGHT

    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите число.\n"
            "Например: 8 или 8.5"
        )
        return CONCRETE_WIDTH


async def concrete_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить высоту и показать кнопки выбора класса бетона"""
    try:
        height = float(update.message.text.replace(',', '.'))
        if height <= 0 or height > 10:
            await update.message.reply_text(
                "❌ Высота должна быть от 0 до 10 метров.\n"
                "Попробуйте ещё раз:"
            )
            return CONCRETE_HEIGHT

        context.user_data['concrete_height'] = height

        # Кнопки выбора класса бетона
        keyboard = [
            [InlineKeyboardButton("B7.5", callback_data="concrete_class_B7.5"),
             InlineKeyboardButton("B10", callback_data="concrete_class_B10"),
             InlineKeyboardButton("B12.5", callback_data="concrete_class_B12.5")],
            [InlineKeyboardButton("B15", callback_data="concrete_class_B15"),
             InlineKeyboardButton("B20", callback_data="concrete_class_B20"),
             InlineKeyboardButton("B22.5", callback_data="concrete_class_B22.5")],
            [InlineKeyboardButton("B25", callback_data="concrete_class_B25"),
             InlineKeyboardButton("B30", callback_data="concrete_class_B30"),
             InlineKeyboardButton("B35", callback_data="concrete_class_B35")],
            [InlineKeyboardButton("B40", callback_data="concrete_class_B40")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Высота: {height} м\n\n"
            "🏗️ Шаг 4 из 5\n\n"
            "Выберите **класс бетона**:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return CONCRETE_CLASS

    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите число.\n"
            "Например: 0.2 или 0.25"
        )
        return CONCRETE_HEIGHT


async def concrete_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить класс бетона и показать кнопки процента запаса"""
    query = update.callback_query
    await query.answer()

    concrete_class = query.data.replace("concrete_class_", "")
    context.user_data['concrete_class'] = concrete_class

    # Кнопки выбора процента запаса
    keyboard = [
        [InlineKeyboardButton("0% (без запаса)", callback_data="concrete_wastage_0"),
         InlineKeyboardButton("5%", callback_data="concrete_wastage_5")],
        [InlineKeyboardButton("7%", callback_data="concrete_wastage_7"),
         InlineKeyboardButton("10%", callback_data="concrete_wastage_10")],
        [InlineKeyboardButton("15%", callback_data="concrete_wastage_15")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"✅ Класс бетона: {concrete_class}\n\n"
        "🏗️ Шаг 5 из 5\n\n"
        "Выберите **процент запаса** на потери:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return CONCRETE_WASTAGE


async def concrete_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать и показать результат"""
    query = update.callback_query
    await query.answer()

    wastage = float(query.data.replace("concrete_wastage_", ""))

    # Получаем все параметры
    length = context.user_data['concrete_length']
    width = context.user_data['concrete_width']
    height = context.user_data['concrete_height']
    concrete_class = context.user_data['concrete_class']

    # Рассчитываем
    if CALCULATORS_AVAILABLE:
        result = calculate_concrete(length, width, height, concrete_class, wastage)
        formatted_result = format_calculator_result("concrete", result)

        await query.edit_message_text(
            f"✅ **РЕЗУЛЬТАТ РАСЧЁТА БЕТОНА**\n\n"
            f"{formatted_result}\n\n"
            f"📋 Параметры:\n"
            f"• Длина: {length} м\n"
            f"• Ширина: {width} м\n"
            f"• Высота: {height} м\n"
            f"• Класс: {concrete_class}\n"
            f"• Запас: {wastage}%",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            "❌ Модуль калькуляторов недоступен."
        )

    # Очистка данных
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена диалога"""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Расчёт отменён.\n\n"
        "Используйте /calculators для нового расчёта."
    )
    return ConversationHandler.END


# ========================================
# СОЗДАНИЕ CONVERSATIONHANDLER
# ========================================

def create_concrete_calculator_handler():
    """Создать ConversationHandler для калькулятора бетона"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(concrete_start, pattern="^calc_concrete$")
        ],
        states={
            CONCRETE_LENGTH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, concrete_length)
            ],
            CONCRETE_WIDTH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, concrete_width)
            ],
            CONCRETE_HEIGHT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, concrete_height)
            ],
            CONCRETE_CLASS: [
                CallbackQueryHandler(concrete_class, pattern="^concrete_class_")
            ],
            CONCRETE_WASTAGE: [
                CallbackQueryHandler(concrete_calculate, pattern="^concrete_wastage_")
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel)
        ],
        name="concrete_calculator",
        persistent=False,
        per_message=False,
        per_chat=True,
        per_user=True
    )


# ========================================
# БЫСТРАЯ ВЕРСИЯ - Текстовая команда
# ========================================

async def quick_concrete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Быстрый расчёт бетона одной командой

    Использование: /calc_concrete 10 8 0.2 B25 5
    """
    try:
        args = context.args
        if len(args) < 4:
            await update.message.reply_text(
                "❌ Недостаточно параметров.\n\n"
                "**Формат:**\n"
                "`/calc_concrete длина ширина высота класс [запас]`\n\n"
                "**Пример:**\n"
                "`/calc_concrete 10 8 0.2 B25 5`",
                parse_mode='Markdown'
            )
            return

        length = float(args[0].replace(',', '.'))
        width = float(args[1].replace(',', '.'))
        height = float(args[2].replace(',', '.'))
        concrete_class = args[3].upper()
        wastage = float(args[4].replace(',', '.')) if len(args) > 4 else 5.0

        if CALCULATORS_AVAILABLE:
            result = calculate_concrete(length, width, height, concrete_class, wastage)
            formatted_result = format_calculator_result("concrete", result)

            await update.message.reply_text(
                f"✅ **РЕЗУЛЬТАТ РАСЧЁТА БЕТОНА**\n\n"
                f"{formatted_result}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Модуль калькуляторов недоступен.")

    except (ValueError, IndexError) as e:
        logger.error(f"Error in quick_concrete: {e}")
        await update.message.reply_text(
            f"❌ Ошибка в параметрах: {str(e)}\n\n"
            "Проверьте формат команды."
        )
