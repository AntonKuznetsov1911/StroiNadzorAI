"""
Модуль генерации изображений для StroiNadzorAI
Использует Gemini AI для создания технических схем и диаграмм
"""

import os
import logging
from io import BytesIO
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# Gemini генератор
gemini_generator = None

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
    Использует Gemini AI для создания технических схем

    Args:
        user_request: Запрос пользователя (на русском)
        use_hd: Не используется (для совместимости)

    Returns:
        Dict с данными изображения или None
    """
    try:
        logger.info(f"🎨 Запрос на генерацию схемы: {user_request}")

        # Используем Gemini AI для создания схемы
        generator = get_gemini_generator()

        if not generator:
            logger.error("❌ Gemini генератор не инициализирован")
            return None

        logger.info("📌 Генерирую схему с Gemini AI...")

        # Используем синхронную обёртку для асинхронной функции
        import asyncio
        try:
            logger.info(f"📌 Вызываю generate_schematic_image с: {user_request}")
            image_data = asyncio.run(
                generator.generate_schematic_image(user_request)
            )
            logger.info(f"📌 Результат: {image_data is not None}")
        except Exception as gemini_error:
            logger.error(f"❌ Ошибка Gemini: {gemini_error}")
            import traceback
            traceback.print_exc()
            return None

        if image_data:
            result = {
                "image_data": image_data,
                "model": "gemini-2.5-flash",
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
            return None

    except Exception as e:
        logger.error(f"❌ Ошибка генерации изображения: {e}")
        import traceback
        traceback.print_exc()
        return None


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

    model = result.get("model", "gemini-ai")

    text = f"🎨 **Схема создана**\n\n"
    text += f"📝 **Ваш запрос:** {user_request}\n\n"

    if result.get("revised_prompt"):
        text += f"🤖 **Описание:**\n{result['revised_prompt']}\n\n"

    text += f"⚙️ **Параметры:**\n"
    text += f"• Модель: {result['model']}\n"
    text += f"• Размер: {result['size']}\n"
    text += f"• Тип: Техническая схема\n"
    text += f"\n⏰ {result['timestamp']}"
    text += "\n\n💡 *Создано с помощью Gemini AI*"

    return text
