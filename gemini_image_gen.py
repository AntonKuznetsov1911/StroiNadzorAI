"""
Модуль для генерации изображений с помощью Gemini API
Использует новый google-genai SDK с поддержкой реальной генерации изображений
Модели: gemini-2.5-flash-preview-image-generation
"""

import os
import logging
import asyncio
import base64
from io import BytesIO
from typing import Optional, Dict, List, Union
from PIL import Image

logger = logging.getLogger(__name__)

# Глобальный клиент Gemini
_gemini_client = None
IMAGE_GENERATION_ENABLED = False


def get_gemini_client():
    """Получить или создать Gemini клиент"""
    global _gemini_client, IMAGE_GENERATION_ENABLED

    if _gemini_client is not None:
        return _gemini_client

    try:
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY не найден")
            return None

        _gemini_client = genai.Client(api_key=api_key)
        IMAGE_GENERATION_ENABLED = True
        logger.info("Gemini клиент инициализирован")
        return _gemini_client

    except ImportError:
        logger.warning("google-genai не установлен")
        return None
    except Exception as e:
        logger.error(f"Ошибка инициализации Gemini: {e}")
        return None


class GeminiImageGenerator:
    """Класс для генерации изображений через Gemini API"""

    def __init__(self, api_key: str = None):
        """
        Инициализация генератора

        Args:
            api_key: API ключ (если не указан, берётся из env)
        """
        from google import genai
        from google.genai import types

        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY не найден")

        self.client = genai.Client(api_key=self.api_key)
        self.types = types

        # Модели для разных задач
        self.image_model = "gemini-2.5-flash-preview-image-generation"  # Генерация изображений
        self.vision_model = "gemini-2.5-flash"  # Анализ изображений

        logger.info(f"GeminiImageGenerator инициализирован (модель: {self.image_model})")

    async def generate_image(
        self,
        prompt: str,
        reference_image: Optional[Union[bytes, Image.Image]] = None,
        aspect_ratio: str = "1:1",
        style: str = "technical"
    ) -> Optional[Dict]:
        """
        Генерирует изображение по текстовому описанию

        Args:
            prompt: Описание изображения
            reference_image: Референсное изображение (опционально)
            aspect_ratio: Соотношение сторон (1:1, 16:9, 9:16, 4:3, 3:4)
            style: Стиль (technical, realistic, schematic)

        Returns:
            Dict с image_data (BytesIO), text (описание), model
        """
        try:
            logger.info(f"Генерация изображения: {prompt[:100]}...")

            # Улучшаем промпт для строительной тематики
            enhanced_prompt = self._enhance_construction_prompt(prompt, style)

            # Формируем контент для запроса
            contents = [enhanced_prompt]

            # Добавляем референсное изображение если есть
            if reference_image:
                if isinstance(reference_image, bytes):
                    ref_img = Image.open(BytesIO(reference_image))
                else:
                    ref_img = reference_image
                contents.insert(0, ref_img)

            # Выполняем генерацию в отдельном потоке
            loop = asyncio.get_event_loop()

            def _generate():
                response = self.client.models.generate_content(
                    model=self.image_model,
                    contents=contents,
                    config=self.types.GenerateContentConfig(
                        response_modalities=['TEXT', 'IMAGE']
                    )
                )
                return response

            response = await loop.run_in_executor(None, _generate)

            # Обрабатываем результат
            result = {
                "image_data": None,
                "text": "",
                "model": self.image_model,
                "prompt": prompt
            }

            for part in response.parts:
                if part.text is not None:
                    result["text"] = part.text
                elif part.inline_data is not None:
                    # Получаем изображение
                    image = part.as_image()
                    img_buffer = BytesIO()
                    image.save(img_buffer, format='PNG')
                    img_buffer.seek(0)
                    result["image_data"] = img_buffer
                    logger.info("Изображение успешно сгенерировано")

            return result if result["image_data"] else None

        except Exception as e:
            logger.error(f"Ошибка генерации изображения: {e}")
            return None

    async def generate_construction_scheme(
        self,
        description: str,
        scheme_type: str = "general"
    ) -> Optional[Dict]:
        """
        Генерирует строительную схему

        Args:
            description: Описание схемы
            scheme_type: Тип схемы (foundation, wall, roof, electrical, plumbing)

        Returns:
            Dict с image_data и описанием
        """
        scheme_prompts = {
            "foundation": "technical construction blueprint of foundation, cross-section view, dimensions, reinforcement bars, concrete layers",
            "wall": "technical construction blueprint of wall structure, layers detail, insulation, materials cross-section",
            "roof": "technical construction blueprint of roof structure, rafters, insulation layers, waterproofing membrane",
            "electrical": "electrical wiring diagram, circuit layout, panel box, outlets and switches positions",
            "plumbing": "plumbing system diagram, pipes layout, water supply and drainage, fixtures positions",
            "general": "technical construction blueprint, professional engineering drawing style"
        }

        base_style = scheme_prompts.get(scheme_type, scheme_prompts["general"])
        full_prompt = f"{base_style}, showing: {description}, clean technical drawing, labeled parts, measurement annotations, professional CAD style, white background"

        return await self.generate_image(full_prompt, style="technical")

    async def visualize_defect(
        self,
        defect_description: str,
        defect_photo: Optional[bytes] = None
    ) -> Optional[Dict]:
        """
        Визуализирует строительный дефект

        Args:
            defect_description: Описание дефекта
            defect_photo: Фото дефекта для анализа (опционально)

        Returns:
            Dict с визуализацией
        """
        prompt = f"""Create a technical illustration showing construction defect:
{defect_description}

Style: technical diagram with annotations, clear markings showing problem areas,
arrows pointing to defects, measurement indicators, professional inspection report style.
Include labels in Russian explaining the defect causes and recommended repairs."""

        return await self.generate_image(
            prompt,
            reference_image=defect_photo,
            style="technical"
        )

    async def edit_image(
        self,
        image: Union[bytes, Image.Image],
        edit_instruction: str
    ) -> Optional[Dict]:
        """
        Редактирует изображение по инструкции

        Args:
            image: Исходное изображение
            edit_instruction: Инструкция по редактированию

        Returns:
            Dict с отредактированным изображением
        """
        try:
            if isinstance(image, bytes):
                img = Image.open(BytesIO(image))
            else:
                img = image

            prompt = f"Edit this image: {edit_instruction}"

            loop = asyncio.get_event_loop()

            def _edit():
                response = self.client.models.generate_content(
                    model=self.image_model,
                    contents=[img, prompt],
                    config=self.types.GenerateContentConfig(
                        response_modalities=['TEXT', 'IMAGE']
                    )
                )
                return response

            response = await loop.run_in_executor(None, _edit)

            result = {"image_data": None, "text": ""}

            for part in response.parts:
                if part.text is not None:
                    result["text"] = part.text
                elif part.inline_data is not None:
                    edited_image = part.as_image()
                    img_buffer = BytesIO()
                    edited_image.save(img_buffer, format='PNG')
                    img_buffer.seek(0)
                    result["image_data"] = img_buffer

            return result if result["image_data"] else None

        except Exception as e:
            logger.error(f"Ошибка редактирования изображения: {e}")
            return None

    async def analyze_image(
        self,
        image: Union[bytes, Image.Image],
        analysis_prompt: str = None
    ) -> Optional[str]:
        """
        Анализирует изображение

        Args:
            image: Изображение для анализа
            analysis_prompt: Дополнительный промпт для анализа

        Returns:
            Текстовый анализ
        """
        try:
            if isinstance(image, bytes):
                img = Image.open(BytesIO(image))
            else:
                img = image

            prompt = analysis_prompt or """Проанализируй это строительное изображение.
Опиши:
1. Что изображено
2. Видимые дефекты или проблемы
3. Рекомендации по исправлению
4. Соответствие строительным нормам"""

            loop = asyncio.get_event_loop()

            def _analyze():
                response = self.client.models.generate_content(
                    model=self.vision_model,
                    contents=[img, prompt]
                )
                return response.text

            return await loop.run_in_executor(None, _analyze)

        except Exception as e:
            logger.error(f"Ошибка анализа изображения: {e}")
            return None

    def _enhance_construction_prompt(self, prompt: str, style: str = "technical") -> str:
        """Улучшает промпт для строительной тематики"""

        style_additions = {
            "technical": "professional technical drawing, blueprint style, clean lines, measurement annotations, labeled components, engineering documentation quality",
            "realistic": "photorealistic, high detail, natural lighting, professional construction photography",
            "schematic": "simplified schematic diagram, clear symbols, flowchart style, easy to understand"
        }

        style_text = style_additions.get(style, style_additions["technical"])

        # Добавляем строительный контекст
        enhanced = f"""Construction industry visualization:
{prompt}

Style requirements: {style_text}
Quality: high resolution, professional grade, suitable for technical documentation
Language: include Russian labels and annotations where appropriate"""

        return enhanced

    async def improve_prompt(self, user_request: str) -> str:
        """
        Улучшает пользовательский промпт с помощью AI

        Args:
            user_request: Исходный запрос пользователя

        Returns:
            Улучшенный промпт для генерации
        """
        try:
            prompt = f"""Ты - эксперт по созданию промптов для генерации строительных изображений.

Пользователь запросил: "{user_request}"

Создай детальный промпт на английском языке для генерации технического изображения.
Включи: тип визуализации, ключевые элементы, технические детали, стиль, ракурс.
Ответ - только промпт, без пояснений."""

            loop = asyncio.get_event_loop()

            def _improve():
                response = self.client.models.generate_content(
                    model=self.vision_model,
                    contents=[prompt]
                )
                return response.text.strip()

            return await loop.run_in_executor(None, _improve)

        except Exception as e:
            logger.error(f"Ошибка улучшения промпта: {e}")
            return user_request


def initialize_gemini_generator() -> Optional[GeminiImageGenerator]:
    """
    Инициализирует генератор изображений Gemini

    Returns:
        Экземпляр GeminiImageGenerator или None
    """
    try:
        api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            logger.warning("GEMINI_API_KEY не найден в переменных окружения")
            return None

        generator = GeminiImageGenerator(api_key)
        logger.info("Gemini генератор успешно инициализирован")
        return generator

    except ImportError:
        logger.error("google-genai не установлен. Выполните: pip install google-genai")
        return None
    except Exception as e:
        logger.error(f"Ошибка инициализации Gemini генератора: {e}")
        return None


# === ФУНКЦИИ ДЛЯ СОВМЕСТИМОСТИ С BOT.PY ===

async def generate_construction_image_gemini(
    user_request: str,
    reference_image: bytes = None
) -> Optional[Dict]:
    """
    Генерирует строительное изображение (для использования в bot.py)

    Args:
        user_request: Запрос пользователя
        reference_image: Референсное изображение (опционально)

    Returns:
        Dict с image_data, text, model или None
    """
    generator = initialize_gemini_generator()
    if not generator:
        return None

    # Определяем тип схемы из запроса
    scheme_keywords = {
        "фундамент": "foundation",
        "стен": "wall",
        "крыш": "roof",
        "кровл": "roof",
        "электр": "electrical",
        "проводк": "electrical",
        "водопровод": "plumbing",
        "канализац": "plumbing",
        "труб": "plumbing"
    }

    scheme_type = "general"
    request_lower = user_request.lower()
    for keyword, s_type in scheme_keywords.items():
        if keyword in request_lower:
            scheme_type = s_type
            break

    # Генерируем изображение
    if scheme_type != "general":
        return await generator.generate_construction_scheme(user_request, scheme_type)
    else:
        return await generator.generate_image(user_request, reference_image)


def is_image_generation_available() -> bool:
    """Проверить доступность генерации изображений"""
    client = get_gemini_client()
    return client is not None
