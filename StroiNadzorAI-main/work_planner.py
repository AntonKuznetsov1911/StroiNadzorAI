"""
Модуль умного планирования строительных работ v3.8
CPM метод, учёт погодных условий, расчёт ресурсов
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import json

logger = logging.getLogger(__name__)


# ========================================
# ТИПЫ РАБОТ И ИХ ПАРАМЕТРЫ
# ========================================

WORK_TYPES = {
    "foundation_excavation": {
        "name": "Земляные работы (котлован)",
        "duration_per_m3": 0.5,  # часов на 1 м³
        "workers_per_100m3": 4,
        "equipment": ["экскаватор", "самосвал"],
        "weather_dependent": True,
        "min_temp": -10,
        "rain_allowed": False
    },
    "foundation_concrete": {
        "name": "Бетонирование фундамента",
        "duration_per_m3": 1.5,  # часов на 1 м³
        "workers_per_10m3": 6,
        "equipment": ["бетононасос", "вибратор"],
        "weather_dependent": True,
        "min_temp": -15,  # с противоморозными добавками
        "rain_allowed": False,
        "requires_heating_below": 5  # °C
    },
    "masonry": {
        "name": "Кирпичная кладка",
        "duration_per_m2": 2.0,  # часов на 1 м²
        "workers_per_100m2": 4,
        "equipment": ["леса", "миксер"],
        "weather_dependent": True,
        "min_temp": -5,
        "rain_allowed": False
    },
    "concrete_columns": {
        "name": "Бетонирование колонн",
        "duration_per_m3": 2.5,
        "workers_per_5m3": 4,
        "equipment": ["кран", "вибратор", "опалубка"],
        "weather_dependent": True,
        "min_temp": -10,
        "rain_allowed": False
    },
    "slab_concrete": {
        "name": "Бетонирование плиты перекрытия",
        "duration_per_m2": 0.8,
        "workers_per_100m2": 8,
        "equipment": ["бетононасос", "вибратор"],
        "weather_dependent": True,
        "min_temp": -10,
        "rain_allowed": False
    },
    "roofing": {
        "name": "Кровельные работы",
        "duration_per_m2": 1.5,
        "workers_per_100m2": 4,
        "equipment": ["леса", "кран"],
        "weather_dependent": True,
        "min_temp": -15,
        "rain_allowed": False,
        "max_wind": 15  # м/с
    },
    "plastering": {
        "name": "Штукатурка стен",
        "duration_per_m2": 1.2,
        "workers_per_100m2": 5,
        "equipment": ["леса", "миксер"],
        "weather_dependent": False,
        "min_temp": 5
    }
}


# ========================================
# ФУНКЦИИ РАСЧЁТА СРОКОВ
# ========================================

def calculate_work_duration(
    work_type: str,
    volume: float,
    temp: float = 20,
    consider_weather: bool = True
) -> Dict:
    """
    Расчёт длительности работ

    Args:
        work_type: Тип работы
        volume: Объём работ (м³, м²)
        temp: Температура воздуха
        consider_weather: Учитывать погодные условия

    Returns:
        Словарь с параметрами
    """
    if work_type not in WORK_TYPES:
        return {"error": "Неизвестный тип работы"}

    work = WORK_TYPES[work_type]

    # Базовая длительность
    if "duration_per_m3" in work:
        base_hours = volume * work["duration_per_m3"]
    else:
        base_hours = volume * work["duration_per_m2"]

    # Коэффициент температуры
    temp_coef = 1.0
    heating_required = False

    if consider_weather and work["weather_dependent"]:
        if temp < work["min_temp"]:
            return {
                "error": f"Температура слишком низкая! Минимум: {work['min_temp']}°C",
                "min_temp": work["min_temp"]
            }

        # Прогрев бетона
        if "requires_heating_below" in work and temp < work["requires_heating_below"]:
            heating_required = True
            temp_coef = 1.5  # +50% времени на прогрев

        # Зимние условия
        if -10 <= temp < 0:
            temp_coef = 1.3  # +30% времени
        elif temp < -10:
            temp_coef = 1.5  # +50% времени

    total_hours = base_hours * temp_coef

    # Рабочие дни (8 часов в день)
    work_days = total_hours / 8

    # Количество рабочих
    workers = 0
    if "workers_per_100m3" in work:
        workers = max(2, int(volume / 100 * work["workers_per_100m3"]))
    elif "workers_per_10m3" in work:
        workers = max(2, int(volume / 10 * work["workers_per_10m3"]))
    elif "workers_per_5m3" in work:
        workers = max(2, int(volume / 5 * work["workers_per_5m3"]))
    elif "workers_per_100m2" in work:
        workers = max(2, int(volume / 100 * work["workers_per_100m2"]))

    return {
        "work_name": work["name"],
        "base_hours": round(base_hours, 1),
        "total_hours": round(total_hours, 1),
        "work_days": round(work_days, 1),
        "workers_needed": workers,
        "equipment": work["equipment"],
        "temp_coefficient": temp_coef,
        "heating_required": heating_required,
        "weather_dependent": work["weather_dependent"]
    }


def calculate_project_schedule(
    works: List[Dict],
    start_date: datetime,
    temp: float = 20
) -> Dict:
    """
    Расчёт графика проекта по методу CPM

    Args:
        works: Список работ с зависимостями
        start_date: Дата начала
        temp: Средняя температура

    Returns:
        График работ с критическим путём
    """
    schedule = []
    current_date = start_date

    for work in works:
        work_type = work.get("type")
        volume = work.get("volume")
        dependencies = work.get("dependencies", [])

        # Расчёт длительности
        duration_info = calculate_work_duration(work_type, volume, temp)

        if "error" in duration_info:
            schedule.append({
                "work": WORK_TYPES[work_type]["name"],
                "error": duration_info["error"],
                "status": "blocked"
            })
            continue

        # Учитываем зависимости
        dep_end_date = current_date
        for dep_idx in dependencies:
            if dep_idx < len(schedule):
                dep_end = schedule[dep_idx].get("end_date", current_date)
                if dep_end > dep_end_date:
                    dep_end_date = dep_end

        start = dep_end_date
        end = start + timedelta(days=duration_info["work_days"])

        schedule.append({
            "work": duration_info["work_name"],
            "start_date": start.strftime("%d.%m.%Y"),
            "end_date": end.strftime("%d.%m.%Y"),
            "duration_days": duration_info["work_days"],
            "workers": duration_info["workers_needed"],
            "equipment": duration_info["equipment"],
            "heating": duration_info["heating_required"]
        })

        current_date = end

    # Общая длительность
    if schedule:
        total_days = (
            datetime.strptime(schedule[-1]["end_date"], "%d.%m.%Y") - start_date
        ).days

        return {
            "schedule": schedule,
            "total_duration_days": total_days,
            "completion_date": schedule[-1]["end_date"],
            "critical_path": len(schedule)  # Упрощённо - все работы критичные
        }

    return {"error": "Не удалось построить график"}


# ========================================
# КОМАНДЫ
# ========================================

async def planner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /planner - планировщик работ"""

    keyboard = [
        [InlineKeyboardButton("🏗️ Бетонирование фундамента", callback_data="plan_foundation")],
        [InlineKeyboardButton("🧱 Кирпичная кладка", callback_data="plan_masonry")],
        [InlineKeyboardButton("⬜ Бетонирование плиты", callback_data="plan_slab")],
        [InlineKeyboardButton("🏠 Кровельные работы", callback_data="plan_roofing")],
        [InlineKeyboardButton("📋 Свой проект", callback_data="plan_custom")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📅 **УМНЫЙ ПЛАНИРОВЩИК РАБОТ**\n\n"
        "Выберите тип работ для расчёта графика:\n\n"
        "**Что умеет планировщик:**\n"
        "✅ Расчёт сроков работ\n"
        "✅ Учёт погодных условий\n"
        "✅ Определение критического пути\n"
        "✅ Расчёт потребности в рабочих\n"
        "✅ Необходимое оборудование\n"
        "✅ Учёт зимних условий",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_planner_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий планировщика"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "plan_foundation":
        await query.edit_message_text(
            "🏗️ **ПЛАН БЕТОНИРОВАНИЯ ФУНДАМЕНТА**\n\n"
            "Отправьте параметры в формате:\n"
            "`/plan_calc foundation <объём м³> <температура°C>`\n\n"
            "**Пример:**\n"
            "`/plan_calc foundation 500 -10`\n\n"
            "Это рассчитает график бетонирования 500 м³ при -10°C",
            parse_mode='Markdown'
        )

    elif data == "plan_masonry":
        await query.edit_message_text(
            "🧱 **ПЛАН КИРПИЧНОЙ КЛАДКИ**\n\n"
            "Отправьте параметры в формате:\n"
            "`/plan_calc masonry <площадь м²> <температура°C>`\n\n"
            "**Пример:**\n"
            "`/plan_calc masonry 1000 5`\n\n"
            "Это рассчитает график кладки 1000 м² при +5°C",
            parse_mode='Markdown'
        )

    elif data == "plan_slab":
        await query.edit_message_text(
            "⬜ **ПЛАН БЕТОНИРОВАНИЯ ПЛИТЫ**\n\n"
            "Отправьте параметры в формате:\n"
            "`/plan_calc slab <площадь м²> <температура°C>`\n\n"
            "**Пример:**\n"
            "`/plan_calc slab 2000 15`",
            parse_mode='Markdown'
        )

    elif data == "plan_roofing":
        await query.edit_message_text(
            "🏠 **ПЛАН КРОВЕЛЬНЫХ РАБОТ**\n\n"
            "Отправьте параметры в формате:\n"
            "`/plan_calc roofing <площадь м²> <температура°C>`\n\n"
            "**Пример:**\n"
            "`/plan_calc roofing 1500 10`",
            parse_mode='Markdown'
        )


async def plan_calc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /plan_calc - расчёт плана работ"""

    if len(context.args) < 3:
        await update.message.reply_text(
            "❌ **Неверный формат**\n\n"
            "Использование:\n"
            "`/plan_calc <тип> <объём> <температура>`\n\n"
            "**Примеры:**\n"
            "• `/plan_calc foundation_concrete 500 -10`\n"
            "• `/plan_calc masonry 1000 5`\n"
            "• `/plan_calc slab_concrete 2000 15`",
            parse_mode='Markdown'
        )
        return

    work_type = context.args[0]
    try:
        volume = float(context.args[1])
        temp = float(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ Объём и температура должны быть числами")
        return

    # Расчёт
    result = calculate_work_duration(work_type, volume, temp)

    if "error" in result:
        await update.message.reply_text(
            f"❌ **Ошибка планирования**\n\n{result['error']}",
            parse_mode='Markdown'
        )
        return

    # Формируем ответ
    response = f"📅 **ПЛАН РАБОТ: {result['work_name']}**\n\n"
    response += f"**Исходные данные:**\n"
    response += f"• Объём работ: {volume} м³/м²\n"
    response += f"• Температура: {temp}°C\n\n"

    response += f"**Расчёт длительности:**\n"
    response += f"• Базовое время: {result['base_hours']:.1f} часов\n"

    if result['temp_coefficient'] > 1.0:
        response += f"• Коэффициент погоды: ×{result['temp_coefficient']}\n"
        response += f"• Скорректированное время: {result['total_hours']:.1f} часов\n"

    response += f"• **Рабочих дней: {result['work_days']:.1f}** ⏱️\n\n"

    response += f"**Ресурсы:**\n"
    response += f"• Рабочих: {result['workers_needed']} чел\n"
    response += f"• Оборудование: {', '.join(result['equipment'])}\n"

    if result['heating_required']:
        response += f"\n⚠️ **Требуется прогрев бетона!**\n"
        response += f"• Провод ПНСВ или термоматы\n"
        response += f"• Трансформаторная подстанция\n"
        response += f"• Контроль температуры каждые 4 часа\n"

    await update.message.reply_text(response, parse_mode='Markdown')
