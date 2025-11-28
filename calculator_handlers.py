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
        format_calculator_result,
        calculate_math_expression,
        format_math_result
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

# Универсальный математический калькулятор
(MATH_EXPRESSION, MATH_RESULT) = range(24, 26)


# ========================================
# КАЛЬКУЛЯТОР БЕТОНА - ConversationHandler
# ========================================

async def concrete_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора бетона"""
    query = update.callback_query

    message_text = (
        "🏗️ **КАЛЬКУЛЯТОР ОБЪЁМА БЕТОНА**\n\n"
        "Посчитаю сколько бетона нужно для вашей конструкции:\n"
        "• Фундамент (ленточный, плитный)\n"
        "• Плита перекрытия\n"
        "• Стена, колонна\n"
        "• Любой прямоугольный элемент\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**Шаг 1 из 5**\n\n"
        "📏 Введите **ДЛИНУ** конструкции в метрах:\n\n"
        "_Примеры:_\n"
        "• Фундамент длиной 10 м → `10`\n"
        "• Плита 12.5 м → `12.5`\n\n"
        "Для отмены введите /cancel"
    )

    if query:
        await query.answer()
        await query.edit_message_text(message_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(message_text, parse_mode='Markdown')

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
            f"✅ Длина: **{length} м**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 2 из 5**\n\n"
            "📏 Введите **ШИРИНУ** конструкции в метрах:\n\n"
            "_Примеры:_\n"
            "• Фундамент шириной 0.4 м → `0.4`\n"
            "• Плита 8.5 м → `8.5`\n"
            "• Стена толщиной 0.3 м → `0.3`",
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
            f"✅ Ширина: **{width} м**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 3 из 5**\n\n"
            "📏 Введите **ВЫСОТУ (ТОЛЩИНУ)** конструкции в метрах:\n\n"
            "_Примеры:_\n"
            "• Плита перекрытия 20 см → `0.2`\n"
            "• Фундамент высотой 1.2 м → `1.2`\n"
            "• Стяжка 5 см → `0.05`\n"
            "• Стена высотой 3 м → `3`",
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


# ========================================
# КАЛЬКУЛЯТОР АРМАТУРЫ - ConversationHandler
# ========================================

async def rebar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора арматуры"""
    query = update.callback_query

    message_text = (
        "🔧 **КАЛЬКУЛЯТОР АРМАТУРЫ**\n\n"
        "Посчитаю сколько арматуры нужно для:\n"
        "• Фундамента (ленточного, плитного)\n"
        "• Плиты перекрытия\n"
        "• Колонн, балок\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**Шаг 1 из 6**\n\n"
        "📏 Введите **ДЛИНУ** армируемой конструкции в метрах:\n\n"
        "_Примеры:_\n"
        "• Фундамент 10 м → `10`\n"
        "• Плита 12.5 м → `12.5`\n\n"
        "Для отмены введите /cancel"
    )

    if query:
        await query.answer()
        await query.edit_message_text(message_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(message_text, parse_mode='Markdown')

    return REBAR_LENGTH


async def rebar_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить длину"""
    try:
        length = float(update.message.text.replace(',', '.'))
        if length <= 0 or length > 1000:
            await update.message.reply_text("❌ Длина должна быть от 0 до 1000 м")
            return REBAR_LENGTH

        context.user_data['rebar_length'] = length
        await update.message.reply_text(
            f"✅ Длина: **{length} м**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 2 из 6**\n\n"
            "📏 Введите **ШИРИНУ** конструкции в метрах:\n\n"
            "_Примеры:_\n"
            "• Фундамент шириной 0.4 м → `0.4`\n"
            "• Плита 8 м → `8`",
            parse_mode='Markdown'
        )
        return REBAR_WIDTH
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return REBAR_LENGTH


async def rebar_width(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить ширину"""
    try:
        width = float(update.message.text.replace(',', '.'))
        if width <= 0 or width > 1000:
            await update.message.reply_text("❌ Ширина должна быть от 0 до 1000 м")
            return REBAR_WIDTH

        context.user_data['rebar_width'] = width
        await update.message.reply_text(
            f"✅ Ширина: **{width} м**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 3 из 6**\n\n"
            "📏 Введите **ВЫСОТУ (ТОЛЩИНУ)** конструкции в метрах:\n\n"
            "_Примеры:_\n"
            "• Плита 20 см → `0.2`\n"
            "• Фундамент 1.5 м → `1.5`",
            parse_mode='Markdown'
        )
        return REBAR_HEIGHT
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return REBAR_WIDTH


async def rebar_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить высоту"""
    try:
        height = float(update.message.text.replace(',', '.'))
        if height <= 0 or height > 10:
            await update.message.reply_text("❌ Высота должна быть от 0 до 10 м")
            return REBAR_HEIGHT

        context.user_data['rebar_height'] = height

        # Кнопки выбора диаметра
        keyboard = [
            [InlineKeyboardButton("Ø8", callback_data="rebar_diam_8"),
             InlineKeyboardButton("Ø10", callback_data="rebar_diam_10"),
             InlineKeyboardButton("Ø12", callback_data="rebar_diam_12")],
            [InlineKeyboardButton("Ø14", callback_data="rebar_diam_14"),
             InlineKeyboardButton("Ø16", callback_data="rebar_diam_16"),
             InlineKeyboardButton("Ø18", callback_data="rebar_diam_18")],
            [InlineKeyboardButton("Ø20", callback_data="rebar_diam_20"),
             InlineKeyboardButton("Ø22", callback_data="rebar_diam_22"),
             InlineKeyboardButton("Ø25", callback_data="rebar_diam_25")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Высота: {height} м\n\n"
            "🔧 Шаг 4 из 6\n\n"
            "Выберите **диаметр арматуры** (мм):",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return REBAR_DIAMETER
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return REBAR_HEIGHT


async def rebar_diameter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить диаметр"""
    query = update.callback_query
    await query.answer()

    diameter = int(query.data.replace("rebar_diam_", ""))
    context.user_data['rebar_diameter'] = diameter

    await query.edit_message_text(
        f"✅ Диаметр: Ø{diameter} мм\n\n"
        "🔧 Шаг 5 из 6\n\n"
        "Введите **шаг арматуры** в мм:\n\n"
        "_Например: 200 (для шага 20 см)_",
        parse_mode='Markdown'
    )
    return REBAR_SPACING


async def rebar_spacing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить шаг"""
    try:
        spacing = float(update.message.text.replace(',', '.'))
        if spacing <= 0 or spacing > 1000:
            await update.message.reply_text("❌ Шаг должен быть от 0 до 1000 мм")
            return REBAR_SPACING

        context.user_data['rebar_spacing'] = spacing

        # Кнопки выбора типа элемента
        keyboard = [
            [InlineKeyboardButton("Плита (slab)", callback_data="rebar_type_slab")],
            [InlineKeyboardButton("Балка (beam)", callback_data="rebar_type_beam")],
            [InlineKeyboardButton("Колонна (column)", callback_data="rebar_type_column")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Шаг: {spacing} мм\n\n"
            "🔧 Шаг 6 из 6\n\n"
            "Выберите **тип элемента**:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return REBAR_TYPE
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return REBAR_SPACING


async def rebar_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать арматуру"""
    query = update.callback_query
    await query.answer()

    element_type = query.data.replace("rebar_type_", "")

    # Получаем параметры
    length = context.user_data['rebar_length']
    width = context.user_data['rebar_width']
    height = context.user_data['rebar_height']
    diameter = context.user_data['rebar_diameter']
    spacing = context.user_data['rebar_spacing']

    if CALCULATORS_AVAILABLE:
        result = calculate_reinforcement(length, width, height, diameter, spacing, element_type)
        formatted_result = format_calculator_result("reinforcement", result)

        type_names = {"slab": "Плита", "beam": "Балка", "column": "Колонна"}

        await query.edit_message_text(
            f"✅ **РЕЗУЛЬТАТ РАСЧЁТА АРМАТУРЫ**\n\n"
            f"{formatted_result}\n\n"
            f"📋 Параметры:\n"
            f"• Длина: {length} м\n"
            f"• Ширина: {width} м\n"
            f"• Высота: {height} м\n"
            f"• Диаметр: Ø{diameter} мм\n"
            f"• Шаг: {spacing} мм\n"
            f"• Тип: {type_names.get(element_type, element_type)}",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text("❌ Модуль калькуляторов недоступен.")

    context.user_data.clear()
    return ConversationHandler.END


def create_rebar_calculator_handler():
    """Создать ConversationHandler для калькулятора арматуры"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(rebar_start, pattern="^calc_reinforcement$")
        ],
        states={
            REBAR_LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, rebar_length)],
            REBAR_WIDTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, rebar_width)],
            REBAR_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, rebar_height)],
            REBAR_DIAMETER: [CallbackQueryHandler(rebar_diameter, pattern="^rebar_diam_")],
            REBAR_SPACING: [MessageHandler(filters.TEXT & ~filters.COMMAND, rebar_spacing)],
            REBAR_TYPE: [CallbackQueryHandler(rebar_calculate, pattern="^rebar_type_")],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="rebar_calculator",
        persistent=False,
        per_message=False,
        per_chat=True,
        per_user=True
    )


# ========================================
# КАЛЬКУЛЯТОР ОПАЛУБКИ - ConversationHandler
# ========================================

async def formwork_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора опалубки"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "📐 **КАЛЬКУЛЯТОР ОПАЛУБКИ**\n\n"
            "Шаг 1 из 3\n\n"
            "Введите **площадь опалубки** в м²:\n\n"
            "_Например: 150_",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "📐 **КАЛЬКУЛЯТОР ОПАЛУБКИ**\n\n"
            "Шаг 1 из 3\n\n"
            "Введите **площадь опалубки** в м²:",
            parse_mode='Markdown'
        )
    return FORMWORK_AREA


async def formwork_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить площадь"""
    try:
        area = float(update.message.text.replace(',', '.'))
        if area <= 0 or area > 100000:
            await update.message.reply_text("❌ Площадь должна быть от 0 до 100000 м²")
            return FORMWORK_AREA

        context.user_data['formwork_area'] = area
        await update.message.reply_text(
            f"✅ Площадь: {area} м²\n\n"
            "📐 Шаг 2 из 3\n\n"
            "Введите **срок эксплуатации** в днях:\n\n"
            "_Например: 30_",
            parse_mode='Markdown'
        )
        return FORMWORK_DURATION
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return FORMWORK_AREA


async def formwork_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить срок"""
    try:
        duration = int(update.message.text.replace(',', '.'))
        if duration <= 0 or duration > 365:
            await update.message.reply_text("❌ Срок должен быть от 1 до 365 дней")
            return FORMWORK_DURATION

        context.user_data['formwork_duration'] = duration

        # Кнопки типа опалубки
        keyboard = [
            [InlineKeyboardButton("Щитовая (panel)", callback_data="formwork_type_panel")],
            [InlineKeyboardButton("Стеновая (wall)", callback_data="formwork_type_wall")],
            [InlineKeyboardButton("Универсальная (universal)", callback_data="formwork_type_universal")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Срок: {duration} дней\n\n"
            "📐 Шаг 3 из 3\n\n"
            "Выберите **тип опалубки**:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return FORMWORK_TYPE
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return FORMWORK_DURATION


async def formwork_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать опалубку"""
    query = update.callback_query
    await query.answer()

    formwork_type = query.data.replace("formwork_type_", "")

    area = context.user_data['formwork_area']
    duration = context.user_data['formwork_duration']

    if CALCULATORS_AVAILABLE:
        result = calculate_formwork(area, duration, formwork_type)
        formatted_result = format_calculator_result("formwork", result)

        type_names = {"panel": "Щитовая", "wall": "Стеновая", "universal": "Универсальная"}

        await query.edit_message_text(
            f"✅ **РЕЗУЛЬТАТ РАСЧЁТА ОПАЛУБКИ**\n\n"
            f"{formatted_result}\n\n"
            f"📋 Параметры:\n"
            f"• Площадь: {area} м²\n"
            f"• Срок: {duration} дней\n"
            f"• Тип: {type_names.get(formwork_type, formwork_type)}",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text("❌ Модуль калькуляторов недоступен.")

    context.user_data.clear()
    return ConversationHandler.END


def create_formwork_calculator_handler():
    """Создать ConversationHandler для калькулятора опалубки"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(formwork_start, pattern="^calc_formwork$")
        ],
        states={
            FORMWORK_AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, formwork_area)],
            FORMWORK_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, formwork_duration)],
            FORMWORK_TYPE: [CallbackQueryHandler(formwork_calculate, pattern="^formwork_type_")],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="formwork_calculator",
        persistent=False,
        per_message=False,
        per_chat=True,
        per_user=True
    )


# ========================================
# КАЛЬКУЛЯТОР ЭЛЕКТРОСНАБЖЕНИЯ - ConversationHandler
# ========================================

async def elec_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора электроснабжения"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "⚡ **КАЛЬКУЛЯТОР ЭЛЕКТРОСНАБЖЕНИЯ**\n\n"
            "Шаг 1 из 5\n\n"
            "Введите **количество кранов** (шт):\n\n"
            "_Например: 2_",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "⚡ **КАЛЬКУЛЯТОР ЭЛЕКТРОСНАБЖЕНИЯ**\n\n"
            "Шаг 1 из 5\n\n"
            "Введите **количество кранов** (шт):",
            parse_mode='Markdown'
        )
    return ELEC_CRANE


async def elec_crane(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить количество кранов"""
    try:
        crane_count = int(update.message.text.replace(',', '.'))
        if crane_count < 0 or crane_count > 100:
            await update.message.reply_text("❌ Количество должно быть от 0 до 100")
            return ELEC_CRANE

        context.user_data['elec_crane'] = crane_count
        await update.message.reply_text(
            f"✅ Краны: {crane_count} шт\n\n"
            "⚡ Шаг 2 из 5\n\n"
            "Введите **количество насосов** (шт):",
            parse_mode='Markdown'
        )
        return ELEC_PUMP
    except ValueError:
        await update.message.reply_text("❌ Введите целое число")
        return ELEC_CRANE


async def elec_pump(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить количество насосов"""
    try:
        pump_count = int(update.message.text.replace(',', '.'))
        if pump_count < 0 or pump_count > 100:
            await update.message.reply_text("❌ Количество должно быть от 0 до 100")
            return ELEC_PUMP

        context.user_data['elec_pump'] = pump_count
        await update.message.reply_text(
            f"✅ Насосы: {pump_count} шт\n\n"
            "⚡ Шаг 3 из 5\n\n"
            "Введите **количество сварочных аппаратов** (шт):",
            parse_mode='Markdown'
        )
        return ELEC_WELDER
    except ValueError:
        await update.message.reply_text("❌ Введите целое число")
        return ELEC_PUMP


async def elec_welder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить количество сварочных"""
    try:
        welder_count = int(update.message.text.replace(',', '.'))
        if welder_count < 0 or welder_count > 100:
            await update.message.reply_text("❌ Количество должно быть от 0 до 100")
            return ELEC_WELDER

        context.user_data['elec_welder'] = welder_count
        await update.message.reply_text(
            f"✅ Сварочные: {welder_count} шт\n\n"
            "⚡ Шаг 4 из 5\n\n"
            "Введите **количество обогревателей** (шт):",
            parse_mode='Markdown'
        )
        return ELEC_HEATER
    except ValueError:
        await update.message.reply_text("❌ Введите целое число")
        return ELEC_WELDER


async def elec_heater(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить количество обогревателей"""
    try:
        heater_count = int(update.message.text.replace(',', '.'))
        if heater_count < 0 or heater_count > 100:
            await update.message.reply_text("❌ Количество должно быть от 0 до 100")
            return ELEC_HEATER

        context.user_data['elec_heater'] = heater_count
        await update.message.reply_text(
            f"✅ Обогреватели: {heater_count} шт\n\n"
            "⚡ Шаг 5 из 5\n\n"
            "Введите **количество бытовок** (шт):",
            parse_mode='Markdown'
        )
        return ELEC_CABIN
    except ValueError:
        await update.message.reply_text("❌ Введите целое число")
        return ELEC_HEATER


async def elec_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать электроснабжение"""
    try:
        cabin_count = int(update.message.text.replace(',', '.'))
        if cabin_count < 0 or cabin_count > 100:
            await update.message.reply_text("❌ Количество должно быть от 0 до 100")
            return ELEC_CABIN

        crane_count = context.user_data['elec_crane']
        pump_count = context.user_data['elec_pump']
        welder_count = context.user_data['elec_welder']
        heater_count = context.user_data['elec_heater']

        if CALCULATORS_AVAILABLE:
            result = calculate_electrical(crane_count, pump_count, welder_count, heater_count, cabin_count)
            formatted_result = format_calculator_result("electrical", result)

            await update.message.reply_text(
                f"✅ **РЕЗУЛЬТАТ РАСЧЁТА ЭЛЕКТРОСНАБЖЕНИЯ**\n\n"
                f"{formatted_result}\n\n"
                f"📋 Параметры:\n"
                f"• Краны: {crane_count} шт\n"
                f"• Насосы: {pump_count} шт\n"
                f"• Сварочные: {welder_count} шт\n"
                f"• Обогреватели: {heater_count} шт\n"
                f"• Бытовки: {cabin_count} шт",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Модуль калькуляторов недоступен.")

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ Введите целое число")
        return ELEC_CABIN


def create_electrical_calculator_handler():
    """Создать ConversationHandler для калькулятора электроснабжения"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(elec_start, pattern="^calc_electrical$")
        ],
        states={
            ELEC_CRANE: [MessageHandler(filters.TEXT & ~filters.COMMAND, elec_crane)],
            ELEC_PUMP: [MessageHandler(filters.TEXT & ~filters.COMMAND, elec_pump)],
            ELEC_WELDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, elec_welder)],
            ELEC_HEATER: [MessageHandler(filters.TEXT & ~filters.COMMAND, elec_heater)],
            ELEC_CABIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, elec_calculate)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="electrical_calculator",
        persistent=False,
        per_message=False,
        per_chat=True,
        per_user=True
    )


# ========================================
# КАЛЬКУЛЯТОР ВОДОСНАБЖЕНИЯ - ConversationHandler
# ========================================

async def water_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора водоснабжения"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "💧 **КАЛЬКУЛЯТОР ВОДОСНАБЖЕНИЯ**\n\n"
            "Шаг 1 из 2\n\n"
            "Введите **количество рабочих** (чел):\n\n"
            "_Например: 50_",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "💧 **КАЛЬКУЛЯТОР ВОДОСНАБЖЕНИЯ**\n\n"
            "Шаг 1 из 2\n\n"
            "Введите **количество рабочих** (чел):",
            parse_mode='Markdown'
        )
    return WATER_WORKERS


async def water_workers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить количество рабочих"""
    try:
        workers = int(update.message.text.replace(',', '.'))
        if workers <= 0 or workers > 10000:
            await update.message.reply_text("❌ Количество должно быть от 1 до 10000")
            return WATER_WORKERS

        context.user_data['water_workers'] = workers
        await update.message.reply_text(
            f"✅ Рабочие: {workers} чел\n\n"
            "💧 Шаг 2 из 2\n\n"
            "Введите **количество замесов бетона в день**:\n\n"
            "_Например: 10_",
            parse_mode='Markdown'
        )
        return WATER_BATCHES
    except ValueError:
        await update.message.reply_text("❌ Введите целое число")
        return WATER_WORKERS


async def water_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать водоснабжение"""
    try:
        batches = int(update.message.text.replace(',', '.'))
        if batches < 0 or batches > 1000:
            await update.message.reply_text("❌ Количество должно быть от 0 до 1000")
            return WATER_BATCHES

        workers = context.user_data['water_workers']

        if CALCULATORS_AVAILABLE:
            result = calculate_water(workers=workers, mixers_per_day=batches)
            formatted_result = format_calculator_result("water", result)

            await update.message.reply_text(
                f"✅ **РЕЗУЛЬТАТ РАСЧЁТА ВОДОСНАБЖЕНИЯ**\n\n"
                f"{formatted_result}\n\n"
                f"📋 Параметры:\n"
                f"• Рабочие: {workers} чел\n"
                f"• Замесов бетона в день: {batches}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Модуль калькуляторов недоступен.")

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ Введите целое число")
        return WATER_BATCHES


def create_water_calculator_handler():
    """Создать ConversationHandler для калькулятора водоснабжения"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(water_start, pattern="^calc_water$")
        ],
        states={
            WATER_WORKERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, water_workers)],
            WATER_BATCHES: [MessageHandler(filters.TEXT & ~filters.COMMAND, water_calculate)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="water_calculator",
        persistent=False,
        per_message=False,
        per_chat=True,
        per_user=True
    )


# ========================================
# КАЛЬКУЛЯТОР ЗИМНЕГО ПРОГРЕВА - ConversationHandler
# ========================================

async def winter_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора зимнего прогрева"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "❄️ **КАЛЬКУЛЯТОР ЗИМНЕГО ПРОГРЕВА**\n\n"
            "Шаг 1 из 3\n\n"
            "Введите **объём бетона** в м³:\n\n"
            "_Например: 50_",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❄️ **КАЛЬКУЛЯТОР ЗИМНЕГО ПРОГРЕВА**\n\n"
            "Шаг 1 из 3\n\n"
            "Введите **объём бетона** в м³:",
            parse_mode='Markdown'
        )
    return WINTER_VOLUME


async def winter_volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить объём бетона"""
    try:
        volume = float(update.message.text.replace(',', '.'))
        if volume <= 0 or volume > 10000:
            await update.message.reply_text("❌ Объём должен быть от 0 до 10000 м³")
            return WINTER_VOLUME

        context.user_data['winter_volume'] = volume
        await update.message.reply_text(
            f"✅ Объём: {volume} м³\n\n"
            "❄️ Шаг 2 из 3\n\n"
            "Введите **температуру воздуха** (°C):\n\n"
            "_Например: -15_",
            parse_mode='Markdown'
        )
        return WINTER_TEMP
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return WINTER_VOLUME


async def winter_temp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить температуру"""
    try:
        temp = float(update.message.text.replace(',', '.'))
        if temp > 5 or temp < -50:
            await update.message.reply_text("❌ Температура должна быть от -50 до +5 °C")
            return WINTER_TEMP

        context.user_data['winter_temp'] = temp

        # Кнопки метода прогрева
        keyboard = [
            [InlineKeyboardButton("Электроды (electrode)", callback_data="winter_method_electrode")],
            [InlineKeyboardButton("Провод (wire)", callback_data="winter_method_wire")],
            [InlineKeyboardButton("Термомат (thermomat)", callback_data="winter_method_thermomat")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Температура: {temp} °C\n\n"
            "❄️ Шаг 3 из 3\n\n"
            "Выберите **метод прогрева**:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return WINTER_METHOD
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return WINTER_TEMP


async def winter_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать зимний прогрев"""
    query = update.callback_query
    await query.answer()

    method = query.data.replace("winter_method_", "")

    volume = context.user_data['winter_volume']
    temp = context.user_data['winter_temp']

    if CALCULATORS_AVAILABLE:
        result = calculate_winter_heating(volume, temp, method)
        formatted_result = format_calculator_result("winter_heating", result)

        method_names = {"electrode": "Электроды", "wire": "Провод ПНСВ", "thermomat": "Термоматы"}

        await query.edit_message_text(
            f"✅ **РЕЗУЛЬТАТ РАСЧЁТА ЗИМНЕГО ПРОГРЕВА**\n\n"
            f"{formatted_result}\n\n"
            f"📋 Параметры:\n"
            f"• Объём бетона: {volume} м³\n"
            f"• Температура: {temp} °C\n"
            f"• Метод: {method_names.get(method, method)}",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text("❌ Модуль калькуляторов недоступен.")

    context.user_data.clear()
    return ConversationHandler.END


def create_winter_calculator_handler():
    """Создать ConversationHandler для калькулятора зимнего прогрева"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(winter_start, pattern="^calc_winter_heating$")
        ],
        states={
            WINTER_VOLUME: [MessageHandler(filters.TEXT & ~filters.COMMAND, winter_volume)],
            WINTER_TEMP: [MessageHandler(filters.TEXT & ~filters.COMMAND, winter_temp)],
            WINTER_METHOD: [CallbackQueryHandler(winter_calculate, pattern="^winter_method_")],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="winter_calculator",
        persistent=False,
        per_message=False,
        per_chat=True,
        per_user=True
    )
# ========================================
# УНИВЕРСАЛЬНЫЙ МАТЕМАТИЧЕСКИЙ КАЛЬКУЛЯТОР
# ========================================

async def math_calculator_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало работы с математическим калькулятором"""
    query = update.callback_query
    if query:
        await query.answer()
        context.user_data['math_expression'] = ""
        
        keyboard = create_math_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🧮 **МАТЕМАТИЧЕСКИЙ КАЛЬКУЛЯТОР**\n\n"
            "📝 **Выражение:**\n"
            "`0`\n\n"
            "💡 Используйте кнопки для ввода или отправьте выражение текстом\n\n"
            "**Примеры:**\n"
            "• `2 + 2`\n"
            "• `10 * 5.5`\n"
            "• `(100 + 50) / 2`\n"
            "• `2^3` (2 в степени 3)\n"
            "• `3.14 * 2`",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return MATH_EXPRESSION
    else:
        await update.message.reply_text(
            "🧮 **МАТЕМАТИЧЕСКИЙ КАЛЬКУЛЯТОР**\n\n"
            "Введите математическое выражение или используйте /calc_math для интерактивного режима",
            parse_mode='Markdown'
        )
        return MATH_EXPRESSION


def create_math_keyboard():
    """Создать клавиатуру математического калькулятора"""
    return [
        [
            InlineKeyboardButton("C", callback_data="math_clear"),
            InlineKeyboardButton("⌫", callback_data="math_backspace"),
            InlineKeyboardButton("÷", callback_data="math_/"),
            InlineKeyboardButton("×", callback_data="math_*")
        ],
        [
            InlineKeyboardButton("7", callback_data="math_7"),
            InlineKeyboardButton("8", callback_data="math_8"),
            InlineKeyboardButton("9", callback_data="math_9"),
            InlineKeyboardButton("-", callback_data="math_-")
        ],
        [
            InlineKeyboardButton("4", callback_data="math_4"),
            InlineKeyboardButton("5", callback_data="math_5"),
            InlineKeyboardButton("6", callback_data="math_6"),
            InlineKeyboardButton("+", callback_data="math_+")
        ],
        [
            InlineKeyboardButton("1", callback_data="math_1"),
            InlineKeyboardButton("2", callback_data="math_2"),
            InlineKeyboardButton("3", callback_data="math_3"),
            InlineKeyboardButton("=", callback_data="math_=")
        ],
        [
            InlineKeyboardButton("0", callback_data="math_0"),
            InlineKeyboardButton(".", callback_data="math_."),
            InlineKeyboardButton("(", callback_data="math_("),
            InlineKeyboardButton(")", callback_data="math_)")
        ],
        [
            InlineKeyboardButton("^", callback_data="math_^"),
            InlineKeyboardButton("√", callback_data="math_sqrt"),
            InlineKeyboardButton("π", callback_data="math_pi"),
            InlineKeyboardButton("e", callback_data="math_e")
        ],
        [
            InlineKeyboardButton("✅ Вычислить", callback_data="math_calculate"),
            InlineKeyboardButton("❌ Отмена", callback_data="math_cancel")
        ]
    ]


async def math_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий кнопок калькулятора"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.replace("math_", "")
    expression = context.user_data.get('math_expression', '')
    
    if data == "clear":
        expression = ""
    elif data == "backspace":
        expression = expression[:-1] if expression else ""
    elif data == "=" or data == "calculate":
        if expression:
            if CALCULATORS_AVAILABLE:
                result = calculate_math_expression(expression)
                formatted = format_math_result(result)
                
                keyboard = create_math_keyboard()
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    formatted,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
                if result.get("success"):
                    context.user_data['math_expression'] = str(result['formatted'])
                else:
                    context.user_data['math_expression'] = expression
            else:
                await query.edit_message_text("❌ Модуль калькуляторов недоступен.")
        else:
            await query.answer("Введите выражение", show_alert=True)
        return MATH_EXPRESSION
    elif data == "cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Калькулятор закрыт.\n\nИспользуйте /calculators для нового расчёта.")
        return ConversationHandler.END
    elif data == "sqrt":
        expression += "**(1/2)"
    elif data == "pi":
        expression += "3.14159265359"
    elif data == "e":
        expression += "2.71828182846"
    else:
        expression += data
    
    context.user_data['math_expression'] = expression
    
    keyboard = create_math_keyboard()
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    display_expr = expression if expression else "0"
    
    await query.edit_message_text(
        f"🧮 **МАТЕМАТИЧЕСКИЙ КАЛЬКУЛЯТОР**\n\n"
        f"📝 **Выражение:**\n"
        f"`{display_expr}`\n\n"
        f"💡 Используйте кнопки для ввода или отправьте выражение текстом",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return MATH_EXPRESSION


async def math_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового ввода выражения"""
    expression = update.message.text.strip()
    
    if CALCULATORS_AVAILABLE:
        result = calculate_math_expression(expression)
        formatted = format_math_result(result)
        
        if result.get("success"):
            context.user_data['math_expression'] = str(result['formatted'])
        else:
            context.user_data['math_expression'] = expression
        
        keyboard = create_math_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            formatted,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Модуль калькуляторов недоступен.")
    
    return MATH_EXPRESSION


def create_math_calculator_handler():
    """Создать ConversationHandler для математического калькулятора"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(math_calculator_start, pattern="^calc_math$")
        ],
        states={
            MATH_EXPRESSION: [
                CallbackQueryHandler(math_button_handler, pattern="^math_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, math_text_handler)
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^math_cancel$")
        ],
        name="math_calculator",
        persistent=False,
        per_message=False,
        per_chat=True,
        per_user=True
    )


async def quick_math(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Быстрый расчёт математического выражения"""
    try:
        if not context.args:
            await update.message.reply_text(
                "🧮 **МАТЕМАТИЧЕСКИЙ КАЛЬКУЛЯТОР**\n\n"
                "**Формат:**\n"
                "`/calc_math выражение`\n\n"
                "**Примеры:**\n"
                "• `/calc_math 2+2`\n"
                "• `/calc_math 10*5.5`\n"
                "• `/calc_math (100+50)/2`\n"
                "• `/calc_math 2^3`\n\n"
                "Или используйте `/calculators` для интерактивного режима",
                parse_mode='Markdown'
            )
            return
        
        expression = " ".join(context.args)
        
        if CALCULATORS_AVAILABLE:
            result = calculate_math_expression(expression)
            formatted = format_math_result(result)
            
            await update.message.reply_text(formatted, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Модуль калькуляторов недоступен.")
    
    except Exception as e:
        logger.error(f"Error in quick_math: {e}")
        await update.message.reply_text(
            f"❌ Ошибка: {str(e)}\n\nПроверьте формат выражения."
        )

