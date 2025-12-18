"""
Тестирование модуля веб-поиска нормативов
"""

from web_search import (
    search_regulation_cntd,
    search_minstroy_news,
    should_perform_web_search,
    extract_regulation_codes,
    perform_web_search
)

print("=" * 60)
print("ТЕСТ 1: Определение необходимости веб-поиска")
print("=" * 60)

test_messages = [
    "какой бетон нужен для фундамента?",  # False
    "актуальный СП 63.13330.2018",  # True
    "новые требования 2025",  # True
    "что такое СНиП?",  # False
]

for msg in test_messages:
    result = should_perform_web_search(msg)
    print(f"'{msg}' => {result}")

print("\n" + "=" * 60)
print("ТЕСТ 2: Извлечение кодов нормативов")
print("=" * 60)

test_texts = [
    "Нужен СП 63.13330.2018 и ГОСТ 31937-2011",
    "Согласно СНиП 2.01.07-85",
    "Обычный текст без нормативов"
]

for text in test_texts:
    codes = extract_regulation_codes(text)
    print(f"'{text}' => {codes}")

print("\n" + "=" * 60)
print("ТЕСТ 3: Поиск норматива на docs.cntd.ru")
print("=" * 60)

regulation = search_regulation_cntd("СП 63.13330.2018")
if regulation:
    print(f"[OK] Найден: {regulation['title']}")
    print(f"     Статус: {regulation['status']}")
    print(f"     Ссылка: {regulation['link']}")
else:
    print("[FAIL] Норматив не найден (возможен таймаут подключения)")

print("\n" + "=" * 60)
print("ТЕСТ 4: Комплексный веб-поиск")
print("=" * 60)

test_query = "актуальные требования СП 63.13330.2018 в 2025 году"
results = perform_web_search(test_query)

if results:
    print("[OK] Результаты веб-поиска:")
    print(results)
else:
    print("[FAIL] Результаты не найдены (возможен таймаут подключения)")

print("\n" + "=" * 60)
print("Тестирование завершено")
print("=" * 60)
