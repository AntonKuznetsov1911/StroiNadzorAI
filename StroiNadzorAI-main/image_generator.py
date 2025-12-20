"""
Модуль генерации изображений для StroiNadzorAI
Использует Stable Diffusion Web UI для профессиональной генерации
"""

import os
import logging
from io import BytesIO
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# Генераторы изображений
sd_generator = None
prompt_engineer = None


def get_sd_generator():
    """Получить SD генератор (ленивая инициализация)"""
    global sd_generator
    if sd_generator is None:
        try:
            from stable_diffusion_api import initialize_sd_generator
            sd_generator = initialize_sd_generator()
            if sd_generator:
                logger.info("✅ Stable Diffusion генератор загружен")
            else:
                logger.warning("⚠️ SD генератор не инициализирован (API недоступен)")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить SD генератор: {e}")
    return sd_generator


def get_prompt_engineer():
    """Получить промпт-инженера (ленивая инициализация)"""
    global prompt_engineer
    if prompt_engineer is None:
        try:
            from prompt_engineer import initialize_prompt_engineer
            prompt_engineer = initialize_prompt_engineer()
            if prompt_engineer:
                logger.info("✅ Prompt Engineer загружен")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить Prompt Engineer: {e}")
    return prompt_engineer


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

async def generate_construction_image(user_request: str, use_hd: bool = False) -> Optional[Dict]:
    """
    Сгенерировать изображение на основе запроса пользователя
    Использует Stable Diffusion Web UI

    Args:
        user_request: Запрос пользователя (на русском)
        use_hd: Использовать HD качество (для SD - 1024x1024)

    Returns:
        Dict с данными изображения или None
    """
    try:
        logger.info(f"🎨 Запрос на генерацию: {user_request}")

        # Определяем тип схемы из запроса
        schematic_type = detect_schematic_type(user_request)
        logger.info(f"📋 Определен тип схемы: {schematic_type}")

        # Проверяем доступность Stable Diffusion
        sd_gen = get_sd_generator()
        if not sd_gen:
            logger.error("❌ Stable Diffusion недоступен")
            return None

        logger.info("🚀 Используем Stable Diffusion для генерации")
        return await generate_with_sd(user_request, schematic_type, use_hd)

    except Exception as e:
        logger.error(f"❌ Ошибка генерации изображения: {e}")
        import traceback
        traceback.print_exc()
        return None


async def generate_with_sd(
    user_request: str,
    schematic_type: str,
    use_hd: bool = False
) -> Optional[Dict]:
    """
    Генерация через Stable Diffusion

    Args:
        user_request: Запрос пользователя
        schematic_type: Тип схемы
        use_hd: HD качество

    Returns:
        Dict с результатом или None
    """
    try:
        sd_gen = get_sd_generator()
        engineer = get_prompt_engineer()

        # Улучшаем промпт
        if engineer:
            logger.info("🔧 Используем AI промпт-инженеринг")
            enhanced = engineer.enhance_prompt(user_request, schematic_type, use_ai=True)
            prompt = enhanced["prompt"]
            negative_prompt = enhanced["negative_prompt"]
        else:
            # Простой перевод без AI
            logger.info("🔧 Используем базовый промпт")
            prompt = user_request
            negative_prompt = None

        logger.info(f"📝 Финальный промпт: {prompt[:100]}...")

        # Генерируем (теперь с await)
        image_data = await sd_gen.generate_construction_schematic(
            description=user_request,
            schematic_type=schematic_type,
            style="technical"
        )

        if image_data:
            result = {
                "image_data": image_data,
                "model": "stable-diffusion",
                "original_prompt": user_request,
                "enhanced_prompt": prompt,
                "size": "1024x1024" if use_hd else "1024x1024",
                "quality": "hd" if use_hd else "standard",
                "style": schematic_type,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "generator": "Stable Diffusion Web UI"
            }
            logger.info("✅ SD генерация успешна")
            return result
        else:
            logger.error("❌ SD не вернул данные")
            return None

    except Exception as e:
        logger.error(f"❌ Ошибка SD генерации: {e}")
        import traceback
        traceback.print_exc()
        return None


def detect_schematic_type(user_request: str) -> str:
    """
    Определяет тип схемы из запроса пользователя

    Args:
        user_request: Запрос пользователя

    Returns:
        Тип схемы: technical, blueprint, isometric, diagram
    """
    request_lower = user_request.lower()

    # Ключевые слова для разных типов
    if any(word in request_lower for word in ["чертёж", "план", "планировка", "чертеж"]):
        return "blueprint"
    elif any(word in request_lower for word in ["изометрия", "3d", "объём", "объемный", "аксонометрия"]):
        return "isometric"
    elif any(word in request_lower for word in ["разрез", "сечение", "узел", "деталь"]):
        return "diagram"
    else:
        return "technical"


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

    generator = result.get("generator", "AI")

    text = f"🎨 **Изображение создано**\n\n"
    text += f"📝 **Ваш запрос:** {user_request}\n\n"

    if result.get("enhanced_prompt"):
        text += f"🤖 **Улучшенный промпт:**\n{result['enhanced_prompt'][:200]}...\n\n"

    text += f"⚙️ **Параметры:**\n"
    text += f"• Генератор: {generator}\n"
    text += f"• Размер: {result.get('size', 'N/A')}\n"
    text += f"• Стиль: {result.get('style', 'technical')}\n"
    text += f"• Качество: {result.get('quality', 'standard').upper()}\n"

    text += f"\n⏰ {result['timestamp']}"
    text += "\n\n💡 *Создано с помощью Stable Diffusion*"

    return text


def get_generation_status() -> Dict[str, bool]:
    """
    Получить статус доступности генераторов

    Returns:
        Dict с информацией о доступных генераторах
    """
    status = {
        "sd_available": False,
        "prompt_engineer_available": False,
        "preferred_generator": None
    }

    # Проверяем SD
    sd_gen = get_sd_generator()
    if sd_gen:
        status["sd_available"] = True
        status["preferred_generator"] = "stable_diffusion"

    # Проверяем Prompt Engineer
    engineer = get_prompt_engineer()
    if engineer:
        status["prompt_engineer_available"] = True

    return status
