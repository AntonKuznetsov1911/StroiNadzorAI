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
        "mixers_per_day": mixers_per_day,
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

    elif calc_type == "water":
        return f"""💧 **РАСЧЁТ ВОДОСНАБЖЕНИЯ**

👷 **Персонал:** {result['workers']} рабочих

💦 **Потребление воды в сутки:**
• Питьевая: {result['drinking_total']} л ({result['drinking_per_person']} л/чел)
• Душевые: {result['shower_total']} л ({result['shower_per_person']} л/чел)
• Мойка бетономешалок: {result['mixer_total']} л ({result.get('mixers_per_day', 0)} замесов × {result['mixer_water']} л)
• Пожаротушение (резерв): {result['fire_total']} л ({result['fire_flow']} л/с × 1 час)

📊 **Суммарное потребление:**
• В сутки: {result['daily_consumption']} м³
• В месяц (22 раб. дня): {result['monthly_consumption']} м³

🔧 **Технические требования:**
• Давление: {result['required_pressure']}
• Диаметр трубы: {result['pipe_diameter']}
• Резервуар: {result['storage_tank']}

💡 **Рекомендации:**
• {result['recommendations']['meter']}
• {result['recommendations']['heating']}
• {result['recommendations']['filtration']}

📚 **Нормативы:** СНиП 2.04.02-84, СП 30.13330.2016"""

    elif calc_type == "formwork":
        return f"""📦 **РАСЧЁТ ОПАЛУБКИ**

📏 **Площадь:** {result['area']} м²

📦 **Количество материала:**
• Щиты опалубки: {result['panels_needed']} шт
• С запасом: {result['panels_with_reserve']} шт

🔄 **Оборачиваемость:** {result['reuse_cycles']} циклов

💰 **Стоимость:**
• Минимум: {result['cost_estimate_min']:,.0f} руб
• Максимум: {result['cost_estimate_max']:,.0f} руб

🔧 **Рекомендации:**
• {result['recommendations']['material']}
• {result['recommendations']['treatment']}
• {result['recommendations']['props']}

📚 **Нормативы:** СП 70.13330.2012"""

    elif calc_type == "electrical":
        return f"""⚡ **РАСЧЁТ ЭЛЕКТРОСНАБЖЕНИЯ**

🏗️ **Установленная мощность:** {result['installed_power']} кВт

📊 **Расчётная мощность:**
• С коэф. спроса (Кс={result['demand_factor']}): {result['calculated_power']} кВт

⚡ **Пиковый ток:** {result['peak_current']} А

🔌 **Ввод электроэнергии:**
• Сечение кабеля: {result['cable_section']}
• Автомат: {result['circuit_breaker']}

🔋 **Трансформатор:** {result['transformer_capacity']}

💡 **Дополнительно:**
• Резервный дизель-генератор: {result['backup_generator']}
• Освещение стройплощадки: {result['site_lighting']}

💰 **Месячные затраты:** ≈{result['monthly_cost']:,.0f} руб

📚 **Нормативы:** ПУЭ-7, СП 256.1325800.2016"""

    elif calc_type == "winter":
        return f"""❄️ **РАСЧЁТ ЗИМНЕГО ПРОГРЕВА**

🏗️ **Объём бетона:** {result['volume']} м³
🌡️ **Температура:** {result['temperature']}°C
🔥 **Метод прогрева:** {result['heating_method_name']}

⚡ **Энергозатраты:**
• На м³: {result['energy_per_m3']} кВт·ч
• Всего: {result['total_energy']} кВт·ч

⏱️ **Время прогрева:** {result['heating_days']} суток

💰 **Стоимость:**
• Электроэнергия: {result['electricity_cost']:,.0f} руб

🧪 **Противоморозные добавки:**
• {result['recommended_additive']['name']}
• Дозировка: {result['recommended_additive']['dosage']}
• Температура применения: {result['recommended_additive']['temp_range']}

⚠️ **Важно:**
• Целевая прочность: {result['target_strength']}% от R28
• Контроль температуры каждые 2-4 часа
• Запрещён прогрев при t < -25°C без добавок

📚 **Нормативы:** СП 70.13330.2012, ГОСТ 24211-2008"""

    elif calc_type == "brick":
        return f"""🧱 **РАСЧЁТ КИРПИЧА**

📏 **Параметры стены:**
• Площадь: {result['wall_area']} м²
• Без проёмов: {result['net_area']} м²
• Толщина: {result['thickness']} м

🧱 **Кирпич:**
• Тип: {result['brick_type']}
• На 1 м²: {result['bricks_per_m2']:.0f} шт
• Всего: {result['total_bricks']} шт
• С запасом: {result['total_bricks_with_reserve']} шт

🧪 **Раствор:**
• Объём: {result['mortar_volume']} м³
• Мешков (50 кг): {result['mortar_bags']} шт

💰 **Стоимость:** ≈{result['cost_estimate']:,.0f} руб

📚 **Нормативы:** СП 70.13330.2012"""

    elif calc_type == "tile":
        return f"""🔲 **РАСЧЁТ ПЛИТКИ**

📏 **Помещение:**
• Площадь: {result['room_area']} м²
• Размер плитки: {result['tile_size']}

🔲 **Плитка:**
• Без запаса: {result['tiles_needed']} шт
• С запасом ({result['wastage_percent']}%): {result['tiles_with_wastage']} шт

🧪 **Материалы:**
• Клей: {result['adhesive_kg']} кг ({result['adhesive_bags']} мешков)
• Затирка: {result['grout_kg']} кг ({result['grout_bags']} мешков)

💰 **Стоимость:** ≈{result['cost_estimate']:,.0f} руб"""

    elif calc_type == "paint":
        return f"""🎨 **РАСЧЁТ КРАСКИ**

📏 **Параметры:**
• Площадь: {result['area']} м²
• Тип краски: {result['paint_type']}
• Поверхность: {result['surface_type']}
• Слоёв: {result['layers']}

🎨 **Расход:**
• На 1 м²: {result['consumption_per_m2']} л
• Всего: {result['total_consumption']} л
• С запасом: {result['total_with_reserve']} л

📦 **Упаковка:**
• Банок 2.5 л: {result['cans_2_5l']} шт
• Банок 10 л: {result['cans_10l']} шт
• Грунтовка: {result['primer_liters']} л ({result['primer_cans']} банок)

💰 **Стоимость:** ≈{result['cost_estimate']:,.0f} руб"""

    elif calc_type == "wall_area":
        return f"""📐 **РАСЧЁТ ПЛОЩАДИ СТЕН**

📏 **Помещение:**
• Размеры: {result['room_dimensions']}
• Периметр: {result['perimeter']} м

🧱 **Стены:**
• Общая площадь: {result['total_wall_area']} м²
• Окна: {result['windows_count']} шт ({result['windows_area']} м²)
• Двери: {result['doors_count']} шт ({result['doors_area']} м²)
• Площадь без проёмов: {result['net_wall_area']} м²

🏠 **Потолок:**
• Площадь: {result['ceiling_area']} м²

📊 **Итого:**
• Стены + потолок: {result['total_area_walls_ceiling']} м²"""

    elif calc_type == "roof":
        return f"""🏠 **РАСЧЁТ КРОВЛИ**

📏 **Параметры:**
• Основание: {result['base_area']} м²
• Тип кровли: {result['roof_type']}
• Угол наклона: {result['slope']}°

🏠 **Площадь:**
• Чистая: {result['roof_area']} м²
• Свесы: {result['roof_area_with_overhang']} м²

🔧 **Материалы:**
• Листов металлочерепицы: {result['metal_sheets_needed']} шт
• Утеплитель: {result['insulation_volume']} м³
• Пароизоляция: {result['vapor_barrier_area']} м²

💰 **Стоимость:** ≈{result['cost_estimate']:,.0f} руб"""

    elif calc_type == "plaster":
        return f"""🧱 **РАСЧЁТ ШТУКАТУРКИ**

📏 **Параметры:**
• Площадь: {result['area']} м²
• Толщина: {result['thickness_mm']} мм
• Тип: {result['plaster_type']}

🧱 **Расход:**
• На 1 м²: {result['consumption_per_m2']} кг
• Всего: {result['total_consumption']} кг
• С запасом: {result['total_with_reserve']} кг

📦 **Упаковка:**
• Мешков 25 кг: {result['bags_25kg']} шт
• Мешков 30 кг: {result['bags_30kg']} шт

💰 **Стоимость:** ≈{result['cost_estimate']:,.0f} руб"""

    elif calc_type == "wallpaper":
        return f"""🖼️ **РАСЧЁТ ОБОЕВ**

📏 **Параметры:**
• Площадь стен: {result['wall_area']} м²
• Размер рулона: {result['roll_size']}
• Раппорт: {result['pattern_repeat']} м

🖼️ **Обои:**
• Без запаса: {result['rolls_needed']} рулонов
• С запасом ({result['wastage_percent']}%): {result['rolls_with_wastage']} рулонов

🧪 **Клей:**
• Всего: {result['adhesive_kg']} кг ({result['adhesive_packs']} пачек)

💰 **Стоимость:** ≈{result['cost_estimate']:,.0f} руб"""

    elif calc_type == "laminate":
        return f"""🪵 **РАСЧЁТ ЛАМИНАТА**

📏 **Помещение:**
• Площадь: {result['room_area']} м²
• Размер доски: {result['plank_size']}

🪵 **Ламинат:**
• Без запаса: {result['planks_needed']} досок
• С запасом ({result['wastage_percent']}%): {result['planks_with_wastage']} досок
• Упаковок: {result['packs_needed']} шт

🔧 **Дополнительно:**
• Подложка: {result['underlay_area']} м² ({result['underlay_rolls']} рулонов)
• Плинтус: {result['skirting_length']} м

💰 **Стоимость:** ≈{result['cost_estimate']:,.0f} руб"""

    elif calc_type == "insulation":
        return f"""🧊 **РАСЧЁТ УТЕПЛИТЕЛЯ**

📏 **Параметры:**
• Площадь: {result['area']} м²
• Толщина: {result['thickness_mm']} мм
• Тип: {result['insulation_type']}

🧊 **Утеплитель:**
• Объём: {result['volume']} м³
• Упаковок: {result['packs_needed']} шт

🔧 **Дополнительно:**
• Пароизоляция: {result['vapor_barrier_area']} м²
• Дюбели: {result['dowels_total']} шт

💰 **Стоимость:** ≈{result['cost_estimate']:,.0f} руб"""

    elif calc_type == "foundation":
        return f"""⚓ **РАСЧЁТ ФУНДАМЕНТА**

📏 **Параметры:**
• Размеры: {result['dimensions']}
• Тип: {result['foundation_type']}

🏗️ **Материалы:**
• Объём бетона: {result['volume']} м³
• Площадь подошвы: {result['base_area']} м²
• Арматура: {result['rebar_kg']} кг ({result['rebar_tons']} т)
• Опалубка: {result['formwork_area']} м²

💰 **Стоимость:** ≈{result['cost_estimate']:,.0f} руб"""

    elif calc_type == "stairs":
        return f"""🪜 **РАСЧЁТ ЛЕСТНИЦЫ**

📏 **Параметры:**
• Высота этажа: {result['floor_height']} м
• Ширина проступи: {result['step_width']} м
• Высота подступенка: {result['actual_step_height']} м

🪜 **Лестница:**
• Количество ступеней: {result['steps_count']} шт
• Длина косоура: {result['stringer_length']} м
• Площадь ступеней: {result['steps_area']} м²

🏗️ **Материалы:**
• Бетон: {result['concrete_volume']} м³
• Арматура: {result['rebar_kg']} кг

💰 **Стоимость:** ≈{result['cost_estimate']:,.0f} руб"""

    elif calc_type == "drywall":
        return f"""📐 **РАСЧЁТ ГИПСОКАРТОНА**

📏 **Помещение:**
• Размеры: {result['room_dimensions']}
• Площадь стен: {result['walls_area']} м²
• Площадь потолка: {result['ceiling_area']} м²
• Всего: {result['total_area']} м²

📐 **ГКЛ:**
• Листов: {result['sheets_needed']} шт
• С запасом: {result['sheets_with_reserve']} шт

🔧 **Профили:**
• ПП (потолочные): {result['pp_length']} м
• ПН (направляющие): {result['pn_length']} м
• ПС (стоечные): {result['ps_length']} м

🪛 **Крепёж:**
• Саморезы: {result['screws_total']} шт
• Шпаклёвка: {result['putty_kg']} кг ({result['putty_bags']} мешков)

💰 **Стоимость:** ≈{result['cost_estimate']:,.0f} руб"""

    elif calc_type == "earthwork":
        return f"""🚜 **РАСЧЁТ ЗЕМЛЯНЫХ РАБОТ**

📏 **Котлован:**
• Размеры: {result['dimensions']}
• Объём: {result['volume']} м³
• Тип грунта: {result['soil_type']}

🚜 **Работы:**
• Объём с разрыхлением: {result['loose_volume']} м³
• Время работы: {result['hours_needed']} ч ({result['days_needed']} дней)
• Самосвалов: {result['trucks_needed']} шт

💰 **Стоимость:**
• Работы: {result['work_cost']:,.0f} руб
• С накладными: {result['cost_estimate']:,.0f} руб"""

    elif calc_type == "labor":
        return f"""👷 **РАСЧЁТ ТРУДОЗАТРАТ**

📊 **Работы:**
• Тип: {result['work_type']}
• Объём: {result['volume']} {result['work_unit']}
• Норма: {result['norm_per_unit']} чел·час/{result['work_unit']}

👷 **Трудозатраты:**
• В часах: {result['labor_hours']} чел·час
• В днях: {result['labor_days']} чел·дней
• Рабочих (за {result['deadline_days']} дней): {result['workers_needed']} чел

💰 **Стоимость:**
• Всего: {result['total_cost']:,.0f} руб
• На единицу: {result['cost_per_unit']} руб/{result['work_unit']}"""

    # Fallback для неизвестных типов
    return "Результат: " + str(result)


# ========================================
# 7. УНИВЕРСАЛЬНЫЙ МАТЕМАТИЧЕСКИЙ КАЛЬКУЛЯТОР
# ========================================

def calculate_math_expression(expression: str) -> Dict:
    """
    Вычислить математическое выражение
    
    Args:
        expression: строка с математическим выражением
        
    Returns:
        dict с результатом вычисления
    """
    import re
    
    # Безопасная обработка выражения
    try:
        # Заменяем запятые на точки
        expression = expression.replace(',', '.')
        
        # Удаляем все символы кроме цифр, операторов, скобок и точки
        # Разрешаем: +, -, *, /, ^, **, (, ), ., числа, пробелы
        safe_chars = r'[0-9+\-*/.()^ \s]'
        cleaned = ''.join(re.findall(safe_chars, expression))
        
        # Заменяем ^ на ** для возведения в степень
        cleaned = cleaned.replace('^', '**')
        
        # Проверяем на опасные функции (eval может выполнить любой код)
        dangerous = ['import', 'exec', 'eval', '__', 'open', 'file']
        if any(d in expression.lower() for d in dangerous):
            return {
                "success": False,
                "error": "Недопустимые символы в выражении",
                "expression": expression
            }
        
        # Вычисляем выражение
        result = eval(cleaned)
        
        # Форматируем результат
        if isinstance(result, float):
            # Округляем до 10 знаков после запятой
            if abs(result) < 1e-10:
                result = 0.0
            else:
                result = round(result, 10)
        
        return {
            "success": True,
            "expression": expression,
            "result": result,
            "formatted": f"{result:,.10f}".rstrip('0').rstrip('.') if isinstance(result, float) else str(result)
        }
        
    except ZeroDivisionError:
        return {
            "success": False,
            "error": "Деление на ноль",
            "expression": expression
        }
    except SyntaxError as e:
        return {
            "success": False,
            "error": f"Синтаксическая ошибка: {str(e)}",
            "expression": expression
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Ошибка вычисления: {str(e)}",
            "expression": expression
        }


def format_math_result(result: Dict) -> str:
    """
    Форматировать результат математического калькулятора
    
    Args:
        result: результат из calculate_math_expression
        
    Returns:
        отформатированный текст
    """
    if result.get("success"):
        return f"""🧮 **МАТЕМАТИЧЕСКИЙ КАЛЬКУЛЯТОР**

📝 **Выражение:**
`{result['expression']}`

✅ **Результат:**
`{result['formatted']}`

💡 **Подсказка:** Используйте кнопки для ввода или введите выражение вручную"""
    else:
        return f"""🧮 **МАТЕМАТИЧЕСКИЙ КАЛЬКУЛЯТОР**

❌ **Ошибка:**
{result.get('error', 'Неизвестная ошибка')}

📝 **Выражение:**
`{result.get('expression', '')}`

💡 **Попробуйте ещё раз**"""


# ========================================
# 8. КАЛЬКУЛЯТОР КИРПИЧА/БЛОКОВ
# ========================================

def calculate_brick(
    length: float,  # длина стены, м
    height: float,   # высота стены, м
    thickness: float = 0.25,  # толщина стены, м (0.12, 0.25, 0.38, 0.51)
    brick_type: str = "single",  # single, double, one_and_half
    openings_area: float = 0,  # площадь проёмов, м²
    mortar_thickness: float = 0.01  # толщина шва, м
) -> Dict:
    """
    Расчёт количества кирпича для кладки
    
    Returns:
        dict с результатами расчёта
    """
    # Размеры кирпича (стандарт): 250×120×65 мм
    brick_sizes = {
        "single": {"length": 0.25, "width": 0.12, "height": 0.065},  # одинарный
        "one_and_half": {"length": 0.25, "width": 0.12, "height": 0.088},  # полуторный
        "double": {"length": 0.25, "width": 0.12, "height": 0.138}  # двойной
    }
    
    brick = brick_sizes.get(brick_type, brick_sizes["single"])
    
    # Площадь стены
    wall_area = length * height
    # Площадь без проёмов
    net_area = wall_area - openings_area
    
    # Количество кирпичей на 1 м² (с учётом швов)
    # Для кладки в 1 кирпич (0.25 м)
    if thickness == 0.12:  # полкирпича
        bricks_per_m2 = 1 / (brick["length"] * brick["height"])
    elif thickness == 0.25:  # 1 кирпич
        bricks_per_m2 = 1 / (brick["length"] * brick["height"]) * 2
    elif thickness == 0.38:  # 1.5 кирпича
        bricks_per_m2 = 1 / (brick["length"] * brick["height"]) * 3
    elif thickness == 0.51:  # 2 кирпича
        bricks_per_m2 = 1 / (brick["length"] * brick["height"]) * 4
    else:
        bricks_per_m2 = 1 / (brick["length"] * brick["height"]) * (thickness / 0.12)
    
    # С учётом швов (примерно -5%)
    bricks_per_m2 = bricks_per_m2 * 0.95
    
    # Общее количество кирпичей
    total_bricks = math.ceil(net_area * bricks_per_m2)
    # Запас 5-10%
    total_bricks_with_reserve = math.ceil(total_bricks * 1.08)
    
    # Расход раствора (примерно 0.25 м³ на 1 м² стены)
    mortar_per_m2 = 0.25 * (thickness / 0.25)
    mortar_volume = net_area * mortar_per_m2
    
    result = {
        "wall_area": round(wall_area, 2),
        "openings_area": openings_area,
        "net_area": round(net_area, 2),
        "thickness": thickness,
        "brick_type": brick_type,
        "bricks_per_m2": round(bricks_per_m2, 0),
        "total_bricks": total_bricks,
        "total_bricks_with_reserve": total_bricks_with_reserve,
        "mortar_volume": round(mortar_volume, 2),
        "mortar_bags": math.ceil(mortar_volume * 1.3),  # 1 м³ = 1.3 мешка по 50 кг
        "cost_estimate": round(total_bricks_with_reserve * 15, 2),  # ~15 руб/кирпич
        "recommendations": {
            "brick_types": {
                "single": "Одинарный (250×120×65) - для внутренних стен",
                "one_and_half": "Полуторный (250×120×88) - универсальный",
                "double": "Двойной (250×120×138) - быстрее кладка"
            },
            "mortar": "Цементно-песчаный раствор М100-М150",
            "wastage": "Запас 8% на бой и подрезку"
        }
    }
    
    return result


# ========================================
# 9. КАЛЬКУЛЯТОР ПЛИТКИ
# ========================================

def calculate_tile(
    length: float,  # длина помещения, м
    width: float,   # ширина помещения, м
    tile_length: float = 0.3,  # длина плитки, м
    tile_width: float = 0.3,   # ширина плитки, м
    wastage: float = 10.0,  # процент запаса на подрезку
    grout_width: float = 0.002  # ширина шва, м
) -> Dict:
    """
    Расчёт количества плитки
    
    Returns:
        dict с результатами расчёта
    """
    # Площадь помещения
    room_area = length * width
    
    # Площадь одной плитки
    tile_area = tile_length * tile_width
    
    # Количество плиток без запаса
    tiles_needed = math.ceil(room_area / tile_area)
    
    # С запасом на подрезку
    tiles_with_wastage = math.ceil(tiles_needed * (1 + wastage / 100))
    
    # Расход клея (примерно 4-6 кг/м²)
    adhesive_per_m2 = 5  # кг/м²
    adhesive_total = math.ceil(room_area * adhesive_per_m2)
    
    # Расход затирки (примерно 0.5-1 кг/м²)
    grout_per_m2 = 0.75  # кг/м²
    grout_total = round(room_area * grout_per_m2, 1)
    
    # Периметр для плинтуса (если нужен)
    perimeter = 2 * (length + width)
    
    result = {
        "room_area": round(room_area, 2),
        "tile_size": f"{tile_length*1000:.0f}×{tile_width*1000:.0f} мм",
        "tile_area": round(tile_area, 3),
        "tiles_needed": tiles_needed,
        "tiles_with_wastage": tiles_with_wastage,
        "wastage_percent": wastage,
        "adhesive_kg": adhesive_total,
        "adhesive_bags": math.ceil(adhesive_total / 25),  # мешки по 25 кг
        "grout_kg": grout_total,
        "grout_bags": math.ceil(grout_total / 2.5),  # мешки по 2.5 кг
        "perimeter": round(perimeter, 2),
        "cost_estimate": round(tiles_with_wastage * 500, 2),  # ~500 руб/м²
        "recommendations": {
            "wastage": f"Запас {wastage}% на подрезку и бой",
            "adhesive": "Клей для плитки (цементный или полимерный)",
            "grout": "Затирка для швов (цементная или эпоксидная)",
            "layout": "Рекомендуется диагональная укладка +15% к запасу"
        }
    }
    
    return result


# ========================================
# 10. КАЛЬКУЛЯТОР КРАСКИ
# ========================================

def calculate_paint(
    area: float,  # площадь поверхности, м²
    paint_type: str = "water",  # water, oil, latex
    layers: int = 2,  # количество слоёв
    surface_type: str = "smooth"  # smooth, rough, porous
) -> Dict:
    """
    Расчёт расхода краски
    
    Returns:
        dict с результатами расчёта
    """
    # Расход краски на 1 м² в зависимости от типа (л/м²)
    paint_consumption = {
        "water": {"smooth": 0.1, "rough": 0.12, "porous": 0.15},  # водоэмульсионная
        "oil": {"smooth": 0.12, "rough": 0.15, "porous": 0.18},  # масляная
        "latex": {"smooth": 0.08, "rough": 0.1, "porous": 0.12}  # латексная
    }
    
    base_consumption = paint_consumption.get(paint_type, paint_consumption["water"])
    consumption_per_m2 = base_consumption.get(surface_type, base_consumption["smooth"])
    
    # Общий расход с учётом слоёв
    total_consumption = area * consumption_per_m2 * layers
    
    # Запас 10%
    total_with_reserve = total_consumption * 1.1
    
    # Количество банок (обычно 2.5 л или 10 л)
    cans_2_5l = math.ceil(total_with_reserve / 2.5)
    cans_10l = math.ceil(total_with_reserve / 10)
    
    # Расход грунтовки (примерно 0.1 л/м²)
    primer_consumption = area * 0.1
    primer_cans = math.ceil(primer_consumption / 2.5)
    
    result = {
        "area": area,
        "paint_type": paint_type,
        "surface_type": surface_type,
        "layers": layers,
        "consumption_per_m2": round(consumption_per_m2, 3),
        "total_consumption": round(total_consumption, 2),
        "total_with_reserve": round(total_with_reserve, 2),
        "cans_2_5l": cans_2_5l,
        "cans_10l": cans_10l,
        "primer_liters": round(primer_consumption, 1),
        "primer_cans": primer_cans,
        "cost_estimate": round(total_with_reserve * 300, 2),  # ~300 руб/л
        "recommendations": {
            "paint_types": {
                "water": "Водоэмульсионная - для внутренних работ",
                "oil": "Масляная - для наружных работ",
                "latex": "Латексная - влагостойкая, для ванных"
            },
            "primer": "Грунтовка обязательна для пористых поверхностей",
            "layers": f"Рекомендуется {layers} слоя для качественного покрытия"
        }
    }
    
    return result


# ========================================
# 11. КАЛЬКУЛЯТОР ПЛОЩАДИ СТЕН
# ========================================

def calculate_wall_area(
    length: float,  # длина помещения, м
    width: float,   # ширина помещения, м
    height: float,  # высота помещения, м
    windows_count: int = 0,  # количество окон
    window_area: float = 1.5,  # площадь одного окна, м²
    doors_count: int = 0,  # количество дверей
    door_area: float = 2.0  # площадь одной двери, м²
) -> Dict:
    """
    Расчёт площади стен для покраски/обоев
    
    Returns:
        dict с результатами расчёта
    """
    # Периметр помещения
    perimeter = 2 * (length + width)
    
    # Площадь всех стен
    total_wall_area = perimeter * height
    
    # Площадь проёмов
    windows_total = windows_count * window_area
    doors_total = doors_count * door_area
    openings_total = windows_total + doors_total
    
    # Площадь без проёмов
    net_wall_area = total_wall_area - openings_total
    
    # Площадь потолка
    ceiling_area = length * width
    
    result = {
        "room_dimensions": f"{length}×{width}×{height} м",
        "perimeter": round(perimeter, 2),
        "total_wall_area": round(total_wall_area, 2),
        "windows_count": windows_count,
        "windows_area": round(windows_total, 2),
        "doors_count": doors_count,
        "doors_area": round(doors_total, 2),
        "openings_total": round(openings_total, 2),
        "net_wall_area": round(net_wall_area, 2),
        "ceiling_area": round(ceiling_area, 2),
        "total_area_walls_ceiling": round(net_wall_area + ceiling_area, 2),
        "recommendations": {
            "paint": f"Для покраски: {round(net_wall_area, 1)} м² стен",
            "wallpaper": f"Для обоев: {round(net_wall_area, 1)} м² стен",
            "ceiling": f"Для потолка: {round(ceiling_area, 1)} м²"
        }
    }
    
    return result


# ========================================
# 12. КАЛЬКУЛЯТОР КРОВЛИ
# ========================================

def calculate_roof(
    length: float,  # длина здания, м
    width: float,   # ширина здания, м
    roof_type: str = "gable",  # gable, hip, flat
    slope: float = 30,  # угол наклона, градусы
    overhang: float = 0.5  # свес, м
) -> Dict:
    """
    Расчёт площади кровли и материалов
    
    Returns:
        dict с результатами расчёта
    """
    # Площадь основания
    base_area = length * width
    
    # Площадь кровли в зависимости от типа
    if roof_type == "flat":  # плоская
        roof_area = base_area
        slope_factor = 1.0
    elif roof_type == "gable":  # двускатная
        # Площадь одного ската
        slope_rad = math.radians(slope)
        slope_length = (width / 2) / math.cos(slope_rad)
        roof_area = 2 * length * slope_length
        slope_factor = 1 / math.cos(slope_rad)
    elif roof_type == "hip":  # вальмовая
        # Упрощённый расчёт
        slope_rad = math.radians(slope)
        slope_factor = 1 / math.cos(slope_rad)
        roof_area = base_area * slope_factor
    else:
        roof_area = base_area
        slope_factor = 1.0
    
    # С учётом свесов
    roof_area_with_overhang = roof_area + (2 * (length + width) * overhang)
    
    # Для металлочерепицы (полезная ширина листа ~1.1 м)
    metal_sheet_width = 1.1
    metal_sheets_needed = math.ceil(roof_area_with_overhang / metal_sheet_width / length)
    
    # Расход утеплителя (толщина 200 мм)
    insulation_thickness = 0.2
    insulation_volume = roof_area_with_overhang * insulation_thickness
    
    # Расход пароизоляции (равен площади кровли)
    vapor_barrier_area = roof_area_with_overhang
    
    result = {
        "base_area": round(base_area, 2),
        "roof_type": roof_type,
        "slope": slope,
        "roof_area": round(roof_area, 2),
        "roof_area_with_overhang": round(roof_area_with_overhang, 2),
        "slope_factor": round(slope_factor, 2),
        "metal_sheets_needed": metal_sheets_needed,
        "insulation_volume": round(insulation_volume, 2),
        "vapor_barrier_area": round(vapor_barrier_area, 2),
        "cost_estimate": round(roof_area_with_overhang * 1500, 2),  # ~1500 руб/м²
        "recommendations": {
            "roof_types": {
                "flat": "Плоская - для хозяйственных построек",
                "gable": "Двускатная - классическая, простая",
                "hip": "Вальмовая - сложнее, но красивее"
            },
            "materials": "Металлочерепица, профлист, мягкая кровля",
            "insulation": "Минеральная вата 200 мм для утепления"
        }
    }
    
    return result


# ========================================
# 13. КАЛЬКУЛЯТОР ШТУКАТУРКИ
# ========================================

def calculate_plaster(
    area: float,  # площадь поверхности, м²
    thickness: float = 0.02,  # толщина слоя, м (20 мм)
    plaster_type: str = "cement"  # cement, gypsum, decorative
) -> Dict:
    """
    Расчёт расхода штукатурки
    
    Returns:
        dict с результатами расчёта
    """
    # Расход штукатурки на 1 м² при толщине 1 мм (кг/м²·мм)
    consumption_per_mm = {
        "cement": 1.8,  # цементная
        "gypsum": 0.9,  # гипсовая
        "decorative": 1.2  # декоративная
    }
    
    base_consumption = consumption_per_mm.get(plaster_type, consumption_per_mm["cement"])
    
    # Толщина в мм
    thickness_mm = thickness * 1000
    
    # Расход на м²
    consumption_per_m2 = base_consumption * thickness_mm
    
    # Общий расход
    total_consumption = area * consumption_per_m2
    
    # Запас 10%
    total_with_reserve = total_consumption * 1.1
    
    # Количество мешков (обычно 25-30 кг)
    bags_25kg = math.ceil(total_consumption / 25)
    bags_30kg = math.ceil(total_consumption / 30)
    
    result = {
        "area": area,
        "thickness": thickness,
        "thickness_mm": thickness_mm,
        "plaster_type": plaster_type,
        "consumption_per_m2": round(consumption_per_m2, 1),
        "total_consumption": round(total_consumption, 1),
        "total_with_reserve": round(total_with_reserve, 1),
        "bags_25kg": bags_25kg,
        "bags_30kg": bags_30kg,
        "cost_estimate": round(total_with_reserve * 15, 2),  # ~15 руб/кг
        "recommendations": {
            "plaster_types": {
                "cement": "Цементная - для наружных работ",
                "gypsum": "Гипсовая - для внутренних, быстро сохнет",
                "decorative": "Декоративная - финишная отделка"
            },
            "thickness": f"Толщина слоя {thickness_mm} мм - стандартная",
            "primer": "Обязательна грунтовка перед штукатуркой"
        }
    }
    
    return result


# ========================================
# 14. КАЛЬКУЛЯТОР ОБОЕВ
# ========================================

def calculate_wallpaper(
    wall_area: float,  # площадь стен, м²
    roll_length: float = 10,  # длина рулона, м
    roll_width: float = 0.53,  # ширина рулона, м
    pattern_repeat: float = 0,  # раппорт рисунка, м (0 если без рисунка)
    wastage: float = 10.0  # процент запаса
) -> Dict:
    """
    Расчёт количества обоев
    
    Returns:
        dict с результатами расчёта
    """
    # Площадь одного рулона
    roll_area = roll_length * roll_width
    
    # Если есть раппорт, уменьшаем полезную длину
    if pattern_repeat > 0:
        # Округляем вверх до целого числа раппортов
        usable_length = math.floor(roll_length / pattern_repeat) * pattern_repeat
        roll_area = usable_length * roll_width
    
    # Количество рулонов без запаса
    rolls_needed = math.ceil(wall_area / roll_area)
    
    # С запасом
    rolls_with_wastage = math.ceil(rolls_needed * (1 + wastage / 100))
    
    # Расход клея (примерно 0.1-0.15 кг/м²)
    adhesive_per_m2 = 0.12
    adhesive_total = math.ceil(wall_area * adhesive_per_m2)
    
    result = {
        "wall_area": wall_area,
        "roll_size": f"{roll_length}×{roll_width*1000:.0f} м",
        "roll_area": round(roll_area, 2),
        "pattern_repeat": pattern_repeat,
        "rolls_needed": rolls_needed,
        "rolls_with_wastage": rolls_with_wastage,
        "wastage_percent": wastage,
        "adhesive_kg": adhesive_total,
        "adhesive_packs": math.ceil(adhesive_total / 0.2),  # пачки по 200 г
        "cost_estimate": round(rolls_with_wastage * 500, 2),  # ~500 руб/рулон
        "recommendations": {
            "pattern": "При наличии раппорта запас увеличить до 15%",
            "adhesive": "Клей для обоев (универсальный или специальный)",
            "preparation": "Стены должны быть ровными и загрунтованными"
        }
    }
    
    return result


# ========================================
# 15. КАЛЬКУЛЯТОР ЛАМИНАТА
# ========================================

def calculate_laminate(
    length: float,  # длина помещения, м
    width: float,   # ширина помещения, м
    plank_length: float = 1.28,  # длина доски, м
    plank_width: float = 0.192,  # ширина доски, м
    wastage: float = 7.0  # процент запаса
) -> Dict:
    """
    Расчёт количества ламината
    
    Returns:
        dict с результатами расчёта
    """
    # Площадь помещения
    room_area = length * width
    
    # Площадь одной доски
    plank_area = plank_length * plank_width
    
    # Количество досок
    planks_needed = math.ceil(room_area / plank_area)
    
    # С запасом
    planks_with_wastage = math.ceil(planks_needed * (1 + wastage / 100))
    
    # Количество упаковок (обычно 8-10 досок в упаковке)
    planks_per_pack = 8
    packs_needed = math.ceil(planks_with_wastage / planks_per_pack)
    
    # Расход подложки (равен площади пола)
    underlay_area = room_area
    
    # Расход плинтуса (периметр)
    perimeter = 2 * (length + width)
    
    result = {
        "room_area": round(room_area, 2),
        "plank_size": f"{plank_length*1000:.0f}×{plank_width*1000:.0f} мм",
        "plank_area": round(plank_area, 3),
        "planks_needed": planks_needed,
        "planks_with_wastage": planks_with_wastage,
        "packs_needed": packs_needed,
        "wastage_percent": wastage,
        "underlay_area": round(underlay_area, 2),
        "underlay_rolls": math.ceil(underlay_area / 10),  # рулоны по 10 м²
        "skirting_length": round(perimeter, 2),
        "cost_estimate": round(packs_needed * 2000, 2),  # ~2000 руб/упаковка
        "recommendations": {
            "wastage": f"Запас {wastage}% на подрезку",
            "underlay": "Подложка 2-3 мм для звукоизоляции",
            "installation": "Укладка плавающим способом с зазором 10 мм"
        }
    }
    
    return result


# ========================================
# 16. КАЛЬКУЛЯТОР УТЕПЛИТЕЛЯ
# ========================================

def calculate_insulation(
    area: float,  # площадь утепления, м²
    thickness: float = 0.1,  # толщина утеплителя, м (100 мм)
    insulation_type: str = "mineral_wool"  # mineral_wool, polystyrene, penoplex
) -> Dict:
    """
    Расчёт количества утеплителя
    
    Returns:
        dict с результатами расчёта
    """
    # Объём утеплителя
    volume = area * thickness
    
    # Количество упаковок в зависимости от типа
    pack_volumes = {
        "mineral_wool": 0.36,  # м³ в упаковке
        "polystyrene": 0.3,
        "penoplex": 0.3
    }
    
    pack_volume = pack_volumes.get(insulation_type, pack_volumes["mineral_wool"])
    packs_needed = math.ceil(volume / pack_volume)
    
    # Расход пароизоляции (равен площади)
    vapor_barrier_area = area
    
    # Расход дюбелей (примерно 5-6 шт/м²)
    dowels_per_m2 = 5.5
    dowels_total = math.ceil(area * dowels_per_m2)
    
    result = {
        "area": area,
        "thickness": thickness,
        "thickness_mm": thickness * 1000,
        "volume": round(volume, 2),
        "insulation_type": insulation_type,
        "packs_needed": packs_needed,
        "vapor_barrier_area": round(vapor_barrier_area, 2),
        "dowels_total": dowels_total,
        "cost_estimate": round(packs_needed * 800, 2),  # ~800 руб/упаковка
        "recommendations": {
            "insulation_types": {
                "mineral_wool": "Минеральная вата - негорючая, паропроницаемая",
                "polystyrene": "Пенопласт - дешёвый, но горючий",
                "penoplex": "Экструдированный пенополистирол - прочный, влагостойкий"
            },
            "thickness": f"Толщина {thickness*1000:.0f} мм - стандартная для стен",
            "vapor_barrier": "Пароизоляция обязательна с внутренней стороны"
        }
    }
    
    return result


# ========================================
# 17. КАЛЬКУЛЯТОР ФУНДАМЕНТА
# ========================================

def calculate_foundation(
    length: float,  # длина фундамента, м
    width: float,   # ширина фундамента, м
    depth: float,   # глубина заложения, м
    foundation_type: str = "strip"  # strip, slab, pile
) -> Dict:
    """
    Расчёт фундамента
    
    Returns:
        dict с результатами расчёта
    """
    if foundation_type == "strip":  # ленточный
        # Периметр
        perimeter = 2 * (length + width)
        # Объём бетона
        volume = perimeter * width * depth
        # Площадь подошвы
        base_area = perimeter * width
    elif foundation_type == "slab":  # плитный
        volume = length * width * depth
        base_area = length * width
    elif foundation_type == "pile":  # свайный
        # Упрощённый расчёт для ростверка
        volume = length * width * 0.3  # ростверк 30 см
        base_area = length * width
    else:
        volume = length * width * depth
        base_area = length * width
    
    # Арматура (примерно 80-100 кг/м³)
    rebar_per_m3 = 90
    rebar_total = volume * rebar_per_m3 / 1000  # в тоннах
    
    # Опалубка (периметр × высота)
    if foundation_type == "strip":
        formwork_area = 2 * (length + width) * depth
    elif foundation_type == "slab":
        formwork_area = 2 * (length + width) * depth
    else:
        formwork_area = 0
    
    result = {
        "foundation_type": foundation_type,
        "dimensions": f"{length}×{width}×{depth} м",
        "volume": round(volume, 2),
        "base_area": round(base_area, 2),
        "rebar_tons": round(rebar_total, 2),
        "rebar_kg": round(rebar_total * 1000, 0),
        "formwork_area": round(formwork_area, 2),
        "cost_estimate": round(volume * 5000, 2),  # ~5000 руб/м³
        "recommendations": {
            "types": {
                "strip": "Ленточный - для домов с подвалом",
                "slab": "Плитный - для слабых грунтов",
                "pile": "Свайный - для сложных грунтов"
            },
            "depth": f"Глубина {depth} м - стандартная для средней полосы",
            "rebar": "Арматура А500С, диаметр 12-16 мм"
        }
    }
    
    return result


# ========================================
# 18. КАЛЬКУЛЯТОР ЛЕСТНИЦ
# ========================================

def calculate_stairs(
    floor_height: float,  # высота этажа, м
    step_width: float = 0.3,  # ширина проступи, м
    step_height: float = 0.15,  # высота подступенка, м
    stairs_width: float = 1.0  # ширина лестницы, м
) -> Dict:
    """
    Расчёт лестницы
    
    Returns:
        dict с результатами расчёта
    """
    # Количество ступеней
    steps_count = math.ceil(floor_height / step_height)
    
    # Фактическая высота подступенка
    actual_step_height = floor_height / steps_count
    
    # Длина косоура
    stringer_length = math.sqrt((floor_height ** 2) + ((steps_count * step_width) ** 2))
    
    # Площадь ступеней
    steps_area = steps_count * step_width * stairs_width
    
    # Объём бетона (для монолитной лестницы)
    # Толщина плиты ~15 см
    concrete_volume = steps_area * 0.15
    
    # Арматура
    rebar_kg = steps_area * 12  # ~12 кг/м²
    
    result = {
        "floor_height": floor_height,
        "steps_count": steps_count,
        "step_width": step_width,
        "actual_step_height": round(actual_step_height, 3),
        "stairs_width": stairs_width,
        "stringer_length": round(stringer_length, 2),
        "steps_area": round(steps_area, 2),
        "concrete_volume": round(concrete_volume, 2),
        "rebar_kg": round(rebar_kg, 1),
        "cost_estimate": round(steps_area * 3000, 2),  # ~3000 руб/м²
        "recommendations": {
            "formula": "2h + b = 60-65 см (оптимально)",
            "safety": "Высота подступенка не более 20 см",
            "width": "Ширина проступи не менее 25 см"
        }
    }
    
    return result


# ========================================
# 19. КАЛЬКУЛЯТОР ГИПСОКАРТОНА
# ========================================

def calculate_drywall(
    length: float,  # длина помещения, м
    width: float,   # ширина помещения, м
    height: float,  # высота помещения, м
    ceiling: bool = True  # делать потолок
) -> Dict:
    """
    Расчёт гипсокартона
    
    Returns:
        dict с результатами расчёта
    """
    # Площадь стен
    perimeter = 2 * (length + width)
    walls_area = perimeter * height
    
    # Площадь потолка
    ceiling_area = length * width if ceiling else 0
    
    # Общая площадь
    total_area = walls_area + ceiling_area
    
    # Размер листа ГКЛ: 2500×1200 мм = 3 м²
    sheet_area = 3.0
    sheets_needed = math.ceil(total_area / sheet_area)
    # Запас 10%
    sheets_with_reserve = math.ceil(sheets_needed * 1.1)
    
    # Профили ПП (потолочные) - шаг 600 мм
    if ceiling:
        pp_length = (math.ceil(length / 0.6) + 1) * width + (math.ceil(width / 0.6) + 1) * length
    else:
        pp_length = 0
    
    # Профили ПН (направляющие) - периметр
    pn_length = perimeter * 2  # для стен и потолка
    
    # Профили ПС (стоечные) - шаг 600 мм
    ps_length = math.ceil(perimeter / 0.6) * height
    
    # Саморезы (примерно 20-25 шт/м²)
    screws_per_m2 = 22
    screws_total = math.ceil(total_area * screws_per_m2)
    
    # Шпаклёвка (примерно 1 кг/м²)
    putty_kg = math.ceil(total_area * 1)
    
    result = {
        "room_dimensions": f"{length}×{width}×{height} м",
        "walls_area": round(walls_area, 2),
        "ceiling_area": round(ceiling_area, 2),
        "total_area": round(total_area, 2),
        "sheets_needed": sheets_needed,
        "sheets_with_reserve": sheets_with_reserve,
        "pp_length": round(pp_length, 1),  # потолочные профили
        "pn_length": round(pn_length, 1),  # направляющие
        "ps_length": round(ps_length, 1),  # стоечные
        "screws_total": screws_total,
        "putty_kg": putty_kg,
        "putty_bags": math.ceil(putty_kg / 20),  # мешки по 20 кг
        "cost_estimate": round(sheets_with_reserve * 400, 2),  # ~400 руб/лист
        "recommendations": {
            "profiles": "Профили ПП 60×27, ПН 28×27, ПС 60×27",
            "screws": "Саморезы 3.5×25 мм для ГКЛ",
            "putty": "Шпаклёвка финишная для стыков"
        }
    }
    
    return result


# ========================================
# 20. КАЛЬКУЛЯТОР ЗЕМЛЯНЫХ РАБОТ
# ========================================

def calculate_earthwork(
    length: float,  # длина котлована, м
    width: float,   # ширина котлована, м
    depth: float,   # глубина котлована, м
    soil_type: str = "clay"  # clay, sand, rock
) -> Dict:
    """
    Расчёт земляных работ
    
    Returns:
        dict с результатами расчёта
    """
    # Объём выемки
    volume = length * width * depth
    
    # Коэффициент разрыхления грунта
    loosening_factor = {
        "clay": 1.3,  # глина
        "sand": 1.15,  # песок
        "rock": 1.5  # скальный
    }
    
    factor = loosening_factor.get(soil_type, loosening_factor["clay"])
    loose_volume = volume * factor
    
    # Производительность экскаватора (м³/час)
    excavator_productivity = {
        "clay": 50,  # глина
        "sand": 60,  # песок
        "rock": 30  # скальный
    }
    
    productivity = excavator_productivity.get(soil_type, excavator_productivity["clay"])
    hours_needed = volume / productivity
    
    # Количество самосвалов (грузоподъёмность 10 т, плотность грунта 1.8 т/м³)
    truck_capacity = 10 / 1.8  # м³
    trucks_needed = math.ceil(loose_volume / truck_capacity)
    
    # Стоимость работ
    cost_per_m3 = {
        "clay": 300,  # руб/м³
        "sand": 250,
        "rock": 800
    }
    
    work_cost = volume * cost_per_m3.get(soil_type, cost_per_m3["clay"])
    
    result = {
        "dimensions": f"{length}×{width}×{depth} м",
        "volume": round(volume, 2),
        "soil_type": soil_type,
        "loosening_factor": factor,
        "loose_volume": round(loose_volume, 2),
        "hours_needed": round(hours_needed, 1),
        "days_needed": round(hours_needed / 8, 1),  # 8 часов в день
        "trucks_needed": trucks_needed,
        "work_cost": round(work_cost, 2),
        "cost_estimate": round(work_cost * 1.2, 2),  # с накладными
        "recommendations": {
            "soil_types": {
                "clay": "Глина - коэффициент разрыхления 1.3",
                "sand": "Песок - коэффициент разрыхления 1.15",
                "rock": "Скальный - коэффициент разрыхления 1.5"
            },
            "equipment": "Экскаватор + самосвалы для вывоза",
            "safety": "Обязательны откосы или крепление стенок"
        }
    }
    
    return result


# ========================================
# 21. КАЛЬКУЛЯТОР ТРУДОЗАТРАТ
# ========================================

def calculate_labor(
    work_type: str,  # тип работы
    volume: float,   # объём работ
    work_unit: str = "m3"  # единица измерения: m3, m2, m
) -> Dict:
    """
    Расчёт трудозатрат
    
    Returns:
        dict с результатами расчёта
    """
    # Нормы времени (чел·час на единицу)
    labor_norms = {
        "concrete": {"m3": 2.5, "unit": "м³"},
        "masonry": {"m2": 1.8, "unit": "м²"},
        "plaster": {"m2": 0.8, "unit": "м²"},
        "paint": {"m2": 0.3, "unit": "м²"},
        "tile": {"m2": 1.2, "unit": "м²"},
        "roof": {"m2": 1.5, "unit": "м²"}
    }
    
    norm_data = labor_norms.get(work_type, {"m3": 2.0, "unit": "м³"})
    norm_key = work_unit if work_unit in norm_data else "m3"
    norm_per_unit = norm_data.get(norm_key, norm_data.get("m3", 2.0))
    
    # Трудозатраты в чел·час
    labor_hours = volume * norm_per_unit
    
    # Трудозатраты в чел·дни (8 часов в день)
    labor_days = labor_hours / 8
    
    # Количество рабочих (при сроке выполнения)
    # Предположим срок 10 дней
    deadline_days = 10
    workers_needed = math.ceil(labor_days / deadline_days)
    
    # Стоимость работ (примерно 500 руб/чел·час)
    cost_per_hour = 500
    total_cost = labor_hours * cost_per_hour
    
    result = {
        "work_type": work_type,
        "volume": volume,
        "work_unit": norm_data["unit"],
        "norm_per_unit": norm_per_unit,
        "labor_hours": round(labor_hours, 1),
        "labor_days": round(labor_days, 1),
        "workers_needed": workers_needed,
        "deadline_days": deadline_days,
        "total_cost": round(total_cost, 2),
        "cost_per_unit": round(total_cost / volume, 2),
        "recommendations": {
            "norms": "Нормы по ЕНиР (Единые нормы и расценки)",
            "productivity": "Производительность зависит от условий работы",
            "safety": "Учитывать время на подготовку и уборку"
        }
    }
    
    return result