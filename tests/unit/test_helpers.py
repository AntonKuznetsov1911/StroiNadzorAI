"""
Tests for helper functions
"""

import pytest
from datetime import datetime

from src.utils.helpers import (
    extract_regulations,
    calculate_defect_severity,
    extract_defect_type,
    format_datetime,
    truncate_text,
    sanitize_filename,
    get_severity_text_ru
)
from src.database.models import DefectSeverity


class TestHelpers:
    """Tests for utility helpers"""

    def test_extract_regulations(self):
        """Test regulation extraction"""
        text = "Согласно СП 63.13330.2018 и ГОСТ 10180-2012..."
        regulations = extract_regulations(text)

        assert "СП 63.13330.2018" in regulations
        assert "ГОСТ 10180-2012" in regulations
        assert len(regulations) == 2

    def test_extract_regulations_empty(self):
        """Test regulation extraction with no regulations"""
        text = "Какой-то текст без нормативов"
        regulations = extract_regulations(text)

        assert len(regulations) == 0

    def test_calculate_defect_severity_critical(self):
        """Test critical severity detection"""
        text = "Обнаружена критическая трещина, угроза обрушения"
        severity = calculate_defect_severity(text)

        assert severity == DefectSeverity.CRITICAL

    def test_calculate_defect_severity_major(self):
        """Test major severity detection"""
        text = "Значительное повреждение конструкции"
        severity = calculate_defect_severity(text)

        assert severity == DefectSeverity.MAJOR

    def test_calculate_defect_severity_minor(self):
        """Test minor severity detection"""
        text = "Незначительное косметическое повреждение"
        severity = calculate_defect_severity(text)

        assert severity == DefectSeverity.MINOR

    def test_extract_defect_type(self):
        """Test defect type extraction"""
        text = "На стене обнаружена трещина шириной 2мм"
        defect_type = extract_defect_type(text)

        assert defect_type == "трещина"

    def test_extract_defect_type_corrosion(self):
        """Test corrosion detection"""
        text = "Арматура подвержена коррозии"
        defect_type = extract_defect_type(text)

        assert defect_type == "коррозия"

    def test_format_datetime(self):
        """Test datetime formatting"""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        formatted = format_datetime(dt)

        assert formatted == "15.01.2024 10:30"

    def test_truncate_text(self):
        """Test text truncation"""
        text = "Очень длинный текст" * 10
        truncated = truncate_text(text, max_length=50)

        assert len(truncated) <= 50
        assert truncated.endswith("...")

    def test_truncate_text_short(self):
        """Test text truncation with short text"""
        text = "Короткий текст"
        truncated = truncate_text(text, max_length=100)

        assert truncated == text

    def test_sanitize_filename(self):
        """Test filename sanitization"""
        filename = "Отчет № 123 (важный).pdf"
        sanitized = sanitize_filename(filename)

        assert " " not in sanitized
        assert "№" not in sanitized
        assert "(" not in sanitized

    def test_get_severity_text_ru(self):
        """Test Russian severity text"""
        assert get_severity_text_ru(DefectSeverity.CRITICAL) == "Критический"
        assert get_severity_text_ru(DefectSeverity.MAJOR) == "Значительный"
        assert get_severity_text_ru(DefectSeverity.MINOR) == "Незначительный"
