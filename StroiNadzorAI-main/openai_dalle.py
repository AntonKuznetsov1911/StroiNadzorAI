"""
Модуль для генерации изображений через OpenAI DALL-E
Используется для создания технических схем, чертежей, планов
"""

import os
import logging
import asyncio
from io import BytesIO
from typing import Optional, Dict
from datetime import datetime
import base64

logger = logging.getLogger(__name__)

# API ключ
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI клиент
openai_client = None


def get_openai_client():
    """Получить OpenAI клиент (ленивая инициализация)"""
    global openai_client
    if openai_client is None and OPENAI_API_KEY:
        try:
            from openai import OpenAI
            openai_client = OpenAI(api_key=OPENAI_API_KEY)
            logger.info("✅ OpenAI DALL-E клиент инициализирован")
        except ImportError:
            logger.error("❌ Библиотека openai не установлена")
    return openai_client


async def generate_image_dalle(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "standard",
    style: str = "natural"
) -> Optional[Dict]:
    """
    Сгенерировать изображение через DALL-E 3

    Args:
        prompt: Промпт для генерации (на английском)
        size: Размер изображения (1024x1024, 1792x1024, 1024x1792)
        quality: Качество (standard или hd)
        style: Стиль (vivid или natural)

    Returns:
        Dict с данными изображения или None
        {
            "image_data": BytesIO объект с изображением,
            "url": URL изображения (временный),
            "revised_prompt": Улучшенный промпт от DALL-E,
            "model": "dall-e-3",
            "size": размер,
            "quality": качество,
            "timestamp": время генерации
        }
    """
    try:
        client = get_openai_client()
        if not client:
            logger.error("❌ OpenAI клиент недоступен")
            return None

        logger.info(f"🎨 Запуск DALL-E 3 генерации...")
        logger.info(f"📝 Промпт: {prompt[:100]}...")
        logger.info(f"⚙️ Параметры: size={size}, quality={quality}, style={style}")

        # Улучшаем промпт для технических схем
        enhanced_prompt = enhance_construction_prompt(prompt)
        logger.info(f"📝 Улучшенный промпт: {enhanced_prompt[:100]}...")

        # Запускаем генерацию асинхронно
        loop = asyncio.get_event_loop()

        def _generate():
            return client.images.generate(
                model="dall-e-3",
                prompt=enhanced_prompt,
                size=size,
                quality=quality,
                style=style,
                n=1,
                response_format="url"  # Сначала получаем URL, потом скачиваем
            )

        response = await loop.run_in_executor(None, _generate)

        if not response.data or len(response.data) == 0:
            logger.error("❌ DALL-E не вернул изображение")
            return None

        image_data_item = response.data[0]
        image_url = image_data_item.url
        revised_prompt = image_data_item.revised_prompt

        logger.info(f"✅ DALL-E сгенерировал изображение")
        logger.info(f"🔄 Revised prompt: {revised_prompt}")

        # Скачиваем изображение
        import httpx

        async def _download():
            async with httpx.AsyncClient() as http_client:
                img_response = await http_client.get(image_url)
                img_response.raise_for_status()
                return BytesIO(img_response.content)

        image_data = await _download()
        logger.info("✅ Изображение скачано")

        result = {
            "image_data": image_data,
            "url": image_url,
            "revised_prompt": revised_prompt,
            "model": "dall-e-3",
            "size": size,
            "quality": quality,
            "style": style,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "generator": "OpenAI DALL-E 3"
        }

        return result

    except Exception as e:
        logger.error(f"❌ Ошибка генерации DALL-E: {e}")
        import traceback
        traceback.print_exc()
        return None


def enhance_construction_prompt(prompt: str) -> str:
    """
    Улучшить промпт для строительных/технических схем

    Args:
        prompt: Исходный промпт

    Returns:
        Улучшенный промпт
    """
    # Если промпт уже содержит технические термины - оставляем как есть
    technical_terms = [
        "technical", "blueprint", "diagram", "schematic",
        "engineering", "construction", "architectural",
        "isometric", "CAD", "drawing"
    ]

    if any(term.lower() in prompt.lower() for term in technical_terms):
        return prompt

    # Добавляем технический контекст
    enhanced = f"{prompt}. Professional technical drawing style, "
    enhanced += "clean lines, white background, accurate proportions, "
    enhanced += "engineering diagram quality, construction blueprint aesthetic"

    return enhanced


def format_dalle_result(result: Dict, user_request: str) -> str:
    """
    Форматировать результат генерации DALL-E для отправки пользователю

    Args:
        result: Результат генерации
        user_request: Оригинальный запрос пользователя

    Returns:
        Отформатированный текст
    """
    if not result:
        return "❌ Не удалось сгенерировать изображение через DALL-E"

    text = f"🎨 **Изображение создано через DALL-E 3**\n\n"
    text += f"📝 **Ваш запрос:** {user_request}\n\n"

    if result.get("revised_prompt"):
        text += f"🔄 **DALL-E улучшил промпт:**\n{result['revised_prompt'][:200]}...\n\n"

    text += f"⚙️ **Параметры:**\n"
    text += f"• Модель: DALL-E 3\n"
    text += f"• Размер: {result.get('size', '1024x1024')}\n"
    text += f"• Качество: {result.get('quality', 'standard').upper()}\n"
    text += f"• Стиль: {result.get('style', 'natural')}\n"

    text += f"\n⏰ {result['timestamp']}"
    text += "\n\n💡 *Создано с помощью OpenAI DALL-E 3*"

    return text


def is_dalle_available() -> bool:
    """
    Проверить доступность DALL-E

    Returns:
        True если DALL-E доступен
    """
    return bool(OPENAI_API_KEY and get_openai_client())


async def test_dalle_generation():
    """
    Тестовая генерация для проверки работы DALL-E
    """
    test_prompt = "Technical construction diagram showing concrete foundation cross-section, professional blueprint style"

    logger.info("🧪 Тест DALL-E генерации...")

    result = await generate_image_dalle(
        prompt=test_prompt,
        size="1024x1024",
        quality="standard"
    )

    if result:
        logger.info("✅ Тест пройден: DALL-E работает корректно")
        return True
    else:
        logger.error("❌ Тест провален: DALL-E не работает")
        return False


# === СПЕЦИАЛИЗИРОВАННЫЕ ФУНКЦИИ ДЛЯ СТРОИТЕЛЬНЫХ СХЕМ ===

async def generate_construction_plan(
    description_ru: str,
    schematic_type: str = "blueprint"
) -> Optional[Dict]:
    """
    Генерация строительного плана/схемы

    Args:
        description_ru: Описание на русском
        schematic_type: Тип схемы (blueprint, isometric, diagram, plan)

    Returns:
        Dict с результатом генерации
    """
    # Создаем промпт на английском
    style_map = {
        "blueprint": "architectural blueprint style, top-down view, technical drawing",
        "isometric": "isometric construction view, 3D perspective, technical illustration",
        "diagram": "technical diagram, cross-section view, engineering schematic",
        "plan": "floor plan style, architectural layout, clean professional drawing"
    }

    style_prompt = style_map.get(schematic_type, style_map["blueprint"])

    # Базовый промпт (описание должно быть переведено на английский заранее)
    prompt = f"Construction schematic: {description_ru}. {style_prompt}. "
    prompt += "White background, clear labels, accurate measurements, professional quality"

    logger.info(f"🏗️ Генерация строительной схемы типа: {schematic_type}")

    result = await generate_image_dalle(
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        style="natural"  # natural лучше для технических схем
    )

    return result


async def generate_sewer_system_diagram(
    description: str,
    num_manholes: int = 3,
    distance: str = "in straight line"
) -> Optional[Dict]:
    """
    Специализированная функция для генерации схемы канализационных колодцев

    Args:
        description: Описание системы
        num_manholes: Количество колодцев
        distance: Расположение (например "in straight line")

    Returns:
        Dict с результатом
    """
    prompt = f"Technical engineering diagram of sewer system layout. "
    prompt += f"Shows {num_manholes} manholes {distance} from administrative building to central sewage. "
    prompt += "Top view, professional blueprint style, white background, "
    prompt += "clear labels for each manhole, distance markers, pipe connections shown. "
    prompt += "Clean technical drawing with measurements and annotations"

    logger.info(f"🚰 Генерация схемы канализации: {num_manholes} колодцев")

    result = await generate_image_dalle(
        prompt=prompt,
        size="1792x1024",  # Широкий формат для линейной схемы
        quality="standard",
        style="natural"
    )

    return result
