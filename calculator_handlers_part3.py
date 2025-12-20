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
