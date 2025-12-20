"""
Оптимизированные обработчики для разных AI моделей
Используются в bot.py для умного распределения задач
"""

import logging
import asyncio
from typing import Dict, Optional
import os

logger = logging.getLogger(__name__)


# ============================================================================
# ОБРАБОТЧИК GROK (простые вопросы, web search)
# ============================================================================

async def handle_with_grok(
    question: str,
    user_id: int,
    conversation_history: list,
    system_prompt: str,
    needs_web_search: bool = False
) -> str:
    """
    Обработка вопроса через xAI Grok

    Args:
        question: Вопрос пользователя
        user_id: ID пользователя
        conversation_history: История разговора
        system_prompt: Системный промпт
        needs_web_search: Нужен ли поиск в интернете

    Returns:
        Ответ от Grok
    """
    logger.info(f"🟢 Используем Grok {'с web search' if needs_web_search else 'без web search'}")

    try:
        from xai_client import XAIClient

        xai_client = XAIClient(api_key=os.getenv("XAI_API_KEY"))

        # Формируем сообщения
        messages = [{"role": "system", "content": system_prompt}]

        for msg in conversation_history:
            if msg.get("role") != "system":
                messages.append(msg)

        messages.append({"role": "user", "content": question})

        # Параметры поиска
        search_parameters = None
        if needs_web_search:
            search_parameters = [{"type": "web_search"}]

        # Вызываем Grok
        response = await xai_client.chat_completions_create_async(
            model="grok-2-latest",
            messages=messages,
            max_tokens=2000,
            temperature=0.7,
            search_parameters=search_parameters
        )

        answer = response["choices"][0]["message"]["content"]

        logger.info(f"✅ Ответ получен от Grok ({len(answer)} символов)")

        return answer

    except Exception as e:
        logger.error(f"❌ Ошибка Grok: {e}")
        raise


# ============================================================================
# ОБРАБОТЧИК CLAUDE (технические вопросы)
# ============================================================================

async def handle_with_claude_technical(
    question: str,
    user_id: int,
    conversation_history: list,
    system_prompt: str
) -> str:
    """
    Обработка технического вопроса через Claude Sonnet 4.5

    Args:
        question: Вопрос пользователя
        user_id: ID пользователя
        conversation_history: История разговора
        system_prompt: Системный промпт

    Returns:
        Ответ от Claude
    """
    logger.info("🔵 Используем Claude Sonnet 4.5 для технического вопроса")

    try:
        from anthropic import Anthropic

        claude_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        # Формируем сообщения
        messages = []
        for msg in conversation_history:
            if msg.get("role") != "system":
                messages.append(msg)

        messages.append({"role": "user", "content": question})

        # Вызываем Claude в отдельном потоке
        loop = asyncio.get_event_loop()

        def _call_claude():
            response = claude_client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2500,
                temperature=0.7,
                system=system_prompt,
                messages=messages
            )
            return response.content[0].text

        answer = await loop.run_in_executor(None, _call_claude)

        logger.info(f"✅ Ответ получен от Claude ({len(answer)} символов)")

        return answer

    except Exception as e:
        logger.error(f"❌ Ошибка Claude: {e}")
        raise


# ============================================================================
# ОБРАБОТЧИК GEMINI VISION (анализ фото дефектов)
# ============================================================================

async def handle_with_gemini_vision(
    question: str,
    photo_file_id: str,
    bot,
    system_prompt: str
) -> str:
    """
    Анализ фото дефектов через Gemini Vision

    Args:
        question: Вопрос/описание к фото
        photo_file_id: ID фото в Telegram
        bot: Telegram bot instance
        system_prompt: Системный промпт

    Returns:
        Экспертное заключение по дефектам
    """
    logger.info("🟣 Используем Gemini Vision для анализа дефекта на фото")

    try:
        import google.generativeai as genai
        import base64
        from PIL import Image
        from io import BytesIO

        # Конфигурируем Gemini
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        # Скачиваем фото
        file = await bot.get_file(photo_file_id)
        photo_bytes = await file.download_as_bytearray()

        # Конвертируем в base64
        image = Image.open(BytesIO(photo_bytes))
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()

        # Формируем промпт
        full_prompt = f"{system_prompt}\n\nВОПРОС ПОЛЬЗОВАТЕЛЯ: {question}"

        # Генерируем ответ в отдельном потоке
        loop = asyncio.get_event_loop()

        def _call_gemini():
            response = model.generate_content([
                full_prompt,
                {"mime_type": "image/jpeg", "data": img_base64}
            ])
            return response.text

        analysis = await loop.run_in_executor(None, _call_gemini)

        logger.info(f"✅ Анализ готов от Gemini ({len(analysis)} символов)")

        return analysis

    except Exception as e:
        logger.error(f"❌ Ошибка Gemini: {e}")
        raise


# ============================================================================
# ОБРАБОТЧИК CLAUDE DALLE (генерация чертежей)
# ============================================================================

async def handle_with_claude_dalle(
    question: str,
    dalle_prompt_creator_system: str
) -> Dict:
    """
    Генерация технического чертежа
    Шаг 1: Claude создаёт детальный промпт по ГОСТ
    Шаг 2: DALL-E генерирует чертёж

    Args:
        question: Описание того, что нужно нарисовать
        dalle_prompt_creator_system: Системный промпт для создания промптов

    Returns:
        Dict с изображением и описанием
    """
    logger.info("🎨 Генерация чертежа: Claude → DALL-E")

    try:
        from anthropic import Anthropic
        from openai import OpenAI
        import re

        # Шаг 1: Claude создаёт промпт для DALL-E
        claude_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        loop = asyncio.get_event_loop()

        def _call_claude_for_prompt():
            response = claude_client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2000,
                temperature=0.7,
                system=dalle_prompt_creator_system,
                messages=[
                    {"role": "user", "content": f"Создай промпт для DALL-E: {question}"}
                ]
            )
            return response.content[0].text

        logger.info("📝 Шаг 1/2: Claude создаёт детальный промпт по ГОСТ...")
        full_response = await loop.run_in_executor(None, _call_claude_for_prompt)

        # Парсим ответ Claude (формат: ПРОМПТ: ... ОПИСАНИЕ: ...)
        prompt_match = re.search(r'\*\*ПРОМПТ:\*\*\s*\n(.+?)(?=\n\*\*ОПИСАНИЕ:|$)', full_response, re.DOTALL)
        desc_match = re.search(r'\*\*ОПИСАНИЕ:\*\*\s*\n(.+)', full_response, re.DOTALL)

        dalle_prompt = prompt_match.group(1).strip() if prompt_match else full_response
        description = desc_match.group(1).strip() if desc_match else "Технический чертёж по ГОСТ"

        # Убираем кавычки
        dalle_prompt = dalle_prompt.strip('"').strip("'")

        logger.info(f"✅ Промпт готов: {dalle_prompt[:100]}...")

        # Шаг 2: DALL-E генерирует чертёж
        logger.info("🎨 Шаг 2/2: DALL-E генерирует чертёж...")

        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        def _call_dalle():
            response = openai_client.images.generate(
                model="dall-e-3",
                prompt=dalle_prompt,
                size="1024x1024",
                quality="standard",
                n=1
            )
            return response.data[0].url

        image_url = await loop.run_in_executor(None, _call_dalle)

        logger.info(f"✅ Чертёж готов: {image_url}")

        return {
            "image_url": image_url,
            "description": description,
            "prompt_used": dalle_prompt
        }

    except Exception as e:
        logger.error(f"❌ Ошибка генерации чертежа: {e}")
        raise


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def format_claude_response_for_telegram(text: str) -> str:
    """
    Форматирование ответа Claude для Telegram
    """
    # Можно добавить дополнительное форматирование если нужно
    return text


def format_gemini_response_for_telegram(text: str) -> str:
    """
    Форматирование ответа Gemini для Telegram
    """
    return text
