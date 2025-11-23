"""
FastAPI Middleware
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования всех запросов"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Обработка запроса

        Args:
            request: Запрос
            call_next: Следующий handler

        Returns:
            Response: Ответ
        """
        # Начало обработки
        start_time = time.time()

        # ID запроса
        request_id = f"{int(time.time() * 1000)}"

        # Логируем входящий запрос
        logger.info(
            f"Request {request_id}: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None
            }
        )

        # Обрабатываем запрос
        try:
            response = await call_next(request)

            # Время обработки
            process_time = time.time() - start_time

            # Логируем ответ
            logger.info(
                f"Response {request_id}: {response.status_code} in {process_time:.3f}s",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "process_time": process_time
                }
            )

            # Добавляем заголовки
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.3f}"

            return response

        except Exception as e:
            process_time = time.time() - start_time

            logger.error(
                f"Error {request_id}: {str(e)}",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "process_time": process_time
                },
                exc_info=True
            )

            raise


class CORSHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware для добавления CORS заголовков"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Обработка запроса"""
        response = await call_next(request)

        # Добавляем CORS заголовки
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Expose-Headers"] = "X-Request-ID, X-Process-Time"

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware для безопасности"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Обработка запроса"""
        response = await call_next(request)

        # Добавляем security заголовки
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
