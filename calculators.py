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
    slab_length: float,
    slab_width: float,
    slab_thickness: float,
    rebar_diameter: int = 12,
    mesh_spacing: int = 200,
    double_mesh: bool = True
) -> Dict:
    """
    Расчёт арматуры по СП 63.13330.2018
    """
    if slab_length <= 0 or slab_width <= 0 or slab_thickness <= 0:
        return {"error": "Все размеры должны быть положительными"}

    rebar_weights = {
        6: 0.222, 8: 0.395, 10: 0.617, 12: 0.888,
        14: 1.210, 16: 1.580, 18: 2.000, 20: 2.470
    }

    available_diams = sorted(rebar_weights.keys())
    selected_diam = min(available_diams, key=lambda x: abs(x - rebar_diameter))
    weight_per_meter = rebar_weights[selected_diam]

    rebar_spacing = min(200, max(100, int(slab_thickness * 1000 * 4)))
    if mesh_spacing:
        rebar_spacing = mesh_spacing

    num_lengthwise = int(slab_length * 1000 / rebar_spacing) + 1
    num_widthwise = int(slab_width * 1000 / rebar_spacing) + 1

    mesh_count = 2 if double_mesh else 1
    total_length = mesh_count * (num_lengthwise * slab_width + num_widthwise * slab_length)

    total_mass = total_length * weight_per_meter
    slab_area = slab_length * slab_width

    return {
        "total_length": round(total_length, 2),
        "total_mass": round(total_mass, 2),
        "rebar_diameter": selected_diam,
        "weight_per_meter": weight_per_meter,
        "rebar_spacing": rebar_spacing,
        "num_lengthwise": num_lengthwise,
        "num_widthwise": num_widthwise,
        "slab_area": round(slab_area, 2),
        "mass_per_m2": round(total_mass / slab_area, 2),
        "double_mesh": double_mesh,
        "standards": "СП 63.13330.2018"
    }

# ========================================
# 3. КАЛЬКУЛЯТОР ОПАЛУБКИ
# ========================================

def calculate_formwork(
    length: float,
    width: float,
    height: float,
    formwork_type: str = "plywood"
) -> Dict:
    """Расчёт опалубки"""
    if length <= 0 or width <= 0 or height <= 0:
        return {"error": "Размеры должны быть положительными"}

    side_area = 2 * (length + width) * height
    bottom_area = length * width
    total_area = side_area + bottom_area

    formwork_materials = {
        "plywood": {"name": "Фанера", "reuse": 5, "cost_per_m2": 450},
        "boards": {"name": "Доски", "reuse": 3, "cost_per_m2": 300},
        "metal": {"name": "Металлическая", "reuse": 100, "cost_per_m2": 1500}
    }

    material = formwork_materials.get(formwork_type, formwork_materials["plywood"])
    cost = (total_area * material["cost_per_m2"]) / material["reuse"]

    return {
        "total_area": round(total_area, 2),
        "side_area": round(side_area, 2),
        "bottom_area": round(bottom_area, 2),
        "formwork_type": material["name"],
        "reuse_count": material["reuse"],
        "cost": round(cost, 2),
        "cost_per_m2": round(cost / total_area, 2)
    }

# ========================================
# 4. КАЛЬКУЛЯТОР ЭЛЕКТРОСНАБЖЕНИЯ
# ========================================

def calculate_electrical(
    total_power: float,
    voltage: int = 220,
    cable_length: float = 50,
    cable_type: str = "copper"
) -> Dict:
    """Расчёт электроснабжения"""
    if total_power <= 0 or cable_length <= 0:
        return {"error": "Мощность и длина кабеля должны быть положительными"}

    current = total_power / voltage

    if cable_type == "copper":
        cross_section = current / 8
    else:
        cross_section = current / 6

    standard_sections = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120]
    selected_section = min([s for s in standard_sections if s >= cross_section], default=120)

    voltage_drop = (2 * current * cable_length * 0.0175) / selected_section
    voltage_drop_percent = (voltage_drop / voltage) * 100

    return {
        "total_power": total_power,
        "current": round(current, 2),
        "cable_type": cable_type,
        "cross_section": selected_section,
        "cable_length": cable_length,
        "voltage_drop": round(voltage_drop, 2),
        "voltage_drop_percent": round(voltage_drop_percent, 2),
        "recommended_breaker": int(current * 1.25)
    }

# ========================================
# 5. КАЛЬКУЛЯТОР ВОДОСНАБЖЕНИЯ
# ========================================

def calculate_water(
    num_residents: int,
    fixtures_count: int = 5,
    pipe_length: float = 30
) -> Dict:
    """Расчёт водоснабжения"""
    if num_residents <= 0:
        return {"error": "Количество жильцов должно быть положительным"}

    daily_consumption_per_person = 200
    total_daily = num_residents * daily_consumption_per_person
    peak_hourly = total_daily * 0.15
    flow_rate = peak_hourly / 3600

    velocity = 1.2
    diameter = math.sqrt((4 * flow_rate) / (math.pi * velocity * 1000)) * 1000

    standard_diameters = [15, 20, 25, 32, 40, 50]
    selected_diameter = min([d for d in standard_diameters if d >= diameter], default=50)

    return {
        "num_residents": num_residents,
        "daily_consumption": round(total_daily, 0),
        "peak_hourly": round(peak_hourly, 2),
        "flow_rate": round(flow_rate, 3),
        "pipe_diameter": selected_diameter,
        "pipe_length": pipe_length,
        "fixtures_count": fixtures_count
    }

# ========================================
# 6. МАТЕМАТИЧЕСКИЙ КАЛЬКУЛЯТОР
# ========================================

def calculate_math_expression(expression: str) -> Dict:
    """Безопасный математический калькулятор"""
    try:
        allowed_chars = set('0123456789+-*/().^sqrt ')
        if not all(c in allowed_chars for c in expression.replace('sqrt', '').replace('^', '')):
            return {"error": "Недопустимые символы в выражении"}

        expr = expression.replace('^', '**').replace('sqrt', 'math.sqrt')
        result = eval(expr, {"__builtins__": {}}, {"math": math})

        return {
            "expression": expression,
            "result": round(result, 6)
        }
    except Exception as e:
        return {"error": f"Ошибка вычисления: {str(e)}"}

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
    temperature_inside: float = 20
) -> Dict:
    """Расчёт зимнего прогрева бетона"""
    if volume <= 0:
        return {"error": "Объём должен быть положительным"}

    temp_diff = temperature_inside - temperature_outside
    heating_power = volume * 0.5 * temp_diff
    heating_time = 3 if temperature_outside > -10 else 7

    return {
        "volume": round(volume, 3),
        "heating_power": round(heating_power, 2),
        "heating_time_days": heating_time,
        "temp_diff": round(temp_diff, 1)
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
        return (
            f"🔩 **РЕЗУЛЬТАТЫ РАСЧЁТА АРМАТУРЫ**\n\n"
            f"📏 Длина: **{format_number(result['total_length'])} м**\n"
            f"⚖️ Масса: **{format_number(result['total_mass'])} кг**\n\n"
            f"• Диаметр: {result['rebar_diameter']} мм\n"
            f"• Шаг: {result['rebar_spacing']} мм\n"
            f"• Сетка: {'двойная' if result['double_mesh'] else 'одинарная'}\n"
            f"• На м²: {format_number(result['mass_per_m2'])} кг/м²\n\n"
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
    'format_calculator_result', 'CALCULATORS', 'NORMATIVE_DOCUMENTS'
]
