"""
Координатор AI для StroiNadzorAI
XAI (Grok) - главный AI, определяет необходимость передачи задач другим AI
OPENAI - для генерации изображений через DALL-E
Anthropic (Claude) - резервный вариант при сбое XAI
"""

import os
import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from xai_client import XAIClient, call_xai_with_retry

logger = logging.getLogger(__name__)

# API ключи
XAI_API_KEY = os.getenv("XAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Клиенты AI
xai_client = None
openai_client = None
anthropic_client = None


def get_xai_client():
    """Получить XAI клиент"""
    global xai_client
    if xai_client is None and XAI_API_KEY:
        xai_client = XAIClient(api_key=XAI_API_KEY)
        logger.info("✅ XAI клиент инициализирован")
    return xai_client


def get_openai_client():
    """Получить OpenAI клиент"""
    global openai_client
    if openai_client is None and OPENAI_API_KEY:
        try:
            from openai import OpenAI
            openai_client = OpenAI(api_key=OPENAI_API_KEY)
            logger.info("✅ OpenAI клиент инициализирован")
        except ImportError:
            logger.error("❌ Библиотека openai не установлена")
    return openai_client


def get_anthropic_client():
    """Получить Anthropic клиент"""
    global anthropic_client
    if anthropic_client is None and ANTHROPIC_API_KEY:
        try:
            from anthropic import Anthropic
            anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
            logger.info("✅ Anthropic клиент инициализирован")
        except ImportError:
            logger.error("❌ Библиотека anthropic не установлена")
    return anthropic_client


# === ТРИГГЕРЫ ДЛЯ ГЕНЕРАЦИИ ИЗОБРАЖЕНИЙ ===

def should_generate_image(user_message: str) -> bool:
    """
    Определить, нужна ли генерация изображения

    Args:
        user_message: Сообщение пользователя

    Returns:
        True если нужна генерация
    """
    image_triggers = [
        "нарисуй", "покажи", "сгенерируй", "создай изображение",
        "создай картинку", "создай фото", "как выглядит",
        "визуализируй", "сделай рисунок", "изобрази",
        "покажи как выглядит", "прислать картинку",
        "пришли картинку", "пришли изображение", "пришли фото",
        "отправь картинку", "отправь изображение",
        "можешь прислать", "можешь отправить",
        "можешь показать картинку", "можешь показать изображение",
        "нужна картинка", "нужно изображение",
        "хочу увидеть", "хочу картинку", "нарисуй схему",
        "нарисуй план", "покажи схему", "схему колодцев",
        "схему канализации", "план расположения"
    ]

    message_lower = user_message.lower()
    return any(trigger in message_lower for trigger in image_triggers)


# === КООРДИНАЦИЯ AI ===

async def analyze_request_and_coordinate(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    system_prompt: str = ""
) -> Dict:
    """
    Главная функция координации AI
    XAI анализирует запрос и определяет, нужна ли генерация изображения

    Args:
        user_message: Сообщение пользователя
        conversation_history: История разговора
        system_prompt: Системный промпт

    Returns:
        Dict с результатами:
        {
            "text_response": "текстовый ответ от XAI",
            "needs_image": True/False,
            "image_prompt": "промпт для DALL-E" (если needs_image=True),
            "image_result": {...} (если изображение сгенерировано),
            "ai_used": "xai" или "anthropic",
            "error": None или текст ошибки
        }
    """
    result = {
        "text_response": "",
        "needs_image": False,
        "image_prompt": None,
        "image_result": None,
        "ai_used": None,
        "error": None
    }

    try:
        # Проверяем, нужна ли генерация изображения
        needs_image = should_generate_image(user_message)
        result["needs_image"] = needs_image

        logger.info(f"🎯 Координация: needs_image={needs_image}")

        # Если нужно изображение - готовим специальный промпт для XAI
        if needs_image:
            enhanced_system_prompt = system_prompt + """

🎨 ВАЖНО: Пользователь запросил генерацию изображения!

Ваша задача:
1. Проанализируйте запрос и опишите, что именно нужно нарисовать
2. Дайте техническое описание со всеми нормами и правилами (расстояния, глубины, материалы и т.д.)
3. В конце ответа добавьте блок:

📝 **Промпт для генерации изображения:**
[Здесь опишите НА АНГЛИЙСКОМ ЯЗЫКЕ детальный промпт для DALL-E, включающий:
- Тип изображения (technical diagram, construction blueprint, etc.)
- Что именно изображено
- Стиль (technical drawing, professional blueprint, isometric view, etc.)
- Важные детали и размеры]

Пример:
📝 **Промпт для генерации изображения:**
"Technical construction diagram showing sewer manhole layout from administrative building to central sewage system. Three manholes in a straight line. Professional blueprint style with measurements, top view perspective, engineering drawing with annotations."
"""
            messages = [{"role": "system", "content": enhanced_system_prompt}] + conversation_history
        else:
            messages = [{"role": "system", "content": system_prompt}] + conversation_history

        # Пробуем XAI
        try:
            text_response = await call_xai_with_fallback(messages, needs_image)
            result["text_response"] = text_response
            result["ai_used"] = "xai"

            # Если нужно изображение - извлекаем промпт из ответа XAI
            if needs_image:
                image_prompt = extract_image_prompt_from_response(text_response)
                if image_prompt:
                    result["image_prompt"] = image_prompt
                    logger.info(f"📝 Извлечен промпт для DALL-E: {image_prompt[:100]}...")
                else:
                    # Если XAI не дал промпт - создаем базовый из запроса пользователя
                    result["image_prompt"] = f"Technical construction diagram: {user_message}"
                    logger.warning("⚠️ XAI не предоставил промпт, используем базовый")

        except Exception as e:
            logger.error(f"❌ Ошибка XAI: {e}")
            # Fallback на Anthropic
            try:
                text_response = await call_anthropic_with_prompt(messages)
                result["text_response"] = text_response
                result["ai_used"] = "anthropic"
                logger.info("✅ Использован fallback на Anthropic")

                # Для Anthropic тоже пробуем извлечь промпт
                if needs_image:
                    image_prompt = extract_image_prompt_from_response(text_response)
                    result["image_prompt"] = image_prompt or f"Construction diagram: {user_message}"

            except Exception as e2:
                logger.error(f"❌ Ошибка Anthropic: {e2}")
                result["error"] = f"Все AI недоступны: XAI ({str(e)}), Anthropic ({str(e2)})"
                return result

        # Если нужно изображение - запускаем DALL-E параллельно
        # (это происходит в основном коде бота после получения текста)

    except Exception as e:
        logger.error(f"❌ Критическая ошибка координации: {e}")
        result["error"] = str(e)

    return result


async def call_xai_with_fallback(messages: List[Dict], needs_image: bool = False) -> str:
    """
    Вызов XAI с обработкой ошибок

    Args:
        messages: Список сообщений
        needs_image: Требуется ли генерация изображения

    Returns:
        Текстовый ответ
    """
    client = get_xai_client()
    if not client:
        raise Exception("XAI клиент недоступен")

    # Выбор модели в зависимости от задачи
    if needs_image:
        model = "grok-2-1212"  # Reasoning модель для лучшего анализа
        max_tokens = 2000
    else:
        model = "grok-2-1212"
        max_tokens = 2500

    logger.info(f"🚀 Вызов XAI модели: {model}")

    # Используем асинхронную версию
    response = await client.chat_completions_create_async(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.7,
        search_parameters={
            "mode": "auto",
            "return_citations": True,
            "sources": [{"type": "web"}, {"type": "news"}]
        }
    )

    if response and "choices" in response and len(response["choices"]) > 0:
        return response["choices"][0]["message"]["content"]
    else:
        raise Exception("XAI вернул пустой ответ")


async def call_anthropic_with_prompt(messages: List[Dict]) -> str:
    """
    Вызов Anthropic Claude как fallback

    Args:
        messages: Список сообщений

    Returns:
        Текстовый ответ
    """
    client = get_anthropic_client()
    if not client:
        raise Exception("Anthropic клиент недоступен")

    logger.info("🚀 Вызов Anthropic Claude (fallback)")

    # Anthropic требует отдельно system и messages
    system_content = ""
    user_messages = []

    for msg in messages:
        if msg["role"] == "system":
            system_content = msg["content"]
        else:
            user_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    # Используем async версию через executor
    loop = asyncio.get_event_loop()

    def _call_claude():
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2500,
            system=system_content,
            messages=user_messages
        )
        return response.content[0].text

    text = await loop.run_in_executor(None, _call_claude)
    return text


def extract_image_prompt_from_response(text: str) -> Optional[str]:
    """
    Извлечь промпт для генерации изображения из ответа AI

    Args:
        text: Ответ от AI

    Returns:
        Промпт для DALL-E или None
    """
    import re

    # Ищем блок "Промпт для генерации изображения:"
    patterns = [
        r"📝\s*\*\*Промпт для генерации изображения:\*\*\s*\n\"([^\"]+)\"",
        r"📝\s*\*\*Промпт для генерации изображения:\*\*\s*\n([^\n]+)",
        r"Промпт для DALL-E:\s*\n\"([^\"]+)\"",
        r"Промпт для DALL-E:\s*\n([^\n]+)",
        r"Image prompt:\s*\"([^\"]+)\"",
        r"Image prompt:\s*([^\n]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            prompt = match.group(1).strip()
            logger.info(f"✅ Найден промпт: {prompt[:50]}...")
            return prompt

    logger.warning("⚠️ Промпт для изображения не найден в ответе AI")
    return None


# === ПАРАЛЛЕЛЬНАЯ ГЕНЕРАЦИЯ ===

async def generate_text_and_image_parallel(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    system_prompt: str = ""
) -> Dict:
    """
    Параллельная генерация текста (XAI) и изображения (DALL-E)

    Args:
        user_message: Сообщение пользователя
        conversation_history: История разговора
        system_prompt: Системный промпт

    Returns:
        Dict с результатами текста и изображения
    """
    from openai_dalle import generate_image_dalle

    logger.info("🚀 Запуск параллельной генерации текста и изображения")

    # Сначала XAI анализирует и дает промпт
    coordination_result = await analyze_request_and_coordinate(
        user_message,
        conversation_history,
        system_prompt
    )

    if coordination_result["error"]:
        return coordination_result

    # Если нужно изображение - запускаем DALL-E параллельно с возвратом текста
    if coordination_result["needs_image"] and coordination_result["image_prompt"]:
        logger.info("🎨 Запуск DALL-E для генерации изображения...")

        try:
            # Генерируем изображение (это может занять время)
            image_result = await generate_image_dalle(
                prompt=coordination_result["image_prompt"],
                size="1024x1024",
                quality="standard"
            )

            coordination_result["image_result"] = image_result
            logger.info("✅ Изображение успешно сгенерировано")

        except Exception as e:
            logger.error(f"❌ Ошибка генерации изображения: {e}")
            coordination_result["image_result"] = None

    return coordination_result


# === СТАТУС СИСТЕМЫ ===

def get_ai_status() -> Dict[str, bool]:
    """
    Получить статус доступности AI сервисов

    Returns:
        Dict с доступностью каждого AI
    """
    status = {
        "xai_available": bool(XAI_API_KEY and get_xai_client()),
        "openai_available": bool(OPENAI_API_KEY and get_openai_client()),
        "anthropic_available": bool(ANTHROPIC_API_KEY and get_anthropic_client())
    }

    return status
