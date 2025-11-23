"""
Вспомогательные функции
"""

import re
from datetime import datetime
from typing import List, Optional
from src.database.models import DefectSeverity


# База нормативов
REGULATIONS = {
    "СП 63.13330.2018": "Бетонные и железобетонные конструкции",
    "СП 28.13330.2017": "Защита от коррозии",
    "СП 13-102-2003": "Правила обследования конструкций",
    "ГОСТ 23055-78": "Контроль сварки металлов",
    "СП 22.13330.2016": "Основания зданий и сооружений",
    "СП 70.13330.2012": "Несущие и ограждающие конструкции",
    "ГОСТ 10180-2012": "Методы определения прочности бетона",
    "СП 50-101-2004": "Проектирование фундаментов",
    "СП 48.13330.2019": "Организация строительства",
    "СП 17.13330.2017": "Кровли",
    "СП 50.13330.2012": "Тепловая защита зданий",
    "СП 60.13330.2020": "Отопление, вентиляция и кондиционирование",
    "СП 71.13330.2017": "Изоляционные и отделочные покрытия",
}


def extract_regulations(text: str) -> List[str]:
    """
    Извлечение упомянутых нормативов из текста

    Args:
        text: Текст для анализа

    Returns:
        List[str]: Список найденных нормативов
    """
    mentioned = []

    for reg_code in REGULATIONS.keys():
        if reg_code in text:
            mentioned.append(reg_code)

    return mentioned


def calculate_defect_severity(analysis_text: str) -> Optional[DefectSeverity]:
    """
    Определение критичности дефекта по тексту анализа

    Args:
        analysis_text: Текст анализа

    Returns:
        Optional[DefectSeverity]: Критичность или None
    """
    text_lower = analysis_text.lower()

    # Ключевые слова для критичности
    critical_keywords = [
        "критический", "критичен", "опасн", "разрушени", "обрушени",
        "угроз", "немедленн", "аварийн"
    ]

    major_keywords = [
        "значительн", "существенн", "серьезн", "важн"
    ]

    minor_keywords = [
        "незначительн", "мелк", "косметическ", "небольш"
    ]

    # Проверяем на критичность
    for keyword in critical_keywords:
        if keyword in text_lower:
            return DefectSeverity.CRITICAL

    for keyword in major_keywords:
        if keyword in text_lower:
            return DefectSeverity.MAJOR

    for keyword in minor_keywords:
        if keyword in text_lower:
            return DefectSeverity.MINOR

    # По умолчанию
    return DefectSeverity.INFO


def extract_defect_type(analysis_text: str) -> Optional[str]:
    """
    Извлечение типа дефекта из текста

    Args:
        analysis_text: Текст анализа

    Returns:
        Optional[str]: Тип дефекта или None
    """
    text_lower = analysis_text.lower()

    # Типы дефектов
    defect_types = {
        "трещина": ["трещин", "растрескивани"],
        "коррозия": ["коррози", "ржавчин"],
        "отслоение": ["отслоени", "отслаивани", "вздути"],
        "деформация": ["деформаци", "прогиб", "искривлени"],
        "протечка": ["протечк", "влаг", "сыр", "плесен"],
        "разрушение": ["разрушени", "скол", "выкрашивани"],
    }

    for defect_type, keywords in defect_types.items():
        for keyword in keywords:
            if keyword in text_lower:
                return defect_type

    return None


def format_datetime(dt: datetime, format_str: str = "%d.%m.%Y %H:%M") -> str:
    """
    Форматирование даты и времени

    Args:
        dt: DateTime объект
        format_str: Формат строки

    Returns:
        str: Отформатированная строка
    """
    return dt.strftime(format_str)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Обрезка текста до определенной длины

    Args:
        text: Исходный текст
        max_length: Максимальная длина
        suffix: Суффикс для обрезанного текста

    Returns:
        str: Обрезанный текст
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def sanitize_filename(filename: str) -> str:
    """
    Очистка имени файла от небезопасных символов

    Args:
        filename: Исходное имя файла

    Returns:
        str: Безопасное имя файла
    """
    # Удаляем небезопасные символы
    safe_filename = re.sub(r'[^\w\s\-\.]', '', filename)

    # Заменяем пробелы на подчеркивания
    safe_filename = safe_filename.replace(' ', '_')

    return safe_filename


def get_severity_emoji(severity: DefectSeverity) -> str:
    """
    Получить эмодзи для критичности

    Args:
        severity: Критичность

    Returns:
        str: Эмодзи
    """
    emoji_map = {
        DefectSeverity.CRITICAL: "🔴",
        DefectSeverity.MAJOR: "🟠",
        DefectSeverity.MINOR: "🟡",
        DefectSeverity.INFO: "🔵",
    }

    return emoji_map.get(severity, "⚪")


def get_severity_text_ru(severity: DefectSeverity) -> str:
    """
    Получить русский текст для критичности

    Args:
        severity: Критичность

    Returns:
        str: Русский текст
    """
    text_map = {
        DefectSeverity.CRITICAL: "Критический",
        DefectSeverity.MAJOR: "Значительный",
        DefectSeverity.MINOR: "Незначительный",
        DefectSeverity.INFO: "Информация",
    }

    return text_map.get(severity, "Неизвестно")
