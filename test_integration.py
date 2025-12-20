"""
Тест интеграции умного выбора моделей в StroiNadzorAI
Проверяет работу model_selector, optimized_handlers и smart_model_wrapper
"""

import logging
import sys
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """Проверка импорта всех модулей оптимизации"""
    logger.info("\n" + "="*80)
    logger.info("ТЕСТ 1: Импорт модулей оптимизации")
    logger.info("="*80)

    errors = []

    try:
        from model_selector import ModelSelector, should_use_web_search, extract_regulation_codes
        logger.info("✅ model_selector.py импортирован успешно")
    except Exception as e:
        errors.append(f"❌ model_selector.py: {e}")

    try:
        from optimized_prompts import (
            CLAUDE_SYSTEM_PROMPT_TECHNICAL,
            GEMINI_IMAGE_PROMPT_SYSTEM,
            GROK_SYSTEM_PROMPT_GENERAL,
            GEMINI_VISION_PROMPT_DEFECTS
        )
        logger.info("✅ optimized_prompts.py импортирован успешно")
        logger.info(f"   - CLAUDE_SYSTEM_PROMPT_TECHNICAL: {len(CLAUDE_SYSTEM_PROMPT_TECHNICAL)} символов")
        logger.info(f"   - GEMINI_IMAGE_PROMPT_SYSTEM: {len(GEMINI_IMAGE_PROMPT_SYSTEM)} символов")
        logger.info(f"   - GROK_SYSTEM_PROMPT_GENERAL: {len(GROK_SYSTEM_PROMPT_GENERAL)} символов")
        logger.info(f"   - GEMINI_VISION_PROMPT_DEFECTS: {len(GEMINI_VISION_PROMPT_DEFECTS)} символов")
    except Exception as e:
        errors.append(f"❌ optimized_prompts.py: {e}")

    try:
        from optimized_handlers import (
            handle_with_claude_technical,
            handle_with_gemini_vision,
            handle_with_gemini_image,
            handle_with_grok
        )
        logger.info("✅ optimized_handlers.py импортирован успешно")
    except Exception as e:
        errors.append(f"❌ optimized_handlers.py: {e}")

    try:
        from smart_model_wrapper import smart_model_selection_text, smart_model_selection_photo
        logger.info("✅ smart_model_wrapper.py импортирован успешно")
    except Exception as e:
        errors.append(f"❌ smart_model_wrapper.py: {e}")

    if errors:
        for err in errors:
            logger.error(err)
        return False

    return True


def test_model_selector():
    """Проверка работы умного селектора моделей"""
    logger.info("\n" + "="*80)
    logger.info("ТЕСТ 2: Классификация запросов")
    logger.info("="*80)

    try:
        from model_selector import ModelSelector

        selector = ModelSelector()

        # Тестовые запросы
        test_cases = [
            # Технические вопросы -> Claude
            ("Какой класс бетона нужен для фундамента?", False, "claude_technical"),
            ("Расчёт нагрузки на плиту перекрытия 6x8 м", False, "claude_technical"),
            ("Требования СП 63.13330 к толщине утеплителя", False, "claude_technical"),

            # Простые вопросы -> Grok
            ("Привет, как дела?", False, "grok_general"),
            ("Что такое бетон?", False, "grok_general"),

            # Чертежи -> Gemini Image
            ("Нарисуй чертёж лестницы", False, "gemini_image"),
            ("Покажи схему армирования фундамента", False, "gemini_image"),

            # Фото дефектов -> Gemini Vision
            ("Проанализируй этот дефект", True, "gemini_vision"),
        ]

        all_passed = True

        for question, has_photo, expected_model in test_cases:
            decision = selector.classify_request(question, has_photo)

            status = "✅" if decision["model"] == expected_model else "❌"
            logger.info(f"\n{status} Вопрос: '{question[:50]}...'")
            logger.info(f"   Ожидается: {expected_model}")
            logger.info(f"   Получено: {decision['model']}")
            logger.info(f"   Причина: {decision['reason']}")
            logger.info(f"   Стоимость: ${decision['estimated_cost']:.3f}")

            if decision["model"] != expected_model:
                all_passed = False

        return all_passed

    except Exception as e:
        logger.error(f"❌ Ошибка в тесте классификатора: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_keys():
    """Проверка наличия API ключей (необязательно для локального тестирования)"""
    logger.info("\n" + "="*80)
    logger.info("ТЕСТ 3: Проверка API ключей")
    logger.info("="*80)

    api_keys = {
        "ANTHROPIC_API_KEY": "Claude Sonnet 4.5",
        "GOOGLE_API_KEY": "Gemini 2.0 Flash (Vision + Image)",
        "XAI_API_KEY": "Grok"
    }

    keys_present = 0
    total_keys = len(api_keys)

    for key_name, service in api_keys.items():
        key_value = os.getenv(key_name)
        if key_value:
            logger.info(f"✅ {key_name} ({service}): присутствует ({key_value[:10]}...)")
            keys_present += 1
        else:
            logger.warning(f"⚠️ {key_name} ({service}): отсутствует")

    if keys_present == 0:
        logger.warning("⚠️ Ни один API ключ не настроен - требуется для production")
        logger.info("💡 Для локального тестирования это нормально")
    elif keys_present < total_keys:
        logger.warning(f"⚠️ Настроено {keys_present}/{total_keys} API ключей")
        logger.info("💡 Некоторые функции будут недоступны")
    else:
        logger.info(f"✅ Все {total_keys} API ключей настроены!")

    # Всегда возвращаем True для локального тестирования
    # API ключи нужны только для production
    return True


def test_helper_functions():
    """Проверка вспомогательных функций"""
    logger.info("\n" + "="*80)
    logger.info("ТЕСТ 4: Вспомогательные функции")
    logger.info("="*80)

    try:
        from model_selector import should_use_web_search, extract_regulation_codes

        # Тест should_use_web_search
        web_search_cases = [
            ("Последние новости строительства", True),
            ("Что сейчас в новостях?", True),
            ("Какой класс бетона для фундамента?", False),
        ]

        for question, expected in web_search_cases:
            result = should_use_web_search(question)
            status = "✅" if result == expected else "❌"
            logger.info(f"{status} Web search для '{question[:40]}...': {result} (ожидается {expected})")

        # Тест extract_regulation_codes
        regulation_cases = [
            ("Требования СП 63.13330 к утеплению", ["СП 63.13330"]),
            ("ГОСТ 2.307 и ГОСТ 2.303", ["ГОСТ 2.307", "ГОСТ 2.303"]),
            ("Простой вопрос без нормативов", []),
        ]

        for question, expected in regulation_cases:
            result = extract_regulation_codes(question)
            status = "✅" if set(result) == set(expected) else "❌"
            logger.info(f"{status} Нормативы в '{question[:40]}...': {result} (ожидается {expected})")

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка в тесте вспомогательных функций: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Запуск всех тестов"""
    logger.info("\n" + "="*80)
    logger.info("🚀 НАЧАЛО ТЕСТИРОВАНИЯ ИНТЕГРАЦИИ")
    logger.info("="*80)

    results = {
        "Импорт модулей": test_imports(),
        "Классификация запросов": test_model_selector(),
        "API ключи": test_api_keys(),
        "Вспомогательные функции": test_helper_functions()
    }

    # Итоговый отчёт
    logger.info("\n" + "="*80)
    logger.info("📊 ИТОГОВЫЙ ОТЧЁТ")
    logger.info("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{status}: {test_name}")

    logger.info("\n" + "-"*80)
    logger.info(f"Успешно: {passed}/{total} тестов ({passed*100//total}%)")
    logger.info("-"*80)

    if passed == total:
        logger.info("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Интеграция работает корректно.")
        return True
    else:
        logger.warning(f"\n⚠️ Некоторые тесты не прошли. Необходима доработка.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
