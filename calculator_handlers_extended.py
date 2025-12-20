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


# ========================================
# ЭКСПОРТ НОВЫХ ОБРАБОТЧИКОВ
# ========================================

__all__ = [
    'create_brick_calculator_handler',
    'create_tile_calculator_handler',
    'create_paint_calculator_handler',
    'create_wall_area_calculator_handler',
]
