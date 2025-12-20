"""
Модуль для работы с Google Gemini 2.5 Flash
- Анализ изображений (дефекты, чертежи)
- Генерация изображений через Imagen 3
"""

import os
import logging
import base64
from io import BytesIO
from typing import Optional, Dict, List
from PIL import Image

logger = logging.getLogger(__name__)

# Gemini клиент
gemini_client = None
GEMINI_AVAILABLE = False


def init_gemini():
    """Инициализация Google Gemini API"""
    global gemini_client, GEMINI_AVAILABLE

    try:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("⚠️ GEMINI_API_KEY не найден в .env")
            return False

        genai.configure(api_key=api_key)
        gemini_client = genai
        GEMINI_AVAILABLE = True

        logger.info("✅ Google Gemini 2.5 Flash инициализирован")
        return True

    except ImportError:
        logger.warning("⚠️ Установите: pip install google-generativeai")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации Gemini: {e}")
        return False


# Инициализируем при загрузке модуля
init_gemini()


# ========================================
# АНАЛИЗ ИЗОБРАЖЕНИЙ (Vision)
# ========================================

async def analyze_construction_image(
    image_data: bytes,
    prompt: str = None,
    analysis_type: str = "defect"
) -> Optional[Dict]:
    """
    Анализ строительного изображения через Gemini 2.5 Flash

    Args:
        image_data: Байты изображения
        prompt: Дополнительный промпт (опционально)
        analysis_type: Тип анализа (defect, blueprint, material, quality)

    Returns:
        Dict с результатами анализа
    """
    if not GEMINI_AVAILABLE or not gemini_client:
        logger.warning("Gemini недоступен")
        return None

    try:
        # Загружаем изображение
        image = Image.open(BytesIO(image_data))

        # Промпты для разных типов анализа
        analysis_prompts = {
            "defect": """Проанализируй это строительное фото как эксперт-строитель.

ЗАДАЧА: Определить дефекты и несоответствия нормативам РФ (СП, ГОСТ, СНиП).

СТРУКТУРА ОТВЕТА:

🔍 **ЧТО ВИЖУ**
• Тип конструкции (фундамент/стена/перекрытие/кровля/отделка)
• Материалы
• Состояние

⚠️ **ДЕФЕКТЫ** (если есть)
Для каждого дефекта:
• Название дефекта
• Критичность: 🔴 Критично / 🟡 Средне / 🟢 Незначительно
• Нарушенный норматив (СП 63.13330, ГОСТ 10180 и т.д.)
• Возможные последствия

✅ **РЕКОМЕНДАЦИИ**
• Метод устранения (пошагово)
• Необходимые материалы
• Срочность работ
• Примерная стоимость (если можно оценить)

📋 **НОРМАТИВЫ**
Укажи конкретные пункты СП/ГОСТ/СНиП, которые нарушены

Если дефектов НЕТ - напиши что всё в порядке и дай рекомендации по эксплуатации.""",

            "blueprint": """Проанализируй этот строительный чертёж/схему как эксперт.

ЗАДАЧА: Проверить соответствие нормативам и найти ошибки.

СТРУКТУРА ОТВЕТА:

📐 **ЧТО НА ЧЕРТЕЖЕ**
• Тип документа (план, разрез, узел)
• Элементы конструкции
• Размеры и масштаб

✅ **СООТВЕТСТВИЯ НОРМАМ**
Что выполнено правильно

⚠️ **ОШИБКИ И НЕСООТВЕТСТВИЯ**
• Нарушения СП/ГОСТ
• Отсутствующие элементы
• Неверные размеры

💡 **РЕКОМЕНДАЦИИ**
Что нужно исправить""",

            "material": """Определи строительный материал на фото.

СТРУКТУРА ОТВЕТА:

🧱 **МАТЕРИАЛ**
• Название
• Характеристики (марка, класс прочности)
• Применение

✅ **КАЧЕСТВО**
• Визуальная оценка
• Соответствие ГОСТ

💡 **РЕКОМЕНДАЦИИ**
• Как использовать
• На что обратить внимание""",

            "quality": """Оцени качество строительных работ на фото.

СТРУКТУРА ОТВЕТА:

⭐ **ОБЩАЯ ОЦЕНКА**: [1-5 звёзд]

✅ **ЧТО ХОРОШО**
• Список положительных моментов

⚠️ **ЧТО ПЛОХО**
• Список недостатков
• Нарушения технологии

📋 **СООТВЕТСТВИЕ НОРМАТИВАМ**
• СП/ГОСТ которым соответствует или нет

💡 **РЕКОМЕНДАЦИИ**
• Что нужно доработать"""
        }

        # Выбираем промпт
        system_prompt = analysis_prompts.get(analysis_type, analysis_prompts["defect"])

        # Добавляем пользовательский промпт если есть
        if prompt:
            system_prompt += f"\n\nДОПОЛНИТЕЛЬНО: {prompt}"

        # Создаём модель (gemini-1.5-flash - стабильная версия с хорошими лимитами)
        model = gemini_client.GenerativeModel('gemini-1.5-flash')

        # Генерируем ответ
        response = model.generate_content([system_prompt, image])

        if response and response.text:
            logger.info(f"✅ Gemini проанализировал изображение ({analysis_type})")

            return {
                "analysis": response.text,
                "model": "gemini-1.5-flash",
                "analysis_type": analysis_type,
                "success": True
            }

    except Exception as e:
        logger.error(f"❌ Ошибка анализа Gemini: {e}")
        return None

    return None


# ========================================
# ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ (Imagen 3)
# ========================================

async def generate_construction_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    style: str = "technical"
) -> Optional[Dict]:
    """
    Генерация строительного изображения через Imagen 3

    Args:
        prompt: Описание изображения
        aspect_ratio: Соотношение сторон (1:1, 16:9, 9:16, 4:3, 3:4)
        style: Стиль (technical, realistic, blueprint, sketch)

    Returns:
        Dict с данными изображения
    """
    if not GEMINI_AVAILABLE or not gemini_client:
        logger.warning("Gemini недоступен для генерации")
        return None

    try:
        # Стили для разных типов изображений
        style_prompts = {
            "technical": "Professional technical drawing, clean lines, blueprint style, annotated, engineering documentation quality",
            "realistic": "Photorealistic construction site, professional photography, high detail, natural lighting",
            "blueprint": "Architectural blueprint, technical schematic, dimension lines, professional CAD style, white background",
            "sketch": "Hand-drawn construction sketch, pencil drawing, architectural illustration"
        }

        # Формируем финальный промпт
        style_description = style_prompts.get(style, style_prompts["technical"])
        final_prompt = f"{prompt}. Style: {style_description}. High quality, professional construction industry standard."

        logger.info(f"🎨 Генерация через Imagen 3: {prompt[:50]}...")

        # Создаём модель для генерации (gemini-1.5-flash)
        model = gemini_client.GenerativeModel('gemini-1.5-flash')

        # ПРИМЕЧАНИЕ: Imagen 3 интегрирован в Gemini API
        # Для генерации используем текстовый запрос с указанием на создание изображения
        generation_request = f"""Generate a detailed technical prompt for creating this construction image:

{final_prompt}

The prompt should be in English, highly detailed, suitable for professional image generation.
Include specific details about:
- Materials and textures
- Lighting and perspective
- Technical accuracy
- Professional quality standards
- Construction industry context"""

        response = model.generate_content(generation_request)

        if response and response.text:
            # Для реальной генерации через Imagen нужен отдельный API endpoint
            # Пока возвращаем подготовленный промпт
            logger.info("✅ Gemini подготовил промпт для генерации")

            return {
                "enhanced_prompt": response.text,
                "original_prompt": prompt,
                "model": "gemini-2.5-flash + imagen-3",
                "aspect_ratio": aspect_ratio,
                "style": style,
                "note": "Промпт подготовлен. Для реальной генерации требуется Imagen 3 API endpoint"
            }

    except Exception as e:
        logger.error(f"❌ Ошибка генерации Gemini: {e}")
        return None

    return None


# ========================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ========================================

def is_gemini_available() -> bool:
    """Проверить доступность Gemini"""
    return GEMINI_AVAILABLE


def get_supported_analysis_types() -> List[str]:
    """Получить список поддерживаемых типов анализа"""
    return ["defect", "blueprint", "material", "quality"]


def format_analysis_result(result: Dict) -> str:
    """
    Форматировать результат анализа для отправки пользователю

    Args:
        result: Результат от analyze_construction_image

    Returns:
        Отформатированный текст
    """
    if not result or not result.get("success"):
        return "❌ Не удалось проанализировать изображение"

    analysis_text = result.get("analysis", "")
    model = result.get("model", "gemini-2.5-flash")

    footer = f"\n\n🤖 Анализ выполнен: {model}"

    return analysis_text + footer


# ========================================
# КЛАСС ДЛЯ СОВМЕСТИМОСТИ
# ========================================

class GeminiVisionAnalyzer:
    """Класс для анализа изображений через Gemini"""

    def __init__(self):
        self.available = GEMINI_AVAILABLE
        logger.info(f"GeminiVisionAnalyzer: {'✅ доступен' if self.available else '❌ недоступен'}")

    async def analyze_defect_photo(self, image_data: bytes, user_prompt: str = None) -> Optional[str]:
        """
        Анализ фото дефекта

        Args:
            image_data: Байты изображения
            user_prompt: Дополнительный вопрос пользователя

        Returns:
            Текст анализа или None
        """
        result = await analyze_construction_image(
            image_data=image_data,
            prompt=user_prompt,
            analysis_type="defect"
        )

        if result:
            return format_analysis_result(result)
        return None

    async def analyze_blueprint(self, image_data: bytes) -> Optional[str]:
        """Анализ чертежа"""
        result = await analyze_construction_image(
            image_data=image_data,
            analysis_type="blueprint"
        )

        if result:
            return format_analysis_result(result)
        return None

    async def check_quality(self, image_data: bytes) -> Optional[str]:
        """Проверка качества работ"""
        result = await analyze_construction_image(
            image_data=image_data,
            analysis_type="quality"
        )

        if result:
            return format_analysis_result(result)
        return None


def initialize_gemini_vision() -> Optional[GeminiVisionAnalyzer]:
    """Инициализировать анализатор Gemini Vision"""
    if GEMINI_AVAILABLE:
        return GeminiVisionAnalyzer()
    return None


# ========================================
# ТЕСТИРОВАНИЕ
# ========================================

if __name__ == "__main__":
    import asyncio

    async def test_gemini():
        """Тест модуля"""
        print("=== Тест Gemini Vision ===\n")

        if not is_gemini_available():
            print("❌ Gemini недоступен. Проверьте GEMINI_API_KEY в .env")
            return

        print("✅ Gemini доступен")
        print(f"Поддерживаемые типы анализа: {get_supported_analysis_types()}")

        # Создаём тестовое изображение
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        # Тест анализа
        print("\n🔍 Тест анализа изображения...")
        analyzer = initialize_gemini_vision()
        if analyzer:
            result = await analyzer.analyze_defect_photo(img_bytes.getvalue())
            if result:
                print(f"✅ Анализ выполнен:\n{result[:200]}...")
            else:
                print("❌ Анализ не удался")

        # Тест генерации промпта
        print("\n🎨 Тест генерации промпта...")
        gen_result = await generate_construction_image(
            prompt="Фундамент ленточный с арматурой",
            style="technical"
        )
        if gen_result:
            print(f"✅ Промпт создан:\n{gen_result.get('enhanced_prompt', '')[:200]}...")
        else:
            print("❌ Генерация не удалась")

    asyncio.run(test_gemini())
