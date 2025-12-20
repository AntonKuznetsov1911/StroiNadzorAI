"""
ПРИМЕРЫ ИНТЕГРАЦИИ ОПТИМИЗИРОВАННЫХ МОДЕЛЕЙ В BOT.PY

Этот файл содержит готовые к использованию функции
для внедрения умного выбора моделей в существующий бот
"""

import logging
from typing import Dict, Optional, List
import asyncio

# Импорт оптимизированных компонентов
from model_selector import ModelSelector, should_use_web_search
from optimized_prompts import (
    CLAUDE_SYSTEM_PROMPT_TECHNICAL,
    CLAUDE_DALLE_PROMPT_CREATOR,
    GROK_SYSTEM_PROMPT_GENERAL,
    GEMINI_VISION_PROMPT_DEFECTS
)

logger = logging.getLogger(__name__)


# ============================================================================
# ПРИМЕР 1: Умный обработчик текстовых сообщений
# ============================================================================

async def handle_message_optimized(update, context):
    """
    Оптимизированный обработчик сообщений с умным выбором модели

    Замените вашу текущую функцию handle_message на эту
    """
    user_id = update.effective_user.id
    question = update.message.text
    has_photo = bool(update.message.photo)

    # Инициализация селектора моделей
    selector = ModelSelector()

    # Умный выбор модели
    decision = selector.classify_request(question, has_photo)

    logger.info(f"🤖 Модель: {decision['model']} | Причина: {decision['reason']}")
    logger.info(f"💰 Ожидаемая стоимость: ${decision['estimated_cost']:.3f}")

    # Отправляем сообщение "печатаю..."
    thinking_message = await update.message.reply_text("🤔 Анализирую вопрос...")

    try:
        # Выбираем обработчик в зависимости от модели
        if decision["model"] == "claude_technical":
            response = await handle_with_claude_technical(
                question, user_id, decision["needs_web_search"]
            )

        elif decision["model"] == "claude_dalle":
            response = await handle_with_claude_dalle(question, user_id)

        elif decision["model"] == "gemini_vision":
            photo = update.message.photo[-1]  # Берём фото в лучшем качестве
            response = await handle_with_gemini_vision(question, photo, user_id)

        elif decision["model"] == "grok_websearch":
            response = await handle_with_grok_websearch(question, user_id)

        else:  # grok_general
            response = await handle_with_grok_general(question, user_id)

        # Удаляем "печатаю..."
        await thinking_message.delete()

        # Отправляем ответ
        await update.message.reply_text(response, parse_mode="Markdown")

        # Сохраняем в историю
        await save_to_history(user_id, question, response)

        # Логируем статистику
        log_usage_stats(decision)

    except Exception as e:
        logger.error(f"Ошибка обработки: {e}")
        await thinking_message.edit_text(
            "⚠️ Произошла ошибка. Попробуйте ещё раз или перефразируйте вопрос."
        )


# ============================================================================
# ПРИМЕР 2: Обработчик с Claude (технические вопросы)
# ============================================================================

async def handle_with_claude_technical(
    question: str,
    user_id: int,
    needs_web_search: bool = False
) -> str:
    """
    Обработка технического вопроса через Claude Sonnet 4.5

    Args:
        question: Вопрос пользователя
        user_id: ID пользователя
        needs_web_search: Нужен ли дополнительный web search

    Returns:
        Ответ от Claude
    """
    logger.info("🔵 Используем Claude Sonnet 4.5 для технического вопроса")

    # Получаем историю разговора
    conversation_history = await get_conversation_history(user_id, limit=10)

    # Если нужен web search - сначала собираем актуальные данные через Grok
    web_context = ""
    if needs_web_search:
        logger.info("🌐 Сначала ищем актуальные данные через Grok...")
        web_context = await search_with_grok(question)

    # Формируем сообщения для Claude
    messages = [
        {"role": "system", "content": CLAUDE_SYSTEM_PROMPT_TECHNICAL}
    ]

    # Добавляем контекст из web search (если есть)
    if web_context:
        messages.append({
            "role": "system",
            "content": f"АКТУАЛЬНАЯ ИНФОРМАЦИЯ ИЗ ИНТЕРНЕТА:\n{web_context}"
        })

    # Добавляем историю
    messages.extend(conversation_history)

    # Добавляем текущий вопрос
    messages.append({"role": "user", "content": question})

    # Вызываем Claude
    claude_client = get_claude_client()

    # Отделяем system от messages для Anthropic API
    system_content = messages[0]["content"]
    if web_context:
        system_content += "\n\n" + messages[1]["content"]
        user_messages = messages[2:]
    else:
        user_messages = messages[1:]

    response = claude_client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2500,
        temperature=0.7,
        system=system_content,
        messages=user_messages
    )

    answer = response.content[0].text

    logger.info(f"✅ Ответ получен от Claude ({len(answer)} символов)")

    return answer


# ============================================================================
# ПРИМЕР 3: Обработчик с Grok (простые вопросы + web search)
# ============================================================================

async def handle_with_grok_general(question: str, user_id: int) -> str:
    """
    Обработка простого вопроса через Grok

    Args:
        question: Вопрос пользователя
        user_id: ID пользователя

    Returns:
        Ответ от Grok
    """
    logger.info("🟢 Используем Grok для простого вопроса")

    # Получаем историю
    conversation_history = await get_conversation_history(user_id, limit=5)

    # Формируем сообщения
    messages = [
        {"role": "system", "content": GROK_SYSTEM_PROMPT_GENERAL}
    ]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": question})

    # Определяем, нужен ли web search
    use_web_search = should_use_web_search(question)

    # Вызываем Grok
    grok_client = get_grok_client()

    search_params = None
    if use_web_search:
        logger.info("🌐 Включаем web search для Grok")
        search_params = {
            "mode": "auto",
            "return_citations": True,
            "sources": [
                {"type": "web"},
                {"type": "news"}
            ]
        }

    response = await call_grok_async(
        client=grok_client,
        model="grok-4-1-fast",
        messages=messages,
        max_tokens=1500,
        temperature=0.7,
        search_parameters=search_params
    )

    logger.info(f"✅ Ответ получен от Grok ({len(response)} символов)")

    return response


# ============================================================================
# ПРИМЕР 4: Генерация чертежей (Claude создаёт промпт → DALL-E рисует)
# ============================================================================

async def handle_with_claude_dalle(question: str, user_id: int) -> Dict:
    """
    Генерация технического чертежа
    Шаг 1: Claude создаёт детальный промпт по ГОСТ
    Шаг 2: DALL-E генерирует чертёж

    Args:
        question: Описание того, что нужно нарисовать
        user_id: ID пользователя

    Returns:
        Dict с изображением и описанием
    """
    logger.info("🎨 Генерация чертежа: Claude → DALL-E")

    # Шаг 1: Claude создаёт промпт для DALL-E
    claude_client = get_claude_client()

    prompt_messages = [
        {"role": "system", "content": CLAUDE_DALLE_PROMPT_CREATOR},
        {"role": "user", "content": f"Создай промпт для DALL-E: {question}"}
    ]

    logger.info("📝 Шаг 1/2: Claude создаёт детальный промпт по ГОСТ...")

    response = claude_client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2000,
        temperature=0.7,
        messages=prompt_messages
    )

    full_response = response.content[0].text

    # Парсим ответ Claude (формат: ПРОМПТ: ... ОПИСАНИЕ: ...)
    dalle_prompt, description = parse_claude_dalle_response(full_response)

    logger.info(f"✅ Промпт готов: {dalle_prompt[:100]}...")

    # Шаг 2: DALL-E генерирует чертёж
    logger.info("🎨 Шаг 2/2: DALL-E генерирует чертёж...")

    openai_client = get_openai_client()

    image_response = openai_client.images.generate(
        model="dall-e-3",
        prompt=dalle_prompt,
        size="1024x1024",
        quality="standard",
        n=1
    )

    image_url = image_response.data[0].url

    logger.info(f"✅ Чертёж готов: {image_url}")

    return {
        "image_url": image_url,
        "description": description,
        "prompt_used": dalle_prompt
    }


# ============================================================================
# ПРИМЕР 5: Анализ фото дефектов через Gemini Vision
# ============================================================================

async def handle_with_gemini_vision(
    question: str,
    photo,
    user_id: int
) -> str:
    """
    Анализ фото дефектов через Gemini Vision

    Args:
        question: Описание/вопрос к фото
        photo: Telegram Photo object
        user_id: ID пользователя

    Returns:
        Экспертное заключение по дефектам
    """
    logger.info("🟣 Используем Gemini Vision для анализа дефекта")

    # Скачиваем фото
    import io
    from PIL import Image
    import base64

    file = await photo.get_file()
    photo_bytes = await file.download_as_bytearray()

    # Конвертируем в base64 для Gemini
    image = Image.open(io.BytesIO(photo_bytes))
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()

    # Вызываем Gemini
    import google.generativeai as genai

    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-2.5-flash')

    # Формируем промпт
    full_prompt = f"{GEMINI_VISION_PROMPT_DEFECTS}\n\nВОПРОС ПОЛЬЗОВАТЕЛЯ: {question}"

    # Генерируем ответ
    response = model.generate_content([
        full_prompt,
        {"mime_type": "image/jpeg", "data": img_base64}
    ])

    analysis = response.text

    logger.info(f"✅ Анализ готов ({len(analysis)} символов)")

    return analysis


# ============================================================================
# ПРИМЕР 6: Параллельная обработка (для комплексных запросов)
# ============================================================================

async def handle_complex_request_parallel(question: str, user_id: int) -> str:
    """
    Параллельная обработка сложного запроса
    Например: вопрос о нормативе требует и технического анализа,
    и проверки актуальности

    Args:
        question: Вопрос пользователя
        user_id: ID пользователя

    Returns:
        Комбинированный ответ
    """
    logger.info("⚡ Параллельная обработка: Claude + Grok web search")

    # Запускаем параллельно
    tasks = [
        handle_with_claude_technical(question, user_id, needs_web_search=False),
        search_with_grok(question)
    ]

    claude_answer, web_data = await asyncio.gather(*tasks)

    # Комбинируем результаты
    if web_data:
        combined_answer = f"{claude_answer}\n\n{web_data}"
    else:
        combined_answer = claude_answer

    return combined_answer


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

async def search_with_grok(question: str) -> str:
    """
    Поиск актуальной информации через Grok web search

    Returns:
        Результаты поиска или пустую строку
    """
    grok_client = get_grok_client()

    messages = [
        {
            "role": "system",
            "content": "Найди актуальную информацию в интернете и предоставь её кратко."
        },
        {"role": "user", "content": question}
    ]

    search_params = {
        "mode": "auto",
        "return_citations": True,
        "sources": [
            {"type": "web"},
            {"type": "news"}
        ]
    }

    try:
        response = await call_grok_async(
            client=grok_client,
            model="grok-4-1-fast",
            messages=messages,
            max_tokens=800,
            temperature=0.5,
            search_parameters=search_params
        )

        return f"🌐 **АКТУАЛЬНЫЕ ДАННЫЕ ИЗ ИНТЕРНЕТА:**\n{response}"

    except Exception as e:
        logger.error(f"Ошибка web search: {e}")
        return ""


def parse_claude_dalle_response(response: str) -> tuple:
    """
    Парсинг ответа Claude для извлечения промпта и описания

    Args:
        response: Полный ответ от Claude

    Returns:
        (dalle_prompt, description)
    """
    import re

    # Ищем блоки ПРОМПТ: и ОПИСАНИЕ:
    prompt_match = re.search(r'\*\*ПРОМПТ:\*\*\s*\n(.+?)(?=\n\*\*ОПИСАНИЕ:|$)', response, re.DOTALL)
    desc_match = re.search(r'\*\*ОПИСАНИЕ:\*\*\s*\n(.+)', response, re.DOTALL)

    dalle_prompt = prompt_match.group(1).strip() if prompt_match else response
    description = desc_match.group(1).strip() if desc_match else "Технический чертёж по ГОСТ"

    # Убираем кавычки из промпта если есть
    dalle_prompt = dalle_prompt.strip('"').strip("'")

    return dalle_prompt, description


async def get_conversation_history(user_id: int, limit: int = 10) -> List[Dict]:
    """
    Получить историю разговора пользователя

    Args:
        user_id: ID пользователя
        limit: Максимальное количество сообщений

    Returns:
        List сообщений в формате [{"role": "user", "content": "..."}, ...]
    """
    # Здесь ваша логика получения истории из БД или JSON
    # Пример:
    try:
        from history_manager import get_user_history
        history = await get_user_history(user_id, limit=limit)
        return history
    except:
        return []


async def save_to_history(user_id: int, question: str, answer: str):
    """
    Сохранить диалог в историю

    Args:
        user_id: ID пользователя
        question: Вопрос
        answer: Ответ
    """
    try:
        from history_manager import add_message_to_history_async
        await add_message_to_history_async(user_id, 'user', question)
        await add_message_to_history_async(user_id, 'assistant', answer)
    except Exception as e:
        logger.error(f"Ошибка сохранения истории: {e}")


def log_usage_stats(decision: Dict):
    """
    Логировать статистику использования моделей

    Args:
        decision: Результат classify_request()
    """
    logger.info(
        f"📊 СТАТИСТИКА: "
        f"Модель={decision['model']} | "
        f"Стоимость=${decision['estimated_cost']:.3f} | "
        f"Приоритет={decision['priority']}"
    )

    # Можно сохранять в БД для аналитики


# ============================================================================
# ПРИМЕР 7: A/B тестирование (сравнение Grok vs Claude)
# ============================================================================

async def ab_test_models(question: str, user_id: int) -> Dict:
    """
    A/B тестирование: отправить один вопрос и Grok, и Claude
    Сравнить качество ответов

    Args:
        question: Вопрос для тестирования
        user_id: ID пользователя

    Returns:
        Dict с ответами обеих моделей
    """
    logger.info("🔬 A/B тест: Grok vs Claude")

    # Запускаем параллельно
    tasks = [
        handle_with_grok_general(question, user_id),
        handle_with_claude_technical(question, user_id)
    ]

    grok_answer, claude_answer = await asyncio.gather(*tasks)

    return {
        "grok": grok_answer,
        "claude": claude_answer,
        "question": question
    }


# ============================================================================
# ПРИМЕР 8: Fallback chain (цепочка запасных вариантов)
# ============================================================================

async def answer_with_fallback_chain(question: str, user_id: int) -> str:
    """
    Попытка ответить с цепочкой fallback
    1. Пробуем Grok (бесплатно)
    2. Если ошибка → пробуем Claude
    3. Если и Claude не работает → заглушка

    Args:
        question: Вопрос
        user_id: ID пользователя

    Returns:
        Ответ
    """
    # Попытка 1: Grok
    try:
        logger.info("Попытка 1: Grok")
        return await handle_with_grok_general(question, user_id)
    except Exception as e:
        logger.warning(f"Grok недоступен: {e}")

    # Попытка 2: Claude
    try:
        logger.info("Попытка 2: Claude (fallback)")
        return await handle_with_claude_technical(question, user_id)
    except Exception as e:
        logger.error(f"Claude также недоступен: {e}")

    # Fallback: заглушка
    return (
        "⚠️ К сожалению, AI сервисы временно недоступны.\n"
        "Попробуйте повторить запрос через несколько минут."
    )


# ============================================================================
# ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ
# ============================================================================

def get_claude_client():
    """Получить Claude API клиент"""
    from anthropic import Anthropic
    import os
    return Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def get_grok_client():
    """Получить Grok API клиент"""
    from xai_client import XAIClient
    import os
    return XAIClient(api_key=os.getenv("XAI_API_KEY"))


def get_openai_client():
    """Получить OpenAI API клиент"""
    from openai import OpenAI
    import os
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def call_grok_async(client, model, messages, max_tokens, temperature, search_parameters=None):
    """
    Асинхронный вызов Grok API

    Args:
        client: XAI клиент
        model: Модель Grok
        messages: Список сообщений
        max_tokens: Максимум токенов
        temperature: Температура
        search_parameters: Параметры web search

    Returns:
        Текстовый ответ
    """
    # Используем синхронный вызов через executor для асинхронности
    loop = asyncio.get_event_loop()

    def _call():
        response = client.chat_completions_create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            search_parameters=search_parameters
        )
        return response["choices"][0]["message"]["content"]

    return await loop.run_in_executor(None, _call)


# ============================================================================
# ГОТОВО!
# Теперь можно использовать эти функции в bot.py
# ============================================================================
