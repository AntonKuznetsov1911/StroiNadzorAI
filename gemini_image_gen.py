"""
Модуль для генерации изображений
Поддержка: OpenAI DALL-E 3, Google Gemini
"""

import os
import logging
import asyncio
import base64
import httpx
from io import BytesIO
from typing import Optional, Dict, Union
from PIL import Image

logger = logging.getLogger(__name__)

# ========================================
# ИНИЦИАЛИЗАЦИЯ ДВИЖКОВ ГЕНЕРАЦИИ
# ========================================

# OpenAI клиент
openai_client = None
OPENAI_IMAGE_ENABLED = False

# Gemini клиент
gemini_client = None
GEMINI_IMAGE_ENABLED = False

# Приоритет: 1) OpenAI DALL-E  2) Gemini
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


def init_gemini_image():
    """Инициализация Gemini для генерации изображений"""
    global gemini_client, GEMINI_IMAGE_ENABLED

    try:
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key:
            gemini_client = genai.Client(api_key=api_key)
            GEMINI_IMAGE_ENABLED = True
            logger.info("✅ Gemini Image инициализирован")
            return True
    except ImportError:
        logger.debug("google-genai не установлен")
    except Exception as e:
        logger.warning(f"Ошибка инициализации Gemini: {e}")

    return False


def init_image_engine():
    """Инициализация движка генерации изображений"""
    global IMAGE_ENGINE

    # Пробуем OpenAI DALL-E (приоритет)
    if init_openai_image():
        IMAGE_ENGINE = "openai"
        logger.info("🎨 Движок генерации: OpenAI DALL-E 3")
        return True

    # Пробуем Gemini
    if init_gemini_image():
        IMAGE_ENGINE = "gemini"
        logger.info("🎨 Движок генерации: Gemini")
        return True

    logger.warning("⚠️ Генерация изображений отключена (нет доступных движков)")
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
        # Улучшаем промпт для строительной тематики
        enhanced_prompt = f"""Professional construction technical illustration:
{prompt}

Style: Clean technical drawing, blueprint style, professional engineering documentation.
Include measurement annotations and labels in Russian where appropriate.
High quality, detailed, suitable for technical documentation."""

        loop = asyncio.get_event_loop()

        def _generate():
            response = openai_client.images.generate(
                model="dall-e-3",
                prompt=enhanced_prompt[:4000],  # DALL-E 3 limit
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
# ГЕНЕРАЦИЯ ЧЕРЕЗ GEMINI
# ========================================

async def generate_with_gemini(
    prompt: str,
    reference_image: Optional[bytes] = None
) -> Optional[Dict]:
    """
    Генерация изображения через Gemini

    Args:
        prompt: Описание изображения
        reference_image: Референсное изображение (опционально)

    Returns:
        Dict с image_data, text, model
    """
    if not GEMINI_IMAGE_ENABLED or not gemini_client:
        return None

    try:
        from google.genai import types

        # Улучшаем промпт
        enhanced_prompt = f"""Construction industry visualization:
{prompt}

Style: Professional technical drawing, blueprint style, clean lines, measurement annotations.
Quality: High resolution, suitable for technical documentation.
Language: Include Russian labels and annotations where appropriate."""

        contents = [enhanced_prompt]

        if reference_image:
            ref_img = Image.open(BytesIO(reference_image))
            contents.insert(0, ref_img)

        loop = asyncio.get_event_loop()

        def _generate():
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash-preview-image-generation",
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE']
                )
            )
            return response

        response = await loop.run_in_executor(None, _generate)

        result = {"image_data": None, "text": "", "model": "gemini-2.5-flash", "engine": "gemini"}

        for part in response.parts:
            if part.text is not None:
                result["text"] = part.text
            elif part.inline_data is not None:
                image = part.as_image()
                img_buffer = BytesIO()
                image.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                result["image_data"] = img_buffer
                logger.info("✅ Изображение сгенерировано через Gemini")

        return result if result["image_data"] else None

    except Exception as e:
        logger.error(f"Ошибка Gemini: {e}")

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
    Генерирует строительное изображение

    Приоритет движков:
    1. OpenAI DALL-E 3 (лучшее качество)
    2. Gemini (бесплатный)

    Args:
        user_request: Запрос пользователя
        reference_image: Референсное изображение
        size: Размер изображения
        quality: Качество (standard/hd)

    Returns:
        Dict с image_data, text, model, engine
    """
    if not IMAGE_ENGINE:
        logger.warning("Генерация изображений недоступна")
        return None

    logger.info(f"🎨 Генерация изображения ({IMAGE_ENGINE}): {user_request[:100]}...")

    # Используем выбранный движок
    if IMAGE_ENGINE == "openai":
        result = await generate_with_openai(user_request, size, quality)
        # Fallback на Gemini
        if not result and GEMINI_IMAGE_ENABLED:
            logger.info("OpenAI не сработал, пробуем Gemini...")
            result = await generate_with_gemini(user_request, reference_image)

    elif IMAGE_ENGINE == "gemini":
        result = await generate_with_gemini(user_request, reference_image)

    else:
        result = None

    if result:
        logger.info(f"✅ Изображение сгенерировано ({result.get('engine', '?')})")

    return result


def is_image_generation_available() -> bool:
    """Проверить доступность генерации изображений"""
    return IMAGE_ENGINE is not None


def get_image_engine() -> Optional[str]:
    """Получить текущий движок генерации"""
    return IMAGE_ENGINE


# ========================================
# КЛАСС ДЛЯ СОВМЕСТИМОСТИ
# ========================================

class GeminiImageGenerator:
    """Класс для генерации изображений (совместимость с bot.py)"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        logger.info(f"GeminiImageGenerator: движок = {IMAGE_ENGINE}")

    async def generate_image(
        self,
        prompt: str,
        reference_image: Optional[Union[bytes, Image.Image]] = None,
        aspect_ratio: str = "1:1",
        style: str = "technical"
    ) -> Optional[Dict]:
        """Генерирует изображение"""
        ref_bytes = None
        if reference_image:
            if isinstance(reference_image, Image.Image):
                buf = BytesIO()
                reference_image.save(buf, format='PNG')
                ref_bytes = buf.getvalue()
            else:
                ref_bytes = reference_image

        return await generate_construction_image_gemini(prompt, ref_bytes)

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

        return await generate_construction_image_gemini(prompt, defect_photo)

    async def analyze_image(
        self,
        image: Union[bytes, Image.Image],
        analysis_prompt: str = None
    ) -> Optional[str]:
        """Анализирует изображение"""
        if not GEMINI_IMAGE_ENABLED:
            return None

        try:
            if isinstance(image, bytes):
                img = Image.open(BytesIO(image))
            else:
                img = image

            prompt = analysis_prompt or """Проанализируй это строительное изображение.
Опиши: что изображено, видимые дефекты, рекомендации по исправлению."""

            loop = asyncio.get_event_loop()

            def _analyze():
                response = gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[img, prompt]
                )
                return response.text

            return await loop.run_in_executor(None, _analyze)

        except Exception as e:
            logger.error(f"Ошибка анализа: {e}")
            return None


def initialize_gemini_generator() -> Optional[GeminiImageGenerator]:
    """Инициализирует генератор изображений"""
    if IMAGE_ENGINE:
        return GeminiImageGenerator()
    return None
