"""
Модуль для генерации изображений через Gemini 2.5 Flash Image
Поддержка: Google Gemini с генерацией изображений
"""

import os
import logging
import asyncio
from io import BytesIO
from typing import Optional, Dict, Union
from PIL import Image

logger = logging.getLogger(__name__)

# ========================================
# ИНИЦИАЛИЗАЦИЯ ДВИЖКА ГЕНЕРАЦИИ
# ========================================

# Gemini модель
gemini_model = None
GEMINI_IMAGE_ENABLED = False

# Движок генерации
IMAGE_ENGINE = None


def init_gemini_image():
    """Инициализация Gemini Image Generation"""
    global gemini_model, GEMINI_IMAGE_ENABLED

    try:
        import google.generativeai as genai

        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            gemini_model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
            GEMINI_IMAGE_ENABLED = True
            logger.info("✅ Gemini 2.5 Flash Image инициализирован")
            return True
        else:
            logger.warning("⚠️ GOOGLE_API_KEY не найден")
    except ImportError:
        logger.debug("google-generativeai не установлен")
    except Exception as e:
        logger.warning(f"Ошибка инициализации Gemini Image: {e}")

    return False


def init_image_engine():
    """Инициализация движка генерации изображений"""
    global IMAGE_ENGINE

    # Используем Gemini 2.5 Flash Image
    if init_gemini_image():
        IMAGE_ENGINE = "gemini"
        logger.info("🎨 Движок генерации: Gemini 2.5 Flash Image")
        return True

    logger.warning("⚠️ Генерация изображений отключена (нужен GOOGLE_API_KEY)")
    return False


# Инициализируем при загрузке модуля
init_image_engine()


# ========================================
# ГЕНЕРАЦИЯ ЧЕРЕЗ GEMINI
# ========================================

async def generate_with_gemini(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "standard"
) -> Optional[Dict]:
    """
    Генерация изображения через Gemini 2.5 Flash Image

    Args:
        prompt: Описание изображения
        size: Размер (не используется напрямую, Gemini определяет сам)
        quality: Качество (standard, hd)

    Returns:
        Dict с image_data, text, model
    """
    if not GEMINI_IMAGE_ENABLED or not gemini_model:
        return None

    try:
        import google.generativeai as genai

        # Формируем промпт для генерации технического чертежа
        full_prompt = f"""Создай профессиональный технический чертёж для строительства:

{prompt}

Требования:
- Стиль технического чертежа (blueprint) с точными размерами
- Соответствие ГОСТ (российские строительные стандарты)
- Чёткие размерные линии со стрелками
- Спецификации материалов и подписи на русском языке
- Высокая детализация, инженерное качество
- Указание масштаба (1:20, 1:50 и т.д.)
- Штриховка по ГОСТ 2.306"""

        logger.info("🎨 Генерируем изображение через Gemini 2.5 Flash...")

        loop = asyncio.get_event_loop()

        def _generate():
            response = gemini_model.generate_content(
                full_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=8192,
                    response_modalities=["TEXT", "IMAGE"]
                )
            )
            return response

        response = await loop.run_in_executor(None, _generate)

        # Извлекаем изображение из ответа
        image_data = None
        description = ""

        for part in response.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                image_bytes = part.inline_data.data
                image_data = BytesIO(image_bytes)
                image_data.name = "drawing.png"
                logger.info(f"✅ Изображение получено ({len(image_bytes)} байт)")
            elif hasattr(part, 'text'):
                description = part.text

        if image_data:
            return {
                "image_data": image_data,
                "text": description,
                "model": "gemini-2.5-flash",
                "engine": "gemini",
                "prompt": prompt
            }

        # Если изображение не получено
        logger.warning("⚠️ Gemini не вернул изображение, только текст")
        return None

    except Exception as e:
        logger.error(f"Ошибка Gemini Image: {e}")

    return None


# ========================================
# ОСНОВНЫЕ ФУНКЦИИ
# ========================================

async def generate_construction_image_gemini(
    user_request: str,
    reference_image: bytes = None,
    size: str = "1024x1024",
    quality: str = "standard"
) -> Optional[Dict]:
    """
    Генерирует строительное изображение через Gemini 2.5 Flash Image

    Args:
        user_request: Запрос пользователя
        reference_image: Референсное изображение (не используется)
        size: Размер изображения
        quality: Качество (standard/hd)

    Returns:
        Dict с image_data, text, model, engine
    """
    if not IMAGE_ENGINE:
        logger.warning("Генерация изображений недоступна (нужен GOOGLE_API_KEY)")
        return None

    logger.info(f"🎨 Генерация изображения: {user_request[:100]}...")

    result = await generate_with_gemini(user_request, size, quality)

    if result:
        logger.info("✅ Изображение сгенерировано через Gemini")

    return result


def is_image_generation_available() -> bool:
    """Проверить доступность генерации изображений"""
    return IMAGE_ENGINE is not None


def get_image_engine() -> Optional[str]:
    """Получить текущий движок генерации"""
    return IMAGE_ENGINE


# ========================================
# КЛАСС ДЛЯ СОВМЕСТИМОСТИ С BOT.PY
# ========================================

class GeminiImageGenerator:
    """Класс для генерации изображений через Gemini"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        logger.info(f"ImageGenerator: движок = {IMAGE_ENGINE}")

    async def generate_image(
        self,
        prompt: str,
        reference_image: Optional[Union[bytes, Image.Image]] = None,
        aspect_ratio: str = "1:1",
        style: str = "technical"
    ) -> Optional[Dict]:
        """Генерирует изображение"""
        return await generate_construction_image_gemini(prompt)

    async def generate_construction_scheme(
        self,
        description: str,
        scheme_type: str = "general"
    ) -> Optional[Dict]:
        """Генерирует строительную схему"""
        scheme_prompts = {
            "foundation": "Чертёж фундамента: поперечное сечение, армирование, размеры",
            "wall": "Чертёж стены: слои, утепление, привязка к осям",
            "roof": "Чертёж крыши: стропильная система, утепление, узлы",
            "electrical": "Электрическая схема: проводка, щиток, розетки",
            "plumbing": "Схема водоснабжения: трубы, разводка, подключения",
            "general": "Технический строительный чертёж"
        }

        base = scheme_prompts.get(scheme_type, scheme_prompts["general"])
        prompt = f"{base}: {description}"

        return await generate_construction_image_gemini(prompt)

    async def visualize_defect(
        self,
        defect_description: str,
        defect_photo: Optional[bytes] = None
    ) -> Optional[Dict]:
        """Визуализирует строительный дефект"""
        prompt = f"""Техническая иллюстрация строительного дефекта:
{defect_description}

Стиль: техническая схема с аннотациями, стрелками к дефектам,
размерными указателями, в стиле акта строительной инспекции.
Подписи на русском языке с описанием дефекта и рекомендуемых мер."""

        return await generate_construction_image_gemini(prompt)


def initialize_gemini_generator() -> Optional[GeminiImageGenerator]:
    """Инициализирует генератор изображений"""
    if IMAGE_ENGINE:
        return GeminiImageGenerator()
    return None
