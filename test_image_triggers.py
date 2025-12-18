"""
Тест триггеров генерации изображений
"""

from image_generator import should_generate_image

print("=" * 60)
print("ТЕСТ ТРИГГЕРОВ ГЕНЕРАЦИИ ИЗОБРАЖЕНИЙ")
print("=" * 60)

test_messages = [
    ("Можешь прислать картинку с примером где от здания три колодца", True),
    ("нарисуй трещину в стене", True),
    ("покажи как выглядит дефект", True),
    ("пришли изображение фундамента", True),
    ("отправь картинку узла", True),
    ("можешь показать картинку балки", True),
    ("хочу увидеть арматуру", True),
    ("нужна картинка колонны", True),
    ("какой бетон нужен для фундамента?", False),
    ("СП 63.13330.2018 актуальный?", False),
    ("расскажи про СНиП", False),
]

print("\nПроверка триггеров:\n")

success = 0
fail = 0

for message, expected in test_messages:
    result = should_generate_image(message)
    status = "[OK]" if result == expected else "[FAIL]"

    if result == expected:
        success += 1
    else:
        fail += 1

    print(f"{status} '{message}'")
    print(f"     Ожидалось: {expected}, Получено: {result}\n")

print("=" * 60)
print(f"Результаты: {success} успешных, {fail} неудачных")
print("=" * 60)

if fail == 0:
    print("\n✓ Все тесты пройдены!")
else:
    print(f"\n✗ {fail} тестов провалено")
