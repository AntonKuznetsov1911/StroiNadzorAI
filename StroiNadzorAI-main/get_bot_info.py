"""Получить информацию о боте"""
import os
from dotenv import load_dotenv
import requests

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8405009065:AAFiwfbUE8BW8T7OjVq26WoMw3kpVXdHISQ")

# Запрос к API Telegram
response = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe")
data = response.json()

if data.get("ok"):
    bot_info = data.get("result")
    print("=" * 60)
    print("  ИНФОРМАЦИЯ О ВАШЕМ TELEGRAM БОТЕ")
    print("=" * 60)
    print()
    print(f"Имя бота: {bot_info.get('first_name')}")
    print(f"Username: @{bot_info.get('username')}")
    print(f"ID: {bot_info.get('id')}")
    print()
    print("Ссылка для открытия бота в Telegram:")
    print(f"https://t.me/{bot_info.get('username')}")
    print()
    print("=" * 60)
    print("  ИНСТРУКЦИЯ:")
    print("=" * 60)
    print()
    print("1. Запустите бота: python bot.py")
    print("   или двойной клик на start_bot.bat")
    print()
    print("2. Откройте ссылку выше в браузере")
    print("   или найдите бота в Telegram по username")
    print()
    print("3. Нажмите кнопку 'Start' в Telegram")
    print()
    print("4. Готово! Бот работает!")
    print()
else:
    print(f"Ошибка: {data}")
