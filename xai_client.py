"""
Клиент для работы с xAI Grok API без зависимости от OpenAI
"""
import httpx
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class XAIClient:
    """Клиент для xAI Grok API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.x.ai/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def chat_completions_create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        timeout: int = 120,
        search_parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Создать chat completion запрос к xAI Grok API

        Args:
            model: Модель (например "grok-2-latest")
            messages: Список сообщений [{"role": "user", "content": "..."}]
            max_tokens: Максимальное количество токенов в ответе
            temperature: Температура генерации (0-2)
            timeout: Таймаут запроса в секундах
            search_parameters: Параметры поиска [{"type": "web_search"}, {"type": "x_search"}]

        Returns:
            Ответ от API в формате словаря
        """
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        # Добавляем tools если переданы
        if search_parameters:
            payload["search_parameters"] = search_parameters

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            logger.error(f"xAI API timeout after {timeout}s")
            raise Exception("⚠️ Превышено время ожидания ответа от AI. Попробуйте еще раз.")
        except httpx.HTTPStatusError as e:
            logger.error(f"xAI API HTTP error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 429:
                raise Exception("⚠️ Превышен лимит запросов к xAI API. Попробуйте через минуту.")
            elif e.response.status_code == 401:
                raise Exception("❌ Неверный API ключ xAI. Проверьте XAI_API_KEY в настройках.")
            else:
                raise Exception(f"⚠️ Ошибка xAI API: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Unexpected xAI API error: {e}")
            raise Exception("❌ Неожиданная ошибка при обращении к xAI API.")

    async def chat_completions_create_async(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        timeout: int = 120,
        search_parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Асинхронная версия chat_completions_create
        """
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        # Добавляем tools если переданы
        if search_parameters:
            payload["search_parameters"] = search_parameters

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            logger.error(f"xAI API timeout after {timeout}s")
            raise Exception("⚠️ Превышено время ожидания ответа от AI. Попробуйте еще раз.")
        except httpx.HTTPStatusError as e:
            logger.error(f"xAI API HTTP error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 429:
                raise Exception("⚠️ Превышен лимит запросов к xAI API. Попробуйте через минуту.")
            elif e.response.status_code == 401:
                raise Exception("❌ Неверный API ключ xAI. Проверьте XAI_API_KEY в настройках.")
            else:
                raise Exception(f"⚠️ Ошибка xAI API: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Unexpected xAI API error: {e}")
            raise Exception("❌ Неожиданная ошибка при обращении к xAI API.")

    async def chat_completions_create_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        timeout: int = 120
    ):
        """
        Streaming версия chat completions (асинхронный генератор)

        Yields:
            str - части текста по мере их получения от API
        """
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream('POST', url, json=payload, headers=self.headers) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith('data: '):
                            data = line[6:]  # Убираем 'data: '

                            if data == '[DONE]':
                                break

                            try:
                                import json
                                chunk = json.loads(data)

                                # Извлекаем текст из чанка
                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    delta = chunk['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                continue

        except httpx.TimeoutException:
            logger.error(f"xAI API streaming timeout after {timeout}s")
            raise Exception("⚠️ Превышено время ожидания ответа от AI.")
        except httpx.HTTPStatusError as e:
            logger.error(f"xAI API streaming HTTP error: {e.response.status_code}")
            if e.response.status_code == 429:
                raise Exception("⚠️ Превышен лимит запросов к xAI API. Попробуйте через минуту.")
            elif e.response.status_code == 401:
                raise Exception("❌ Неверный API ключ xAI.")
            else:
                raise Exception(f"⚠️ Ошибка xAI API: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Unexpected xAI streaming error: {e}")
            raise Exception("❌ Ошибка при получении ответа от AI.")


def call_xai_with_retry(client: XAIClient, model: str, messages: List[Dict[str, str]],
                        max_tokens: int = 1000, temperature: float = 0.7,
                        max_retries: int = 3, search_parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Вызов xAI API с retry logic и exponential backoff

    Args:
        client: Экземпляр XAIClient
        model: Модель для использования
        messages: Список сообщений
        max_tokens: Максимум токенов
        temperature: Температура
        max_retries: Максимальное количество попыток
        search_parameters: Параметры поиска (web_search, x_search и т.д.)

    Returns:
        Ответ от API
    """
    import time

    for attempt in range(max_retries):
        try:
            return client.chat_completions_create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                tools=tools
            )
        except Exception as e:
            error_message = str(e)

            # Если это rate limit, пробуем еще раз
            if "лимит" in error_message.lower() and attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"xAI API rate limit hit (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s")
                time.sleep(wait_time)
            else:
                # Для всех остальных ошибок или если попытки исчерпаны
                raise

    raise Exception("⚠️ xAI API временно недоступен после нескольких попыток.")
