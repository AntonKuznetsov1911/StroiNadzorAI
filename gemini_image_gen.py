"""
Модуль для генерации изображений
Поддержка: OpenAI DALL-E 3
"""

import os
import logging
import asyncio
import httpx
from io import BytesIO
from typing import Optional, Dict, Union
from PIL import Image

logger = logging.getLogger(__name__)

# ========================================
# ИНИЦИАЛИЗАЦИЯ ДВИЖКА ГЕНЕРАЦИИ
# ========================================

# OpenAI клиент
openai_client = None
OPENAI_IMAGE_ENABLED = False

# Движок генерации
IMAGE_ENGINE = None


def init_openai_image():
    """Инициализация OpenAI DALL-E"""
    global openai_client, OPENAI_IMAGE_ENABLED

    try:
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            openai_client = OpenAI(api_key=api_key)
            OPENAI_IMAGE_ENABLED = True
            logger.info("✅ OpenAI DALL-E инициализирован")
            return True
    except ImportError:
        logger.debug("openai не установлен")
    except Exception as e:
        logger.warning(f"Ошибка инициализации OpenAI: {e}")

    return False


def init_image_engine():
    """Инициализация движка генерации изображений"""
    global IMAGE_ENGINE

    # Пробуем OpenAI DALL-E
    if init_openai_image():
        IMAGE_ENGINE = "openai"
        logger.info("🎨 Движок генерации: OpenAI DALL-E 3")
        return True

    logger.warning("⚠️ Генерация изображений отключена (нужен OPENAI_API_KEY)")
    return False


# Инициализируем при загрузке модуля
init_image_engine()


# ========================================
# ГЕНЕРАЦИЯ ЧЕРЕЗ OPENAI DALL-E
# ========================================

async def generate_with_openai(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "standard",
    style: str = "natural"
) -> Optional[Dict]:
    """
    Генерация изображения через OpenAI DALL-E 3

    Args:
        prompt: Описание изображения
        size: Размер (1024x1024, 1024x1792, 1792x1024)
        quality: Качество (standard, hd)
        style: Стиль (natural, vivid)

    Returns:
        Dict с image_data, text, model
    """
    if not OPENAI_IMAGE_ENABLED or not openai_client:
        return None

    try:
        # Проверяем, является ли промпт уже детальным техническим
        # (от xAI Grok - содержит "dimension lines", "annotated", "scale")
        is_technical_prompt = any(keyword in prompt.lower() for keyword in
                                  ["dimension lines", "annotated", "scale", "measurements labeled", "technical"])

        if is_technical_prompt:
            # Используем промпт как есть (от xAI Grok)
            final_prompt = prompt[:4000]  # DALL-E 3 limit
            logger.info("📐 Используем детальный технический промпт от xAI Grok")
        else:
            # Старый механизм для простых запросов
            final_prompt = f"""Professional construction technical illustration:
{prompt}

Style: Clean technical drawing, blueprint style, professional engineering documentation.
Include measurement annotations and labels in Russian where appropriate.
High quality, detailed, suitable for technical documentation."""[:4000]
            logger.info("📝 Используем стандартный промпт с улучшением")

        loop = asyncio.get_event_loop()

        def _generate():
            response = openai_client.images.generate(
                model="dall-e-3",
                prompt=final_prompt,
                size=size,
                quality=quality,
                style=style,
                n=1
            )
            return response

        response = await loop.run_in_executor(None, _generate)

        if response.data and len(response.data) > 0:
            image_url = response.data[0].url
            revised_prompt = response.data[0].revised_prompt

            # Скачиваем изображение
            async with httpx.AsyncClient() as client:
                img_response = await client.get(image_url)
                img_data = BytesIO(img_response.content)
                img_data.seek(0)

            logger.info("✅ Изображение сгенерировано через DALL-E 3")

            return {
                "image_data": img_data,
                "text": revised_prompt or "",
                "model": "dall-e-3",
                "engine": "openai",
                "prompt": prompt
            }

    except Exception as e:
        logger.error(f"Ошибка DALL-E: {e}")

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
    Генерирует строительное изображение через OpenAI DALL-E 3

    Args:
        user_request: Запрос пользователя
        reference_image: Референсное изображение (не используется в DALL-E)
        size: Размер изображения
        quality: Качество (standard/hd)

    Returns:
        Dict с image_data, text, model, engine
    """
    if not IMAGE_ENGINE:
        logger.warning("Генерация изображений недоступна (нужен OPENAI_API_KEY)")
        return None

    logger.info(f"🎨 Генерация изображения: {user_request[:100]}...")

    result = await generate_with_openai(user_request, size, quality)

    if result:
        logger.info("✅ Изображение сгенерировано")

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
    """Класс для генерации изображений (совместимость с bot.py)"""

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
            "foundation": "technical blueprint of foundation, cross-section, reinforcement",
            "wall": "technical blueprint of wall structure, layers, insulation",
            "roof": "technical blueprint of roof structure, rafters, insulation",
            "electrical": "electrical wiring diagram, circuit layout",
            "plumbing": "plumbing system diagram, pipes layout",
            "general": "technical construction blueprint"
        }

        base = scheme_prompts.get(scheme_type, scheme_prompts["general"])
        prompt = f"{base}: {description}, clean technical drawing, labeled parts, measurements"

        return await generate_construction_image_gemini(prompt)

    async def visualize_defect(
        self,
        defect_description: str,
        defect_photo: Optional[bytes] = None
    ) -> Optional[Dict]:
        """Визуализирует строительный дефект"""
        prompt = f"""Technical illustration of construction defect:
{defect_description}

Style: technical diagram with annotations, arrows pointing to defects,
measurement indicators, professional inspection report style.
Labels in Russian explaining the defect and recommended repairs."""

        return await generate_construction_image_gemini(prompt)


def initialize_gemini_generator() -> Optional[GeminiImageGenerator]:
    """Инициализирует генератор изображений"""
    if IMAGE_ENGINE:
        return GeminiImageGenerator()
    return None
