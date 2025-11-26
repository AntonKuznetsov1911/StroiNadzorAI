"""
Строительные калькуляторы для СтройНадзорAI v3.0
"""

import math
from typing import Dict, Tuple

# ========================================
# 1. КАЛЬКУЛЯТОР БЕТОНА
# ========================================

def calculate_concrete(
    length: float,  # длина, м
    width: float,   # ширина, м
    height: float,  # высота/толщина, м
    concrete_class: str = "B25",  # класс бетона
    wastage: float = 5.0  # процент запаса
) -> Dict:
    """
    Расчёт объёма бетона и параметров

    Returns:
        dict с результатами расчёта
    """
    # Объём бетона
    volume = length * width * height  # м³

    # Объём с учётом запаса
    volume_with_wastage = volume * (1 + wastage / 100)

    # Прочность по классам
    strength_map = {
        "B7.5": 100,
        "B12.5": 150,
        "B15": 200,
        "B20": 250,
        "B22.5": 300,
        "B25": 350,
        "B30": 400,
        "B35": 450,
        "B40": 500
    }

    strength = strength_map.get(concrete_class, 350)

    # Рекомендации по осадке конуса
    cone_slump_recommendations = {
        "П1": "1-5 см (жёсткий, для фундаментов)",
        "П2": "5-10 см (пластичный, универсальный)",
        "П3": "10-15 см (литой, для колонн)",
        "П4": "15-20 см (текучий, для сложных форм)"
    }

    result = {
        "volume": round(volume, 2),
        "volume_with_wastage": round(volume_with_wastage, 2),
        "concrete_class": concrete_class,
        "strength": strength,  # кг/см²
        "wastage_percent": wastage,
        "cone_slump_recommendations": cone_slump_recommendations,
        "water_cement_ratio": "0.5-0.6 для B25",
        "cement_consumption": f"{volume_with_wastage * 350:.0f} кг (350 кг/м³)",
        "tests_required": math.ceil(volume_with_wastage / 100),  # 1 серия на 100 м³
        "cost_estimate_min": round(volume_with_wastage * 4000, 2),  # мин 4000 руб/м³
        "cost_estimate_max": round(volume_with_wastage * 6000, 2)   # макс 6000 руб/м³
    }

    return result


# ========================================
# 2. КАЛЬКУЛЯТОР АРМАТУРЫ
# ========================================

def calculate_reinforcement(
    length: float,  # длина элемента, м
    width: float,   # ширина элемента, м
    height: float,  # высота элемента, м
    bar_diameter: int = 12,  # диаметр стержня, мм
    spacing: int = 200,  # шаг стержней, мм
    element_type: str = "slab"  # тип элемента: slab, beam, column
) -> Dict:
    """
    Расчёт арматуры для ЖБ конструкций

    Returns:
        dict с результатами расчёта
    """
    # Погонные метры стержней
    if element_type == "slab":
        # Плита: сетка в 2 слоя (верхний и нижний)
        rows = int(width * 1000 / spacing) + 1
        bars_per_direction = rows * length
        total_meters = bars_per_direction * 2 * 2  # 2 направления * 2 слоя

    elif element_type == "beam":
        # Балка: продольная + хомуты
        longitudinal = length * 4  # 4 стержня продольных
        stirrups_count = int(length * 1000 / spacing)
        stirrups_length = 2 * (width + height) * stirrups_count / 1000
        total_meters = longitudinal + stirrups_length

    elif element_type == "column":
        # Колонна: продольная + хомуты
        longitudinal = height * 4  # 4 угловых стержня
        stirrups_count = int(height * 1000 / spacing)
        stirrups_length = 2 * (length + width) * stirrups_count / 1000
        total_meters = longitudinal + stirrups_length

    else:
        total_meters = 0

    # Вес арматуры
    # Масса 1м стержня = π * (d/2)² * ρ, где ρ = 7850 кг/м³ для стали
    weight_per_meter = math.pi * (bar_diameter / 2000) ** 2 * 7850  # кг/м
    total_weight = total_meters * weight_per_meter

    # Нормативы
    protective_layer = {
        "slab": f"{bar_diameter + 10} мм (мин {bar_diameter + 10} мм)",
        "beam": f"{bar_diameter + 15} мм (мин {bar_diameter + 15} мм)",
        "column": f"{bar_diameter + 20} мм (мин {bar_diameter + 20} мм)"
    }

    result = {
        "element_type": element_type,
        "bar_diameter": bar_diameter,  # мм
        "spacing": spacing,  # мм
        "total_meters": round(total_meters, 2),
        "weight_per_meter": round(weight_per_meter, 3),
        "total_weight": round(total_weight, 2),  # кг
        "protective_layer": protective_layer.get(element_type, "20-30 мм"),
        "reinforcement_ratio": f"{(total_weight / (length * width * height * 2500)) * 100:.2f}%",
        "cost_estimate": round(total_weight * 80, 2),  # ~80 руб/кг
        "recommendations": {
            "class": "A500C (горячекатаная)",
            "welding": "Допускается для A500C",
            "overlap": f"40 * {bar_diameter} = {40 * bar_diameter} мм",
            "anchorage": f"30 * {bar_diameter} = {30 * bar_diameter} мм"
        }
    }

    return result


# ========================================
# 3. КАЛЬКУЛЯТОР ОПАЛУБКИ
# ========================================

def calculate_formwork(
    area: float,  # площадь опалубки, м²
    reuse_cycles: int = 30,  # количество циклов использования
    concrete_time: int = 1,  # дней на бетонирование
    hardening_time: int = 7,  # дней на твердение
    stripping_time: int = 1   # дней на распалубку
) -> Dict:
    """
    Расчёт опалубки и оборачиваемости

    Returns:
        dict с результатами расчёта
    """
    # Цикл оборачиваемости
    cycle_days = concrete_time + hardening_time + stripping_time

    # Количество оборотов в месяц
    turnovers_per_month = 30 / cycle_days

    # Количество комплектов опалубки
    # Если нужно забетонировать N этажей за T дней
    # Комплектов = N / (30 дней / цикл)

    result = {
        "area": area,  # м²
        "cycle_days": cycle_days,
        "turnovers_per_month": round(turnovers_per_month, 2),
        "reuse_cycles": reuse_cycles,
        "cost_per_m2": 500,  # руб/м² (средняя стоимость фанерной опалубки)
        "cost_total": round(area * 500, 2),
        "cost_per_reuse": round(area * 500 / reuse_cycles, 2),
        "recommendations": {
            "plywood": "Фанера ФСФ 18-21 мм (30-40 оборотов)",
            "metal": "Металлическая (100-150 оборотов, дороже)",
            "release_agent": "Обязательна смазка перед каждым использованием",
            "cleaning": "Очистка после каждого цикла"
        }
    }

    return result


# ========================================
# 4. КАЛЬКУЛЯТОР ЭЛЕКТРОСНАБЖЕНИЯ
# ========================================

def calculate_electrical(
    crane_power: float = 60,  # кВт, башенный кран
    pump_power: float = 40,   # кВт, бетононасос
    welders: int = 5,         # количество сварочных постов
    heaters: int = 10,        # количество тепловых пушек
    trailers: int = 10,       # количество бытовок
    lighting_power: float = 10,  # кВт, освещение
    utilization_factor: float = 0.75,  # коэффициент использования
    power_factor: float = 0.9  # cos φ
) -> Dict:
    """
    Расчёт потребной мощности электроснабжения стройплощадки

    Returns:
        dict с результатами расчёта
    """
    # Мощность оборудования
    welder_power = welders * 7  # 7 кВт на пост
    heater_power = heaters * 5  # 5 кВт на пушку
    trailer_power = trailers * 3  # 3 кВт на бытовку

    # Суммарная установленная мощность
    total_installed = (
        crane_power +
        pump_power +
        welder_power +
        heater_power +
        trailer_power +
        lighting_power
    )

    # Расчётная мощность с коэффициентами
    calculated_power = (total_installed * utilization_factor) / power_factor

    # Рекомендуемая мощность (с запасом 20%)
    recommended_power = calculated_power * 1.2

    result = {
        "crane_power": crane_power,
        "pump_power": pump_power,
        "welders": welders,
        "welder_power": welder_power,
        "heaters": heaters,
        "heater_power": heater_power,
        "trailers": trailers,
        "trailer_power": trailer_power,
        "lighting_power": lighting_power,
        "total_installed": round(total_installed, 2),
        "utilization_factor": utilization_factor,
        "power_factor": power_factor,
        "calculated_power": round(calculated_power, 2),
        "recommended_power": round(recommended_power, 2),
        "transformer_capacity": f"{math.ceil(recommended_power / 100) * 100} кВА",
        "cable_recommendation": "СИП-3 или ВВГнг для временных сетей",
        "monthly_consumption": f"{recommended_power * 8 * 22:.0f} кВт·ч (8ч/день, 22 дня)",
        "monthly_cost": f"{recommended_power * 8 * 22 * 6:.0f} руб (≈6 руб/кВт·ч)"
    }

    return result


# ========================================
# 5. КАЛЬКУЛЯТОР ВОДОСНАБЖЕНИЯ
# ========================================

def calculate_water(
    workers: int = 50,  # количество рабочих
    drinking: float = 25,  # л/чел·смену питьевая
    shower: float = 40,    # л/чел·смену душевые
    mixer_water: float = 300,  # л/замес мойка бетономешалки
    mixers_per_day: int = 5,   # количество замесов
    fire_flow: float = 10      # л/с пожаротушение
) -> Dict:
    """
    Расчёт потребности в воде для стройплощадки

    Returns:
        dict с результатами расчёта
    """
    # Потребление воды
    drinking_total = workers * drinking
    shower_total = workers * shower
    mixer_total = mixer_water * mixers_per_day
    fire_total = fire_flow * 3600  # л/час (минимум 1 час)

    # Суммарное потребление в сутки
    daily_consumption = drinking_total + shower_total + mixer_total + fire_total

    # Месячное потребление
    monthly_consumption = daily_consumption * 22  # 22 рабочих дня

    result = {
        "workers": workers,
        "drinking_per_person": drinking,
        "drinking_total": drinking_total,
        "shower_per_person": shower,
        "shower_total": shower_total,
        "mixer_water": mixer_water,
        "mixer_total": mixer_total,
        "fire_flow": fire_flow,
        "fire_total": fire_total,
        "daily_consumption": round(daily_consumption / 1000, 2),  # м³
        "monthly_consumption": round(monthly_consumption / 1000, 2),  # м³
        "required_pressure": "2-3 атм для хозяйственных нужд",
        "pipe_diameter": "Ду 50-100 мм для временного водопровода",
        "storage_tank": f"{math.ceil(daily_consumption / 1000)} м³ резервуар",
        "recommendations": {
            "meter": "Обязателен счётчик воды",
            "heating": "Подогрев зимой (электро-ТЭНы)",
            "filtration": "Фильтр грубой очистки на входе"
        }
    }

    return result


# ========================================
# 6. КАЛЬКУЛЯТОР ЗИМНЕГО ПРОГРЕВА БЕТОНА
# ========================================

def calculate_winter_heating(
    volume: float,  # объём бетона, м³
    temperature: int = -15,  # температура воздуха, °C
    heating_method: str = "electrodes",  # метод: electrodes, cable, tents
    target_strength: float = 70  # целевая прочность, % от R28
) -> Dict:
    """
    Расчёт прогрева бетона в зимних условиях

    Returns:
        dict с результатами расчёта
    """
    # Энергозатраты на прогрев
    energy_map = {
        "electrodes": 100,  # кВт·ч/м³ (электроды)
        "cable": 35,        # кВт·ч/м³ (греющий кабель ПНСВ)
        "tents": 50         # кВт·ч/м³ (тепляки)
    }

    energy_per_m3 = energy_map.get(heating_method, 50)
    total_energy = volume * energy_per_m3

    # Время прогрева в зависимости от температуры
    heating_time_map = {
        -5: 3,
        -10: 7,
        -15: 10,
        -20: 14,
        -25: 18
    }

    # Найти ближайшую температуру
    temps = sorted(heating_time_map.keys())
    closest_temp = min(temps, key=lambda t: abs(t - temperature))
    heating_days = heating_time_map[closest_temp]

    # Стоимость прогрева
    electricity_cost = total_energy * 6  # ~6 руб/кВт·ч

    # Противоморозные добавки
    additives_map = {
        "nitrite": {
            "name": "Нитрит натрия",
            "dosage": "3-5% от массы цемента",
            "min_temp": -15,
            "warning": "⚠️ ТОКСИЧЕН! СИЗ обязательны"
        },
        "potash": {
            "name": "Поташ (K2CO3)",
            "dosage": "4-6% от массы цемента",
            "min_temp": -15,
            "warning": "Менее токсичен чем нитрит"
        },
        "formate": {
            "name": "Формиат натрия",
            "dosage": "2-4% от массы цемента",
            "min_temp": -20,
            "warning": "Современная добавка, безопаснее"
        }
    }

    result = {
        "volume": volume,
        "temperature": temperature,
        "heating_method": heating_method,
        "energy_per_m3": energy_per_m3,
        "total_energy": round(total_energy, 2),
        "heating_days": heating_days,
        "electricity_cost": round(electricity_cost, 2),
        "target_strength": target_strength,
        "additives": additives_map,
        "recommendations": {
            "cable_length": f"{volume * 30:.0f} м кабеля ПНСВ (30-40 м на 1 м³)" if heating_method == "cable" else "N/A",
            "voltage": "127В или 220В через трансформатор" if heating_method == "electrodes" else "N/A",
            "temperature_control": "Обязательно каждые 4 часа",
            "thermometer": "Электронный со щупом",
            "min_strength_before_freeze": "50% R28 минимум перед замерзанием"
        },
        "cost_multiplier": f"{1 + abs(temperature) / 100:.2f}x к летней стоимости СМР"
    }

    return result


# ========================================
# ФОРМАТИРОВАНИЕ РЕЗУЛЬТАТОВ
# ========================================

def format_calculator_result(calc_type: str, result: Dict) -> str:
    """
    Форматировать результаты калькулятора в текст для бота

    Args:
        calc_type: тип калькулятора
        result: результаты расчёта

    Returns:
        отформатированный текст
    """
    if calc_type == "concrete":
        return f"""🏗️ **РАСЧЁТ БЕТОНА**

📏 **Размеры:**
• Длина × Ширина × Высота: {result.get('volume', 0)} м³

📦 **Объём бетона:**
• Чистый объём: {result['volume']} м³
• С запасом ({result['wastage_percent']}%): {result['volume_with_wastage']} м³

💪 **Класс бетона:**
• {result['concrete_class']} (прочность {result['strength']} кг/см²)

🧪 **Параметры:**
• В/Ц отношение: {result['water_cement_ratio']}
• Расход цемента: {result['cement_consumption']}
• Испытания: {result['tests_required']} серий кубиков (1 серия на 100 м³)

📊 **Осадка конуса (удобоукладываемость):**
{chr(10).join([f"• {k}: {v}" for k, v in result['cone_slump_recommendations'].items()])}

💰 **Стоимость:**
• Минимум: {result['cost_estimate_min']:,.0f} руб
• Максимум: {result['cost_estimate_max']:,.0f} руб

📚 **Нормативы:** СП 63.13330.2018, ГОСТ 10180-2012"""

    elif calc_type == "reinforcement":
        return f"""🔧 **РАСЧЁТ АРМАТУРЫ**

🏗️ **Элемент:** {result['element_type']}

📏 **Параметры:**
• Диаметр стержней: ∅{result['bar_diameter']} мм
• Шаг стержней: {result['spacing']} мм

📦 **Количество:**
• Общая длина: {result['total_meters']} м
• Масса 1 м: {result['weight_per_meter']} кг
• Общий вес: {result['total_weight']} кг

🛡️ **Защитный слой:** {result['protective_layer']}

📊 **Процент армирования:** {result['reinforcement_ratio']}

💰 **Стоимость:** ≈{result['cost_estimate']:,.0f} руб

🔧 **Рекомендации:**
• Класс: {result['recommendations']['class']}
• Сварка: {result['recommendations']['welding']}
• Нахлёст: {result['recommendations']['overlap']}
• Анкеровка: {result['recommendations']['anchorage']}

📚 **Нормативы:** СП 63.13330.2018, ГОСТ 5781-82"""

    # TODO: добавить форматирование для остальных калькуляторов

    return "Результат: " + str(result)
