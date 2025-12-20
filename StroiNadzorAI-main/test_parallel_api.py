"""
Тест параллельной работы OpenAI и Claude API
"""
import os
import sys
import asyncio
import time
from dotenv import load_dotenv
from openai import OpenAI
import anthropic

# Устанавливаем UTF-8 для вывода в консоль (для Windows)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Загрузка переменных окружения
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Инициализация клиентов
openai_client = None
anthropic_client = None

if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
if ANTHROPIC_API_KEY:
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


async def call_openai_text(question: str):
    """Тест OpenAI API"""
    if not openai_client:
        return None

    try:
        start = time.time()
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ты - эксперт по строительству."},
                    {"role": "user", "content": question}
                ],
                max_tokens=100,
                temperature=0.7
            )
        )
        elapsed = time.time() - start
        return ("OpenAI", response.choices[0].message.content, elapsed)
    except Exception as e:
        print(f"❌ OpenAI error: {e}")
        return None


async def call_claude_text(question: str):
    """Тест Claude API"""
    if not anthropic_client:
        return None

    try:
        start = time.time()
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=100,
                system="Ты - эксперт по строительству.",
                messages=[
                    {"role": "user", "content": question}
                ],
                temperature=0.7
            )
        )
        elapsed = time.time() - start
        return ("Claude", response.content[0].text, elapsed)
    except Exception as e:
        print(f"❌ Claude error: {e}")
        return None


async def test_parallel():
    """Тест параллельной работы обоих API"""
    question = "Какая допустимая ширина трещины в бетоне?"

    print("🔄 Запуск параллельного теста API...")
    print(f"❓ Вопрос: {question}\n")

    tasks = []
    if OPENAI_API_KEY:
        tasks.append(call_openai_text(question))
        print("✅ OpenAI API готов")
    else:
        print("⚠️  OpenAI API ключ не найден")

    if ANTHROPIC_API_KEY:
        tasks.append(call_claude_text(question))
        print("✅ Claude API готов")
    else:
        print("⚠️  Claude API ключ не найден")

    if not tasks:
        print("❌ Нет доступных API!")
        return

    print("\n⏱️  Ожидание ответов...\n")

    # Запускаем параллельно и собираем все результаты
    results = await asyncio.gather(*tasks)

    # Фильтруем None результаты
    results = [r for r in results if r is not None]

    if not results:
        print("❌ Все API вернули ошибку!")
        return

    # Сортируем по времени
    results.sort(key=lambda x: x[2])

    print("📊 РЕЗУЛЬТАТЫ (по скорости):\n")
    for i, (api_name, answer, elapsed) in enumerate(results, 1):
        print(f"{i}. ⚡ {api_name} - {elapsed:.2f}с")
        print(f"   💬 {answer[:100]}...")
        print()

    fastest = results[0]
    print(f"🏆 ПОБЕДИТЕЛЬ: {fastest[0]} ({fastest[2]:.2f}с)")

    if len(results) > 1:
        diff = results[1][2] - results[0][2]
        print(f"⏱️  Разница: {diff:.2f}с быстрее!")


async def main():
    """Главная функция"""
    print("="*60)
    print("🧪 ТЕСТ ПАРАЛЛЕЛЬНОЙ РАБОТЫ OpenAI + Claude API")
    print("="*60)
    print()

    await test_parallel()

    print("\n" + "="*60)
    print("✅ Тест завершен!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
