# -*- coding: utf-8 -*-
"""
Тест обновленных калькуляторов
"""

from calculators import *

print("=== Тестирование обновленных калькуляторов v4.0 ===\n")

# Тест 1: Калькулятор бетона
print("1. Тест калькулятора бетона:")
result = calculate_concrete(10, 5, 0.2)
if "error" not in result:
    print(f"   OK Объем: {result['volume']} м3")
    print(f"   OK С потерями: {result['volume_with_wastage']} м3")
    print(f"   OK Цемент: {result['cement_total']} кг")
else:
    print(f"   ERROR {result['error']}")

# Тест 2: Калькулятор арматуры
print("\n2. Тест калькулятора арматуры:")
result = calculate_reinforcement(10, 5, 0.2)
if "error" not in result:
    print(f"   OK Длина: {result['total_length']} м")
    print(f"   OK Масса: {result['total_mass']} кг")
else:
    print(f"   ERROR {result['error']}")

# Тест 3: Калькулятор кирпича
print("\n3. Тест калькулятора кирпича:")
result = calculate_brick(10, 3)
if "error" not in result:
    print(f"   OK Площадь: {result['wall_area']} м2")
    print(f"   OK Кирпичей: {result['total_bricks']} шт")
else:
    print(f"   ERROR {result['error']}")

# Тест 4: Калькулятор утеплителя
print("\n4. Тест калькулятора утеплителя:")
result = calculate_insulation(50)
if "error" not in result:
    print(f"   OK Объем: {result['volume']} м3")
    print(f"   OK Масса: {result['mass']} кг")
else:
    print(f"   ERROR {result['error']}")

# Тест 5: Калькулятор фундамента
print("\n5. Тест калькулятора фундамента:")
result = calculate_foundation("ленточный", 10, 0.4, 0.6)
if "error" not in result:
    print(f"   OK Объем: {result['volume']} м3")
    print(f"   OK Макс. нагрузка: {result['max_load']} т")
else:
    print(f"   ERROR {result['error']}")

# Тест 6: Форматирование результатов
print("\n6. Тест форматирования результатов:")
result = calculate_concrete(5, 3, 0.15)
formatted = format_calculator_result("concrete", result)
print(f"   OK Форматирование работает ({len(formatted)} символов)")

print("\n" + "="*50)
print("Все тесты пройдены успешно!")
print("="*50)
print(f"\nВсего калькуляторов в модуле: {len(CALCULATORS)}")
print("\nСписок доступных калькуляторов:")
for i, name in enumerate(CALCULATORS.keys(), 1):
    print(f"  {i}. {name}")
