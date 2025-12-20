"""
Тестовый скрипт для проверки системы AI координации
Проверяет работу XAI, OpenAI DALL-E, Anthropic Claude
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Проверка наличия API ключей
XAI_API_KEY = os.getenv("XAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


def check_api_keys():
    """Проверка наличия API ключей"""
    print("\n" + "="*60)
    print("🔑 ПРОВЕРКА API КЛЮЧЕЙ")
    print("="*60)

    has_xai = bool(XAI_API_KEY)
    has_openai = bool(OPENAI_API_KEY)
    has_anthropic = bool(ANTHROPIC_API_KEY)

    print(f"✅ XAI_API_KEY: {'Установлен' if has_xai else '❌ НЕ УСТАНОВЛЕН'}")
    print(f"✅ OPENAI_API_KEY: {'Установлен' if has_openai else '❌ НЕ УСТАНОВЛЕН'}")
    print(f"✅ ANTHROPIC_API_KEY: {'Установлен' if has_anthropic else '❌ НЕ УСТАНОВЛЕН'}")

    if not has_xai:
        print("\n⚠️ ВНИМАНИЕ: XAI_API_KEY не установлен - основной AI не будет работать!")

    return has_xai, has_openai, has_anthropic


async def test_xai():
    """Тест XAI (Grok)"""
    print("\n" + "="*60)
    print("🤖 ТЕСТ XAI (GROK)")
    print("="*60)

    try:
        from ai_coordinator import get_xai_client, call_xai_with_fallback

        client = get_xai_client()
        if not client:
            print("❌ XAI клиент не инициализирован")
            return False

        messages = [
            {"role": "system", "content": "Ты - помощник по строительству. Отвечай кратко."},
            {"role": "user", "content": "Какой класс бетона нужен для фундамента? Ответь в одном предложении."}
        ]

        print("📤 Отправка запроса к XAI...")
        response = await call_xai_with_fallback(messages, needs_image=False)

        print(f"✅ Ответ получен:\n{response[:200]}...")
        return True

    except Exception as e:
        print(f"❌ Ошибка тестирования XAI: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_openai_dalle():
    """Тест OpenAI DALL-E"""
    print("\n" + "="*60)
    print("🎨 ТЕСТ OPENAI DALL-E")
    print("="*60)

    try:
        from openai_dalle import generate_image_dalle, is_dalle_available

        if not is_dalle_available():
            print("❌ DALL-E недоступен (нет OPENAI_API_KEY)")
            return False

        print("📤 Отправка запроса к DALL-E...")
        print("📝 Промпт: Technical construction diagram...")

        result = await generate_image_dalle(
            prompt="Simple technical diagram of a concrete foundation with reinforcement bars, blueprint style",
            size="1024x1024",
            quality="standard"
        )

        if result and result.get("image_data"):
            print("✅ Изображение успешно сгенерировано!")
            print(f"📊 Размер: {result['size']}")
            print(f"🔄 Revised prompt: {result['revised_prompt'][:100]}...")

            # Сохраняем для проверки
            result["image_data"].seek(0)
            with open("test_dalle_output.png", "wb") as f:
                f.write(result["image_data"].read())
            print("💾 Изображение сохранено: test_dalle_output.png")

            return True
        else:
            print("❌ Изображение не сгенерировано")
            return False

    except Exception as e:
        print(f"❌ Ошибка тестирования DALL-E: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_anthropic():
    """Тест Anthropic Claude"""
    print("\n" + "="*60)
    print("🧠 ТЕСТ ANTHROPIC CLAUDE")
    print("="*60)

    try:
        from ai_coordinator import call_anthropic_with_prompt

        messages = [
            {"role": "system", "content": "Ты - помощник по строительству. Отвечай кратко."},
            {"role": "user", "content": "Какой класс бетона нужен для фундамента? Ответь в одном предложении."}
        ]

        print("📤 Отправка запроса к Claude...")
        response = await call_anthropic_with_prompt(messages)

        print(f"✅ Ответ получен:\n{response[:200]}...")
        return True

    except Exception as e:
        print(f"❌ Ошибка тестирования Claude: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_coordination():
    """Тест координации AI"""
    print("\n" + "="*60)
    print("🎯 ТЕСТ КООРДИНАЦИИ AI")
    print("="*60)

    try:
        from ai_coordinator import analyze_request_and_coordinate

        # Тест 1: Простой вопрос (без изображения)
        print("\n📝 Тест 1: Простой вопрос")
        result = await analyze_request_and_coordinate(
            user_message="Какой класс бетона нужен для фундамента?",
            conversation_history=[],
            system_prompt="Ты - помощник по строительству."
        )

        if result["error"]:
            print(f"❌ Ошибка: {result['error']}")
            return False

        print(f"✅ Ответ получен от: {result['ai_used'].upper()}")
        print(f"📝 Ответ: {result['text_response'][:150]}...")
        print(f"🎨 Нужно изображение: {result['needs_image']}")

        # Тест 2: Запрос с генерацией изображения
        print("\n📝 Тест 2: Запрос на генерацию изображения")
        result = await analyze_request_and_coordinate(
            user_message="Нарисуй схему колодцев от административного здания до центральной канализации",
            conversation_history=[],
            system_prompt="Ты - помощник по строительству."
        )

        if result["error"]:
            print(f"❌ Ошибка: {result['error']}")
            return False

        print(f"✅ Ответ получен от: {result['ai_used'].upper()}")
        print(f"📝 Ответ: {result['text_response'][:150]}...")
        print(f"🎨 Нужно изображение: {result['needs_image']}")

        if result["needs_image"] and result["image_prompt"]:
            print(f"📝 Промпт для DALL-E: {result['image_prompt'][:100]}...")

        return True

    except Exception as e:
        print(f"❌ Ошибка тестирования координации: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_parallel_generation():
    """Тест параллельной генерации текста и изображения"""
    print("\n" + "="*60)
    print("⚡ ТЕСТ ПАРАЛЛЕЛЬНОЙ ГЕНЕРАЦИИ")
    print("="*60)

    if not OPENAI_API_KEY:
        print("⚠️ Пропущен: нет OPENAI_API_KEY")
        return True

    try:
        from ai_coordinator import generate_text_and_image_parallel

        print("📤 Отправка запроса на параллельную генерацию...")
        print("📝 Запрос: Нарисуй схему фундамента с армированием")

        result = await generate_text_and_image_parallel(
            user_message="Нарисуй схему фундамента с армированием",
            conversation_history=[],
            system_prompt="Ты - помощник по строительству."
        )

        if result["error"]:
            print(f"❌ Ошибка: {result['error']}")
            return False

        print(f"✅ Текст получен от: {result['ai_used'].upper()}")
        print(f"📝 Ответ: {result['text_response'][:150]}...")

        if result["image_result"]:
            print("✅ Изображение сгенерировано")
            # Сохраняем
            result["image_result"]["image_data"].seek(0)
            with open("test_parallel_output.png", "wb") as f:
                f.write(result["image_result"]["image_data"].read())
            print("💾 Изображение сохранено: test_parallel_output.png")
        else:
            print("⚠️ Изображение не сгенерировано")

        return True

    except Exception as e:
        print(f"❌ Ошибка параллельной генерации: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Запуск всех тестов"""
    print("\n" + "="*60)
    print("🧪 ЗАПУСК ТЕСТОВ AI СИСТЕМЫ")
    print("="*60)

    # Проверка ключей
    has_xai, has_openai, has_anthropic = check_api_keys()

    results = {}

    # Тест XAI
    if has_xai:
        results["XAI"] = await test_xai()
    else:
        print("\n⚠️ Пропущен тест XAI: нет API ключа")
        results["XAI"] = False

    # Тест DALL-E
    if has_openai:
        results["DALL-E"] = await test_openai_dalle()
    else:
        print("\n⚠️ Пропущен тест DALL-E: нет API ключа")
        results["DALL-E"] = False

    # Тест Claude
    if has_anthropic:
        results["Claude"] = await test_anthropic()
    else:
        print("\n⚠️ Пропущен тест Claude: нет API ключа")
        results["Claude"] = False

    # Тест координации
    if has_xai or has_anthropic:
        results["Координация"] = await test_coordination()
    else:
        print("\n⚠️ Пропущен тест координации: нет AI ключей")
        results["Координация"] = False

    # Тест параллельной генерации
    if has_xai and has_openai:
        results["Параллельная генерация"] = await test_parallel_generation()
    else:
        print("\n⚠️ Пропущен тест параллельной генерации: нужны XAI + OpenAI")
        results["Параллельная генерация"] = False

    # Итоги
    print("\n" + "="*60)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*60)

    for test_name, passed in results.items():
        status = "✅ ПРОЙДЕН" if passed else "❌ ПРОВАЛЕН"
        print(f"{test_name}: {status}")

    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    print(f"\n📈 Всего: {passed_count}/{total_count} тестов пройдено")

    if passed_count == total_count:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    elif passed_count > 0:
        print("\n⚠️ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
    else:
        print("\n❌ ВСЕ ТЕСТЫ ПРОВАЛЕНЫ")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
