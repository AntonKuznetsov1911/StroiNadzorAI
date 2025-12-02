"""
Модуль генерации изображений для StroiNadzorAI
Поддерживает DALL-E 3 и Gemini AI (fallback) для создания технических диаграмм
"""

import os
import logging
import requests
from io import BytesIO
from typing import Optional, Dict
from datetime import datetime
from openai import OpenAI
import asyncio

logger = logging.getLogger(__name__)

# Инициализация OpenAI клиента
openai_client = None
gemini_generator = None

def get_openai_client():
    """Получить OpenAI клиент (ленивая инициализация)"""
    global openai_client
    if openai_client is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise Exception("OPENAI_API_KEY не найден в переменных окружения")
        openai_client = OpenAI(api_key=api_key)
    return openai_client

def get_gemini_generator():
    """Получить Gemini генератор (ленивая инициализация)"""
    global gemini_generator
    if gemini_generator is None:
        try:
            from gemini_image_gen import initialize_gemini_generator
            gemini_generator = initialize_gemini_generator()
        except Exception as e:
            logger.warning(f"Не удалось загрузить Gemini генератор: {e}")
    return gemini_generator


# === ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ С DALL-E 3 ===

def generate_image_dalle3(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "standard",
    style: str = "vivid"
) -> Optional[Dict]:
    """
    Генерация изображения с помощью DALL-E 3

    Args:
        prompt: Описание изображения на английском
        size: Размер ("1024x1024", "1792x1024", "1024x1792")
        quality: Качество ("standard" или "hd")
        style: Стиль ("vivid" или "natural")

    Returns:
        Dict с URL изображения и метаданными или None
    """
    try:
        logger.info(f"🎨 Генерация изображения DALL-E 3: {prompt[:100]}...")

        client = get_openai_client()

        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality=quality,
            style=style,
            n=1
        )

        image_url = response.data[0].url
        revised_prompt = response.data[0].revised_prompt

        logger.info(f"✅ Изображение сгенерировано: {image_url}")

        return {
            "url": image_url,
            "revised_prompt": revised_prompt,
            "original_prompt": prompt,
            "size": size,
            "quality": quality,
            "style": style,
            "model": "dall-e-3",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    except Exception as e:
        logger.error(f"Ошибка генерации DALL-E 3: {e}")
        return None


def download_image(image_url: str) -> Optional[BytesIO]:
    """
    Скачать изображение по URL

    Args:
        image_url: URL изображения

    Returns:
        BytesIO объект с изображением или None
    """
    try:
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()

        image_data = BytesIO(response.content)
        image_data.seek(0)

        logger.info(f"✅ Изображение скачано ({len(response.content)} байт)")
        return image_data

    except Exception as e:
        logger.error(f"Ошибка скачивания изображения: {e}")
        return None


# === УЛУЧШЕНИЕ ПРОМПТОВ ДЛЯ СТРОИТЕЛЬНОЙ ТЕМАТИКИ ===

def enhance_construction_prompt(user_prompt: str) -> str:
    """
    Улучшить промпт пользователя для строительной тематики

    Args:
        user_prompt: Оригинальный промпт пользователя (на русском)

    Returns:
        Улучшенный промпт на английском
    """
    # Словарь переводов строительных терминов
    construction_terms = {
        "фундамент": "foundation",
        "стена": "wall",
        "перекрытие": "floor slab",
        "балка": "beam",
        "колонна": "column",
        "арматура": "reinforcement",
        "бетон": "concrete",
        "кирпич": "brick",
        "трещина": "crack",
        "дефект": "defect",
        "опалубка": "formwork",
        "каркас": "frame",
        "кровля": "roof",
        "узел": "joint",
        "стык": "connection",
        "сварка": "welding",
        "изоляция": "insulation"
    }

    # Базовый перевод (упрощенный)
    enhanced = user_prompt.lower()
    for ru, en in construction_terms.items():
        enhanced = enhanced.replace(ru, en)

    # Добавляем технические детали
    enhanced = f"Technical construction photography: {enhanced}. " \
               f"Professional engineering quality, detailed, realistic, technical documentation style."

    return enhanced


# === ОПРЕДЕЛЕНИЕ НЕОБХОДИМОСТИ ГЕНЕРАЦИИ ===

def should_generate_image(user_message: str) -> bool:
    """
    Определить, нужна ли генерация изображения

    Args:
        user_message: Сообщение пользователя

    Returns:
        True если нужна генерация, False если нет
    """
    # Триггеры для генерации
    image_triggers = [
        "нарисуй",
        "покажи",
        "сгенерируй",
        "создай изображение",
        "создай картинку",
        "создай фото",
        "как выглядит",
        "визуализируй",
        "сделай рисунок",
        "изобрази",
        "покажи как выглядит",
        "прислать картинку",
        "пришли картинку",
        "пришли изображение",
        "пришли фото",
        "отправь картинку",
        "отправь изображение",
        "можешь прислать",
        "можешь отправить",
        "можешь показать картинку",
        "можешь показать изображение",
        "нужна картинка",
        "нужно изображение",
        "хочу увидеть",
        "хочу картинку"
    ]

    message_lower = user_message.lower()
    return any(trigger in message_lower for trigger in image_triggers)


# === ГЛАВНАЯ ФУНКЦИЯ ГЕНЕРАЦИИ ===

def generate_construction_image(user_request: str, use_hd: bool = False) -> Optional[Dict]:
    """
    Сгенерировать изображение на основе запроса пользователя
    Использует DALL-E 3, если доступен, иначе Gemini AI для создания схемы

    Args:
        user_request: Запрос пользователя (на русском)
        use_hd: Использовать HD качество (дороже)

    Returns:
        Dict с данными изображения или None
    """
    try:
        logger.info(f"🎨 Запрос на генерацию: {user_request}")

        # Пытаемся использовать DALL-E 3
        dalle_result = None
        try:
            # Улучшаем промпт для строительной тематики
            enhanced_prompt = enhance_construction_prompt(user_request)
            logger.info(f"📝 Улучшенный промпт: {enhanced_prompt}")

            # Генерируем изображение
            quality = "hd" if use_hd else "standard"
            dalle_result = generate_image_dalle3(
                prompt=enhanced_prompt,
                size="1024x1024",
                quality=quality,
                style="natural"  # natural для технических изображений
            )

            if dalle_result:
                # Скачиваем изображение
                image_data = download_image(dalle_result["url"])
                if image_data:
                    dalle_result["image_data"] = image_data
                    logger.info("✅ Генерация DALL-E 3 завершена успешно")
                    return dalle_result

        except Exception as dalle_error:
            logger.warning(f"⚠️ DALL-E 3 exception: {dalle_error}")

        # Если DALL-E не дал результат - переключаемся на Gemini
        if dalle_result is None:
            logger.info("🔄 Переключаюсь на Gemini AI для создания схемы...")

            # Fallback на Gemini AI
            generator = get_gemini_generator()
            logger.info(f"📌 Gemini генератор: {generator is not None}")

            if generator:
                logger.info("📌 Создаю event loop для asyncio...")
                # Используем asyncio для запуска асинхронной функции
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    logger.info(f"📌 Вызываю generate_schematic_image с: {user_request}")
                    image_data = loop.run_until_complete(
                        generator.generate_schematic_image(user_request)
                    )
                    logger.info(f"📌 Результат: {image_data is not None}")
                except Exception as gemini_error:
                    logger.error(f"❌ Ошибка Gemini: {gemini_error}")
                    image_data = None
                finally:
                    loop.close()

                if image_data:
                    result = {
                        "image_data": image_data,
                        "model": "gemini-schematic",
                        "original_prompt": user_request,
                        "size": "1024x1024",
                        "quality": "schematic",
                        "style": "technical",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "revised_prompt": f"Техническая схема: {user_request}"
                    }
                    logger.info("✅ Схема Gemini создана успешно")
                    return result
                else:
                    logger.warning("⚠️ Gemini не вернул данные изображения")
            else:
                logger.warning("⚠️ Gemini генератор не инициализирован")

        return None

    except Exception as e:
        logger.error(f"❌ Ошибка генерации изображения: {e}")
        return None


# === СОЗДАНИЕ ТЕХНИЧЕСКИХ ДИАГРАММ ===

def create_technical_diagram(
    diagram_type: str,
    data: Dict,
    title: str = ""
) -> Optional[BytesIO]:
    """
    Создать техническую диаграмму/схему

    Args:
        diagram_type: Тип диаграммы ("node", "detail", "graph", "chart")
        data: Данные для диаграммы
        title: Заголовок

    Returns:
        BytesIO с изображением диаграммы или None
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        # Создаем изображение
        width, height = 800, 600
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)

        # Простой пример: рисуем заголовок
        if title:
            draw.text((20, 20), title, fill='black')

        # Сохраняем в BytesIO
        output = BytesIO()
        img.save(output, format='PNG')
        output.seek(0)

        logger.info(f"✅ Техническая диаграмма создана: {diagram_type}")
        return output

    except Exception as e:
        logger.error(f"Ошибка создания диаграммы: {e}")
        return None


# === ИНФОРМАЦИЯ О СТОИМОСТИ ===

def get_generation_cost(quality: str = "standard", size: str = "1024x1024") -> float:
    """
    Получить стоимость генерации

    Args:
        quality: Качество изображения
        size: Размер изображения

    Returns:
        Стоимость в долларах
    """
    # Цены DALL-E 3 (актуальные на декабрь 2024)
    prices = {
        "standard": {
            "1024x1024": 0.040,
            "1024x1792": 0.080,
            "1792x1024": 0.080
        },
        "hd": {
            "1024x1024": 0.080,
            "1024x1792": 0.120,
            "1792x1024": 0.120
        }
    }

    return prices.get(quality, {}).get(size, 0.040)


# === ФОРМАТИРОВАНИЕ РЕЗУЛЬТАТА ===

def format_generation_result(result: Dict, user_request: str) -> str:
    """
    Форматировать результат генерации для отправки пользователю

    Args:
        result: Результат генерации
        user_request: Оригинальный запрос пользователя

    Returns:
        Отформатированный текст
    """
    if not result:
        return "❌ Не удалось сгенерировать изображение"

    model = result.get("model", "unknown")
    is_gemini = "gemini" in model.lower()

    text = f"🎨 **Изображение {'создано' if is_gemini else 'сгенерировано'}**\n\n"
    text += f"📝 **Ваш запрос:** {user_request}\n\n"

    if result.get("revised_prompt"):
        if is_gemini:
            text += f"🤖 **Описание схемы:**\n{result['revised_prompt']}\n\n"
        else:
            text += f"🤖 **Промпт DALL-E:**\n{result['revised_prompt']}\n\n"

    text += f"⚙️ **Параметры:**\n"
    text += f"• Модель: {result['model']}\n"
    text += f"• Размер: {result['size']}\n"
    text += f"• Качество: {result['quality']}\n"

    if not is_gemini:
        cost = get_generation_cost(result.get("quality", "standard"), result.get("size", "1024x1024"))
        text += f"• Стоимость: ${cost:.3f}\n"

    text += f"\n⏰ {result['timestamp']}"

    if is_gemini:
        text += "\n\n💡 *Схема создана с помощью Gemini AI*"
        text += "\n_Для фотореалистичной генерации добавьте OPENAI_API_KEY_"

    return text
