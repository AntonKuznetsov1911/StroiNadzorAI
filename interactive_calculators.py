"""
Интерактивные калькуляторы с пошаговым вводом параметров
Использует ConversationHandler для удобного взаимодействия
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

# Состояния для ConversationHandler
(LENGTH, WIDTH, HEIGHT, CONCRETE_CLASS, RESULT) = range(5)
(DIAMETER, SPACING_LENGTH, SPACING_WIDTH, LAYERS, REBAR_RESULT) = range(5, 10)

# ===========================================
# ИНТЕРАКТИВНЫЙ КАЛЬКУЛЯТОР БЕТОНА
# ===========================================

async def concrete_calc_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало расчета бетона"""
    await update.message.reply_text(
        "🧮 **Калькулятор бетона**\n\n"
        "Рассчитаем объем бетона и материалы.\n\n"
        "**Шаг 1 из 4:** Введите длину конструкции (м):\n"
        "Например: `10` или `12.5`",
        parse_mode='Markdown'
    )
    return LENGTH

async def concrete_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение длины"""
    try:
        length = float(update.message.text.replace(',', '.'))
        if length <= 0 or length > 1000:
            raise ValueError("Длина должна быть от 0.1 до 1000 м")

        context.user_data['concrete_length'] = length

        await update.message.reply_text(
            f"✅ Длина: **{length} м**\n\n"
            f"**Шаг 2 из 4:** Введите ширину (м):",
            parse_mode='Markdown'
        )
        return WIDTH
    except ValueError:
        await update.message.reply_text(
            "❌ Неправильный формат!\n\n"
            "Введите число (например: 10 или 12.5):"
        )
        return LENGTH

async def concrete_width(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение ширины"""
    try:
        width = float(update.message.text.replace(',', '.'))
        if width <= 0 or width > 1000:
            raise ValueError("Ширина должна быть от 0.1 до 1000 м")

        context.user_data['concrete_width'] = width

        await update.message.reply_text(
            f"✅ Ширина: **{width} м**\n\n"
            f"**Шаг 3 из 4:** Введите высоту/толщину (м):",
            parse_mode='Markdown'
        )
        return HEIGHT
    except ValueError:
        await update.message.reply_text(
            "❌ Неправильный формат!\n\n"
            "Введите число (например: 8 или 5.5):"
        )
        return WIDTH

async def concrete_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение высоты и выбор класса бетона"""
    try:
        height = float(update.message.text.replace(',', '.'))
        if height <= 0 or height > 100:
            raise ValueError("Высота должна быть от 0.01 до 100 м")

        context.user_data['concrete_height'] = height

        # Кнопки выбора класса бетона
        keyboard = [
            [
                InlineKeyboardButton("B15 (М200)", callback_data="concrete_B15"),
                InlineKeyboardButton("B20 (М250)", callback_data="concrete_B20")
            ],
            [
                InlineKeyboardButton("B22.5 (М300)", callback_data="concrete_B22.5"),
                InlineKeyboardButton("B25 (М350)", callback_data="concrete_B25")
            ],
            [
                InlineKeyboardButton("B30 (М400)", callback_data="concrete_B30"),
                InlineKeyboardButton("B35 (М450)", callback_data="concrete_B35")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Высота: **{height} м**\n\n"
            f"**Шаг 4 из 4:** Выберите класс бетона:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return CONCRETE_CLASS
    except ValueError:
        await update.message.reply_text(
            "❌ Неправильный формат!\n\n"
            "Введите число (например: 0.2 или 0.5):"
        )
        return HEIGHT

async def concrete_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор класса бетона и расчет"""
    query = update.callback_query
    await query.answer()

    concrete_class = query.data.replace('concrete_', '')
    context.user_data['concrete_class'] = concrete_class

    # Получаем сохраненные данные
    length = context.user_data['concrete_length']
    width = context.user_data['concrete_width']
    height = context.user_data['concrete_height']

    # Расчет объема бетона
    volume = length * width * height

    # Расчет материалов в зависимости от класса
    cement_ratios = {
        'B15': 250,  # кг цемента на 1 м³
        'B20': 280,
        'B22.5': 310,
        'B25': 350,
        'B30': 390,
        'B35': 420
    }

    cement_per_m3 = cement_ratios.get(concrete_class, 300)
    cement_total = volume * cement_per_m3
    cement_bags = cement_total / 50  # мешков по 50 кг

    # Расчет песка и щебня
    sand = volume * 0.5  # м³
    gravel = volume * 0.8  # м³
    water = volume * 0.17  # м³

    # Стоимость (примерная)
    price_per_m3 = {
        'B15': 3500,
        'B20': 3800,
        'B22.5': 4000,
        'B25': 4200,
        'B30': 4500,
        'B35': 4800
    }
    total_price = volume * price_per_m3.get(concrete_class, 4000)

    result_text = f"""
✅ **РЕЗУЛЬТАТ РАСЧЕТА БЕТОНА**

📐 **Размеры:**
• Длина: {length} м
• Ширина: {width} м
• Высота: {height} м

🏗️ **Объем бетона:** {volume:.2f} м³
🎯 **Класс бетона:** {concrete_class}

📦 **Материалы:**

**Цемент:**
• {cement_total:.0f} кг
• {cement_bags:.1f} мешков (по 50 кг)

**Песок:** {sand:.2f} м³ (~{sand * 1.6:.0f} кг)
**Щебень:** {gravel:.2f} м³ (~{gravel * 1.5:.0f} кг)
**Вода:** {water * 1000:.0f} литров

💰 **Примерная стоимость:**
• {total_price:,.0f} руб (с учетом доставки)
• {price_per_m3[concrete_class]:,.0f} руб/м³

📋 **Рекомендации:**
• Заказывайте бетон с запасом +5-10%
• Время застывания: 28 дней до 100% прочности
• Температура: оптимально +15..+25°C
• Защита от дождя и солнца обязательна

Сохранить расчет? /saved_calcs
Новый расчет? /concrete_calc
"""

    await query.edit_message_text(result_text, parse_mode='Markdown')

    # Сохранение расчета в историю
    if 'saved_calculations' not in context.user_data:
        context.user_data['saved_calculations'] = []

    calculation = {
        'type': 'concrete',
        'params': {
            'length': length,
            'width': width,
            'height': height,
            'class': concrete_class
        },
        'results': {
            'volume': volume,
            'cement_kg': cement_total,
            'cement_bags': cement_bags,
            'sand_m3': sand,
            'gravel_m3': gravel,
            'water_l': water * 1000,
            'price': total_price
        }
    }
    context.user_data['saved_calculations'].append(calculation)

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена расчета"""
    await update.message.reply_text(
        "❌ Расчет отменен.\n\n"
        "Для нового расчета используйте /concrete_calc"
    )
    return ConversationHandler.END

# ===========================================
# ИНТЕРАКТИВНЫЙ КАЛЬКУЛЯТОР АРМАТУРЫ
# ===========================================

async def rebar_calc_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало расчета арматуры"""
    await update.message.reply_text(
        "🔩 **Калькулятор арматуры**\n\n"
        "Рассчитаем количество арматуры для плиты/фундамента.\n\n"
        "**Шаг 1 из 5:** Введите диаметр арматуры (мм):\n"
        "Например: `12` или `14`",
        parse_mode='Markdown'
    )
    return DIAMETER

async def rebar_diameter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение диаметра арматуры"""
    try:
        diameter = int(update.message.text)
        if diameter < 6 or diameter > 40:
            raise ValueError("Диаметр должен быть от 6 до 40 мм")

        context.user_data['rebar_diameter'] = diameter

        await update.message.reply_text(
            f"✅ Диаметр арматуры: **{diameter} мм**\n\n"
            f"**Шаг 2 из 5:** Введите шаг арматуры вдоль (см):\n"
            f"Типовой шаг: 15-20 см",
            parse_mode='Markdown'
        )
        return SPACING_LENGTH
    except ValueError:
        await update.message.reply_text(
            "❌ Неправильный формат!\n\n"
            "Введите целое число (например: 12 или 14):"
        )
        return DIAMETER

async def rebar_spacing_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение шага вдоль"""
    try:
        spacing = float(update.message.text.replace(',', '.'))
        if spacing < 10 or spacing > 50:
            raise ValueError("Шаг должен быть от 10 до 50 см")

        context.user_data['rebar_spacing_length'] = spacing / 100  # в метры

        await update.message.reply_text(
            f"✅ Шаг вдоль: **{spacing} см**\n\n"
            f"**Шаг 3 из 5:** Введите шаг арматуры поперек (см):",
            parse_mode='Markdown'
        )
        return SPACING_WIDTH
    except ValueError:
        await update.message.reply_text(
            "❌ Неправильный формат!\n\n"
            "Введите число (например: 15 или 20):"
        )
        return SPACING_LENGTH

async def rebar_spacing_width(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение шага поперек"""
    try:
        spacing = float(update.message.text.replace(',', '.'))
        if spacing < 10 or spacing > 50:
            raise ValueError("Шаг должен быть от 10 до 50 см")

        context.user_data['rebar_spacing_width'] = spacing / 100  # в метры

        # Кнопки выбора количества слоев
        keyboard = [
            [
                InlineKeyboardButton("1 слой (верхний)", callback_data="rebar_layers_1"),
                InlineKeyboardButton("2 слоя (верх+низ)", callback_data="rebar_layers_2")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Шаг поперек: **{spacing} см**\n\n"
            f"**Шаг 4 из 5:** Количество слоев арматуры:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return LAYERS
    except ValueError:
        await update.message.reply_text(
            "❌ Неправильный формат!\n\n"
            "Введите число (например: 15 или 20):"
        )
        return SPACING_WIDTH

async def rebar_layers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор слоев и финальный ввод размеров"""
    query = update.callback_query
    await query.answer()

    layers = int(query.data.replace('rebar_layers_', ''))
    context.user_data['rebar_layers'] = layers

    await query.edit_message_text(
        f"✅ Количество слоев: **{layers}**\n\n"
        f"**Шаг 5 из 5:** Введите размеры плиты/фундамента:\n"
        f"Формат: `длина ширина` (в метрах)\n"
        f"Например: `10 8`",
        parse_mode='Markdown'
    )
    return REBAR_RESULT

async def rebar_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Расчет арматуры"""
    try:
        dimensions = update.message.text.split()
        length = float(dimensions[0].replace(',', '.'))
        width = float(dimensions[1].replace(',', '.'))

        if length <= 0 or width <= 0 or length > 100 or width > 100:
            raise ValueError("Размеры должны быть от 0.1 до 100 м")

        # Получаем сохраненные данные
        diameter = context.user_data['rebar_diameter']
        spacing_length = context.user_data['rebar_spacing_length']
        spacing_width = context.user_data['rebar_spacing_width']
        layers = context.user_data['rebar_layers']

        # Расчет количества стержней
        bars_length = int(width / spacing_length) + 1
        bars_width = int(length / spacing_width) + 1

        # Общая длина арматуры
        total_length_per_layer = (bars_length * length) + (bars_width * width)
        total_length = total_length_per_layer * layers

        # Вес арматуры (кг/м в зависимости от диаметра)
        weight_per_meter = {
            6: 0.222, 8: 0.395, 10: 0.617, 12: 0.888,
            14: 1.21, 16: 1.58, 18: 2.0, 20: 2.47,
            22: 2.98, 25: 3.85, 28: 4.83, 32: 6.31, 40: 9.87
        }
        weight_pm = weight_per_meter.get(diameter, 1.0)
        total_weight = total_length * weight_pm

        # Стоимость (примерная, 50 руб/кг)
        price_per_kg = 50
        total_price = total_weight * price_per_kg

        # Количество стержней по 11.7 м (стандартная длина)
        standard_length = 11.7
        bars_needed = int(total_length / standard_length) + 1

        result_text = f"""
✅ **РЕЗУЛЬТАТ РАСЧЕТА АРМАТУРЫ**

📐 **Параметры:**
• Размеры: {length} × {width} м
• Диаметр: ⌀{diameter} мм
• Шаг вдоль: {spacing_length*100:.0f} см
• Шаг поперек: {spacing_width*100:.0f} см
• Слои: {layers}

🔩 **Количество стержней:**
• Вдоль: {bars_length} шт. × {length} м
• Поперек: {bars_width} шт. × {width} м

📏 **Общая длина:** {total_length:.1f} м
⚖️ **Общий вес:** {total_weight:.0f} кг
📦 **Стержней 11.7м:** {bars_needed} шт.

💰 **Примерная стоимость:**
• {total_price:,.0f} руб
• {price_per_kg} руб/кг

📋 **Рекомендации:**
• Защитный слой бетона: {diameter * 2} мм
• Нахлест стержней: {diameter * 40} мм
• Вязальная проволока: {int(total_weight * 0.01)} кг
• Класс арматуры: А500С (для расчетов)

Сохранить расчет? /saved_calcs
Новый расчет? /rebar_calc
"""

        await update.message.reply_text(result_text, parse_mode='Markdown')

        return ConversationHandler.END

    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Неправильный формат!\n\n"
            "Введите два числа через пробел (например: 10 8):"
        )
        return REBAR_RESULT

# ===========================================
# СОЗДАНИЕ CONVERSATION HANDLERS
# ===========================================

def create_concrete_calculator_handler():
    """Создать ConversationHandler для калькулятора бетона"""
    return ConversationHandler(
        entry_points=[CommandHandler('concrete_calc', concrete_calc_start)],
        states={
            LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, concrete_length)],
            WIDTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, concrete_width)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, concrete_height)],
            CONCRETE_CLASS: [CallbackQueryHandler(concrete_class, pattern='^concrete_')],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

def create_rebar_calculator_handler():
    """Создать ConversationHandler для калькулятора арматуры"""
    return ConversationHandler(
        entry_points=[CommandHandler('rebar_calc', rebar_calc_start)],
        states={
            DIAMETER: [MessageHandler(filters.TEXT & ~filters.COMMAND, rebar_diameter)],
            SPACING_LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, rebar_spacing_length)],
            SPACING_WIDTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, rebar_spacing_width)],
            LAYERS: [CallbackQueryHandler(rebar_layers, pattern='^rebar_layers_')],
            REBAR_RESULT: [MessageHandler(filters.TEXT & ~filters.COMMAND, rebar_result)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
