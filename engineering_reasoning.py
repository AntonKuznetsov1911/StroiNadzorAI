"""
СтройНадзорAI - Engineering Reasoning Engine
=============================================
Инженерный расчётный движок

Функции:
- Модели строительных объектов (балка, колонна, плита)
- Расчётные алгоритмы по СП
- Автоматический вывод по нормам
- Проверка допустимости параметров
"""

import math
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# КОНСТАНТЫ И СПРАВОЧНИКИ
# ============================================================================

# Классы бетона по прочности (СП 63.13330.2018)
CONCRETE_CLASSES = {
    "B7.5": {"Rb": 4.5, "Rbt": 0.55, "Eb": 16000},
    "B10": {"Rb": 6.0, "Rbt": 0.70, "Eb": 18000},
    "B12.5": {"Rb": 7.5, "Rbt": 0.85, "Eb": 19500},
    "B15": {"Rb": 8.5, "Rbt": 0.95, "Eb": 24000},
    "B20": {"Rb": 11.5, "Rbt": 1.10, "Eb": 27500},
    "B25": {"Rb": 14.5, "Rbt": 1.25, "Eb": 30000},
    "B30": {"Rb": 17.0, "Rbt": 1.40, "Eb": 32500},
    "B35": {"Rb": 19.5, "Rbt": 1.50, "Eb": 34500},
    "B40": {"Rb": 22.0, "Rbt": 1.60, "Eb": 36000},
    "B45": {"Rb": 25.0, "Rbt": 1.70, "Eb": 37500},
    "B50": {"Rb": 27.5, "Rbt": 1.80, "Eb": 39000},
}

# Классы арматуры (СП 63.13330.2018)
REBAR_CLASSES = {
    "A240": {"Rs": 215, "Rsc": 215, "Es": 200000},
    "A400": {"Rs": 355, "Rsc": 355, "Es": 200000},
    "A500": {"Rs": 435, "Rsc": 435, "Es": 200000},
    "A600": {"Rs": 520, "Rsc": 520, "Es": 200000},
    "A800": {"Rs": 695, "Rsc": 695, "Es": 200000},
}

# Диаметры арматуры (мм) и площади сечения (мм²)
REBAR_DIAMETERS = {
    6: 28.3,
    8: 50.3,
    10: 78.5,
    12: 113.1,
    14: 153.9,
    16: 201.1,
    18: 254.5,
    20: 314.2,
    22: 380.1,
    25: 490.9,
    28: 615.8,
    32: 804.2,
    36: 1017.9,
    40: 1256.6,
}

# Минимальный защитный слой бетона (СП 63.13330.2018, таблица 10.1)
MIN_COVER = {
    "interior_dry": 15,        # Внутри помещений, сухо
    "interior_wet": 20,        # Внутри помещений, влажно
    "exterior": 25,            # Снаружи
    "ground_contact": 40,      # Контакт с грунтом
    "aggressive": 50,          # Агрессивная среда
}


# ============================================================================
# МОДЕЛИ ДАННЫХ
# ============================================================================

class ElementType(Enum):
    """Типы конструктивных элементов"""
    BEAM = "beam"              # Балка
    COLUMN = "column"          # Колонна
    SLAB = "slab"              # Плита
    FOUNDATION = "foundation"  # Фундамент
    WALL = "wall"              # Стена


@dataclass
class Material:
    """Материал"""
    name: str
    grade: str
    properties: Dict[str, float]


@dataclass
class Section:
    """Сечение элемента"""
    width: float      # мм
    height: float     # мм
    area: float = 0   # мм² (вычисляется)

    def __post_init__(self):
        if self.area == 0:
            self.area = self.width * self.height


@dataclass
class Reinforcement:
    """Армирование"""
    diameter: int           # мм
    count: int              # количество стержней
    area_total: float = 0   # общая площадь, мм²
    rebar_class: str = "A500"

    def __post_init__(self):
        if self.area_total == 0 and self.diameter in REBAR_DIAMETERS:
            self.area_total = REBAR_DIAMETERS[self.diameter] * self.count


@dataclass
class Load:
    """Нагрузка"""
    value: float           # кН или кН/м
    load_type: str         # distributed, concentrated, moment
    is_design: bool = True # расчётная или нормативная


@dataclass
class CalculationResult:
    """Результат расчёта"""
    success: bool
    element_type: str
    input_params: Dict
    calculated_values: Dict
    checks: List[Dict]      # Проверки с результатами
    conclusion: str
    normative_refs: List[str]
    warnings: List[str]
    recommendations: List[str]


# ============================================================================
# РАСЧЁТНЫЕ АЛГОРИТМЫ
# ============================================================================

class BeamCalculator:
    """Расчёт железобетонной балки по СП 63.13330.2018"""

    @staticmethod
    def calculate_moment_capacity(
        b: float,           # ширина сечения, мм
        h: float,           # высота сечения, мм
        a: float,           # защитный слой, мм
        As: float,          # площадь арматуры, мм²
        concrete_class: str,
        rebar_class: str
    ) -> Dict:
        """
        Расчёт несущей способности по изгибающему моменту

        Returns:
            Dict с результатами расчёта
        """
        # Получаем характеристики материалов
        if concrete_class not in CONCRETE_CLASSES:
            return {"error": f"Неизвестный класс бетона: {concrete_class}"}
        if rebar_class not in REBAR_CLASSES:
            return {"error": f"Неизвестный класс арматуры: {rebar_class}"}

        Rb = CONCRETE_CLASSES[concrete_class]["Rb"]  # МПа
        Rs = REBAR_CLASSES[rebar_class]["Rs"]        # МПа

        # Рабочая высота сечения
        h0 = h - a

        # Граничная относительная высота сжатой зоны (для A500)
        xi_R = 0.493  # СП 63.13330.2018, табл. 6.1

        # Высота сжатой зоны
        x = Rs * As / (Rb * b)

        # Относительная высота сжатой зоны
        xi = x / h0

        # Проверка условия xi <= xi_R
        if xi > xi_R:
            warning = f"⚠️ xi = {xi:.3f} > xi_R = {xi_R:.3f}. Требуется увеличить сечение или добавить сжатую арматуру."
        else:
            warning = None

        # Несущая способность по моменту (кН·м)
        M_Rd = Rs * As * (h0 - 0.5 * x) / 1e6

        return {
            "Rb": Rb,
            "Rs": Rs,
            "h0": h0,
            "x": round(x, 1),
            "xi": round(xi, 4),
            "xi_R": xi_R,
            "xi_check": "OK" if xi <= xi_R else "FAIL",
            "M_Rd": round(M_Rd, 2),
            "M_Rd_unit": "кН·м",
            "warning": warning,
            "norm_ref": "СП 63.13330.2018, п. 8.1.8-8.1.14"
        }

    @staticmethod
    def calculate_required_reinforcement(
        M_Ed: float,        # расчётный момент, кН·м
        b: float,           # ширина сечения, мм
        h: float,           # высота сечения, мм
        a: float,           # защитный слой, мм
        concrete_class: str,
        rebar_class: str
    ) -> Dict:
        """
        Подбор арматуры по заданному моменту

        Returns:
            Dict с требуемой площадью арматуры
        """
        if concrete_class not in CONCRETE_CLASSES:
            return {"error": f"Неизвестный класс бетона: {concrete_class}"}
        if rebar_class not in REBAR_CLASSES:
            return {"error": f"Неизвестный класс арматуры: {rebar_class}"}

        Rb = CONCRETE_CLASSES[concrete_class]["Rb"]
        Rs = REBAR_CLASSES[rebar_class]["Rs"]

        h0 = h - a
        M_Ed_Nmm = M_Ed * 1e6  # перевод в Н·мм

        # Коэффициент αm
        alpha_m = M_Ed_Nmm / (Rb * b * h0 ** 2)

        # Граничное значение αm,R для xi_R = 0.493
        alpha_m_R = 0.390

        if alpha_m > alpha_m_R:
            return {
                "error": "Сечение недостаточно. Увеличьте размеры или добавьте сжатую арматуру.",
                "alpha_m": round(alpha_m, 4),
                "alpha_m_R": alpha_m_R
            }

        # Коэффициент η
        eta = 1 - math.sqrt(1 - 2 * alpha_m)

        # Требуемая площадь арматуры
        As_req = alpha_m * Rb * b * h0 / (Rs * (1 - 0.5 * eta))

        # Минимальный процент армирования (0.1%)
        As_min = 0.001 * b * h0

        As_final = max(As_req, As_min)

        # Подбор стержней
        rebar_options = []
        for d, area in REBAR_DIAMETERS.items():
            if d >= 10:  # минимум 10 мм для рабочей арматуры
                count = math.ceil(As_final / area)
                if count >= 2:  # минимум 2 стержня
                    rebar_options.append({
                        "diameter": d,
                        "count": count,
                        "area_provided": round(area * count, 1),
                        "margin": round((area * count - As_final) / As_final * 100, 1)
                    })

        # Берём оптимальный вариант (минимальный запас >= 0)
        optimal = min([r for r in rebar_options if r["margin"] >= 0],
                      key=lambda x: x["margin"], default=None)

        return {
            "M_Ed": M_Ed,
            "alpha_m": round(alpha_m, 4),
            "eta": round(eta, 4),
            "As_req": round(As_req, 1),
            "As_min": round(As_min, 1),
            "As_final": round(As_final, 1),
            "As_unit": "мм²",
            "optimal_rebar": optimal,
            "all_options": rebar_options[:5],  # топ-5 вариантов
            "norm_ref": "СП 63.13330.2018, п. 8.1.8-8.1.14"
        }


class ColumnCalculator:
    """Расчёт железобетонной колонны по СП 63.13330.2018"""

    @staticmethod
    def calculate_capacity(
        b: float,           # сторона сечения, мм
        h: float,           # другая сторона, мм
        As_total: float,    # общая площадь арматуры, мм²
        concrete_class: str,
        rebar_class: str,
        l0: float,          # расчётная длина, мм
    ) -> Dict:
        """
        Расчёт несущей способности колонны при центральном сжатии

        Returns:
            Dict с результатами
        """
        if concrete_class not in CONCRETE_CLASSES:
            return {"error": f"Неизвестный класс бетона: {concrete_class}"}

        Rb = CONCRETE_CLASSES[concrete_class]["Rb"]
        Rs = REBAR_CLASSES.get(rebar_class, REBAR_CLASSES["A500"])["Rs"]

        # Площадь бетона
        A = b * h
        Ab = A - As_total

        # Гибкость колонны
        i = min(b, h) / math.sqrt(12)  # радиус инерции
        lambda_h = l0 / i

        # Коэффициент продольного изгиба (упрощённо)
        if lambda_h <= 14:
            phi = 1.0
        elif lambda_h <= 28:
            phi = 1.028 - 0.002 * lambda_h
        else:
            phi = 1.14 - 0.006 * lambda_h

        phi = max(phi, 0.4)

        # Несущая способность
        N_Rd = phi * (Rb * Ab + Rs * As_total) / 1000  # кН

        return {
            "A": A,
            "Ab": round(Ab, 1),
            "lambda": round(lambda_h, 1),
            "phi": round(phi, 3),
            "N_Rd": round(N_Rd, 1),
            "N_Rd_unit": "кН",
            "norm_ref": "СП 63.13330.2018, п. 8.1.16-8.1.20"
        }


class SlabCalculator:
    """Расчёт железобетонной плиты"""

    @staticmethod
    def calculate_thickness(
        span: float,        # пролёт, м
        load: float,        # нагрузка, кН/м²
        support_type: str   # "simple", "continuous", "cantilever"
    ) -> Dict:
        """
        Ориентировочный расчёт толщины плиты

        Returns:
            Dict с рекомендуемой толщиной
        """
        # Коэффициенты по типу опирания
        coefficients = {
            "simple": 1/30,       # шарнирное
            "continuous": 1/35,   # неразрезная
            "cantilever": 1/12,   # консоль
        }

        k = coefficients.get(support_type, 1/30)
        span_mm = span * 1000

        # Минимальная толщина по прогибам
        h_min_deflection = span_mm * k

        # Минимальная толщина по конструктивным требованиям
        h_min_constructive = 60  # мм

        h_recommended = max(h_min_deflection, h_min_constructive)

        # Округляем до 10 мм
        h_final = math.ceil(h_recommended / 10) * 10

        return {
            "span": span,
            "support_type": support_type,
            "h_min_deflection": round(h_min_deflection, 1),
            "h_min_constructive": h_min_constructive,
            "h_recommended": round(h_final, 0),
            "h_unit": "мм",
            "norm_ref": "СП 63.13330.2018, п. 8.2"
        }


# ============================================================================
# ОСНОВНОЙ ДВИЖОК
# ============================================================================

class EngineeringReasoningEngine:
    """Основной инженерный расчётный движок"""

    def __init__(self):
        self.beam_calc = BeamCalculator()
        self.column_calc = ColumnCalculator()
        self.slab_calc = SlabCalculator()

    def analyze_request(self, text: str) -> Optional[Dict]:
        """
        Анализ запроса и определение типа расчёта

        Returns:
            Dict с извлечёнными параметрами или None
        """
        import re

        params = {}

        # Извлечение размеров
        size_pattern = r"(\d+)\s*[xх×]\s*(\d+)\s*(мм|см|м)?"
        size_match = re.search(size_pattern, text)
        if size_match:
            w, h = int(size_match.group(1)), int(size_match.group(2))
            unit = size_match.group(3) or "мм"
            if unit == "см":
                w, h = w * 10, h * 10
            elif unit == "м":
                w, h = w * 1000, h * 1000
            params["width"] = w
            params["height"] = h

        # Извлечение класса бетона
        concrete_pattern = r"[BВ]\s*(\d+(?:\.\d+)?)"
        concrete_match = re.search(concrete_pattern, text, re.IGNORECASE)
        if concrete_match:
            params["concrete_class"] = f"B{concrete_match.group(1)}"

        # Извлечение класса арматуры
        rebar_pattern = r"[AА]\s*(\d+)"
        rebar_match = re.search(rebar_pattern, text, re.IGNORECASE)
        if rebar_match:
            params["rebar_class"] = f"A{rebar_match.group(1)}"

        # Извлечение диаметра арматуры
        diameter_pattern = r"[⌀∅dд]\s*(\d+)\s*мм?"
        diameter_match = re.search(diameter_pattern, text)
        if diameter_match:
            params["rebar_diameter"] = int(diameter_match.group(1))

        # Извлечение момента
        moment_pattern = r"[MМ]\s*[=:]\s*(\d+(?:\.\d+)?)\s*(кН[·\*]?м|тс[·\*]?м)?"
        moment_match = re.search(moment_pattern, text)
        if moment_match:
            params["moment"] = float(moment_match.group(1))

        # Извлечение нагрузки
        load_pattern = r"[qQ]\s*[=:]\s*(\d+(?:\.\d+)?)\s*(кН\/м|т\/м)?"
        load_match = re.search(load_pattern, text)
        if load_match:
            params["load"] = float(load_match.group(1))

        # Извлечение пролёта
        span_pattern = r"пролёт\w*\s*[=:]*\s*(\d+(?:\.\d+)?)\s*(м|мм|см)?"
        span_match = re.search(span_pattern, text, re.IGNORECASE)
        if span_match:
            span_val = float(span_match.group(1))
            unit = span_match.group(2) or "м"
            if unit == "мм":
                span_val /= 1000
            elif unit == "см":
                span_val /= 100
            params["span"] = span_val

        return params if params else None

    def perform_beam_calculation(
        self,
        width: float,
        height: float,
        cover: float = 35,
        concrete_class: str = "B25",
        rebar_class: str = "A500",
        moment: float = None,
        rebar_area: float = None
    ) -> CalculationResult:
        """
        Расчёт балки

        Args:
            width: ширина, мм
            height: высота, мм
            cover: защитный слой, мм
            concrete_class: класс бетона
            rebar_class: класс арматуры
            moment: расчётный момент, кН·м (если задан - подбор арматуры)
            rebar_area: площадь арматуры, мм² (если задана - проверка несущей способности)
        """
        checks = []
        warnings = []
        recommendations = []

        input_params = {
            "b": width,
            "h": height,
            "a": cover,
            "concrete": concrete_class,
            "rebar": rebar_class
        }

        if moment is not None:
            # Подбор арматуры
            input_params["M_Ed"] = moment
            result = self.beam_calc.calculate_required_reinforcement(
                M_Ed=moment,
                b=width,
                h=height,
                a=cover,
                concrete_class=concrete_class,
                rebar_class=rebar_class
            )

            if "error" in result:
                return CalculationResult(
                    success=False,
                    element_type="beam",
                    input_params=input_params,
                    calculated_values=result,
                    checks=[],
                    conclusion=f"❌ Ошибка: {result['error']}",
                    normative_refs=["СП 63.13330.2018"],
                    warnings=[result["error"]],
                    recommendations=["Увеличьте размеры сечения"]
                )

            # Формируем вывод
            optimal = result.get("optimal_rebar")
            if optimal:
                conclusion = (
                    f"✅ Требуемая арматура: **{optimal['count']}⌀{optimal['diameter']}** "
                    f"(As = {optimal['area_provided']} мм², запас {optimal['margin']}%)"
                )
            else:
                conclusion = f"✅ Требуемая площадь арматуры: **{result['As_final']} мм²**"

            return CalculationResult(
                success=True,
                element_type="beam",
                input_params=input_params,
                calculated_values=result,
                checks=[{"name": "Подбор арматуры", "status": "OK"}],
                conclusion=conclusion,
                normative_refs=[result.get("norm_ref", "СП 63.13330.2018")],
                warnings=warnings,
                recommendations=recommendations
            )

        elif rebar_area is not None:
            # Проверка несущей способности
            input_params["As"] = rebar_area
            result = self.beam_calc.calculate_moment_capacity(
                b=width,
                h=height,
                a=cover,
                As=rebar_area,
                concrete_class=concrete_class,
                rebar_class=rebar_class
            )

            if "error" in result:
                return CalculationResult(
                    success=False,
                    element_type="beam",
                    input_params=input_params,
                    calculated_values=result,
                    checks=[],
                    conclusion=f"❌ Ошибка: {result['error']}",
                    normative_refs=["СП 63.13330.2018"],
                    warnings=[],
                    recommendations=[]
                )

            checks.append({
                "name": "Условие xi ≤ xi_R",
                "status": result["xi_check"],
                "xi": result["xi"],
                "xi_R": result["xi_R"]
            })

            if result.get("warning"):
                warnings.append(result["warning"])

            conclusion = f"✅ Несущая способность: **M_Rd = {result['M_Rd']} кН·м**"

            return CalculationResult(
                success=True,
                element_type="beam",
                input_params=input_params,
                calculated_values=result,
                checks=checks,
                conclusion=conclusion,
                normative_refs=[result.get("norm_ref", "СП 63.13330.2018")],
                warnings=warnings,
                recommendations=recommendations
            )

        else:
            return CalculationResult(
                success=False,
                element_type="beam",
                input_params=input_params,
                calculated_values={},
                checks=[],
                conclusion="❌ Укажите момент (M) для подбора арматуры или площадь арматуры (As) для проверки",
                normative_refs=["СП 63.13330.2018"],
                warnings=[],
                recommendations=[]
            )

    def format_result(self, result: CalculationResult) -> str:
        """Форматирование результата для Telegram"""
        lines = []

        lines.append(f"🔧 **РАСЧЁТ: {result.element_type.upper()}**\n")

        # Входные данные
        lines.append("📥 **Исходные данные:**")
        for key, value in result.input_params.items():
            lines.append(f"• {key}: {value}")

        lines.append("")

        # Расчётные значения
        if result.calculated_values:
            lines.append("📊 **Расчёт:**")
            for key, value in result.calculated_values.items():
                if key not in ["error", "warning", "norm_ref", "all_options", "optimal_rebar"]:
                    lines.append(f"• {key} = {value}")

        lines.append("")

        # Проверки
        if result.checks:
            lines.append("✔️ **Проверки:**")
            for check in result.checks:
                status_icon = "✅" if check["status"] == "OK" else "❌"
                lines.append(f"{status_icon} {check['name']}")

        lines.append("")

        # Вывод
        lines.append(f"📌 **ВЫВОД:**\n{result.conclusion}")

        # Предупреждения
        if result.warnings:
            lines.append("\n⚠️ **Предупреждения:**")
            for w in result.warnings:
                lines.append(f"• {w}")

        # Нормативы
        if result.normative_refs:
            lines.append(f"\n📚 _{', '.join(result.normative_refs)}_")

        return "\n".join(lines)


# ============================================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ============================================================================

_engine: Optional[EngineeringReasoningEngine] = None


def get_engineering_engine() -> EngineeringReasoningEngine:
    """Получение глобального движка"""
    global _engine
    if _engine is None:
        _engine = EngineeringReasoningEngine()
    return _engine


# ============================================================================
# API
# ============================================================================

def calculate_beam(
    width: float,
    height: float,
    concrete_class: str = "B25",
    rebar_class: str = "A500",
    moment: float = None,
    rebar_area: float = None
) -> CalculationResult:
    """API для расчёта балки"""
    engine = get_engineering_engine()
    return engine.perform_beam_calculation(
        width=width,
        height=height,
        concrete_class=concrete_class,
        rebar_class=rebar_class,
        moment=moment,
        rebar_area=rebar_area
    )


def analyze_engineering_request(text: str) -> Optional[Dict]:
    """API для анализа запроса"""
    engine = get_engineering_engine()
    return engine.analyze_request(text)


def get_concrete_properties(concrete_class: str) -> Optional[Dict]:
    """Получение свойств бетона"""
    return CONCRETE_CLASSES.get(concrete_class)


def get_rebar_area(diameter: int, count: int = 1) -> float:
    """Получение площади арматуры"""
    return REBAR_DIAMETERS.get(diameter, 0) * count
