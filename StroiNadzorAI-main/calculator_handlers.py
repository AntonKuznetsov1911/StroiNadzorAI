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
        calculate_math_expression,
        calculate_brick,
        calculate_tile,
        calculate_paint,
        calculate_wall_area,
        calculate_roof,
        calculate_plaster,
        calculate_wallpaper,
        calculate_laminate,
        calculate_insulation,
        calculate_foundation,
        calculate_stairs,
        calculate_drywall,
        calculate_earthwork,
        calculate_labor,
        format_calculator_result,
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

# Калькулятор кирпича
(BRICK_LENGTH, BRICK_HEIGHT, BRICK_THICKNESS, BRICK_TYPE, BRICK_OPENINGS) = range(26, 31)

# Калькулятор плитки
(TILE_AREA, TILE_LENGTH, TILE_WIDTH, TILE_WASTAGE) = range(31, 35)

# Калькулятор краски
(PAINT_AREA, PAINT_COVERAGE, PAINT_COATS) = range(35, 38)

# Калькулятор площади стен
(WALL_LENGTH, WALL_WIDTH, WALL_HEIGHT, WALL_OPENINGS) = range(38, 42)

# Калькулятор кровли
(ROOF_LENGTH, ROOF_WIDTH, ROOF_TYPE, ROOF_SLOPE) = range(42, 46)

# Калькулятор штукатурки
(PLASTER_AREA, PLASTER_THICKNESS, PLASTER_TYPE) = range(46, 49)

# Калькулятор обоев
(WALLPAPER_AREA, WALLPAPER_ROLL_LENGTH, WALLPAPER_ROLL_WIDTH) = range(49, 52)

# Калькулятор ламината
(LAMINATE_AREA, LAMINATE_LENGTH, LAMINATE_WIDTH, LAMINATE_WASTAGE) = range(52, 56)

# Калькулятор утепления
(INSULATION_AREA, INSULATION_THICKNESS, INSULATION_TYPE) = range(56, 59)

# Калькулятор фундамента
(FOUNDATION_TYPE, FOUNDATION_LENGTH, FOUNDATION_WIDTH, FOUNDATION_HEIGHT, FOUNDATION_SOIL) = range(59, 64)

# Калькулятор лестницы
(STAIRS_HEIGHT, STAIRS_STEP_HEIGHT, STAIRS_STEP_DEPTH) = range(64, 67)

# Калькулятор гипсокартона
(DRYWALL_AREA, DRYWALL_SHEET_LENGTH, DRYWALL_SHEET_WIDTH) = range(67, 70)

# Калькулятор земляных работ
(EARTHWORK_LENGTH, EARTHWORK_WIDTH, EARTHWORK_DEPTH, EARTHWORK_SOIL_TYPE) = range(70, 74)

# Калькулятор трудозатрат
(LABOR_TASK_TYPE, LABOR_QUANTITY, LABOR_WORKERS) = range(74, 77)


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



"""
Расширение интерактивных калькуляторов - 14 новых калькуляторов
Добавляется к calculator_handlers.py
"""

# ========================================
# КАЛЬКУЛЯТОР КИРПИЧА/БЛОКОВ - ConversationHandler
# ========================================

async def brick_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора кирпича"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🧱 **КАЛЬКУЛЯТОР КИРПИЧА/БЛОКОВ**\n\n"
            "Посчитаю количество кирпича для кладки стен.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 1 из 5**\n\n"
            "📏 Введите **ДЛИНУ стены** в метрах:\n\n"
            "_Например: 10_",
            parse_mode='Markdown'
        )
    return BRICK_LENGTH


async def brick_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить длину стены"""
    try:
        length = float(update.message.text.replace(',', '.'))
        if length <= 0 or length > 1000:
            await update.message.reply_text("❌ Длина должна быть от 0 до 1000 м")
            return BRICK_LENGTH

        context.user_data['brick_length'] = length
        await update.message.reply_text(
            f"✅ Длина: {length} м\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 2 из 5**\n\n"
            "📏 Введите **ВЫСОТУ стены** в метрах:\n\n"
            "_Например: 3_",
            parse_mode='Markdown'
        )
        return BRICK_HEIGHT
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return BRICK_LENGTH


async def brick_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить высоту стены"""
    try:
        height = float(update.message.text.replace(',', '.'))
        if height <= 0 or height > 100:
            await update.message.reply_text("❌ Высота должна быть от 0 до 100 м")
            return BRICK_HEIGHT

        context.user_data['brick_height'] = height

        # Кнопки толщины стены
        keyboard = [
            [InlineKeyboardButton("12 см (0.5 кирпича)", callback_data="brick_thick_0.12"),
             InlineKeyboardButton("25 см (1 кирпич)", callback_data="brick_thick_0.25")],
            [InlineKeyboardButton("38 см (1.5 кирпича)", callback_data="brick_thick_0.38"),
             InlineKeyboardButton("51 см (2 кирпича)", callback_data="brick_thick_0.51")],
            [InlineKeyboardButton("64 см (2.5 кирпича)", callback_data="brick_thick_0.64")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Высота: {height} м\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 3 из 5**\n\n"
            "📐 Выберите **ТОЛЩИНУ стены**:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return BRICK_THICKNESS
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return BRICK_HEIGHT


async def brick_thickness(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить толщину стены"""
    query = update.callback_query
    await query.answer()

    thickness = float(query.data.replace("brick_thick_", ""))
    context.user_data['brick_thickness'] = thickness

    # Кнопки типа кирпича
    keyboard = [
        [InlineKeyboardButton("Одинарный (250×120×65)", callback_data="brick_type_standard")],
        [InlineKeyboardButton("Полуторный (250×120×88)", callback_data="brick_type_one_half")],
        [InlineKeyboardButton("Двойной (250×120×138)", callback_data="brick_type_double")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"✅ Толщина: {thickness} м\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**Шаг 4 из 5**\n\n"
        "🧱 Выберите **ТИП КИРПИЧА**:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return BRICK_TYPE


async def brick_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить тип кирпича и запросить проёмы"""
    query = update.callback_query
    await query.answer()

    brick_type = query.data.replace("brick_type_", "")
    context.user_data['brick_type'] = brick_type

    type_names = {
        "standard": "Одинарный (250×120×65)",
        "one_half": "Полуторный (250×120×88)",
        "double": "Двойной (250×120×138)"
    }

    await query.edit_message_text(
        f"✅ Тип: {type_names.get(brick_type, brick_type)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**Шаг 5 из 5**\n\n"
        "🚪 Введите **ПЛОЩАДЬ ПРОЁМОВ** (окна, двери) в м²:\n\n"
        "_Например: 5\nЕсли нет проёмов, введите 0_",
        parse_mode='Markdown'
    )
    return BRICK_OPENINGS


async def brick_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать количество кирпича"""
    try:
        openings = float(update.message.text.replace(',', '.'))
        if openings < 0:
            await update.message.reply_text("❌ Площадь не может быть отрицательной")
            return BRICK_OPENINGS

        length = context.user_data['brick_length']
        height = context.user_data['brick_height']
        thickness = context.user_data['brick_thickness']
        brick_type = context.user_data['brick_type']

        if CALCULATORS_AVAILABLE:
            result = calculate_brick(length, height, thickness, openings, brick_type)
            formatted_result = format_calculator_result("brick", result)

            await update.message.reply_text(
                f"{formatted_result}\n\n"
                f"📋 Параметры:\n"
                f"• Длина стены: {length} м\n"
                f"• Высота стены: {height} м\n"
                f"• Толщина стены: {thickness} м\n"
                f"• Площадь проёмов: {openings} м²",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Модуль калькуляторов недоступен.")

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return BRICK_OPENINGS


def create_brick_calculator_handler():
    """Создать ConversationHandler для калькулятора кирпича"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(brick_start, pattern="^calc_brick$")
        ],
        states={
            BRICK_LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, brick_length)],
            BRICK_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, brick_height)],
            BRICK_THICKNESS: [CallbackQueryHandler(brick_thickness, pattern="^brick_thick_")],
            BRICK_TYPE: [CallbackQueryHandler(brick_type, pattern="^brick_type_")],
            BRICK_OPENINGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, brick_calculate)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="brick_calculator",
        persistent=False,
        per_chat=True,
        per_user=True
    )


# ========================================
# КАЛЬКУЛЯТОР ПЛИТКИ - ConversationHandler
# ========================================

async def tile_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора плитки"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🔲 **КАЛЬКУЛЯТОР ПЛИТКИ**\n\n"
            "Посчитаю количество плитки для облицовки.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 1 из 4**\n\n"
            "📐 Введите **ПЛОЩАДЬ** под облицовку в м²:\n\n"
            "_Например: 20_",
            parse_mode='Markdown'
        )
    return TILE_AREA


async def tile_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить площадь"""
    try:
        area = float(update.message.text.replace(',', '.'))
        if area <= 0:
            await update.message.reply_text("❌ Площадь должна быть положительной")
            return TILE_AREA

        context.user_data['tile_area'] = area
        await update.message.reply_text(
            f"✅ Площадь: {area} м²\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 2 из 4**\n\n"
            "📏 Введите **ДЛИНУ плитки** в метрах:\n\n"
            "_Например: 0.3 (для плитки 30 см)_",
            parse_mode='Markdown'
        )
        return TILE_LENGTH
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return TILE_AREA


async def tile_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить длину плитки"""
    try:
        length = float(update.message.text.replace(',', '.'))
        if length <= 0 or length > 3:
            await update.message.reply_text("❌ Длина должна быть от 0 до 3 м")
            return TILE_LENGTH

        context.user_data['tile_length'] = length
        await update.message.reply_text(
            f"✅ Длина плитки: {length} м\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 3 из 4**\n\n"
            "📏 Введите **ШИРИНУ плитки** в метрах:\n\n"
            "_Например: 0.3_",
            parse_mode='Markdown'
        )
        return TILE_WIDTH
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return TILE_LENGTH


async def tile_width(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить ширину плитки"""
    try:
        width = float(update.message.text.replace(',', '.'))
        if width <= 0 or width > 3:
            await update.message.reply_text("❌ Ширина должна быть от 0 до 3 м")
            return TILE_WIDTH

        context.user_data['tile_width'] = width

        # Кнопки запаса
        keyboard = [
            [InlineKeyboardButton("5%", callback_data="tile_wastage_5"),
             InlineKeyboardButton("10%", callback_data="tile_wastage_10")],
            [InlineKeyboardButton("15%", callback_data="tile_wastage_15"),
             InlineKeyboardButton("20%", callback_data="tile_wastage_20")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Ширина плитки: {width} м\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 4 из 4**\n\n"
            "📦 Выберите **ЗАПАС** на подрезку:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return TILE_WASTAGE
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return TILE_WIDTH


async def tile_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать плитку"""
    query = update.callback_query
    await query.answer()

    wastage = float(query.data.replace("tile_wastage_", ""))

    area = context.user_data['tile_area']
    length = context.user_data['tile_length']
    width = context.user_data['tile_width']

    if CALCULATORS_AVAILABLE:
        result = calculate_tile(area, length, width, wastage)
        formatted_result = format_calculator_result("tile", result)

        await query.edit_message_text(
            f"{formatted_result}\n\n"
            f"📋 Параметры:\n"
            f"• Площадь: {area} м²\n"
            f"• Размер плитки: {length}×{width} м\n"
            f"• Запас: {wastage}%",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text("❌ Модуль калькуляторов недоступен.")

    context.user_data.clear()
    return ConversationHandler.END


def create_tile_calculator_handler():
    """Создать ConversationHandler для калькулятора плитки"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(tile_start, pattern="^calc_tile$")
        ],
        states={
            TILE_AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, tile_area)],
            TILE_LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, tile_length)],
            TILE_WIDTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, tile_width)],
            TILE_WASTAGE: [CallbackQueryHandler(tile_calculate, pattern="^tile_wastage_")],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="tile_calculator",
        persistent=False,
        per_chat=True,
        per_user=True
    )


# ========================================
# КАЛЬКУЛЯТОР КРАСКИ - ConversationHandler
# ========================================

async def paint_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора краски"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🎨 **КАЛЬКУЛЯТОР КРАСКИ**\n\n"
            "Посчитаю количество краски для покрытия поверхности.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 1 из 3**\n\n"
            "📐 Введите **ПЛОЩАДЬ** окрашивания в м²:\n\n"
            "_Например: 50_",
            parse_mode='Markdown'
        )
    return PAINT_AREA


async def paint_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить площадь"""
    try:
        area = float(update.message.text.replace(',', '.'))
        if area <= 0:
            await update.message.reply_text("❌ Площадь должна быть положительной")
            return PAINT_AREA

        context.user_data['paint_area'] = area
        await update.message.reply_text(
            f"✅ Площадь: {area} м²\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 2 из 3**\n\n"
            "📊 Введите **РАСХОД краски** в м²/литр:\n\n"
            "_Обычно 8-12 м²/л\n"
            "Смотрите на банке с краской\n"
            "Например: 10_",
            parse_mode='Markdown'
        )
        return PAINT_COVERAGE
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return PAINT_AREA


async def paint_coverage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить расход краски"""
    try:
        coverage = float(update.message.text.replace(',', '.'))
        if coverage <= 0:
            await update.message.reply_text("❌ Расход должен быть положительным")
            return PAINT_COVERAGE

        context.user_data['paint_coverage'] = coverage

        # Кнопки количества слоёв
        keyboard = [
            [InlineKeyboardButton("1 слой", callback_data="paint_coats_1"),
             InlineKeyboardButton("2 слоя", callback_data="paint_coats_2")],
            [InlineKeyboardButton("3 слоя", callback_data="paint_coats_3")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Расход: {coverage} м²/л\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 3 из 3**\n\n"
            "🖌️ Выберите **КОЛИЧЕСТВО СЛОЁВ**:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return PAINT_COATS
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return PAINT_COVERAGE


async def paint_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать краску"""
    query = update.callback_query
    await query.answer()

    coats = int(query.data.replace("paint_coats_", ""))

    area = context.user_data['paint_area']
    coverage = context.user_data['paint_coverage']

    if CALCULATORS_AVAILABLE:
        result = calculate_paint(area, coverage, coats)
        formatted_result = format_calculator_result("paint", result)

        await query.edit_message_text(
            f"{formatted_result}\n\n"
            f"📋 Параметры:\n"
            f"• Площадь: {area} м²\n"
            f"• Расход: {coverage} м²/л\n"
            f"• Количество слоёв: {coats}",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text("❌ Модуль калькуляторов недоступен.")

    context.user_data.clear()
    return ConversationHandler.END


def create_paint_calculator_handler():
    """Создать ConversationHandler для калькулятора краски"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(paint_start, pattern="^calc_paint$")
        ],
        states={
            PAINT_AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, paint_area)],
            PAINT_COVERAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, paint_coverage)],
            PAINT_COATS: [CallbackQueryHandler(paint_calculate, pattern="^paint_coats_")],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="paint_calculator",
        persistent=False,
        per_chat=True,
        per_user=True
    )


# ========================================
# КАЛЬКУЛЯТОР ПЛОЩАДИ СТЕН - ConversationHandler
# ========================================

async def wall_area_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора площади стен"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "📐 **КАЛЬКУЛЯТОР ПЛОЩАДИ СТЕН**\n\n"
            "Посчитаю площадь стен помещения.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 1 из 4**\n\n"
            "📏 Введите **ДЛИНУ помещения** в метрах:\n\n"
            "_Например: 5_",
            parse_mode='Markdown'
        )
    return WALL_LENGTH


async def wall_area_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить длину помещения"""
    try:
        length = float(update.message.text.replace(',', '.'))
        if length <= 0:
            await update.message.reply_text("❌ Длина должна быть положительной")
            return WALL_LENGTH

        context.user_data['wall_length'] = length
        await update.message.reply_text(
            f"✅ Длина: {length} м\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 2 из 4**\n\n"
            "📏 Введите **ШИРИНУ помещения** в метрах:\n\n"
            "_Например: 4_",
            parse_mode='Markdown'
        )
        return WALL_WIDTH
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return WALL_LENGTH


async def wall_area_width(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить ширину помещения"""
    try:
        width = float(update.message.text.replace(',', '.'))
        if width <= 0:
            await update.message.reply_text("❌ Ширина должна быть положительной")
            return WALL_WIDTH

        context.user_data['wall_width'] = width
        await update.message.reply_text(
            f"✅ Ширина: {width} м\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 3 из 4**\n\n"
            "📏 Введите **ВЫСОТУ помещения** в метрах:\n\n"
            "_Например: 2.7_",
            parse_mode='Markdown'
        )
        return WALL_HEIGHT
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return WALL_WIDTH


async def wall_area_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить высоту помещения"""
    try:
        height = float(update.message.text.replace(',', '.'))
        if height <= 0 or height > 10:
            await update.message.reply_text("❌ Высота должна быть от 0 до 10 м")
            return WALL_HEIGHT

        context.user_data['wall_height'] = height
        await update.message.reply_text(
            f"✅ Высота: {height} м\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 4 из 4**\n\n"
            "🚪 Введите **ПЛОЩАДЬ ПРОЁМОВ** (окна, двери) в м²:\n\n"
            "_Если нет проёмов, введите 0_",
            parse_mode='Markdown'
        )
        return WALL_OPENINGS
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return WALL_HEIGHT


async def wall_area_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать площадь стен"""
    try:
        openings = float(update.message.text.replace(',', '.'))
        if openings < 0:
            await update.message.reply_text("❌ Площадь не может быть отрицательной")
            return WALL_OPENINGS

        length = context.user_data['wall_length']
        width = context.user_data['wall_width']
        height = context.user_data['wall_height']

        if CALCULATORS_AVAILABLE:
            result = calculate_wall_area(length, width, height, openings)
            formatted_result = format_calculator_result("wall_area", result)

            await update.message.reply_text(
                f"{formatted_result}\n\n"
                f"📋 Параметры:\n"
                f"• Длина: {length} м\n"
                f"• Ширина: {width} м\n"
                f"• Высота: {height} м\n"
                f"• Площадь проёмов: {openings} м²",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Модуль калькуляторов недоступен.")

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return WALL_OPENINGS


def create_wall_area_calculator_handler():
    """Создать ConversationHandler для калькулятора площади стен"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(wall_area_start, pattern="^calc_wall_area$")
        ],
        states={
            WALL_LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, wall_area_length)],
            WALL_WIDTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, wall_area_width)],
            WALL_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, wall_area_height)],
            WALL_OPENINGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, wall_area_calculate)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="wall_area_calculator",
        persistent=False,
        per_chat=True,
        per_user=True
    )


    """Создать ConversationHandler для калькулятора площади стен"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(wall_area_start, pattern="^calc_wall_area$")
        ],
        states={
            WALL_LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, wall_area_length)],
            WALL_WIDTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, wall_area_width)],
            WALL_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, wall_area_height)],
            WALL_OPENINGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, wall_area_calculate)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="wall_area_calculator",
        persistent=False,
        per_chat=True,
        per_user=True
    )


# ========================================
# ЭКСПОРТ НОВЫХ ОБРАБОТЧИКОВ
# ========================================

__all__ = [
    'create_brick_calculator_handler',
    'create_tile_calculator_handler',
    'create_paint_calculator_handler',
    'create_wall_area_calculator_handler',
]


"""
Расширение интерактивных калькуляторов - часть 2 (10 калькуляторов)
Кровля, штукатурка, обои, ламинат, утепление, фундамент, лестница, гипсокартон, земляные работы, трудозатраты
"""

# Эти import и переменные уже есть в основном файле, они нужны только для справки
# from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# ========================================
# КАЛЬКУЛЯТОР КРОВЛИ - ConversationHandler
# ========================================

async def roof_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора кровли"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🏠 **КАЛЬКУЛЯТОР КРОВЛИ**\n\n"
            "Посчитаю площадь кровельного материала.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 1 из 4**\n\n"
            "📏 Введите **ДЛИНУ здания** в метрах:\n\n"
            "_Например: 10_",
            parse_mode='Markdown'
        )
    return ROOF_LENGTH


async def roof_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить длину"""
    try:
        length = float(update.message.text.replace(',', '.'))
        if length <= 0:
            await update.message.reply_text("❌ Длина должна быть положительной")
            return ROOF_LENGTH

        context.user_data['roof_length'] = length
        await update.message.reply_text(
            f"✅ Длина: {length} м\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 2 из 4**\n\n"
            "📏 Введите **ШИРИНУ здания** в метрах:\n\n"
            "_Например: 8_",
            parse_mode='Markdown'
        )
        return ROOF_WIDTH
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return ROOF_LENGTH


async def roof_width(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить ширину"""
    try:
        width = float(update.message.text.replace(',', '.'))
        if width <= 0:
            await update.message.reply_text("❌ Ширина должна быть положительной")
            return ROOF_WIDTH

        context.user_data['roof_width'] = width

        # Кнопки типа кровли
        keyboard = [
            [InlineKeyboardButton("Плоская", callback_data="roof_type_flat")],
            [InlineKeyboardButton("Двускатная", callback_data="roof_type_gable")],
            [InlineKeyboardButton("Четырёхскатная (вальмовая)", callback_data="roof_type_hip")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Ширина: {width} м\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 3 из 4**\n\n"
            "🏠 Выберите **ТИП КРОВЛИ**:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return ROOF_TYPE
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return ROOF_WIDTH


async def roof_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить тип кровли"""
    query = update.callback_query
    await query.answer()

    roof_type = query.data.replace("roof_type_", "")
    context.user_data['roof_type'] = roof_type

    type_names = {"flat": "Плоская", "gable": "Двускатная", "hip": "Четырёхскатная"}

    await query.edit_message_text(
        f"✅ Тип: {type_names.get(roof_type, roof_type)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**Шаг 4 из 4**\n\n"
        "📐 Введите **УГОЛ НАКЛОНА** ската в градусах:\n\n"
        "_Обычно 20-45°\n"
        "Для плоской кровли: 0-5°\n"
        "Например: 30_",
        parse_mode='Markdown'
    )
    return ROOF_SLOPE


async def roof_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать кровлю"""
    try:
        slope = float(update.message.text.replace(',', '.'))
        if slope < 0 or slope > 90:
            await update.message.reply_text("❌ Угол должен быть от 0 до 90 градусов")
            return ROOF_SLOPE

        length = context.user_data['roof_length']
        width = context.user_data['roof_width']
        roof_type = context.user_data['roof_type']

        if CALCULATORS_AVAILABLE:
            result = calculate_roof(length, width, roof_type, slope)
            formatted_result = format_calculator_result("roof", result)

            await update.message.reply_text(
                f"{formatted_result}\n\n"
                f"📋 Параметры:\n"
                f"• Длина: {length} м\n"
                f"• Ширина: {width} м\n"
                f"• Угол наклона: {slope}°",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Модуль калькуляторов недоступен.")

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return ROOF_SLOPE


def create_roof_calculator_handler():
    """Создать ConversationHandler для калькулятора кровли"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(roof_start, pattern="^calc_roof$")],
        states={
            ROOF_LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, roof_length)],
            ROOF_WIDTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, roof_width)],
            ROOF_TYPE: [CallbackQueryHandler(roof_type, pattern="^roof_type_")],
            ROOF_SLOPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, roof_calculate)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="roof_calculator",
        persistent=False,
        per_chat=True,
        per_user=True
    )


# ========================================
# КАЛЬКУЛЯТОР ШТУКАТУРКИ - ConversationHandler
# ========================================

async def plaster_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора штукатурки"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🏗️ **КАЛЬКУЛЯТОР ШТУКАТУРКИ**\n\n"
            "Посчитаю расход штукатурной смеси.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 1 из 3**\n\n"
            "📐 Введите **ПЛОЩАДЬ** оштукатуривания в м²:\n\n"
            "_Например: 50_",
            parse_mode='Markdown'
        )
    return PLASTER_AREA


async def plaster_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить площадь"""
    try:
        area = float(update.message.text.replace(',', '.'))
        if area <= 0:
            await update.message.reply_text("❌ Площадь должна быть положительной")
            return PLASTER_AREA

        context.user_data['plaster_area'] = area
        await update.message.reply_text(
            f"✅ Площадь: {area} м²\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 2 из 3**\n\n"
            "📏 Введите **ТОЛЩИНУ слоя** в мм:\n\n"
            "_Обычно 10-30 мм\n"
            "Например: 20_",
            parse_mode='Markdown'
        )
        return PLASTER_THICKNESS
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return PLASTER_AREA


async def plaster_thickness(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить толщину"""
    try:
        thickness = float(update.message.text.replace(',', '.'))
        if thickness <= 0 or thickness > 100:
            await update.message.reply_text("❌ Толщина должна быть от 0 до 100 мм")
            return PLASTER_THICKNESS

        context.user_data['plaster_thickness'] = thickness

        # Кнопки типа штукатурки
        keyboard = [
            [InlineKeyboardButton("Цементная", callback_data="plaster_type_cement")],
            [InlineKeyboardButton("Гипсовая", callback_data="plaster_type_gypsum")],
            [InlineKeyboardButton("Известковая", callback_data="plaster_type_lime")],
            [InlineKeyboardButton("Декоративная", callback_data="plaster_type_decorative")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Толщина: {thickness} мм\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 3 из 3**\n\n"
            "🏗️ Выберите **ТИП ШТУКАТУРКИ**:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return PLASTER_TYPE
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return PLASTER_THICKNESS


async def plaster_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать штукатурку"""
    query = update.callback_query
    await query.answer()

    plaster_type = query.data.replace("plaster_type_", "")

    area = context.user_data['plaster_area']
    thickness = context.user_data['plaster_thickness']

    if CALCULATORS_AVAILABLE:
        result = calculate_plaster(area, thickness, plaster_type)
        formatted_result = format_calculator_result("plaster", result)

        await query.edit_message_text(
            f"{formatted_result}\n\n"
            f"📋 Параметры:\n"
            f"• Площадь: {area} м²\n"
            f"• Толщина слоя: {thickness} мм",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text("❌ Модуль калькуляторов недоступен.")

    context.user_data.clear()
    return ConversationHandler.END


def create_plaster_calculator_handler():
    """Создать ConversationHandler для калькулятора штукатурки"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(plaster_start, pattern="^calc_plaster$")],
        states={
            PLASTER_AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, plaster_area)],
            PLASTER_THICKNESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, plaster_thickness)],
            PLASTER_TYPE: [CallbackQueryHandler(plaster_calculate, pattern="^plaster_type_")],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="plaster_calculator",
        persistent=False,
        per_chat=True,
        per_user=True
    )


# ========================================
# КАЛЬКУЛЯТОР ОБОЕВ - ConversationHandler
# ========================================

async def wallpaper_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора обоев"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "📜 **КАЛЬКУЛЯТОР ОБОЕВ**\n\n"
            "Посчитаю количество рулонов обоев.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 1 из 3**\n\n"
            "📐 Введите **ПЛОЩАДЬ** оклейки в м²:\n\n"
            "_Например: 40_",
            parse_mode='Markdown'
        )
    return WALLPAPER_AREA


async def wallpaper_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить площадь"""
    try:
        area = float(update.message.text.replace(',', '.'))
        if area <= 0:
            await update.message.reply_text("❌ Площадь должна быть положительной")
            return WALLPAPER_AREA

        context.user_data['wallpaper_area'] = area

        # Кнопки длины рулона
        keyboard = [
            [InlineKeyboardButton("10 м (стандарт)", callback_data="wallpaper_length_10")],
            [InlineKeyboardButton("15 м", callback_data="wallpaper_length_15")],
            [InlineKeyboardButton("25 м", callback_data="wallpaper_length_25")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Площадь: {area} м²\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 2 из 3**\n\n"
            "📏 Выберите **ДЛИНУ РУЛОНА**:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return WALLPAPER_ROLL_LENGTH
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return WALLPAPER_AREA


async def wallpaper_roll_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить длину рулона"""
    query = update.callback_query
    await query.answer()

    roll_length = float(query.data.replace("wallpaper_length_", ""))
    context.user_data['wallpaper_roll_length'] = roll_length

    # Кнопки ширины рулона
    keyboard = [
        [InlineKeyboardButton("0.53 м (стандарт)", callback_data="wallpaper_width_0.53")],
        [InlineKeyboardButton("0.7 м", callback_data="wallpaper_width_0.7")],
        [InlineKeyboardButton("1.06 м (метровые)", callback_data="wallpaper_width_1.06")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"✅ Длина рулона: {roll_length} м\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**Шаг 3 из 3**\n\n"
        "📏 Выберите **ШИРИНУ РУЛОНА**:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return WALLPAPER_ROLL_WIDTH


async def wallpaper_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать обои"""
    query = update.callback_query
    await query.answer()

    roll_width = float(query.data.replace("wallpaper_width_", ""))

    area = context.user_data['wallpaper_area']
    roll_length = context.user_data['wallpaper_roll_length']

    if CALCULATORS_AVAILABLE:
        result = calculate_wallpaper(area, roll_length, roll_width)
        formatted_result = format_calculator_result("wallpaper", result)

        await query.edit_message_text(
            f"{formatted_result}\n\n"
            f"📋 Параметры:\n"
            f"• Площадь: {area} м²\n"
            f"• Размер рулона: {roll_length}×{roll_width} м",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text("❌ Модуль калькуляторов недоступен.")

    context.user_data.clear()
    return ConversationHandler.END


def create_wallpaper_calculator_handler():
    """Создать ConversationHandler для калькулятора обоев"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(wallpaper_start, pattern="^calc_wallpaper$")],
        states={
            WALLPAPER_AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallpaper_area)],
            WALLPAPER_ROLL_LENGTH: [CallbackQueryHandler(wallpaper_roll_length, pattern="^wallpaper_length_")],
            WALLPAPER_ROLL_WIDTH: [CallbackQueryHandler(wallpaper_calculate, pattern="^wallpaper_width_")],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="wallpaper_calculator",
        persistent=False,
        per_chat=True,
        per_user=True
    )


# ========================================
# КАЛЬКУЛЯТОР ЛАМИНАТА - ConversationHandler
# ========================================

async def laminate_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора ламината"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🪵 **КАЛЬКУЛЯТОР ЛАМИНАТА**\n\n"
            "Посчитаю количество упаковок ламината.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 1 из 4**\n\n"
            "📐 Введите **ПЛОЩАДЬ** пола в м²:\n\n"
            "_Например: 30_",
            parse_mode='Markdown'
        )
    return LAMINATE_AREA


async def laminate_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить площадь"""
    try:
        area = float(update.message.text.replace(',', '.'))
        if area <= 0:
            await update.message.reply_text("❌ Площадь должна быть положительной")
            return LAMINATE_AREA

        context.user_data['laminate_area'] = area

        # Кнопки длины доски
        keyboard = [
            [InlineKeyboardButton("1.2 м (стандарт)", callback_data="laminate_length_1.2")],
            [InlineKeyboardButton("1.38 м", callback_data="laminate_length_1.38")],
            [InlineKeyboardButton("1.85 м", callback_data="laminate_length_1.85")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Площадь: {area} м²\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 2 из 4**\n\n"
            "📏 Выберите **ДЛИНУ ДОСКИ**:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return LAMINATE_LENGTH
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return LAMINATE_AREA


async def laminate_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить длину доски"""
    query = update.callback_query
    await query.answer()

    length = float(query.data.replace("laminate_length_", ""))
    context.user_data['laminate_length'] = length

    # Кнопки ширины доски
    keyboard = [
        [InlineKeyboardButton("0.19 м", callback_data="laminate_width_0.19")],
        [InlineKeyboardButton("0.2 м (стандарт)", callback_data="laminate_width_0.2")],
        [InlineKeyboardButton("0.33 м (широкая)", callback_data="laminate_width_0.33")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"✅ Длина доски: {length} м\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**Шаг 3 из 4**\n\n"
        "📏 Выберите **ШИРИНУ ДОСКИ**:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return LAMINATE_WIDTH


async def laminate_width(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить ширину доски"""
    query = update.callback_query
    await query.answer()

    width = float(query.data.replace("laminate_width_", ""))
    context.user_data['laminate_width'] = width

    # Кнопки запаса
    keyboard = [
        [InlineKeyboardButton("5%", callback_data="laminate_wastage_5"),
         InlineKeyboardButton("10%", callback_data="laminate_wastage_10")],
        [InlineKeyboardButton("15%", callback_data="laminate_wastage_15")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"✅ Ширина доски: {width} м\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**Шаг 4 из 4**\n\n"
        "📦 Выберите **ЗАПАС** на подрезку:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return LAMINATE_WASTAGE


async def laminate_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать ламинат"""
    query = update.callback_query
    await query.answer()

    wastage = float(query.data.replace("laminate_wastage_", ""))

    area = context.user_data['laminate_area']
    length = context.user_data['laminate_length']
    width = context.user_data['laminate_width']

    if CALCULATORS_AVAILABLE:
        result = calculate_laminate(area, length, width, wastage)
        formatted_result = format_calculator_result("laminate", result)

        await query.edit_message_text(
            f"{formatted_result}\n\n"
            f"📋 Параметры:\n"
            f"• Площадь: {area} м²\n"
            f"• Размер доски: {length}×{width} м\n"
            f"• Запас: {wastage}%",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text("❌ Модуль калькуляторов недоступен.")

    context.user_data.clear()
    return ConversationHandler.END


def create_laminate_calculator_handler():
    """Создать ConversationHandler для калькулятора ламината"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(laminate_start, pattern="^calc_laminate$")],
        states={
            LAMINATE_AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, laminate_area)],
            LAMINATE_LENGTH: [CallbackQueryHandler(laminate_length, pattern="^laminate_length_")],
            LAMINATE_WIDTH: [CallbackQueryHandler(laminate_width, pattern="^laminate_width_")],
            LAMINATE_WASTAGE: [CallbackQueryHandler(laminate_calculate, pattern="^laminate_wastage_")],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="laminate_calculator",
        persistent=False,
        per_chat=True,
        per_user=True
    )


# ========================================
# КАЛЬКУЛЯТОР УТЕПЛЕНИЯ - ConversationHandler
# ========================================

async def insulation_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора утепления"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🧊 **КАЛЬКУЛЯТОР УТЕПЛЕНИЯ**\n\n"
            "Посчитаю объём и стоимость утеплителя.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 1 из 3**\n\n"
            "📐 Введите **ПЛОЩАДЬ** утепления в м²:\n\n"
            "_Например: 80_",
            parse_mode='Markdown'
        )
    return INSULATION_AREA


async def insulation_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить площадь"""
    try:
        area = float(update.message.text.replace(',', '.'))
        if area <= 0:
            await update.message.reply_text("❌ Площадь должна быть положительной")
            return INSULATION_AREA

        context.user_data['insulation_area'] = area

        # Кнопки толщины
        keyboard = [
            [InlineKeyboardButton("50 мм", callback_data="insulation_thick_50"),
             InlineKeyboardButton("100 мм", callback_data="insulation_thick_100")],
            [InlineKeyboardButton("150 мм", callback_data="insulation_thick_150"),
             InlineKeyboardButton("200 мм", callback_data="insulation_thick_200")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Площадь: {area} м²\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 2 из 3**\n\n"
            "📏 Выберите **ТОЛЩИНУ** утеплителя:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return INSULATION_THICKNESS
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return INSULATION_AREA


async def insulation_thickness(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить толщину"""
    query = update.callback_query
    await query.answer()

    thickness = float(query.data.replace("insulation_thick_", ""))
    context.user_data['insulation_thickness'] = thickness

    # Кнопки типа утеплителя
    keyboard = [
        [InlineKeyboardButton("Минеральная вата", callback_data="insulation_type_mineral_wool")],
        [InlineKeyboardButton("Пенополистирол (ППС)", callback_data="insulation_type_polystyrene")],
        [InlineKeyboardButton("XPS (экструд. пенополистирол)", callback_data="insulation_type_eps")],
        [InlineKeyboardButton("ППУ (пенополиуретан)", callback_data="insulation_type_polyurethane")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"✅ Толщина: {thickness} мм\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**Шаг 3 из 3**\n\n"
        "🧊 Выберите **ТИП УТЕПЛИТЕЛЯ**:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return INSULATION_TYPE


async def insulation_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать утепление"""
    query = update.callback_query
    await query.answer()

    insulation_type = query.data.replace("insulation_type_", "")

    area = context.user_data['insulation_area']
    thickness = context.user_data['insulation_thickness']

    if CALCULATORS_AVAILABLE:
        result = calculate_insulation(area, thickness, insulation_type)
        formatted_result = format_calculator_result("insulation", result)

        await query.edit_message_text(
            f"{formatted_result}\n\n"
            f"📋 Параметры:\n"
            f"• Площадь: {area} м²\n"
            f"• Толщина: {thickness} мм",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text("❌ Модуль калькуляторов недоступен.")

    context.user_data.clear()
    return ConversationHandler.END


def create_insulation_calculator_handler():
    """Создать ConversationHandler для калькулятора утепления"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(insulation_start, pattern="^calc_insulation$")],
        states={
            INSULATION_AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, insulation_area)],
            INSULATION_THICKNESS: [CallbackQueryHandler(insulation_thickness, pattern="^insulation_thick_")],
            INSULATION_TYPE: [CallbackQueryHandler(insulation_calculate, pattern="^insulation_type_")],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="insulation_calculator",
        persistent=False,
        per_chat=True,
        per_user=True
    )


# ========================================
# ЭКСПОРТ ОБРАБОТЧИКОВ (часть 2)
# ========================================

__all__ = [
    'create_roof_calculator_handler',
    'create_plaster_calculator_handler',
    'create_wallpaper_calculator_handler',
    'create_laminate_calculator_handler',
    'create_insulation_calculator_handler',
]


"""
Расширение интерактивных калькуляторов - часть 3 (последние 5 калькуляторов)
Фундамент, лестница, гипсокартон, земляные работы, трудозатраты
"""

# ========================================
# КАЛЬКУЛЯТОР ФУНДАМЕНТА - ConversationHandler
# ========================================

async def foundation_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора фундамента"""
    query = update.callback_query
    if query:
        await query.answer()

        # Кнопки типа фундамента
        keyboard = [
            [InlineKeyboardButton("Ленточный", callback_data="foundation_type_strip")],
            [InlineKeyboardButton("Плитный (монолит)", callback_data="foundation_type_slab")],
            [InlineKeyboardButton("Столбчатый", callback_data="foundation_type_pile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "🏗️ **КАЛЬКУЛЯТОР ФУНДАМЕНТА**\n\n"
            "Посчитаю объём бетона для фундамента.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 1 из 5**\n\n"
            "🏗️ Выберите **ТИП ФУНДАМЕНТА**:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    return FOUNDATION_TYPE


async def foundation_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить тип фундамента"""
    query = update.callback_query
    await query.answer()

    foundation_type = query.data.replace("foundation_type_", "")
    context.user_data['foundation_type'] = foundation_type

    type_names = {"strip": "Ленточный", "slab": "Плитный", "pile": "Столбчатый"}

    await query.edit_message_text(
        f"✅ Тип: {type_names.get(foundation_type, foundation_type)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**Шаг 2 из 5**\n\n"
        "📏 Введите **ДЛИНУ** фундамента в метрах:\n\n"
        "_Для ленточного - периметр\n"
        "Для плитного - длина стороны\n"
        "Например: 10_",
        parse_mode='Markdown'
    )
    return FOUNDATION_LENGTH


async def foundation_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить длину"""
    try:
        length = float(update.message.text.replace(',', '.'))
        if length <= 0:
            await update.message.reply_text("❌ Длина должна быть положительной")
            return FOUNDATION_LENGTH

        context.user_data['foundation_length'] = length
        await update.message.reply_text(
            f"✅ Длина: {length} м\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 3 из 5**\n\n"
            "📏 Введите **ШИРИНУ** в метрах:\n\n"
            "_Для ленточного - ширина ленты (0.3-0.6)\n"
            "Для плитного - ширина плиты\n"
            "Например: 0.4_",
            parse_mode='Markdown'
        )
        return FOUNDATION_WIDTH
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return FOUNDATION_LENGTH


async def foundation_width(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить ширину"""
    try:
        width = float(update.message.text.replace(',', '.'))
        if width <= 0:
            await update.message.reply_text("❌ Ширина должна быть положительной")
            return FOUNDATION_WIDTH

        context.user_data['foundation_width'] = width
        await update.message.reply_text(
            f"✅ Ширина: {width} м\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 4 из 5**\n\n"
            "📏 Введите **ВЫСОТУ (ГЛУБИНУ)** в метрах:\n\n"
            "_Обычно 0.5-2 м\n"
            "Например: 1.2_",
            parse_mode='Markdown'
        )
        return FOUNDATION_HEIGHT
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return FOUNDATION_WIDTH


async def foundation_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить высоту"""
    try:
        height = float(update.message.text.replace(',', '.'))
        if height <= 0 or height > 10:
            await update.message.reply_text("❌ Высота должна быть от 0 до 10 м")
            return FOUNDATION_HEIGHT

        context.user_data['foundation_height'] = height
        await update.message.reply_text(
            f"✅ Высота: {height} м\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 5 из 5**\n\n"
            "📊 Введите **НЕСУЩУЮ СПОСОБНОСТЬ ГРУНТА** в кПа:\n\n"
            "_Типовые значения:\n"
            "• Песок: 200-300 кПа\n"
            "• Суглинок: 150-250 кПа\n"
            "• Глина: 100-200 кПа\n"
            "Например: 200_",
            parse_mode='Markdown'
        )
        return FOUNDATION_SOIL
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return FOUNDATION_HEIGHT


async def foundation_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать фундамент"""
    try:
        soil_bearing = float(update.message.text.replace(',', '.'))
        if soil_bearing <= 0:
            await update.message.reply_text("❌ Несущая способность должна быть положительной")
            return FOUNDATION_SOIL

        foundation_type = context.user_data['foundation_type']
        length = context.user_data['foundation_length']
        width = context.user_data['foundation_width']
        height = context.user_data['foundation_height']

        if CALCULATORS_AVAILABLE:
            result = calculate_foundation(foundation_type, length, width, height, soil_bearing)
            formatted_result = format_calculator_result("foundation", result)

            await update.message.reply_text(
                f"{formatted_result}\n\n"
                f"📋 Параметры:\n"
                f"• Длина: {length} м\n"
                f"• Ширина: {width} м\n"
                f"• Высота: {height} м\n"
                f"• Несущая способность: {soil_bearing} кПа",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Модуль калькуляторов недоступен.")

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return FOUNDATION_SOIL


def create_foundation_calculator_handler():
    """Создать ConversationHandler для калькулятора фундамента"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(foundation_start, pattern="^calc_foundation$")],
        states={
            FOUNDATION_TYPE: [CallbackQueryHandler(foundation_type, pattern="^foundation_type_")],
            FOUNDATION_LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, foundation_length)],
            FOUNDATION_WIDTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, foundation_width)],
            FOUNDATION_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, foundation_height)],
            FOUNDATION_SOIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, foundation_calculate)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="foundation_calculator",
        persistent=False,
        per_chat=True,
        per_user=True
    )


# ========================================
# КАЛЬКУЛЯТОР ЛЕСТНИЦЫ - ConversationHandler
# ========================================

async def stairs_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора лестницы"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🪜 **КАЛЬКУЛЯТОР ЛЕСТНИЦЫ**\n\n"
            "Рассчитаю параметры лестницы.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 1 из 3**\n\n"
            "📏 Введите **ВЫСОТУ между этажами** в метрах:\n\n"
            "_Обычно 2.5-3 м\n"
            "Например: 2.7_",
            parse_mode='Markdown'
        )
    return STAIRS_HEIGHT


async def stairs_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить высоту"""
    try:
        height = float(update.message.text.replace(',', '.'))
        if height <= 0 or height > 10:
            await update.message.reply_text("❌ Высота должна быть от 0 до 10 м")
            return STAIRS_HEIGHT

        context.user_data['stairs_height'] = height

        # Кнопки высоты ступени
        keyboard = [
            [InlineKeyboardButton("15 см", callback_data="stairs_step_h_0.15"),
             InlineKeyboardButton("16 см", callback_data="stairs_step_h_0.16")],
            [InlineKeyboardButton("17 см (стандарт)", callback_data="stairs_step_h_0.17"),
             InlineKeyboardButton("18 см", callback_data="stairs_step_h_0.18")],
            [InlineKeyboardButton("19 см", callback_data="stairs_step_h_0.19"),
             InlineKeyboardButton("20 см", callback_data="stairs_step_h_0.20")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Высота: {height} м\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 2 из 3**\n\n"
            "📐 Выберите **ВЫСОТУ СТУПЕНИ**:\n\n"
            "_Рекомендуется 15-18 см_",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return STAIRS_STEP_HEIGHT
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return STAIRS_HEIGHT


async def stairs_step_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить высоту ступени"""
    query = update.callback_query
    await query.answer()

    step_height = float(query.data.replace("stairs_step_h_", ""))
    context.user_data['stairs_step_height'] = step_height

    # Кнопки глубины ступени
    keyboard = [
        [InlineKeyboardButton("25 см", callback_data="stairs_step_d_0.25"),
         InlineKeyboardButton("27 см", callback_data="stairs_step_d_0.27")],
        [InlineKeyboardButton("28 см (стандарт)", callback_data="stairs_step_d_0.28"),
         InlineKeyboardButton("30 см", callback_data="stairs_step_d_0.30")],
        [InlineKeyboardButton("32 см", callback_data="stairs_step_d_0.32")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"✅ Высота ступени: {step_height} м\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**Шаг 3 из 3**\n\n"
        "📐 Выберите **ГЛУБИНУ СТУПЕНИ** (проступь):\n\n"
        "_Рекомендуется 25-32 см_",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return STAIRS_STEP_DEPTH


async def stairs_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать лестницу"""
    query = update.callback_query
    await query.answer()

    step_depth = float(query.data.replace("stairs_step_d_", ""))

    height = context.user_data['stairs_height']
    step_height = context.user_data['stairs_step_height']

    if CALCULATORS_AVAILABLE:
        result = calculate_stairs(height, step_height, step_depth)
        formatted_result = format_calculator_result("stairs", result)

        await query.edit_message_text(
            f"{formatted_result}\n\n"
            f"📋 Параметры:\n"
            f"• Высота между этажами: {height} м\n"
            f"• Высота ступени: {step_height} м\n"
            f"• Глубина ступени: {step_depth} м",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text("❌ Модуль калькуляторов недоступен.")

    context.user_data.clear()
    return ConversationHandler.END


def create_stairs_calculator_handler():
    """Создать ConversationHandler для калькулятора лестницы"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(stairs_start, pattern="^calc_stairs$")],
        states={
            STAIRS_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, stairs_height)],
            STAIRS_STEP_HEIGHT: [CallbackQueryHandler(stairs_step_height, pattern="^stairs_step_h_")],
            STAIRS_STEP_DEPTH: [CallbackQueryHandler(stairs_calculate, pattern="^stairs_step_d_")],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="stairs_calculator",
        persistent=False,
        per_chat=True,
        per_user=True
    )


# ========================================
# КАЛЬКУЛЯТОР ГИПСОКАРТОНА - ConversationHandler
# ========================================

async def drywall_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора гипсокартона"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "📋 **КАЛЬКУЛЯТОР ГИПСОКАРТОНА**\n\n"
            "Посчитаю количество листов ГКЛ.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 1 из 3**\n\n"
            "📐 Введите **ПЛОЩАДЬ** облицовки в м²:\n\n"
            "_Например: 40_",
            parse_mode='Markdown'
        )
    return DRYWALL_AREA


async def drywall_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить площадь"""
    try:
        area = float(update.message.text.replace(',', '.'))
        if area <= 0:
            await update.message.reply_text("❌ Площадь должна быть положительной")
            return DRYWALL_AREA

        context.user_data['drywall_area'] = area

        # Кнопки длины листа
        keyboard = [
            [InlineKeyboardButton("2.5 м (стандарт)", callback_data="drywall_length_2.5")],
            [InlineKeyboardButton("3 м", callback_data="drywall_length_3")],
            [InlineKeyboardButton("4 м", callback_data="drywall_length_4")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Площадь: {area} м²\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 2 из 3**\n\n"
            "📏 Выберите **ДЛИНУ ЛИСТА**:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return DRYWALL_SHEET_LENGTH
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return DRYWALL_AREA


async def drywall_sheet_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить длину листа"""
    query = update.callback_query
    await query.answer()

    sheet_length = float(query.data.replace("drywall_length_", ""))
    context.user_data['drywall_sheet_length'] = sheet_length

    # Кнопки ширины листа
    keyboard = [
        [InlineKeyboardButton("1.2 м (стандарт)", callback_data="drywall_width_1.2")],
        [InlineKeyboardButton("1.25 м", callback_data="drywall_width_1.25")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"✅ Длина листа: {sheet_length} м\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**Шаг 3 из 3**\n\n"
        "📏 Выберите **ШИРИНУ ЛИСТА**:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return DRYWALL_SHEET_WIDTH


async def drywall_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать гипсокартон"""
    query = update.callback_query
    await query.answer()

    sheet_width = float(query.data.replace("drywall_width_", ""))

    area = context.user_data['drywall_area']
    sheet_length = context.user_data['drywall_sheet_length']

    if CALCULATORS_AVAILABLE:
        result = calculate_drywall(area, sheet_length, sheet_width)
        formatted_result = format_calculator_result("drywall", result)

        await query.edit_message_text(
            f"{formatted_result}\n\n"
            f"📋 Параметры:\n"
            f"• Площадь: {area} м²\n"
            f"• Размер листа: {sheet_length}×{sheet_width} м",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text("❌ Модуль калькуляторов недоступен.")

    context.user_data.clear()
    return ConversationHandler.END


def create_drywall_calculator_handler():
    """Создать ConversationHandler для калькулятора гипсокартона"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(drywall_start, pattern="^calc_drywall$")],
        states={
            DRYWALL_AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, drywall_area)],
            DRYWALL_SHEET_LENGTH: [CallbackQueryHandler(drywall_sheet_length, pattern="^drywall_length_")],
            DRYWALL_SHEET_WIDTH: [CallbackQueryHandler(drywall_calculate, pattern="^drywall_width_")],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="drywall_calculator",
        persistent=False,
        per_chat=True,
        per_user=True
    )


# ========================================
# КАЛЬКУЛЯТОР ЗЕМЛЯНЫХ РАБОТ - ConversationHandler
# ========================================

async def earthwork_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора земляных работ"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "⛏️ **КАЛЬКУЛЯТОР ЗЕМЛЯНЫХ РАБОТ**\n\n"
            "Посчитаю объём грунта для выемки.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 1 из 4**\n\n"
            "📏 Введите **ДЛИНУ** котлована в метрах:\n\n"
            "_Например: 15_",
            parse_mode='Markdown'
        )
    return EARTHWORK_LENGTH


async def earthwork_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить длину"""
    try:
        length = float(update.message.text.replace(',', '.'))
        if length <= 0:
            await update.message.reply_text("❌ Длина должна быть положительной")
            return EARTHWORK_LENGTH

        context.user_data['earthwork_length'] = length
        await update.message.reply_text(
            f"✅ Длина: {length} м\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 2 из 4**\n\n"
            "📏 Введите **ШИРИНУ** котлована в метрах:\n\n"
            "_Например: 10_",
            parse_mode='Markdown'
        )
        return EARTHWORK_WIDTH
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return EARTHWORK_LENGTH


async def earthwork_width(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить ширину"""
    try:
        width = float(update.message.text.replace(',', '.'))
        if width <= 0:
            await update.message.reply_text("❌ Ширина должна быть положительной")
            return EARTHWORK_WIDTH

        context.user_data['earthwork_width'] = width
        await update.message.reply_text(
            f"✅ Ширина: {width} м\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 3 из 4**\n\n"
            "📏 Введите **ГЛУБИНУ** котлована в метрах:\n\n"
            "_Обычно 1-3 м\n"
            "Например: 2_",
            parse_mode='Markdown'
        )
        return EARTHWORK_DEPTH
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return EARTHWORK_WIDTH


async def earthwork_depth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить глубину"""
    try:
        depth = float(update.message.text.replace(',', '.'))
        if depth <= 0 or depth > 50:
            await update.message.reply_text("❌ Глубина должна быть от 0 до 50 м")
            return EARTHWORK_DEPTH

        context.user_data['earthwork_depth'] = depth

        # Кнопки типа грунта
        keyboard = [
            [InlineKeyboardButton("Песок", callback_data="earthwork_soil_sand")],
            [InlineKeyboardButton("Суглинок", callback_data="earthwork_soil_loam")],
            [InlineKeyboardButton("Глина", callback_data="earthwork_soil_clay")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Глубина: {depth} м\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 4 из 4**\n\n"
            "🏞️ Выберите **ТИП ГРУНТА**:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return EARTHWORK_SOIL_TYPE
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return EARTHWORK_DEPTH


async def earthwork_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать земляные работы"""
    query = update.callback_query
    await query.answer()

    soil_type = query.data.replace("earthwork_soil_", "")

    length = context.user_data['earthwork_length']
    width = context.user_data['earthwork_width']
    depth = context.user_data['earthwork_depth']

    if CALCULATORS_AVAILABLE:
        result = calculate_earthwork(length, width, depth, soil_type)
        formatted_result = format_calculator_result("earthwork", result)

        await query.edit_message_text(
            f"{formatted_result}\n\n"
            f"📋 Параметры:\n"
            f"• Длина: {length} м\n"
            f"• Ширина: {width} м\n"
            f"• Глубина: {depth} м",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text("❌ Модуль калькуляторов недоступен.")

    context.user_data.clear()
    return ConversationHandler.END


def create_earthwork_calculator_handler():
    """Создать ConversationHandler для калькулятора земляных работ"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(earthwork_start, pattern="^calc_earthwork$")],
        states={
            EARTHWORK_LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, earthwork_length)],
            EARTHWORK_WIDTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, earthwork_width)],
            EARTHWORK_DEPTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, earthwork_depth)],
            EARTHWORK_SOIL_TYPE: [CallbackQueryHandler(earthwork_calculate, pattern="^earthwork_soil_")],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="earthwork_calculator",
        persistent=False,
        per_chat=True,
        per_user=True
    )


# ========================================
# КАЛЬКУЛЯТОР ТРУДОЗАТРАТ - ConversationHandler
# ========================================

async def labor_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для калькулятора трудозатрат"""
    query = update.callback_query
    if query:
        await query.answer()

        # Кнопки типа работ
        keyboard = [
            [InlineKeyboardButton("Кирпичная кладка", callback_data="labor_task_brickwork")],
            [InlineKeyboardButton("Бетонирование", callback_data="labor_task_concrete")],
            [InlineKeyboardButton("Штукатурные работы", callback_data="labor_task_plaster")],
            [InlineKeyboardButton("Малярные работы", callback_data="labor_task_painting")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "👷 **КАЛЬКУЛЯТОР ТРУДОЗАТРАТ**\n\n"
            "Рассчитаю время выполнения работ.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 1 из 3**\n\n"
            "🛠️ Выберите **ТИП РАБОТ**:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    return LABOR_TASK_TYPE


async def labor_task_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить тип работ"""
    query = update.callback_query
    await query.answer()

    task_type = query.data.replace("labor_task_", "")
    context.user_data['labor_task_type'] = task_type

    task_names = {
        "brickwork": "Кирпичная кладка",
        "concrete": "Бетонирование",
        "plaster": "Штукатурные работы",
        "painting": "Малярные работы"
    }

    await query.edit_message_text(
        f"✅ Тип работ: {task_names.get(task_type, task_type)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**Шаг 2 из 3**\n\n"
        "📊 Введите **ОБЪЁМ РАБОТ**:\n\n"
        "_Для кладки - м³\n"
        "Для бетона - м³\n"
        "Для штукатурки - м²\n"
        "Для покраски - м²\n"
        "Например: 50_",
        parse_mode='Markdown'
    )
    return LABOR_QUANTITY


async def labor_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить объём работ"""
    try:
        quantity = float(update.message.text.replace(',', '.'))
        if quantity <= 0:
            await update.message.reply_text("❌ Объём должен быть положительным")
            return LABOR_QUANTITY

        context.user_data['labor_quantity'] = quantity
        await update.message.reply_text(
            f"✅ Объём работ: {quantity}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**Шаг 3 из 3**\n\n"
            "👷 Введите **КОЛИЧЕСТВО РАБОЧИХ**:\n\n"
            "_Например: 4_",
            parse_mode='Markdown'
        )
        return LABOR_WORKERS
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return LABOR_QUANTITY


async def labor_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитать трудозатраты"""
    try:
        workers = int(update.message.text.replace(',', '.'))
        if workers <= 0:
            await update.message.reply_text("❌ Количество рабочих должно быть положительным")
            return LABOR_WORKERS

        task_type = context.user_data['labor_task_type']
        quantity = context.user_data['labor_quantity']

        if CALCULATORS_AVAILABLE:
            result = calculate_labor(task_type, quantity, workers)
            formatted_result = format_calculator_result("labor", result)

            await update.message.reply_text(
                f"{formatted_result}\n\n"
                f"📋 Параметры:\n"
                f"• Объём работ: {quantity}\n"
                f"• Количество рабочих: {workers}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Модуль калькуляторов недоступен.")

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ Введите целое число")
        return LABOR_WORKERS


def create_labor_calculator_handler():
    """Создать ConversationHandler для калькулятора трудозатрат"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(labor_start, pattern="^calc_labor$")],
        states={
            LABOR_TASK_TYPE: [CallbackQueryHandler(labor_task_type, pattern="^labor_task_")],
            LABOR_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, labor_quantity)],
            LABOR_WORKERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, labor_calculate)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="labor_calculator",
        persistent=False,
        per_chat=True,
        per_user=True
    )


# ========================================
# ЭКСПОРТ ОБРАБОТЧИКОВ (часть 3 - последняя)
# ========================================

__all__ = [
    'create_foundation_calculator_handler',
    'create_stairs_calculator_handler',
    'create_drywall_calculator_handler',
    'create_earthwork_calculator_handler',
    'create_labor_calculator_handler',
]
