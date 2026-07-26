"""
Клиент для работы с xAI Grok API без зависимости от OpenAI

Поддерживает два API:
1. Chat Completions API (/v1/chat/completions) - для обычных запросов без инструментов
2. Responses API (/v1/responses) - для запросов с инструментами (web_search, x_search)
   Миграция: search_parameters устарел с 12.01.2026, заменён на tools в Responses API
"""
import httpx
import json
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

    def _parse_responses_api_output(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Преобразовать ответ Responses API в формат Chat Completions для обратной совместимости.

        Responses API возвращает:
        {"output": [{"type": "message", "content": [{"type": "output_text", "text": "..."}]}]}

        Преобразуем в:
        {"choices": [{"message": {"content": "..."}}]}
        """
        text_parts = []

        for output_item in data.get("output", []):
            if output_item.get("type") == "message":
                for content_item in output_item.get("content", []):
                    if content_item.get("type") == "output_text":
                        text_parts.append(content_item.get("text", ""))

        content = "\n".join(text_parts) if text_parts else ""

        return {
            "choices": [{
                "message": {
                    "content": content,
                    "role": "assistant"
                }
            }],
            "usage": data.get("usage", {}),
            "id": data.get("id", "")
        }

    def chat_completions_create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        timeout: int = 120,
        search_parameters: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Создать запрос к xAI Grok API.

        Если переданы tools — использует Responses API (/v1/responses).
        Иначе — Chat Completions API (/v1/chat/completions).

        Args:
            model: Модель (например "grok-4-1-fast")
            messages: Список сообщений [{"role": "user", "content": "..."}]
            max_tokens: Максимальное количество токенов в ответе
            temperature: Температура генерации (0-2)
            timeout: Таймаут запроса в секундах
            search_parameters: УСТАРЕЛ (игнорируется). Используйте tools.
            tools: Инструменты [{"type": "web_search"}, {"type": "x_search"}]

        Returns:
            Ответ от API в формате словаря (совместимом с chat completions)
        """
        # Если переданы tools — используем Responses API
        if tools:
            return self._responses_create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
                tools=tools
            )

        # Обычный Chat Completions API
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

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
            if "⚠️" in str(e) or "❌" in str(e):
                raise
            logger.error(f"Unexpected xAI API error: {e}")
            raise Exception("❌ Неожиданная ошибка при обращении к xAI API.")

    def _responses_create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        timeout: int = 180,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Вызов xAI Responses API (/v1/responses) с инструментами (web_search, x_search).

        Returns:
            Ответ в формате chat completions для обратной совместимости
        """
        url = f"{self.base_url}/responses"

        payload = {
            "model": model,
            "input": messages,
            "store": False
        }

        if tools:
            payload["tools"] = tools

        if temperature is not None:
            payload["temperature"] = temperature

        logger.info(f"🌐 Responses API: model={model}, tools={[t.get('type') for t in (tools or [])]}")

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                data = response.json()

                logger.info(f"✅ Responses API: получен ответ (id={data.get('id', 'N/A')})")

                return self._parse_responses_api_output(data)

        except httpx.TimeoutException:
            logger.error(f"xAI Responses API timeout after {timeout}s")
            raise Exception("⚠️ Превышено время ожидания ответа от AI (поиск). Попробуйте еще раз.")
        except httpx.HTTPStatusError as e:
            logger.error(f"xAI Responses API HTTP error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 429:
                raise Exception("⚠️ Превышен лимит запросов к xAI API. Попробуйте через минуту.")
            elif e.response.status_code == 401:
                raise Exception("❌ Неверный API ключ xAI. Проверьте XAI_API_KEY в настройках.")
            else:
                raise Exception(f"⚠️ Ошибка xAI Responses API: {e.response.status_code}")
        except Exception as e:
            if "⚠️" in str(e) or "❌" in str(e):
                raise
            logger.error(f"Unexpected xAI Responses API error: {e}")
            raise Exception("❌ Неожиданная ошибка при обращении к xAI Responses API.")

    async def chat_completions_create_async(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        timeout: int = 120,
        search_parameters: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Асинхронная версия. Если tools — Responses API, иначе — Chat Completions.
        """
        if tools:
            return await self._responses_create_async(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
                tools=tools
            )

        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

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
            if "⚠️" in str(e) or "❌" in str(e):
                raise
            logger.error(f"Unexpected xAI API error: {e}")
            raise Exception("❌ Неожиданная ошибка при обращении к xAI API.")

    async def _responses_create_async(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        timeout: int = 180,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Асинхронный вызов Responses API (/v1/responses) с инструментами.

        Returns:
            Ответ в формате chat completions для обратной совместимости
        """
        url = f"{self.base_url}/responses"

        payload = {
            "model": model,
            "input": messages,
            "store": False
        }

        if tools:
            payload["tools"] = tools

        if temperature is not None:
            payload["temperature"] = temperature

        logger.info(f"🌐 Responses API (async): model={model}, tools={[t.get('type') for t in (tools or [])]}")

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                data = response.json()

                logger.info(f"✅ Responses API (async): получен ответ (id={data.get('id', 'N/A')})")

                return self._parse_responses_api_output(data)

        except httpx.TimeoutException:
            logger.error(f"xAI Responses API (async) timeout after {timeout}s")
            raise Exception("⚠️ Превышено время ожидания ответа от AI (поиск). Попробуйте еще раз.")
        except httpx.HTTPStatusError as e:
            logger.error(f"xAI Responses API (async) HTTP error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 429:
                raise Exception("⚠️ Превышен лимит запросов к xAI API. Попробуйте через минуту.")
            elif e.response.status_code == 401:
                raise Exception("❌ Неверный API ключ xAI. Проверьте XAI_API_KEY в настройках.")
            else:
                raise Exception(f"⚠️ Ошибка xAI Responses API: {e.response.status_code}")
        except Exception as e:
            if "⚠️" in str(e) or "❌" in str(e):
                raise
            logger.error(f"Unexpected xAI Responses API (async) error: {e}")
            raise Exception("❌ Неожиданная ошибка при обращении к xAI Responses API.")

    async def chat_completions_create_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        timeout: int = 120,
        search_parameters: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Streaming версия (асинхронный генератор).

        Если tools — использует Responses API со streaming.
        Иначе — Chat Completions API со streaming.

        Yields:
            str - части текста по мере их получения от API
        """
        if tools:
            async for chunk in self._responses_create_stream(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
                tools=tools
            ):
                yield chunk
            return

        # Обычный Chat Completions streaming
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
                            data = line[6:]

                            if data == '[DONE]':
                                break

                            try:
                                chunk = json.loads(data)

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
            if "⚠️" in str(e) or "❌" in str(e):
                raise
            logger.error(f"Unexpected xAI streaming error: {e}")
            raise Exception("❌ Ошибка при получении ответа от AI.")

    async def _responses_create_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        timeout: int = 300,
        tools: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Streaming версия Responses API (/v1/responses) с инструментами.

        Responses API streaming использует SSE с событиями вида:
        - response.output_text.delta — содержит delta текста
        - response.completed — завершение

        Yields:
            str - части текста по мере их получения
        """
        url = f"{self.base_url}/responses"

        payload = {
            "model": model,
            "input": messages,
            "stream": True,
            "store": False
        }

        if tools:
            payload["tools"] = tools

        if temperature is not None:
            payload["temperature"] = temperature

        logger.info(f"🌐 Responses API streaming: model={model}, tools={[t.get('type') for t in (tools or [])]}")

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream('POST', url, json=payload, headers=self.headers) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.startswith('data: '):
                            continue

                        data_str = line[6:]

                        if data_str == '[DONE]':
                            break

                        try:
                            event_data = json.loads(data_str)
                            event_type = event_data.get("type", "")

                            # Текстовый дельта от Responses API
                            if event_type == "response.output_text.delta":
                                delta = event_data.get("delta", "")
                                if delta:
                                    yield delta

                        except json.JSONDecodeError:
                            continue

        except httpx.TimeoutException:
            logger.error(f"xAI Responses API streaming timeout after {timeout}s")
            raise Exception("⚠️ Превышено время ожидания ответа от AI (поиск).")
        except httpx.HTTPStatusError as e:
            logger.error(f"xAI Responses API streaming HTTP error: {e.response.status_code}")
            if e.response.status_code == 429:
                raise Exception("⚠️ Превышен лимит запросов к xAI API. Попробуйте через минуту.")
            elif e.response.status_code == 401:
                raise Exception("❌ Неверный API ключ xAI.")
            else:
                raise Exception(f"⚠️ Ошибка xAI Responses API: {e.response.status_code}")
        except Exception as e:
            if "⚠️" in str(e) or "❌" in str(e):
                raise
            logger.error(f"Unexpected xAI Responses streaming error: {e}")
            raise Exception("❌ Ошибка при получении ответа от AI.")


def call_xai_with_retry(client: XAIClient, model: str, messages: List[Dict[str, str]],
                        max_tokens: int = 1000, temperature: float = 0.7,
                        max_retries: int = 3,
                        search_parameters: Optional[Dict[str, Any]] = None,
                        tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Вызов xAI API с retry logic и exponential backoff

    Args:
        client: Экземпляр XAIClient
        model: Модель для использования
        messages: Список сообщений
        max_tokens: Максимум токенов
        temperature: Температура
        max_retries: Максимальное количество попыток
        search_parameters: УСТАРЕЛ. Используйте tools.
        tools: Инструменты [{"type": "web_search"}, {"type": "x_search"}]

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
