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
