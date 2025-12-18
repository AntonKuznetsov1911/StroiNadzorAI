"""Простой тест запуска бота"""
import os
import sys

print("=== ТЕСТ ЗАПУСКА БОТА ===")
print(f"Python версия: {sys.version}")
print(f"Рабочая директория: {os.getcwd()}")
print()

# Проверка .env
print("1. Проверка .env файла...")
if os.path.exists('.env'):
    print("   ✅ .env найден")
    from dotenv import load_dotenv
    load_dotenv()

    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')

    print(f"   TELEGRAM_BOT_TOKEN: {'✅ Установлен' if telegram_token else '❌ Отсутствует'}")
    print(f"   ANTHROPIC_API_KEY: {'✅ Установлен' if anthropic_key else '❌ Отсутствует'}")
else:
    print("   ❌ .env не найден!")
    sys.exit(1)

print()

# Проверка импорта telegram
print("2. Проверка библиотеки telegram...")
try:
    from telegram import Update
    print("   ✅ telegram импортирован")
except Exception as e:
    print(f"   ❌ Ошибка: {e}")
    sys.exit(1)

print()

# Проверка импорта anthropic
print("3. Проверка библиотеки anthropic...")
try:
    import anthropic
    print("   ✅ anthropic импортирован")
except Exception as e:
    print(f"   ❌ Ошибка: {e}")
    sys.exit(1)

print()

# Попытка импорта bot
print("4. Попытка импорта bot.py...")
try:
    import bot
    print("   ✅ bot.py импортирован успешно")
except Exception as e:
    print(f"   ❌ Ошибка импорта: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=== ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ ===")
print()
print("Попытка запуска бота...")
try:
    bot.main()
except Exception as e:
    print(f"❌ Ошибка запуска: {e}")
    import traceback
    traceback.print_exc()
