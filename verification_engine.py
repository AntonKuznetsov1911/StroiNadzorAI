"""
СтройНадзорAI - Verification Engine
====================================
Система верификации ответов и защиты от галлюцинаций

Компоненты:
- NormativeVerifier: проверка наличия нормативного обоснования
- NumberVerifier: проверка корректности чисел и расчётов
- LogicVerifier: проверка логической непротиворечивости
- ResponseFilter: фильтрация и блокировка некорректных ответов
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

VERIFICATION_CONFIG = {
    "require_normative": True,           # Требовать норматив в ответе
    "min_norm_relevance": 0.7,           # Минимальная релевантность норматива
    "block_without_norm": False,         # Блокировать ответ без норматива (soft mode)
    "check_numbers": True,               # Проверять числа
    "check_logic": True,                 # Проверять логику
    "max_uncertainty_phrases": 2,        # Максимум фраз неуверенности
}

# Паттерны нормативных ссылок
NORM_PATTERNS = [
    r"СП\s*\d+\.\d+\.\d+",
    r"ГОСТ\s*[\d\.\-Р]+",
    r"СНиП\s*[\d\.\-]+",
    r"ФЗ[\-\s]*\d+",
    r"ПУЭ",
    r"СанПиН\s*[\d\.]+",
    r"ТР\s*ТС\s*\d+",
    r"п\.\s*\d+\.\d+",
    r"пункт\s*\d+\.\d+",
    r"раздел\s*\d+",
    r"статья\s*\d+",
]

# Фразы неуверенности (галлюцинации)
UNCERTAINTY_PHRASES = [
    "возможно",
    "вероятно",
    "может быть",
    "скорее всего",
    "примерно",
    "около",
    "приблизительно",
    "я думаю",
    "мне кажется",
    "насколько я знаю",
    "если не ошибаюсь",
    "не уверен",
    "точно не знаю",
]

# Опасные фразы (выдумывание норм)
DANGEROUS_PHRASES = [
    r"согласно\s+СП\s*\d{3,}",  # Несуществующие СП с длинными номерами
    r"ГОСТ\s*\d{7,}",           # Несуществующие ГОСТ
    r"по\s+нормам\s+\d{4}",     # Выдуманные нормы
]


# ============================================================================
# МОДЕЛИ ДАННЫХ
# ============================================================================

class VerificationLevel(Enum):
    """Уровень верификации"""
    PASSED = "passed"           # Проверка пройдена
    WARNING = "warning"         # Есть замечания
    FAILED = "failed"           # Проверка не пройдена
    BLOCKED = "blocked"         # Ответ заблокирован


class RiskLevel(Enum):
    """Уровень риска"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class VerificationResult:
    """Результат верификации"""
    level: VerificationLevel
    risk_level: RiskLevel
    has_normative: bool
    normative_refs: List[str]
    warnings: List[str]
    errors: List[str]
    suggestions: List[str]
    confidence_score: float      # 0-1, насколько уверены в ответе
    modified_response: Optional[str]  # Модифицированный ответ (с предупреждениями)


# ============================================================================
# NORMATIVE VERIFIER
# ============================================================================

class NormativeVerifier:
    """Проверка наличия нормативного обоснования"""

    @staticmethod
    def extract_norm_references(text: str) -> List[str]:
        """Извлечение ссылок на нормативы из текста"""
        references = []

        for pattern in NORM_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            references.extend(matches)

        # Убираем дубликаты, сохраняя порядок
        seen = set()
        unique_refs = []
        for ref in references:
            ref_normalized = ref.upper().strip()
            if ref_normalized not in seen:
                seen.add(ref_normalized)
                unique_refs.append(ref)

        return unique_refs

    @staticmethod
    def has_normative_basis(text: str) -> Tuple[bool, List[str]]:
        """
        Проверка наличия нормативного обоснования

        Returns:
            (has_norm, list_of_references)
        """
        refs = NormativeVerifier.extract_norm_references(text)
        return len(refs) > 0, refs

    @staticmethod
    def check_fake_norms(text: str) -> List[str]:
        """Проверка на выдуманные нормативы"""
        warnings = []

        for pattern in DANGEROUS_PHRASES:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                warnings.append(f"Подозрительная ссылка на норматив: {matches}")

        return warnings

    @staticmethod
    async def verify_norm_exists(norm_code: str) -> bool:
        """
        Проверка существования норматива в базе

        TODO: Интеграция с RAG для проверки
        """
        # Базовая проверка формата
        valid_patterns = [
            r"^СП\s*\d+\.\d+\.\d+",
            r"^ГОСТ\s*[\d\.\-Р]+",
            r"^СНиП\s*[\d\.\-]+",
            r"^ФЗ[\-\s]*\d+",
        ]

        for pattern in valid_patterns:
            if re.match(pattern, norm_code, re.IGNORECASE):
                return True

        return False


# ============================================================================
# NUMBER VERIFIER
# ============================================================================

class NumberVerifier:
    """Проверка корректности чисел и расчётов"""

    # Типичные диапазоны значений в строительстве
    TYPICAL_RANGES = {
        "бетон_класс": (7.5, 60),           # B7.5 - B60
        "арматура_диаметр_мм": (6, 40),     # 6-40 мм
        "защитный_слой_мм": (10, 70),       # 10-70 мм
        "температура_бетонирования": (-30, 40),  # -30 до +40°C
        "прочность_МПа": (0.1, 500),        # 0.1 - 500 МПа
        "нагрузка_кН": (0.1, 10000),        # 0.1 - 10000 кН
        "пролёт_м": (0.5, 100),             # 0.5 - 100 м
        "толщина_стены_мм": (50, 1000),     # 50 - 1000 мм
        "высота_этажа_м": (2.5, 6),         # 2.5 - 6 м
    }

    @staticmethod
    def extract_numbers_with_units(text: str) -> List[Dict]:
        """Извлечение чисел с единицами измерения"""
        patterns = [
            (r"(\d+(?:[,\.]\d+)?)\s*(мм|см|м|км)", "length"),
            (r"(\d+(?:[,\.]\d+)?)\s*(кг|т|г)", "weight"),
            (r"(\d+(?:[,\.]\d+)?)\s*(МПа|кПа|Па)", "pressure"),
            (r"(\d+(?:[,\.]\d+)?)\s*(кН|Н|МН)", "force"),
            (r"(\d+(?:[,\.]\d+)?)\s*(°C|градус)", "temperature"),
            (r"B(\d+(?:[,\.]\d+)?)", "concrete_class"),
            (r"[AА](\d+)", "rebar_class"),
        ]

        numbers = []
        for pattern, num_type in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                value = float(match[0].replace(",", ".")) if isinstance(match, tuple) else float(match.replace(",", "."))
                unit = match[1] if isinstance(match, tuple) and len(match) > 1 else ""
                numbers.append({
                    "value": value,
                    "unit": unit,
                    "type": num_type
                })

        return numbers

    @staticmethod
    def check_realistic_values(text: str) -> List[str]:
        """Проверка реалистичности значений"""
        warnings = []

        numbers = NumberVerifier.extract_numbers_with_units(text)

        for num in numbers:
            # Проверка на нереалистичные значения
            if num["type"] == "concrete_class":
                if num["value"] < 7.5 or num["value"] > 100:
                    warnings.append(f"Нереалистичный класс бетона: B{num['value']}")

            elif num["type"] == "pressure" and "МПа" in num["unit"]:
                if num["value"] > 1000:
                    warnings.append(f"Подозрительно высокое давление: {num['value']} МПа")

            elif num["type"] == "length" and num["unit"] == "м":
                if num["value"] > 1000:
                    warnings.append(f"Проверьте размер: {num['value']} м")

        return warnings


# ============================================================================
# LOGIC VERIFIER
# ============================================================================

class LogicVerifier:
    """Проверка логической непротиворечивости"""

    @staticmethod
    def count_uncertainty_phrases(text: str) -> int:
        """Подсчёт фраз неуверенности"""
        count = 0
        text_lower = text.lower()

        for phrase in UNCERTAINTY_PHRASES:
            count += text_lower.count(phrase)

        return count

    @staticmethod
    def check_contradictions(text: str) -> List[str]:
        """Проверка на противоречия в тексте"""
        warnings = []

        # Паттерны противоречий
        contradiction_patterns = [
            (r"не\s+требуется.*требуется", "Противоречие: требуется/не требуется"),
            (r"запрещено.*разрешено", "Противоречие: запрещено/разрешено"),
            (r"допускается.*не\s+допускается", "Противоречие: допускается/не допускается"),
        ]

        for pattern, warning in contradiction_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                warnings.append(warning)

        return warnings

    @staticmethod
    def check_completeness(text: str, question_type: str = None) -> List[str]:
        """Проверка полноты ответа"""
        suggestions = []

        # Минимальная длина осмысленного ответа
        if len(text.strip()) < 50:
            suggestions.append("Ответ слишком краткий, возможно неполный")

        # Проверка наличия ключевых элементов для разных типов вопросов
        if question_type == "calculation":
            if not re.search(r"=|формула|расчёт", text, re.IGNORECASE):
                suggestions.append("В расчётном вопросе отсутствует формула или расчёт")

        if question_type == "normative":
            if not NormativeVerifier.has_normative_basis(text)[0]:
                suggestions.append("В нормативном вопросе отсутствует ссылка на документ")

        return suggestions


# ============================================================================
# MAIN VERIFICATION ENGINE
# ============================================================================

class VerificationEngine:
    """Основной движок верификации ответов"""

    def __init__(self, config: Dict = None):
        self.config = {**VERIFICATION_CONFIG, **(config or {})}

    def verify_response(
        self,
        response: str,
        question: str = None,
        question_type: str = None
    ) -> VerificationResult:
        """
        Полная верификация ответа

        Args:
            response: Текст ответа для проверки
            question: Исходный вопрос (опционально)
            question_type: Тип вопроса (normative, calculation, inspection, etc.)

        Returns:
            VerificationResult с результатами проверки
        """
        warnings = []
        errors = []
        suggestions = []

        # 1. Проверка нормативного обоснования
        has_norm, norm_refs = NormativeVerifier.has_normative_basis(response)

        if self.config["require_normative"] and not has_norm:
            if self.config["block_without_norm"]:
                errors.append("Ответ не содержит нормативного обоснования")
            else:
                warnings.append("Рекомендуется добавить ссылку на норматив")

        # Проверка на выдуманные нормы
        fake_norm_warnings = NormativeVerifier.check_fake_norms(response)
        warnings.extend(fake_norm_warnings)

        # 2. Проверка чисел (если включена)
        if self.config["check_numbers"]:
            number_warnings = NumberVerifier.check_realistic_values(response)
            warnings.extend(number_warnings)

        # 3. Проверка логики (если включена)
        if self.config["check_logic"]:
            # Фразы неуверенности
            uncertainty_count = LogicVerifier.count_uncertainty_phrases(response)
            if uncertainty_count > self.config["max_uncertainty_phrases"]:
                warnings.append(
                    f"Много фраз неуверенности ({uncertainty_count}). "
                    "Возможны неточности в ответе."
                )

            # Противоречия
            contradiction_warnings = LogicVerifier.check_contradictions(response)
            errors.extend(contradiction_warnings)

            # Полнота
            completeness_suggestions = LogicVerifier.check_completeness(response, question_type)
            suggestions.extend(completeness_suggestions)

        # Определяем уровень верификации
        level = self._determine_level(errors, warnings)

        # Определяем уровень риска
        risk_level = self._determine_risk(errors, warnings, has_norm, question_type)

        # Вычисляем confidence score
        confidence = self._calculate_confidence(
            has_norm, norm_refs, len(warnings), len(errors)
        )

        # Модифицируем ответ при необходимости
        modified_response = self._modify_response(response, warnings, errors, has_norm)

        return VerificationResult(
            level=level,
            risk_level=risk_level,
            has_normative=has_norm,
            normative_refs=norm_refs,
            warnings=warnings,
            errors=errors,
            suggestions=suggestions,
            confidence_score=confidence,
            modified_response=modified_response
        )

    def _determine_level(self, errors: List, warnings: List) -> VerificationLevel:
        """Определение уровня верификации"""
        if errors:
            if self.config["block_without_norm"]:
                return VerificationLevel.BLOCKED
            return VerificationLevel.FAILED

        if warnings:
            return VerificationLevel.WARNING

        return VerificationLevel.PASSED

    def _determine_risk(
        self,
        errors: List,
        warnings: List,
        has_norm: bool,
        question_type: str
    ) -> RiskLevel:
        """Определение уровня риска"""
        # Критический риск - ошибки + отсутствие норматива
        if errors and not has_norm:
            return RiskLevel.CRITICAL

        # Высокий риск - есть ошибки
        if errors:
            return RiskLevel.HIGH

        # Средний риск - много предупреждений или нет норматива
        if len(warnings) > 2 or (not has_norm and question_type == "normative"):
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    def _calculate_confidence(
        self,
        has_norm: bool,
        norm_refs: List,
        warning_count: int,
        error_count: int
    ) -> float:
        """Расчёт уровня уверенности (0-1)"""
        score = 1.0

        # Штраф за отсутствие норматива
        if not has_norm:
            score -= 0.3

        # Бонус за каждую ссылку на норматив
        score += min(len(norm_refs) * 0.1, 0.2)

        # Штраф за предупреждения
        score -= warning_count * 0.1

        # Большой штраф за ошибки
        score -= error_count * 0.25

        return max(0.0, min(1.0, score))

    def _modify_response(
        self,
        response: str,
        warnings: List,
        errors: List,
        has_norm: bool
    ) -> Optional[str]:
        """Модификация ответа с добавлением предупреждений"""
        if not warnings and not errors:
            return None

        modified = response

        # Добавляем disclaimer если нет норматива
        if not has_norm and self.config["require_normative"]:
            disclaimer = (
                "\n\n⚠️ **Внимание:** Ответ не содержит прямой ссылки на норматив. "
                "Рекомендуется проверить актуальные СП/ГОСТ перед применением."
            )
            modified += disclaimer

        # Добавляем предупреждения
        if warnings:
            warning_text = "\n\n⚠️ **Замечания:**\n• " + "\n• ".join(warnings)
            modified += warning_text

        return modified


# ============================================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ============================================================================

_verification_engine: Optional[VerificationEngine] = None


def get_verification_engine() -> VerificationEngine:
    """Получение глобального экземпляра движка верификации"""
    global _verification_engine

    if _verification_engine is None:
        _verification_engine = VerificationEngine()

    return _verification_engine


# ============================================================================
# INTEGRATION API
# ============================================================================

def verify_bot_response(
    response: str,
    question: str = None,
    question_type: str = None
) -> VerificationResult:
    """
    API для верификации ответа бота

    Args:
        response: Ответ бота
        question: Вопрос пользователя
        question_type: Тип вопроса

    Returns:
        VerificationResult
    """
    engine = get_verification_engine()
    return engine.verify_response(response, question, question_type)


def should_block_response(verification: VerificationResult) -> bool:
    """Проверка, нужно ли блокировать ответ"""
    return verification.level == VerificationLevel.BLOCKED


def get_safe_response(verification: VerificationResult, original: str) -> str:
    """
    Получение безопасного ответа

    Если есть модифицированный ответ с предупреждениями - возвращает его.
    Если ответ заблокирован - возвращает сообщение об ошибке.
    Иначе - возвращает оригинал.
    """
    if verification.level == VerificationLevel.BLOCKED:
        return (
            "⚠️ **Ответ заблокирован системой верификации**\n\n"
            "Причина: Не найдено нормативное подтверждение.\n\n"
            "Рекомендация: Уточните вопрос или проверьте актуальные СП/ГОСТ самостоятельно.\n\n"
            f"Ошибки:\n• " + "\n• ".join(verification.errors)
        )

    if verification.modified_response:
        return verification.modified_response

    return original


def format_verification_footer(verification: VerificationResult) -> str:
    """Форматирование footer'а с информацией о верификации"""
    if verification.level == VerificationLevel.PASSED:
        icon = "✅"
        status = "Проверено"
    elif verification.level == VerificationLevel.WARNING:
        icon = "⚠️"
        status = "Есть замечания"
    elif verification.level == VerificationLevel.FAILED:
        icon = "❌"
        status = "Требует проверки"
    else:
        icon = "🚫"
        status = "Заблокировано"

    norm_info = ""
    if verification.normative_refs:
        norm_info = f" | 📚 {', '.join(verification.normative_refs[:3])}"

    confidence = f" | 🎯 {verification.confidence_score:.0%}"

    return f"\n\n---\n{icon} _{status}{norm_info}{confidence}_"
