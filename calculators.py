"""
Строительные калькуляторы для СтройНадзорAI v4.0
Обновлено: 2025-11-29
С интеграцией актуальных СП и СНиП 2025
"""

import math
from typing import Dict, Tuple, Union, Optional, List

# ======================
# НОРМАТИВНЫЕ ДОКУМЕНТЫ 2025
# ======================

NORMATIVE_DOCUMENTS = {
    "concrete": {
        "title": "СП 63.13330.2018 (актуализированная редакция СНиП 52-01-2003)",
        "link": "https://docs.cntd.ru/document/1200162530",
        "description": "Бетонные и железобетонные конструкции"
    },
    "foundations": {
        "title": "СП 22.13330.2023 (актуализированная редакция СНиП 2.02.01-83*)",
        "link": "https://docs.cntd.ru/document/1200193290",
        "description": "Основания зданий и сооружений"
    },
    "load_combinations": {
        "title": "СП 20.13330.2023 (актуализированная редакция СНиП 2.01.07-85*)",
        "link": "https://docs.cntd.ru/document/1200193270",
        "description": "Нагрузки и воздействия"
    },
    "brickwork": {
        "title": "СП 15.13330.2024 (актуализированная редакция СНиП II-22-81*)",
        "link": "https://docs.cntd.ru/document/1200201550",
        "description": "Каменные и армокаменные конструкции"
    }
}

def format_number(value: float, decimals: int = 2) -> str:
    """Форматирование чисел с разделением тысяч"""
    return f"{value:,.{decimals}f}".replace(',', ' ')

# ========================================
# 1. КАЛЬКУЛЯТОР БЕТОНА
# ========================================

def calculate_concrete(
    length: float,
    width: float,
    height: float,
    concrete_class: str = "B25",
    wastage: float = 5.0,
    temperature: float = 20,
    humidity: float = 60,
    concrete_type: str = "heavy",
    pumping_distance: float = 0,
    additives: bool = False
) -> Dict:
    """
    Расчёт объёма бетона по СП 63.13330.2018
    """
    if length <= 0 or width <= 0 or height <= 0:
        return {"error": "Размеры должны быть положительными"}
    if not (0 <= wastage <= 50):
        return {"error": "Запас должен быть от 0 до 50%"}
    if not (-50 <= temperature <= 50):
        return {"error": "Температура должна быть от -50 до +50°C"}
    if not (0 <= humidity <= 100):
        return {"error": "Влажность должна быть от 0 до 100%"}

    volume = length * width * height
    compaction_factor = 1.02
    loss_factor = 1.03
    pumping_loss = min(0.05, pumping_distance * 0.001) if pumping_distance > 0 else 0

    if temperature < 5:
        temp_coefficient = 1.1
    elif temperature > 30:
        temp_coefficient = 1.05
    else:
        temp_coefficient = 1.0

    if humidity < 40:
        humidity_coefficient = 1.05
    elif humidity > 80:
        humidity_coefficient = 0.95
    else:
        humidity_coefficient = 1.0

    total_wastage_coefficient = (1 + wastage / 100) * compaction_factor * \
                               1.02 * 1.03 * (1 + pumping_loss) * temp_coefficient * humidity_coefficient

    volume_with_wastage = volume * total_wastage_coefficient

    strength_map = {
        "B7.5": {"strength": 98, "cement_min": 160, "cement_max": 200},
        "B12.5": {"strength": 164, "cement_min": 200, "cement_max": 250},
        "B15": {"strength": 196, "cement_min": 220, "cement_max": 280},
        "B20": {"strength": 262, "cement_min": 250, "cement_max": 320},
        "B22.5": {"strength": 294, "cement_min": 270, "cement_max": 340},
        "B25": {"strength": 327, "cement_min": 290, "cement_max": 370},
        "B30": {"strength": 393, "cement_min": 320, "cement_max": 410},
        "B35": {"strength": 458, "cement_min": 350, "cement_max": 450},
        "B40": {"strength": 524, "cement_min": 380, "cement_max": 490}
    }

    concrete_data = strength_map.get(concrete_class, strength_map["B25"])

    cement_density_map = {
        "heavy": concrete_data["cement_min"] + (concrete_data["cement_max"] - concrete_data["cement_min"]) * 0.5,
        "lightweight": concrete_data["cement_min"] * 0.8,
        "cellular": concrete_data["cement_min"] * 0.6
    }

    cement_per_m3 = cement_density_map.get(concrete_type, concrete_data["cement_min"])
    total_cement = volume_with_wastage * cement_per_m3

    water_cement_ratio = 0.5 if concrete_class in ["B25", "B30"] else 0.45
    if additives:
        water_cement_ratio *= 0.9

    water_per_m3 = cement_per_m3 * water_cement_ratio
    total_water = volume_with_wastage * water_per_m3

    gravel_per_m3 = 1200 if concrete_type == "heavy" else 800
    sand_per_m3 = 650 if concrete_type == "heavy" else 400

    total_gravel = volume_with_wastage * gravel_per_m3
    total_sand = volume_with_wastage * sand_per_m3

    cost_per_m3_map = {"heavy": 4500, "lightweight": 3800, "cellular": 3200}
    cost_per_m3_base = cost_per_m3_map.get(concrete_type, 4500)
    total_cost = volume_with_wastage * cost_per_m3_base

    return {
        "volume": round(volume, 3),
        "volume_with_wastage": round(volume_with_wastage, 3),
        "concrete_class": concrete_class,
        "strength": concrete_data["strength"],
        "concrete_type": concrete_type,
        "cement_total": round(total_cement, 0),
        "cement_per_m3": round(cement_per_m3, 0),
        "water_total": round(total_water, 0),
        "water_per_m3": round(water_per_m3, 0),
        "gravel_total": round(total_gravel, 0),
        "gravel_per_m3": round(gravel_per_m3, 0),
        "sand_total": round(total_sand, 0),
        "sand_per_m3": round(sand_per_m3, 0),
        "water_cement_ratio": round(water_cement_ratio, 3),
        "cost_per_m3": cost_per_m3_base,
        "total_cost": round(total_cost, 2),
        "total_coefficient": round(total_wastage_coefficient, 3),
        "standards": "СП 63.13330.2018, СП 70.13330.2012, ГОСТ 26633-2015"
    }

# ========================================
# 2. КАЛЬКУЛЯТОР АРМАТУРЫ
# ========================================

def calculate_reinforcement(
    length: float,
    width: float,
    height: float,
    diameter: int = 12,
    spacing: int = 200,
    element_type: str = "slab"
) -> Dict:
    """
    Расчёт арматуры по СП 63.13330.2018
    """
    if length <= 0 or width <= 0 or height <= 0:
        return {"error": "Все размеры должны быть положительными"}

    rebar_weights = {
        6: 0.222, 8: 0.395, 10: 0.617, 12: 0.888,
        14: 1.210, 16: 1.580, 18: 2.000, 20: 2.470, 22: 2.980, 25: 3.850
    }

    available_diams = sorted(rebar_weights.keys())
    selected_diam = min(available_diams, key=lambda x: abs(x - diameter))
    weight_per_meter = rebar_weights.get(selected_diam, 0.888)

    rebar_spacing = spacing

    num_lengthwise = int(length * 1000 / rebar_spacing) + 1
    num_widthwise = int(width * 1000 / rebar_spacing) + 1

    # Учитываем тип элемента
    if element_type == "slab":
        # Для плиты - двойная сетка
        mesh_count = 2
        total_length = mesh_count * (num_lengthwise * width + num_widthwise * length)
    elif element_type == "beam":
        # Для балки - продольная арматура + хомуты
        longitudinal = 4 * length  # 4 стержня по длине
        stirrups_count = int(length * 1000 / 300)  # хомуты каждые 300 мм
        stirrup_length = 2 * (width + height) - 0.1
        total_length = longitudinal + stirrups_count * stirrup_length
    elif element_type == "column":
        # Для колонны - вертикальная арматура + хомуты
        vertical = 4 * height  # 4 стержня по высоте
        stirrups_count = int(height * 1000 / 200)  # хомуты каждые 200 мм
        stirrup_length = 2 * (width + length) - 0.1
        total_length = vertical + stirrups_count * stirrup_length
    else:
        mesh_count = 2
        total_length = mesh_count * (num_lengthwise * width + num_widthwise * length)

    total_mass = total_length * weight_per_meter
    element_area = length * width

    return {
        "total_length": round(total_length, 2),
        "total_mass": round(total_mass, 2),
        "rebar_diameter": selected_diam,
        "weight_per_meter": weight_per_meter,
        "rebar_spacing": rebar_spacing,
        "num_lengthwise": num_lengthwise,
        "num_widthwise": num_widthwise,
        "element_area": round(element_area, 2),
        "mass_per_m2": round(total_mass / element_area, 2) if element_area > 0 else 0,
        "element_type": element_type,
        "standards": "СП 63.13330.2018"
    }

# ========================================
# 3. КАЛЬКУЛЯТОР ОПАЛУБКИ
# ========================================

def calculate_formwork(
    area: float,
    duration: int,
    formwork_type: str = "panel"
) -> Dict:
    """Расчёт опалубки по площади и сроку эксплуатации"""
    if area <= 0 or duration <= 0:
        return {"error": "Площадь и срок должны быть положительными"}

    formwork_materials = {
        "panel": {"name": "Щитовая", "reuse": 50, "cost_per_m2": 350, "install_time": 0.5},
        "wall": {"name": "Стеновая", "reuse": 40, "cost_per_m2": 400, "install_time": 0.6},
        "universal": {"name": "Универсальная", "reuse": 100, "cost_per_m2": 600, "install_time": 0.4}
    }

    material = formwork_materials.get(formwork_type, formwork_materials["panel"])

    # Количество оборотов опалубки
    turnovers = max(1, int(duration / 7))  # каждые 7 дней - один оборот

    # Необходимое количество опалубки с учётом оборачиваемости
    required_area = area / turnovers if turnovers > 1 else area

    # Стоимость с учётом износа
    cost = (required_area * material["cost_per_m2"]) / material["reuse"] * turnovers

    # Время монтажа в человеко-часах
    installation_time = required_area * material["install_time"]

    return {
        "total_area": round(area, 2),
        "required_formwork": round(required_area, 2),
        "duration_days": duration,
        "turnovers": turnovers,
        "formwork_type": material["name"],
        "reuse_count": material["reuse"],
        "cost": round(cost, 2),
        "cost_per_m2": round(cost / area, 2) if area > 0 else 0,
        "installation_time_hours": round(installation_time, 1),
        "standards": "СП 70.13330.2012"
    }

# ========================================
# 4. КАЛЬКУЛЯТОР ЭЛЕКТРОСНАБЖЕНИЯ
# ========================================

def calculate_electrical(
    crane_count: int,
    pump_count: int,
    welder_count: int,
    heater_count: int,
    cabin_count: int
) -> Dict:
    """Расчёт электроснабжения стройплощадки"""
    if any(x < 0 for x in [crane_count, pump_count, welder_count, heater_count, cabin_count]):
        return {"error": "Количество оборудования не может быть отрицательным"}

    # Средняя мощность оборудования (кВт)
    power_ratings = {
        "crane": 50,      # Башенный кран
        "pump": 15,       # Бетононасос
        "welder": 10,     # Сварочный аппарат
        "heater": 5,      # Обогреватель
        "cabin": 3        # Бытовка
    }

    # Коэффициенты одновременности
    simultaneity = {
        "crane": 0.7,
        "pump": 0.8,
        "welder": 0.5,
        "heater": 0.9,
        "cabin": 1.0
    }

    # Расчёт установленной мощности
    installed_power = (
        crane_count * power_ratings["crane"] +
        pump_count * power_ratings["pump"] +
        welder_count * power_ratings["welder"] +
        heater_count * power_ratings["heater"] +
        cabin_count * power_ratings["cabin"]
    )

    # Расчёт расчётной мощности с учётом коэффициентов одновременности
    calculated_power = (
        crane_count * power_ratings["crane"] * simultaneity["crane"] +
        pump_count * power_ratings["pump"] * simultaneity["pump"] +
        welder_count * power_ratings["welder"] * simultaneity["welder"] +
        heater_count * power_ratings["heater"] * simultaneity["heater"] +
        cabin_count * power_ratings["cabin"] * simultaneity["cabin"]
    )

    # Ток при напряжении 380В (трёхфазное)
    voltage = 380
    current = (calculated_power * 1000) / (voltage * 1.73)  # 1.73 = sqrt(3)

    # Рекомендуемый автомат
    recommended_breaker = int(current * 1.25 / 10) * 10  # Округляем до 10А вверх

    # Потребление электроэнергии (кВт·ч в день, при 8 часах работы)
    daily_consumption = calculated_power * 8

    return {
        "installed_power": round(installed_power, 2),
        "calculated_power": round(calculated_power, 2),
        "voltage": voltage,
        "current": round(current, 2),
        "recommended_breaker": recommended_breaker,
        "daily_consumption": round(daily_consumption, 2),
        "equipment": {
            "cranes": crane_count,
            "pumps": pump_count,
            "welders": welder_count,
            "heaters": heater_count,
            "cabins": cabin_count
        },
        "standards": "СП 256.1325800.2016"
    }

# ========================================
# 5. КАЛЬКУЛЯТОР ВОДОСНАБЖЕНИЯ
# ========================================

def calculate_water(
    workers: int,
    mixers_per_day: int = 0
) -> Dict:
    """Расчёт водоснабжения стройплощадки"""
    if workers <= 0:
        return {"error": "Количество рабочих должно быть положительным"}

    # Нормы потребления (литры)
    consumption_per_worker = 25  # питьевая вода + бытовые нужды
    consumption_per_mixer = 200  # вода на замес бетона (средний)

    # Расчёт суточного потребления
    workers_consumption = workers * consumption_per_worker
    concrete_consumption = mixers_per_day * consumption_per_mixer
    total_daily = workers_consumption + concrete_consumption

    # Пиковый часовой расход (в обеденное время и при замесах)
    peak_hourly = total_daily * 0.2  # 20% от суточного

    # Расход в л/с
    flow_rate = peak_hourly / 3600

    # Диаметр трубы при скорости 1.5 м/с
    velocity = 1.5
    diameter = math.sqrt((4 * flow_rate / 1000) / (math.pi * velocity)) * 1000

    standard_diameters = [25, 32, 40, 50, 65, 80, 100]
    selected_diameter = min([d for d in standard_diameters if d >= diameter], default=100)

    # Запас воды (на 2 часа пикового потребления)
    reserve_volume = peak_hourly * 2

    return {
        "workers": workers,
        "mixers_per_day": mixers_per_day,
        "daily_consumption": round(total_daily, 0),
        "workers_consumption": round(workers_consumption, 0),
        "concrete_consumption": round(concrete_consumption, 0),
        "peak_hourly": round(peak_hourly, 2),
        "flow_rate": round(flow_rate, 3),
        "pipe_diameter": selected_diameter,
        "reserve_volume": round(reserve_volume, 0),
        "standards": "СНиП 2.04.01-85"
    }

# ========================================
# 6. МАТЕМАТИЧЕСКИЙ КАЛЬКУЛЯТОР
# ========================================

def calculate_math_expression(expression: str) -> Dict:
    """Безопасный математический калькулятор"""
    try:
        allowed_chars = set('0123456789+-*/().^sqrt ')
        if not all(c in allowed_chars for c in expression.replace('sqrt', '').replace('^', '')):
            return {"success": False, "error": "Недопустимые символы в выражении", "expression": expression}

        expr = expression.replace('^', '**').replace('sqrt', 'math.sqrt')
        result = eval(expr, {"__builtins__": {}}, {"math": math})

        return {
            "success": True,
            "expression": expression,
            "result": result,
            "formatted": round(result, 6)
        }
    except Exception as e:
        return {"success": False, "error": f"Ошибка вычисления: {str(e)}", "expression": expression}


def format_math_result(result: Dict) -> str:
    """Форматирование результата математического калькулятора"""
    if not result.get("success", False):
        return (
            f"❌ **ОШИБКА ВЫЧИСЛЕНИЯ**\n\n"
            f"📝 Выражение:\n`{result.get('expression', 'неизвестно')}`\n\n"
            f"⚠️ {result.get('error', 'Неизвестная ошибка')}"
        )

    return (
        f"✅ **РЕЗУЛЬТАТ ВЫЧИСЛЕНИЯ**\n\n"
        f"📝 Выражение:\n`{result['expression']}`\n\n"
        f"💡 Результат:\n**{format_number(result['formatted'], 6)}**"
    )

# ========================================
# 7. КАЛЬКУЛЯТОР КИРПИЧА/БЛОКОВ
# ========================================

def calculate_brick(
    wall_length: float,
    wall_height: float,
    wall_thickness: float = 0.38,
    openings_area: float = 0,
    brick_type: str = "standard"
) -> Dict:
    """Расчёт кирпичной кладки по СП 15.13330.2024"""
    if wall_length <= 0 or wall_height <= 0 or wall_thickness <= 0:
        return {"error": "Размеры должны быть положительными"}

    wall_area = wall_length * wall_height - openings_area
    if wall_area <= 0:
        return {"error": "Площадь проёмов превышает площадь стены"}

    volume = wall_area * wall_thickness

    brick_rates = {
        "standard": {"per_m3": 400, "mortar": 0.25, "name": "Одинарный (250×120×65)"},
        "one_half": {"per_m3": 300, "mortar": 0.21, "name": "Полуторный"},
        "double": {"per_m3": 200, "mortar": 0.19, "name": "Двойной"}
    }

    rates = brick_rates.get(brick_type, brick_rates["standard"])

    total_bricks = volume * rates["per_m3"]
    mortar_volume = volume * rates["mortar"]

    return {
        "wall_area": round(wall_area, 2),
        "volume": round(volume, 3),
        "total_bricks": int(total_bricks),
        "mortar_volume": round(mortar_volume, 3),
        "brick_type": rates["name"],
        "standards": "СП 15.13330.2024"
    }

# ========================================
# ДОПОЛНИТЕЛЬНЫЕ КАЛЬКУЛЯТОРЫ из оригинального кода
# ========================================

def calculate_tile(
    area: float,
    tile_length: float = 0.3,
    tile_width: float = 0.3,
    wastage: float = 10
) -> Dict:
    """Расчёт плитки"""
    if area <= 0 or tile_length <= 0 or tile_width <= 0:
        return {"error": "Все значения должны быть положительными"}

    tile_area = tile_length * tile_width
    tiles_needed = area / tile_area
    tiles_with_wastage = tiles_needed * (1 + wastage / 100)

    return {
        "area": round(area, 2),
        "tiles_needed": int(math.ceil(tiles_with_wastage)),
        "tile_size": f"{tile_length}×{tile_width} м",
        "wastage_percent": wastage
    }

def calculate_paint(
    area: float,
    coverage: float = 10,
    coats: int = 2
) -> Dict:
    """Расчёт краски"""
    if area <= 0 or coverage <= 0 or coats <= 0:
        return {"error": "Все значения должны быть положительными"}

    liters_per_coat = area / coverage
    total_liters = liters_per_coat * coats

    return {
        "area": round(area, 2),
        "coverage": coverage,
        "coats": coats,
        "total_liters": round(total_liters, 2)
    }

def calculate_wall_area(
    room_length: float,
    room_width: float,
    room_height: float,
    openings_area: float = 0
) -> Dict:
    """Расчёт площади стен"""
    if room_length <= 0 or room_width <= 0 or room_height <= 0:
        return {"error": "Размеры должны быть положительными"}

    perimeter = 2 * (room_length + room_width)
    total_area = perimeter * room_height
    net_area = total_area - openings_area

    return {
        "total_area": round(total_area, 2),
        "net_area": round(net_area, 2),
        "perimeter": round(perimeter, 2)
    }

def calculate_roof(
    length: float,
    width: float,
    roof_type: str = "gable",
    slope: float = 30
) -> Dict:
    """Расчёт кровли"""
    if length <= 0 or width <= 0:
        return {"error": "Размеры должны быть положительными"}
    if not (0 <= slope <= 90):
        return {"error": "Угол наклона должен быть от 0 до 90 градусов"}

    slope_coefficient = 1 / math.cos(math.radians(slope))

    if roof_type == "flat":
        area = length * width
    elif roof_type == "gable":
        area = length * width * slope_coefficient
    elif roof_type == "hip":
        area = length * width * slope_coefficient * 1.1
    else:
        area = length * width * slope_coefficient

    area_with_wastage = area * 1.15

    return {
        "area": round(area, 2),
        "area_with_wastage": round(area_with_wastage, 2),
        "roof_type": roof_type,
        "slope": slope
    }

def calculate_plaster(
    area: float,
    thickness: float = 20,
    plaster_type: str = "cement"
) -> Dict:
    """Расчёт штукатурки"""
    if area <= 0 or thickness <= 0:
        return {"error": "Площадь и толщина должны быть положительными"}

    consumption_data = {
        "cement": {"consumption": 16, "name": "Цементная"},
        "gypsum": {"consumption": 9, "name": "Гипсовая"},
        "lime": {"consumption": 12, "name": "Известковая"},
        "decorative": {"consumption": 8, "name": "Декоративная"}
    }

    data = consumption_data.get(plaster_type, consumption_data["cement"])
    consumption_per_m2 = data["consumption"] * (thickness / 10)
    total_consumption = area * consumption_per_m2

    return {
        "area": round(area, 2),
        "thickness": thickness,
        "total_consumption": round(total_consumption, 2),
        "consumption_per_m2": round(consumption_per_m2, 2),
        "plaster_type": data["name"]
    }

def calculate_wallpaper(
    area: float,
    roll_length: float = 10,
    roll_width: float = 0.53,
    pattern_repeat: float = 0
) -> Dict:
    """Расчёт обоев"""
    if area <= 0 or roll_length <= 0 or roll_width <= 0:
        return {"error": "Все значения должны быть положительными"}

    roll_area = roll_length * roll_width
    rolls_needed = math.ceil(area / roll_area * 1.15)

    return {
        "area": round(area, 2),
        "rolls_needed": rolls_needed,
        "roll_size": f"{roll_length}×{roll_width} м"
    }

def calculate_laminate(
    area: float,
    plank_length: float = 1.2,
    plank_width: float = 0.2,
    wastage: float = 10
) -> Dict:
    """Расчёт ламината"""
    if area <= 0 or plank_length <= 0 or plank_width <= 0:
        return {"error": "Все значения должны быть положительными"}

    plank_area = plank_length * plank_width
    total_area_with_wastage = area * (1 + wastage / 100)
    packs_needed = math.ceil(total_area_with_wastage / (plank_area * 8))

    return {
        "area": round(area, 2),
        "packs_needed": packs_needed,
        "plank_size": f"{plank_length}×{plank_width} м"
    }

def calculate_insulation(
    area: float,
    thickness: float = 100,
    insulation_type: str = "mineral_wool"
) -> Dict:
    """Расчёт утеплителя"""
    if area <= 0 or thickness <= 0:
        return {"error": "Площадь и толщина должны быть положительными"}

    insulation_data = {
        "mineral_wool": {"name": "Минеральная вата", "density": 50, "lambda": 0.045, "cost_per_m3": 3500},
        "polystyrene": {"name": "Пенополистирол", "density": 25, "lambda": 0.038, "cost_per_m3": 2800},
        "eps": {"name": "XPS", "density": 35, "lambda": 0.030, "cost_per_m3": 4500},
        "polyurethane": {"name": "ППУ", "density": 30, "lambda": 0.025, "cost_per_m3": 5000}
    }

    data = insulation_data.get(insulation_type, insulation_data["mineral_wool"])
    volume = area * (thickness / 1000)
    mass = volume * data["density"]
    cost = volume * data["cost_per_m3"]

    return {
        "area": round(area, 2),
        "thickness": thickness,
        "volume": round(volume, 3),
        "mass": round(mass, 2),
        "insulation_type": data["name"],
        "cost": round(cost, 2)
    }

def calculate_foundation(
    foundation_type: str,
    length: float,
    width: float,
    height: float,
    soil_bearing: float = 200
) -> Dict:
    """Расчёт фундамента"""
    if length <= 0 or width <= 0 or height <= 0:
        return {"error": "Размеры должны быть положительными"}

    volume = length * width * height
    base_area = length * width
    max_load = soil_bearing * base_area / 100

    return {
        "foundation_type": foundation_type,
        "volume": round(volume, 3),
        "base_area": round(base_area, 2),
        "max_load": round(max_load, 2),
        "soil_bearing": soil_bearing
    }

def calculate_stairs(
    floor_height: float,
    step_height: float = 0.17,
    step_depth: float = 0.28
) -> Dict:
    """Расчёт лестницы"""
    if floor_height <= 0 or step_height <= 0 or step_depth <= 0:
        return {"error": "Все значения должны быть положительными"}

    num_steps = math.ceil(floor_height / step_height)
    staircase_length = num_steps * step_depth

    return {
        "floor_height": round(floor_height, 2),
        "num_steps": num_steps,
        "staircase_length": round(staircase_length, 2),
        "step_height": step_height,
        "step_depth": step_depth
    }

def calculate_drywall(
    area: float,
    sheet_length: float = 2.5,
    sheet_width: float = 1.2
) -> Dict:
    """Расчёт гипсокартона"""
    if area <= 0 or sheet_length <= 0 or sheet_width <= 0:
        return {"error": "Все значения должны быть положительными"}

    sheet_area = sheet_length * sheet_width
    sheets_needed = math.ceil(area / sheet_area * 1.1)

    return {
        "area": round(area, 2),
        "sheets_needed": sheets_needed,
        "sheet_size": f"{sheet_length}×{sheet_width} м"
    }

def calculate_earthwork(
    length: float,
    width: float,
    depth: float,
    soil_type: str = "loam"
) -> Dict:
    """Расчёт земляных работ"""
    if length <= 0 or width <= 0 or depth <= 0:
        return {"error": "Размеры должны быть положительными"}

    volume = length * width * depth

    soil_data = {
        "sand": {"name": "Песок", "density": 1.6},
        "loam": {"name": "Суглинок", "density": 1.7},
        "clay": {"name": "Глина", "density": 1.8}
    }

    data = soil_data.get(soil_type, soil_data["loam"])
    mass = volume * data["density"]

    return {
        "volume": round(volume, 3),
        "mass": round(mass, 2),
        "soil_type": data["name"]
    }

def calculate_labor(
    task_type: str,
    quantity: float,
    workers: int = 1
) -> Dict:
    """Расчёт трудозатрат"""
    if quantity <= 0 or workers <= 0:
        return {"error": "Количество и число рабочих должны быть положительными"}

    labor_rates = {
        "brickwork": 8,
        "concrete": 12,
        "plaster": 10,
        "painting": 15
    }

    hours_per_unit = labor_rates.get(task_type, 10)
    total_hours = quantity * hours_per_unit
    days = math.ceil(total_hours / (8 * workers))

    return {
        "task_type": task_type,
        "quantity": quantity,
        "workers": workers,
        "total_hours": round(total_hours, 1),
        "days": days
    }

def calculate_winter_heating(
    volume: float,
    temperature_outside: float,
    method: str = "electrode"
) -> Dict:
    """Расчёт зимнего прогрева бетона"""
    if volume <= 0:
        return {"error": "Объём должен быть положительным"}

    # Температура прогрева (стандартная для твердения)
    temperature_inside = 20

    temp_diff = temperature_inside - temperature_outside

    # Методы прогрева
    methods = {
        "electrode": {
            "name": "Электроды",
            "power_per_m3": 1.2,  # кВт/м³
            "efficiency": 0.8,
            "electrodes_per_m3": 20  # шт/м³
        },
        "wire": {
            "name": "Провод ПНСВ",
            "power_per_m3": 1.0,  # кВт/м³
            "efficiency": 0.9,
            "wire_per_m3": 50  # м/м³
        },
        "thermomat": {
            "name": "Термоматы",
            "power_per_m3": 0.8,  # кВт/м³
            "efficiency": 0.95,
            "area_per_m3": 2.5  # м²/м³
        }
    }

    method_data = methods.get(method, methods["electrode"])

    # Расчёт мощности прогрева с учётом температурного режима
    temp_coefficient = 1.0 + abs(temperature_outside) * 0.02
    heating_power = volume * method_data["power_per_m3"] * temp_coefficient

    # Время прогрева в сутках
    if temperature_outside > -5:
        heating_time = 3
    elif temperature_outside > -15:
        heating_time = 5
    else:
        heating_time = 7

    # Расход материалов
    if method == "electrode":
        material_consumption = volume * method_data["electrodes_per_m3"]
        material_unit = "шт"
    elif method == "wire":
        material_consumption = volume * method_data["wire_per_m3"]
        material_unit = "м"
    else:  # thermomat
        material_consumption = volume * method_data["area_per_m3"]
        material_unit = "м²"

    # Потребление электроэнергии (кВт·ч)
    total_energy = heating_power * heating_time * 24 / method_data["efficiency"]

    # Стоимость (примерная, 6 руб/кВт·ч)
    cost = total_energy * 6

    return {
        "volume": round(volume, 3),
        "temperature_outside": round(temperature_outside, 1),
        "temperature_inside": temperature_inside,
        "temp_diff": round(temp_diff, 1),
        "method": method_data["name"],
        "heating_power": round(heating_power, 2),
        "heating_time_days": heating_time,
        "material_consumption": round(material_consumption, 1),
        "material_unit": material_unit,
        "total_energy": round(total_energy, 2),
        "estimated_cost": round(cost, 2),
        "standards": "СП 70.13330.2012"
    }

# ========================================
# СЛОВАРЬ ВСЕХ КАЛЬКУЛЯТОРОВ
# ========================================

CALCULATORS = {
    "concrete": calculate_concrete,
    "reinforcement": calculate_reinforcement,
    "formwork": calculate_formwork,
    "electrical": calculate_electrical,
    "water": calculate_water,
    "math": calculate_math_expression,
    "brick": calculate_brick,
    "tile": calculate_tile,
    "paint": calculate_paint,
    "wall_area": calculate_wall_area,
    "roof": calculate_roof,
    "plaster": calculate_plaster,
    "wallpaper": calculate_wallpaper,
    "laminate": calculate_laminate,
    "insulation": calculate_insulation,
    "foundation": calculate_foundation,
    "stairs": calculate_stairs,
    "drywall": calculate_drywall,
    "earthwork": calculate_earthwork,
    "labor": calculate_labor,
    "winter_heating": calculate_winter_heating
}

# ========================================
# ФУНКЦИЯ ФОРМАТИРОВАНИЯ РЕЗУЛЬТАТОВ
# ========================================

def format_calculator_result(calc_type: str, result: Dict) -> str:
    """Форматирование результатов калькулятора"""
    if "error" in result:
        return f"❌ Ошибка: {result['error']}"

    if calc_type == "concrete":
        return (
            f"🧮 **РЕЗУЛЬТАТЫ РАСЧЁТА БЕТОНА**\n\n"
            f"📐 Объём: **{format_number(result['volume'])} м³**\n"
            f"📦 С учётом потерь: **{format_number(result['volume_with_wastage'])} м³**\n\n"
            f"**Материалы:**\n"
            f"• Цемент: {format_number(result['cement_total'], 0)} кг ({format_number(result['cement_per_m3'], 0)} кг/м³)\n"
            f"• Песок: {format_number(result['sand_total'], 0)} кг ({format_number(result['sand_per_m3'], 0)} кг/м³)\n"
            f"• Щебень: {format_number(result['gravel_total'], 0)} кг ({format_number(result['gravel_per_m3'], 0)} кг/м³)\n"
            f"• Вода: {format_number(result['water_total'], 0)} л ({format_number(result['water_per_m3'], 0)} л/м³)\n\n"
            f"💰 Стоимость: {format_number(result['total_cost'])} руб ({format_number(result['cost_per_m3'])} руб/м³)\n\n"
            f"📚 {result['standards']}"
        )

    elif calc_type == "reinforcement":
        element_names = {"slab": "Плита", "beam": "Балка", "column": "Колонна"}
        element_name = element_names.get(result.get('element_type', 'slab'), "Плита")
        return (
            f"🔩 **РЕЗУЛЬТАТЫ РАСЧЁТА АРМАТУРЫ**\n\n"
            f"📏 Длина: **{format_number(result['total_length'])} м**\n"
            f"⚖️ Масса: **{format_number(result['total_mass'])} кг**\n\n"
            f"• Диаметр: Ø{result['rebar_diameter']} мм\n"
            f"• Шаг: {result['rebar_spacing']} мм\n"
            f"• Тип: {element_name}\n"
            f"• На м²: {format_number(result['mass_per_m2'])} кг/м²\n\n"
            f"📚 {result['standards']}"
        )

    elif calc_type == "formwork":
        return (
            f"📦 **РЕЗУЛЬТАТЫ РАСЧЁТА ОПАЛУБКИ**\n\n"
            f"📐 Площадь: **{format_number(result['total_area'])} м²**\n"
            f"📦 Требуется опалубки: **{format_number(result['required_formwork'])} м²**\n\n"
            f"• Тип: {result['formwork_type']}\n"
            f"• Срок эксплуатации: {result['duration_days']} дней\n"
            f"• Оборотов: {result['turnovers']}\n"
            f"• Время монтажа: {result['installation_time_hours']} ч\n\n"
            f"💰 Стоимость: {format_number(result['cost'])} руб\n\n"
            f"📚 {result['standards']}"
        )

    elif calc_type == "electrical":
        return (
            f"⚡ **РЕЗУЛЬТАТЫ РАСЧЁТА ЭЛЕКТРОСНАБЖЕНИЯ**\n\n"
            f"🔌 Установленная мощность: **{format_number(result['installed_power'])} кВт**\n"
            f"⚡ Расчётная мощность: **{format_number(result['calculated_power'])} кВт**\n\n"
            f"**Параметры:**\n"
            f"• Напряжение: {result['voltage']} В\n"
            f"• Ток: {format_number(result['current'])} А\n"
            f"• Автомат: {result['recommended_breaker']} А\n"
            f"• Потребление в день: {format_number(result['daily_consumption'])} кВт·ч\n\n"
            f"**Оборудование:**\n"
            f"• Краны: {result['equipment']['cranes']} шт\n"
            f"• Насосы: {result['equipment']['pumps']} шт\n"
            f"• Сварочные: {result['equipment']['welders']} шт\n"
            f"• Обогреватели: {result['equipment']['heaters']} шт\n"
            f"• Бытовки: {result['equipment']['cabins']} шт\n\n"
            f"📚 {result['standards']}"
        )

    elif calc_type == "water":
        return (
            f"💧 **РЕЗУЛЬТАТЫ РАСЧЁТА ВОДОСНАБЖЕНИЯ**\n\n"
            f"💦 Суточное потребление: **{format_number(result['daily_consumption'], 0)} л**\n"
            f"📊 Пиковый расход: **{format_number(result['peak_hourly'])} л/ч**\n\n"
            f"**Детализация:**\n"
            f"• Для рабочих: {format_number(result['workers_consumption'], 0)} л\n"
            f"• Для бетона: {format_number(result['concrete_consumption'], 0)} л\n"
            f"• Диаметр трубы: {result['pipe_diameter']} мм\n"
            f"• Объём резервуара: {format_number(result['reserve_volume'], 0)} л\n\n"
            f"**Параметры:**\n"
            f"• Рабочих: {result['workers']} чел\n"
            f"• Замесов в день: {result['mixers_per_day']}\n\n"
            f"📚 {result['standards']}"
        )

    elif calc_type == "winter_heating":
        return (
            f"❄️ **РЕЗУЛЬТАТЫ РАСЧЁТА ЗИМНЕГО ПРОГРЕВА**\n\n"
            f"🔥 Мощность прогрева: **{format_number(result['heating_power'])} кВт**\n"
            f"⏱️ Время прогрева: **{result['heating_time_days']} суток**\n\n"
            f"**Параметры:**\n"
            f"• Объём бетона: {format_number(result['volume'])} м³\n"
            f"• Температура воздуха: {result['temperature_outside']}°C\n"
            f"• Температура прогрева: {result['temperature_inside']}°C\n"
            f"• Метод: {result['method']}\n\n"
            f"**Материалы:**\n"
            f"• Расход: {format_number(result['material_consumption'])} {result['material_unit']}\n"
            f"• Электроэнергия: {format_number(result['total_energy'])} кВт·ч\n"
            f"• Примерная стоимость: {format_number(result['estimated_cost'])} руб\n\n"
            f"📚 {result['standards']}"
        )

    elif calc_type == "brick":
        return (
            f"🧱 **РЕЗУЛЬТАТЫ РАСЧЁТА КИРПИЧА**\n\n"
            f"📐 Площадь: **{format_number(result['wall_area'])} м²**\n"
            f"📦 Объём: **{format_number(result['volume'])} м³**\n\n"
            f"• Кирпич: {format_number(result['total_bricks'], 0)} шт\n"
            f"• Раствор: {format_number(result['mortar_volume'])} м³\n\n"
            f"🧱 {result['brick_type']}\n\n"
            f"📚 {result['standards']}"
        )

    else:
        # Универсальное форматирование для остальных калькуляторов
        output = f"📊 **РЕЗУЛЬТАТЫ РАСЧЁТА**\n\n"
        for key, value in result.items():
            if key != "standards" and key != "error":
                output += f"• {key}: {value}\n"
        if "standards" in result:
            output += f"\n📚 {result['standards']}"
        return output

# Экспорт
__all__ = [
    'calculate_concrete', 'calculate_reinforcement', 'calculate_formwork',
    'calculate_electrical', 'calculate_water', 'calculate_math_expression',
    'calculate_brick', 'calculate_tile', 'calculate_paint', 'calculate_wall_area',
    'calculate_roof', 'calculate_plaster', 'calculate_wallpaper', 'calculate_laminate',
    'calculate_insulation', 'calculate_foundation', 'calculate_stairs', 'calculate_drywall',
    'calculate_earthwork', 'calculate_labor', 'calculate_winter_heating',
    'format_calculator_result', 'format_math_result', 'CALCULATORS', 'NORMATIVE_DOCUMENTS'
]
