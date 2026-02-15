"""
СтройНадзорAI - Request Classifier
===================================
Классификация типов инженерных запросов

Типы запросов:
- normative: вопросы по нормативам СП/ГОСТ/СНиП
- calculation: расчётные задачи
- inspection: проверка/экспертиза объекта
- pto: вопросы ПТО (КС-2, КС-3, акты)
- dispute: спорные ситуации, претензии
- emergency: аварийные ситуации
- design: проектирование
- general: общие вопросы
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# ТИПЫ ЗАПРОСОВ
# ============================================================================

class RequestType(Enum):
    """Типы инженерных запросов"""
    NORMATIVE = "normative"      # Вопросы по нормативам
    CALCULATION = "calculation"  # Расчётные задачи
    INSPECTION = "inspection"    # Проверка/экспертиза
    PTO = "pto"                  # Вопросы ПТО
    DISPUTE = "dispute"          # Споры и претензии
    EMERGENCY = "emergency"      # Аварийные ситуации
    DESIGN = "design"            # Проектирование
    GENERAL = "general"          # Общие вопросы


@dataclass
class ClassificationResult:
    """Результат классификации"""
    request_type: RequestType
    confidence: float           # 0-1
    keywords_found: List[str]
    sub_category: Optional[str]
    requires_calculation: bool
    requires_normative: bool
    priority: str               # low, medium, high, critical


# ============================================================================
# КЛЮЧЕВЫЕ СЛОВА ПО КАТЕГОРИЯМ
# ============================================================================

KEYWORDS = {
    RequestType.NORMATIVE: {
        "keywords": [
            "СП", "ГОСТ", "СНиП", "ФЗ", "ПУЭ", "СанПиН", "норматив", "норма",
            "требование", "пункт", "раздел", "статья", "регламент", "стандарт",
            "по нормам", "согласно", "в соответствии", "допускается", "запрещается",
            "обязательно", "рекомендуется", "не допускается", "должен", "следует"
        ],
        "patterns": [
            r"СП\s*\d+",
            r"ГОСТ\s*\d+",
            r"СНиП\s*\d+",
            r"ФЗ[\-\s]*\d+",
            r"пункт\s*\d+",
            r"п\.\s*\d+",
        ],
        "weight": 1.0
    },

    RequestType.CALCULATION: {
        "keywords": [
            "расчёт", "рассчитать", "вычислить", "посчитать", "формула",
            "коэффициент", "нагрузка", "прочность", "несущая способность",
            "момент", "усилие", "напряжение", "деформация", "прогиб",
            "площадь", "объём", "масса", "вес", "диаметр", "толщина",
            "армирование", "сечение", "пролёт", "шаг", "количество",
            "сколько нужно", "какой размер", "минимальный", "максимальный"
        ],
        "patterns": [
            r"\d+\s*(мм|см|м|кг|т|МПа|кН|м²|м³)",
            r"B\d+",  # класс бетона
            r"A\d+",  # класс арматуры
            r"\d+[xх×]\d+",  # размеры
        ],
        "weight": 1.0
    },

    RequestType.INSPECTION: {
        "keywords": [
            "проверка", "проверить", "осмотр", "экспертиза", "обследование",
            "дефект", "трещина", "повреждение", "разрушение", "коррозия",
            "отклонение", "нарушение", "несоответствие", "брак", "качество",
            "контроль", "надзор", "технадзор", "стройконтроль", "приёмка",
            "акт", "заключение", "протокол", "испытание", "тест"
        ],
        "patterns": [
            r"(найден|обнаружен|выявлен)\w*\s+(дефект|трещин|повреждени)",
            r"как\s+проверить",
            r"что\s+делать\s+с",
        ],
        "weight": 1.0
    },

    RequestType.PTO: {
        "keywords": [
            "КС-2", "КС-3", "КС2", "КС3", "акт", "смета", "ППР", "ПОС",
            "исполнительная документация", "журнал работ", "общий журнал",
            "скрытые работы", "освидетельствование", "ИД", "РД",
            "форма", "бланк", "образец", "заполнение", "оформление"
        ],
        "patterns": [
            r"КС[\-\s]?\d",
            r"форма\s+\d+",
            r"как\s+заполнить",
            r"как\s+оформить",
        ],
        "weight": 1.0
    },

    RequestType.DISPUTE: {
        "keywords": [
            "спор", "претензия", "рекламация", "суд", "арбитраж",
            "ответственность", "штраф", "неустойка", "компенсация",
            "виновник", "виноват", "кто отвечает", "права", "обязанности",
            "договор", "контракт", "подрядчик", "заказчик", "застройщик"
        ],
        "patterns": [
            r"кто\s+(виноват|отвечает|несёт)",
            r"что\s+делать\s+если",
            r"как\s+(взыскать|предъявить|подать)",
        ],
        "weight": 1.0
    },

    RequestType.EMERGENCY: {
        "keywords": [
            "авария", "аварийный", "обрушение", "разрушение", "ЧП", "ЧС",
            "срочно", "немедленно", "опасность", "угроза", "риск жизни",
            "эвакуация", "обесточить", "остановить", "прекратить",
            "травма", "несчастный случай", "пострадавший"
        ],
        "patterns": [
            r"срочн|немедленн|аварий",
            r"что\s+делать\s+срочно",
            r"опасн|угроз",
        ],
        "weight": 1.5  # Повышенный приоритет
    },

    RequestType.DESIGN: {
        "keywords": [
            "проект", "проектирование", "чертёж", "схема", "план",
            "конструкция", "узел", "деталь", "спецификация",
            "разрез", "фасад", "планировка", "компоновка",
            "BIM", "ТИМ", "AutoCAD", "Revit", "модель"
        ],
        "patterns": [
            r"как\s+запроектировать",
            r"какую\s+конструкцию",
            r"узел\s+\w+",
        ],
        "weight": 0.9
    },
}


# ============================================================================
# ПОДКАТЕГОРИИ
# ============================================================================

SUBCATEGORIES = {
    RequestType.NORMATIVE: [
        ("concrete", ["бетон", "железобетон", "армирование", "защитный слой"]),
        ("steel", ["металл", "сталь", "сварка", "болт"]),
        ("fire", ["пожар", "огнестойкость", "эвакуация", "СОУЭ"]),
        ("foundation", ["фундамент", "основание", "грунт", "свая"]),
        ("insulation", ["утепление", "теплоизоляция", "энергоэффективность"]),
    ],
    RequestType.CALCULATION: [
        ("structural", ["несущая", "прочность", "устойчивость"]),
        ("volume", ["объём", "площадь", "количество"]),
        ("reinforcement", ["армирование", "арматура", "диаметр"]),
        ("load", ["нагрузка", "усилие", "момент"]),
    ],
}


# ============================================================================
# КЛАССИФИКАТОР
# ============================================================================

class RequestClassifier:
    """Классификатор инженерных запросов"""

    def __init__(self):
        self.keywords = KEYWORDS
        self.subcategories = SUBCATEGORIES

    def classify(self, text: str) -> ClassificationResult:
        """
        Классификация запроса

        Args:
            text: Текст запроса

        Returns:
            ClassificationResult с типом и метаданными
        """
        text_lower = text.lower()
        scores: Dict[RequestType, float] = {}
        found_keywords: Dict[RequestType, List[str]] = {}

        # Подсчёт очков для каждого типа
        for req_type, config in self.keywords.items():
            score = 0.0
            keywords_found = []

            # Проверка ключевых слов
            for keyword in config["keywords"]:
                if keyword.lower() in text_lower:
                    score += 1.0 * config["weight"]
                    keywords_found.append(keyword)

            # Проверка паттернов
            for pattern in config["patterns"]:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    score += 2.0 * config["weight"]  # Паттерны весят больше
                    keywords_found.extend(matches)

            scores[req_type] = score
            found_keywords[req_type] = keywords_found

        # Определяем победителя
        if not any(scores.values()):
            # Нет совпадений - общий вопрос
            return ClassificationResult(
                request_type=RequestType.GENERAL,
                confidence=0.5,
                keywords_found=[],
                sub_category=None,
                requires_calculation=False,
                requires_normative=True,  # По умолчанию нужен норматив
                priority="medium"
            )

        # Находим тип с максимальным score
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        total_score = sum(scores.values())

        # Confidence = доля лучшего типа
        confidence = best_score / total_score if total_score > 0 else 0

        # Определяем подкатегорию
        sub_category = self._detect_subcategory(text_lower, best_type)

        # Определяем требования
        requires_calculation = (
            best_type == RequestType.CALCULATION or
            scores.get(RequestType.CALCULATION, 0) > 2
        )

        requires_normative = best_type in [
            RequestType.NORMATIVE,
            RequestType.INSPECTION,
            RequestType.DISPUTE
        ]

        # Определяем приоритет
        priority = self._determine_priority(best_type, text_lower)

        return ClassificationResult(
            request_type=best_type,
            confidence=min(confidence, 1.0),
            keywords_found=found_keywords.get(best_type, []),
            sub_category=sub_category,
            requires_calculation=requires_calculation,
            requires_normative=requires_normative,
            priority=priority
        )

    def _detect_subcategory(self, text: str, req_type: RequestType) -> Optional[str]:
        """Определение подкатегории"""
        if req_type not in self.subcategories:
            return None

        for sub_name, keywords in self.subcategories[req_type]:
            for keyword in keywords:
                if keyword in text:
                    return sub_name

        return None

    def _determine_priority(self, req_type: RequestType, text: str) -> str:
        """Определение приоритета"""
        # Аварийные ситуации - критический приоритет
        if req_type == RequestType.EMERGENCY:
            return "critical"

        # Проверка на срочные слова
        urgent_words = ["срочно", "немедленно", "быстро", "сейчас", "авария"]
        if any(word in text for word in urgent_words):
            return "high"

        # Споры и проверки - повышенный приоритет
        if req_type in [RequestType.DISPUTE, RequestType.INSPECTION]:
            return "high"

        # Расчёты - средний приоритет
        if req_type == RequestType.CALCULATION:
            return "medium"

        return "medium"

    def get_processing_hints(self, result: ClassificationResult) -> Dict:
        """
        Получение подсказок для обработки запроса

        Returns:
            Dict с рекомендациями по обработке
        """
        hints = {
            "use_rag": result.requires_normative,
            "use_calculator": result.requires_calculation,
            "use_council": result.confidence < 0.7,  # Сложный вопрос - совет AI
            "response_format": "standard",
            "include_warnings": False,
            "include_sources": result.requires_normative,
        }

        # Специфичные подсказки по типу
        if result.request_type == RequestType.EMERGENCY:
            hints["response_format"] = "urgent"
            hints["include_warnings"] = True

        elif result.request_type == RequestType.CALCULATION:
            hints["response_format"] = "calculation"
            hints["include_sources"] = True

        elif result.request_type == RequestType.INSPECTION:
            hints["response_format"] = "inspection_report"
            hints["include_warnings"] = True

        elif result.request_type == RequestType.PTO:
            hints["response_format"] = "document"

        elif result.request_type == RequestType.DISPUTE:
            hints["response_format"] = "legal"
            hints["include_warnings"] = True

        return hints


# ============================================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ============================================================================

_classifier: Optional[RequestClassifier] = None


def get_classifier() -> RequestClassifier:
    """Получение глобального классификатора"""
    global _classifier
    if _classifier is None:
        _classifier = RequestClassifier()
    return _classifier


# ============================================================================
# API
# ============================================================================

def classify_request(text: str) -> ClassificationResult:
    """
    API для классификации запроса

    Args:
        text: Текст запроса пользователя

    Returns:
        ClassificationResult
    """
    classifier = get_classifier()
    return classifier.classify(text)


def get_request_type(text: str) -> RequestType:
    """Быстрое получение типа запроса"""
    result = classify_request(text)
    return result.request_type


def get_processing_hints(text: str) -> Dict:
    """Получение подсказок для обработки"""
    classifier = get_classifier()
    result = classifier.classify(text)
    return classifier.get_processing_hints(result)


def is_urgent_request(text: str) -> bool:
    """Проверка на срочность запроса"""
    result = classify_request(text)
    return result.priority in ["high", "critical"]


def requires_expert_answer(text: str) -> bool:
    """Требуется ли экспертный ответ (LLM Council)"""
    result = classify_request(text)
    return result.confidence < 0.7 or result.requires_calculation
