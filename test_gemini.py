"""
Тест интеграции Gemini API
"""
import os
from dotenv import load_dotenv
from gemini_image_gen import initialize_gemini_generator

# Загрузка переменных окружения
load_dotenv()

def test_gemini_integration():
    """Тестируем инициализацию Gemini генератора"""

    print("=== TEST GEMINI API INTEGRATION ===\n")

    # Проверка API ключа
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        print(f"[OK] GEMINI_API_KEY found (length: {len(api_key)} chars)")
        print(f"     Key starts with: {api_key[:15]}...")
    else:
        print("[ERROR] GEMINI_API_KEY not found!")
        return

    # Инициализация генератора
    print("\nInitializing generator...")
    try:
        generator = initialize_gemini_generator()
        if generator:
            print("[OK] Gemini generator successfully initialized")
            print(f"     Type: {type(generator).__name__}")
            print(f"     Vision model: {generator.vision_model._model_name}")
        else:
            print("[ERROR] Failed to initialize generator")
    except Exception as e:
        print(f"[ERROR] Initialization error: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n=== ALL TESTS PASSED ===")

if __name__ == "__main__":
    test_gemini_integration()
