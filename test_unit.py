"""
Юнит-тесты для критических модулей СтройНадзорAI
=================================================

Тестируемые модули:
1. calculators.py — строительные калькуляторы
2. model_selector.py — маршрутизация AI-запросов
3. cache_manager.py — кэширование
4. circuit_breaker.py — Circuit Breaker
5. llm_council.py — определение сложности вопроса

Запуск: python -m pytest test_unit.py -v
"""

import pytest
import asyncio
from time import time, sleep


# ========================================
# 1. ТЕСТЫ КАЛЬКУЛЯТОРА БЕТОНА
# ========================================

class TestConcreteCalculator:
    """Тесты расчёта бетона по СП 63.13330.2018"""

    def setup_method(self):
        from calculators import calculate_concrete
        self.calc = calculate_concrete

    def test_basic_volume(self):
        """Базовый расчёт объёма: 6x6x0.2 = 7.2 м3"""
        result = self.calc(length=6, width=6, height=0.2)
        assert "error" not in result
        assert result["volume"] == pytest.approx(7.2, rel=0.01)
        assert result["volume"] > 0

    def test_volume_with_wastage(self):
        """Объём с запасом всегда больше чистого объёма"""
        result = self.calc(length=10, width=5, height=0.3)
        assert result["volume_with_wastage"] > result["volume"]

    def test_cement_positive(self):
        """Цемент всегда положительный"""
        result = self.calc(length=3, width=3, height=0.15)
        assert result["cement_total"] > 0
        assert result["cement_per_m3"] > 0

    def test_water_cement_ratio(self):
        """В/Ц соотношение в допустимых пределах"""
        result = self.calc(length=5, width=5, height=0.2)
        assert 0.3 <= result["water_cement_ratio"] <= 0.7

    def test_materials_positive(self):
        """Все материалы положительные"""
        result = self.calc(length=4, width=4, height=0.2)
        assert result["sand_total"] > 0
        assert result["gravel_total"] > 0
        assert result["water_total"] > 0

    def test_cost_positive(self):
        """Стоимость положительная"""
        result = self.calc(length=5, width=5, height=0.2)
        assert result["total_cost"] > 0
        assert result["cost_per_m3"] > 0

    def test_negative_dimensions_error(self):
        """Отрицательные размеры — ошибка"""
        result = self.calc(length=-1, width=5, height=0.2)
        assert "error" in result

    def test_zero_dimensions_error(self):
        """Нулевые размеры — ошибка"""
        result = self.calc(length=0, width=5, height=0.2)
        assert "error" in result

    def test_excessive_wastage_error(self):
        """Слишком большой запас — ошибка"""
        result = self.calc(length=5, width=5, height=0.2, wastage=60)
        assert "error" in result

    def test_temperature_cold(self):
        """Холодная температура увеличивает коэффициент"""
        result_cold = self.calc(length=5, width=5, height=0.2, temperature=-10)
        result_normal = self.calc(length=5, width=5, height=0.2, temperature=20)
        assert result_cold["total_coefficient"] > result_normal["total_coefficient"]

    def test_all_concrete_classes(self):
        """Все классы бетона работают"""
        classes = ["B7.5", "B12.5", "B15", "B20", "B22.5", "B25", "B30", "B35", "B40"]
        for cls in classes:
            result = self.calc(length=5, width=5, height=0.2, concrete_class=cls)
            assert "error" not in result, f"Ошибка для класса {cls}"

    def test_standards_reference(self):
        """Результат содержит ссылку на нормативы"""
        result = self.calc(length=5, width=5, height=0.2)
        assert "СП 63" in result["standards"]


# ========================================
# 2. ТЕСТЫ КАЛЬКУЛЯТОРА АРМАТУРЫ
# ========================================

class TestReinforcementCalculator:
    """Тесты расчёта арматуры по СП 63.13330.2018"""

    def setup_method(self):
        from calculators import calculate_reinforcement
        self.calc = calculate_reinforcement

    def test_basic_slab(self):
        """Базовый расчёт для плиты"""
        result = self.calc(length=6, width=6, height=0.2)
        assert "error" not in result
        assert result["total_length"] > 0
        assert result["total_mass"] > 0

    def test_beam_element(self):
        """Расчёт для балки"""
        result = self.calc(length=6, width=0.3, height=0.5, element_type="beam")
        assert result["element_type"] == "beam"
        assert result["total_mass"] > 0

    def test_column_element(self):
        """Расчёт для колонны"""
        result = self.calc(length=0.4, width=0.4, height=3.0, element_type="column")
        assert result["element_type"] == "column"
        assert result["total_mass"] > 0

    def test_rebar_diameter_selection(self):
        """Ближайший диаметр арматуры"""
        result = self.calc(length=5, width=5, height=0.2, diameter=13)
        assert result["rebar_diameter"] in [12, 14]

    def test_mass_per_m2(self):
        """Масса на м2 положительная"""
        result = self.calc(length=5, width=5, height=0.2)
        assert result["mass_per_m2"] > 0

    def test_negative_dimensions_error(self):
        """Отрицательные размеры — ошибка"""
        result = self.calc(length=-1, width=5, height=0.2)
        assert "error" in result


# ========================================
# 3. ТЕСТЫ КАЛЬКУЛЯТОРА ОПАЛУБКИ
# ========================================

class TestFormworkCalculator:
    """Тесты расчёта опалубки"""

    def setup_method(self):
        from calculators import calculate_formwork
        self.calc = calculate_formwork

    def test_basic_calculation(self):
        """Базовый расчёт опалубки"""
        result = self.calc(area=100, duration=30)
        assert "error" not in result
        assert result["cost"] > 0

    def test_negative_area_error(self):
        """Отрицательная площадь — ошибка"""
        result = self.calc(area=-10, duration=30)
        assert "error" in result


# ========================================
# 4. ТЕСТЫ КАЛЬКУЛЯТОРА ЭЛЕКТРОСНАБЖЕНИЯ
# ========================================

class TestElectricalCalculator:
    """Тесты расчёта электроснабжения"""

    def setup_method(self):
        from calculators import calculate_electrical
        self.calc = calculate_electrical

    def test_basic_calculation(self):
        """Базовый расчёт электроснабжения"""
        result = self.calc(crane_count=1, pump_count=2, welder_count=3, heater_count=4, cabin_count=2)
        assert "error" not in result
        assert result["installed_power"] > 0
        assert result["calculated_power"] > 0
        assert result["calculated_power"] <= result["installed_power"]

    def test_zero_equipment(self):
        """Без оборудования — мощность 0"""
        result = self.calc(crane_count=0, pump_count=0, welder_count=0, heater_count=0, cabin_count=0)
        assert result["installed_power"] == 0

    def test_negative_equipment_error(self):
        """Отрицательное количество — ошибка"""
        result = self.calc(crane_count=-1, pump_count=0, welder_count=0, heater_count=0, cabin_count=0)
        assert "error" in result


# ========================================
# 5. ТЕСТЫ MODEL SELECTOR
# ========================================

class TestModelSelector:
    """Тесты маршрутизации запросов к AI моделям"""

    def setup_method(self):
        from model_selector import ModelSelector
        self.selector = ModelSelector()

    def test_photo_defect_uses_gemini(self):
        """Фото с дефектом -> Gemini Vision"""
        result = self.selector.classify_request("Что за трещина на фото?", has_photo=True)
        assert result["model"] == "gemini_vision"
        assert result["priority"] == "high"

    def test_photo_general_uses_grok(self):
        """Обычное фото -> Grok (бесплатно)"""
        result = self.selector.classify_request("Что на фото?", has_photo=True)
        assert result["model"] == "grok_vision"

    def test_drawing_uses_gemini_image(self):
        """Запрос на рисунок -> Gemini Image"""
        result = self.selector.classify_request("Нарисуй схему фундамента")
        assert result["model"] == "gemini_image"

    def test_simple_question_uses_grok(self):
        """Простой вопрос -> Grok"""
        result = self.selector.classify_request("Что такое бетон?")
        assert result["model"] == "grok_general"

    def test_technical_question_uses_claude(self):
        """Технический расчёт -> Claude"""
        result = self.selector.classify_request("Рассчитай армирование плиты перекрытия")
        assert result["model"] == "claude_technical"

    def test_legal_question_uses_claude(self):
        """Юридический вопрос -> Claude"""
        result = self.selector.classify_request("Какой штраф за нарушение норм строительства по закону?")
        assert result["model"] == "claude_technical"

    def test_regulation_needs_web_search(self):
        """Упоминание СП → needs_web_search"""
        result = self.selector.classify_request("Актуальна ли версия СП 63.13330.2018?")
        assert result["needs_web_search"] is True

    def test_web_search_keywords(self):
        """Слова-триггеры для web search"""
        result = self.selector.classify_request("Какая сейчас цена на арматуру?")
        assert result["needs_web_search"] is True

    def test_estimated_cost_non_negative(self):
        """Стоимость запроса всегда >= 0"""
        result = self.selector.classify_request("Любой вопрос")
        assert result["estimated_cost"] >= 0


# ========================================
# 6. ТЕСТЫ EXTRACT REGULATION CODES
# ========================================

class TestRegulationExtraction:
    """Тесты извлечения кодов нормативов"""

    def setup_method(self):
        from model_selector import extract_regulation_codes
        self.extract = extract_regulation_codes

    def test_sp_code(self):
        """Извлечение кода СП"""
        codes = self.extract("По СП 63.13330.2018 требуется...")
        assert len(codes) > 0

    def test_gost_code(self):
        """Извлечение кода ГОСТ"""
        codes = self.extract("Согласно ГОСТ 31937-2011")
        assert len(codes) > 0

    def test_snip_code(self):
        """Извлечение кода СНиП"""
        codes = self.extract("Как в СНиП 2.01.07-85")
        assert len(codes) > 0

    def test_no_codes(self):
        """Нет кодов -> пустой список"""
        codes = self.extract("Как уложить кирпич?")
        assert len(codes) == 0

    def test_multiple_codes(self):
        """Несколько кодов -> все извлечены"""
        codes = self.extract("По СП 63.13330.2018 и ГОСТ 31937-2011 и СНиП 2.01.07-85")
        assert len(codes) >= 2


# ========================================
# 7. ТЕСТЫ CIRCUIT BREAKER
# ========================================

class TestCircuitBreaker:
    """Тесты паттерна Circuit Breaker"""

    def setup_method(self):
        from circuit_breaker import CircuitBreaker
        self.CircuitBreaker = CircuitBreaker

    def test_initial_state_closed(self):
        """Начальное состояние — CLOSED"""
        cb = self.CircuitBreaker("test")
        assert cb.state == "closed"
        assert cb.can_execute() is True

    def test_opens_after_threshold(self):
        """Размыкание после N ошибок"""
        cb = self.CircuitBreaker("test", failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "open"
        assert cb.can_execute() is False

    def test_stays_closed_under_threshold(self):
        """Не размыкается при < threshold ошибок"""
        cb = self.CircuitBreaker("test", failure_threshold=5)
        for _ in range(4):
            cb.record_failure()
        assert cb.state == "closed"
        assert cb.can_execute() is True

    def test_success_resets_failures(self):
        """Успех сбрасывает счётчик ошибок"""
        cb = self.CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        cb.record_failure()
        # После success счётчик сбросился, 2 ошибки < 3
        assert cb.state == "closed"

    def test_recovery_after_timeout(self):
        """Переход в HALF-OPEN после recovery_timeout"""
        cb = self.CircuitBreaker("test", failure_threshold=2, recovery_timeout=1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        sleep(1.1)
        assert cb.can_execute() is True
        assert cb.state == "half-open"

    def test_half_open_success_closes(self):
        """Успех в HALF-OPEN -> CLOSED"""
        cb = self.CircuitBreaker("test", failure_threshold=2, recovery_timeout=1)
        cb.record_failure()
        cb.record_failure()
        sleep(1.1)
        cb.can_execute()  # -> half-open
        cb.record_success()
        assert cb.state == "closed"

    def test_half_open_failure_opens(self):
        """Ошибка в HALF-OPEN -> OPEN"""
        cb = self.CircuitBreaker("test", failure_threshold=2, recovery_timeout=1)
        cb.record_failure()
        cb.record_failure()
        sleep(1.1)
        cb.can_execute()  # -> half-open
        cb.record_failure()
        assert cb.state == "open"

    def test_stats(self):
        """Статистика работает"""
        cb = self.CircuitBreaker("test_api")
        cb.can_execute()
        cb.record_success()
        cb.can_execute()
        cb.record_failure()
        stats = cb.get_stats()
        assert stats["name"] == "test_api"
        assert stats["total_calls"] == 2
        assert stats["total_failures"] == 1

    def test_reset(self):
        """Принудительный сброс"""
        cb = self.CircuitBreaker("test", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        cb.reset()
        assert cb.state == "closed"
        assert cb.can_execute() is True


# ========================================
# 8. ТЕСТЫ CACHE MANAGER
# ========================================

class TestCacheManager:
    """Тесты функций кэширования"""

    def test_cache_key_deterministic(self):
        """Один и тот же вопрос -> один ключ"""
        from cache_manager import generate_cache_key
        key1 = generate_cache_key("Что такое бетон?")
        key2 = generate_cache_key("Что такое бетон?")
        assert key1 == key2

    def test_cache_key_case_insensitive(self):
        """Ключ не зависит от регистра"""
        from cache_manager import generate_cache_key
        key1 = generate_cache_key("Что такое БЕТОН?")
        key2 = generate_cache_key("что такое бетон?")
        assert key1 == key2

    def test_cache_key_whitespace_normalized(self):
        """Нормализация пробелов"""
        from cache_manager import generate_cache_key
        key1 = generate_cache_key("  Что   такое   бетон?  ")
        key2 = generate_cache_key("Что такое бетон?")
        assert key1 == key2

    def test_cache_key_different_questions(self):
        """Разные вопросы -> разные ключи"""
        from cache_manager import generate_cache_key
        key1 = generate_cache_key("Что такое бетон?")
        key2 = generate_cache_key("Что такое арматура?")
        assert key1 != key2

    def test_cache_key_with_context(self):
        """Ключ с контекстом отличается"""
        from cache_manager import generate_cache_key
        key1 = generate_cache_key("Что такое бетон?")
        key2 = generate_cache_key("Что такое бетон?", user_context="foreman")
        assert key1 != key2

    def test_similarity_identical(self):
        """Идентичные тексты -> similarity = 1.0"""
        from cache_manager import calculate_similarity
        assert calculate_similarity("бетон м400", "бетон м400") == pytest.approx(1.0)

    def test_similarity_different(self):
        """Совершенно разные тексты -> similarity ≈ 0"""
        from cache_manager import calculate_similarity
        sim = calculate_similarity("бетон м400", "юридическая консультация")
        assert sim < 0.2

    def test_similarity_partial(self):
        """Частично совпадающие тексты -> 0 < similarity < 1"""
        from cache_manager import calculate_similarity
        sim = calculate_similarity("расчёт бетона для фундамента", "расчёт арматуры для фундамента")
        assert 0.3 < sim < 0.9

    def test_cache_key_length(self):
        """Ключ кэша SHA-256 — 32 символа"""
        from cache_manager import generate_cache_key
        key = generate_cache_key("Тестовый вопрос")
        assert len(key) == 32


# ========================================
# 9. ТЕСТЫ LLM COUNCIL — ОПРЕДЕЛЕНИЕ СЛОЖНОСТИ
# ========================================

class TestComplexityDetection:
    """Тесты определения сложности вопросов"""

    def setup_method(self):
        from llm_council import is_complex_question
        self.is_complex = is_complex_question

    def test_simple_greeting(self):
        """Приветствие — простой вопрос"""
        is_complex, _ = self.is_complex("Привет")
        assert is_complex is False

    def test_short_question(self):
        """Короткий вопрос < 5 слов — простой"""
        is_complex, _ = self.is_complex("Что такое бетон?")
        assert is_complex is False

    def test_technical_keywords(self):
        """Вопрос с техническими терминами — сложный"""
        is_complex, _ = self.is_complex("Рассчитай армирование плиты с учётом нагрузки на прочность")
        assert is_complex is True

    def test_multiple_normatives(self):
        """Несколько нормативов — сложный вопрос"""
        is_complex, _ = self.is_complex("Сравни требования СП 63.13330 и ГОСТ 31937-2011 к бетону")
        assert is_complex is True

    def test_comparison_marker(self):
        """Маркер сравнения — сложный вопрос"""
        is_complex, _ = self.is_complex("Как правильно бетонировать при отрицательных температурах и зачем это нужно")
        assert is_complex is True

    def test_returns_reason(self):
        """Для сложного вопроса возвращается причина"""
        is_complex, reason = self.is_complex(
            "Как правильно рассчитать армирование плиты перекрытия по СП 63.13330 "
            "с учётом нагрузок и требований к защитному слою бетона?"
        )
        assert is_complex is True
        assert len(reason) > 0


# ========================================
# ЗАПУСК ТЕСТОВ
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
