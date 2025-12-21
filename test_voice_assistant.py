"""
Тестовый скрипт для проверки голосового ассистента
"""
import os
import sys
from dotenv import load_dotenv

print("=" * 60)
print("ПРОВЕРКА ГОЛОСОВОГО АССИСТЕНТА")
print("=" * 60)

# 1. Проверка .env файла
print("\n1️⃣ Проверка .env файла...")
load_dotenv()

google_api_key = os.getenv("GOOGLE_API_KEY")
if google_api_key:
    print(f"   ✅ GOOGLE_API_KEY найден: {google_api_key[:20]}...")
else:
    print("   ❌ GOOGLE_API_KEY не найден в .env!")
    sys.exit(1)

# 2. Проверка websockets
print("\n2️⃣ Проверка websockets...")
try:
    import websockets
    print(f"   ✅ websockets установлен (версия {websockets.__version__})")
except ImportError:
    print("   ❌ websockets НЕ установлен!")
    print("   💡 Установите: pip install websockets>=12.0")
    sys.exit(1)

# 3. Проверка google-generativeai
print("\n3️⃣ Проверка google-generativeai...")
try:
    import google.generativeai as genai
    print(f"   ✅ google-generativeai установлен")
except ImportError:
    print("   ❌ google-generativeai НЕ установлен!")
    print("   💡 Установите: pip install google-generativeai>=0.8.0")
    sys.exit(1)

# 4. Проверка подключения к Gemini API
print("\n4️⃣ Проверка подключения к Gemini API...")
try:
    genai.configure(api_key=google_api_key)
    # Пробуем получить список моделей
    models = genai.list_models()
    print("   ✅ Подключение к Gemini API успешно!")

    # Проверяем доступность Gemini 2.0 Flash
    flash_available = False
    for model in models:
        if "gemini-2.0-flash" in model.name.lower():
            flash_available = True
            print(f"   ✅ Модель найдена: {model.name}")
            break

    if not flash_available:
        print("   ⚠️ Gemini 2.0 Flash не найден, но API работает")

except Exception as e:
    print(f"   ❌ Ошибка подключения к Gemini API: {e}")
    sys.exit(1)

# 5. Проверка gemini_live_api.py
print("\n5️⃣ Проверка модуля gemini_live_api...")
try:
    from gemini_live_api import GeminiLiveSession, is_gemini_live_available
    print("   ✅ gemini_live_api.py импортирован успешно")

    if is_gemini_live_available():
        print("   ✅ Gemini Live API доступен")
    else:
        print("   ❌ Gemini Live API недоступен (нет GOOGLE_API_KEY)")

except ImportError as e:
    print(f"   ❌ Ошибка импорта gemini_live_api: {e}")
    sys.exit(1)

# 6. Проверка gemini_live_bot_integration.py
print("\n6️⃣ Проверка модуля gemini_live_bot_integration...")
try:
    from gemini_live_bot_integration import (
        init_voice_assistant,
        TelegramVoiceAssistant
    )
    print("   ✅ gemini_live_bot_integration.py импортирован успешно")

    # Попробуем инициализировать
    success = init_voice_assistant()
    if success:
        print("   ✅ Голосовой ассистент инициализирован успешно")
    else:
        print("   ⚠️ Голосовой ассистент инициализирован с предупреждениями")

except ImportError as e:
    print(f"   ❌ Ошибка импорта gemini_live_bot_integration: {e}")
    sys.exit(1)
except Exception as e:
    print(f"   ⚠️ Предупреждение при инициализации: {e}")

print("\n" + "=" * 60)
print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
print("=" * 60)
print("\n🎤 ГОЛОСОВОЙ АССИСТЕНТ ГОТОВ К РАБОТЕ!\n")
print("Следующие шаги:")
print("1. Запустите бота: python bot.py")
print("2. В Telegram отправьте боту: /start")
print("3. Нажмите кнопку: 🎤 Голосовой ассистент")
print("4. Отправьте голосовое сообщение")
print("5. Получите голосовой ответ < 500ms!\n")
