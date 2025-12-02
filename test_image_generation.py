"""
Тест генерации изображений через Gemini AI (fallback)
"""
import sys
import os

# Установка правильной директории
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.insert(0, script_dir)

from dotenv import load_dotenv
from image_generator import generate_construction_image

# Загрузка переменных окружения
env_path = os.path.join(script_dir, '.env')
load_dotenv(env_path)

def test_image_generation():
    """Тестируем генерацию изображения"""

    print("=== TEST IMAGE GENERATION (GEMINI FALLBACK) ===\n")

    # Проверяем наличие ключей
    import os
    print(f"OPENAI_API_KEY: {'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
    print(f"GEMINI_API_KEY: {'SET' if os.getenv('GEMINI_API_KEY') else 'NOT SET'}")

    # Тестируем инициализацию Gemini
    from image_generator import get_gemini_generator
    gen = get_gemini_generator()
    print(f"Gemini generator: {'LOADED' if gen else 'FAILED'}\n")

    # Тестовый запрос
    test_request = "три колодца соединены между собой в разрезе от здания"

    print(f"Request: {test_request}\n")
    print("Generating image (will use Gemini fallback since OPENAI_API_KEY is not set)...")

    # Включаем детальное логирование
    import logging
    logging.basicConfig(level=logging.INFO, force=True)

    try:
        result = generate_construction_image(test_request, use_hd=False)

        if result:
            print("\n[SUCCESS] Image generated!")
            print(f"  Model: {result.get('model')}")
            print(f"  Size: {result.get('size')}")
            print(f"  Quality: {result.get('quality')}")
            print(f"  Timestamp: {result.get('timestamp')}")

            # Проверяем наличие данных изображения
            if result.get('image_data'):
                image_data = result['image_data']
                print(f"  Image data size: {len(image_data.getvalue())} bytes")

                # Сохраняем для проверки
                output_path = "test_generated_image.png"
                with open(output_path, 'wb') as f:
                    f.write(image_data.getvalue())
                print(f"  Saved to: {output_path}")

                print("\n=== TEST PASSED ===")
            else:
                print("\n[ERROR] No image data in result")
        else:
            print("\n[ERROR] Generation failed - no result returned")

    except Exception as e:
        print(f"\n[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_image_generation()
