"""
Prometheus Metrics для мониторинга системы
Отслеживание запросов, производительности, ошибок
"""

import logging
import time
from typing import Optional
from functools import wraps

from prometheus_client import (
    Counter, Histogram, Gauge, Info,
    CollectorRegistry, generate_latest,
    CONTENT_TYPE_LATEST
)

logger = logging.getLogger(__name__)


# Registry для метрик
registry = CollectorRegistry()

# ===== ИНФОРМАЦИЯ О СИСТЕМЕ =====
app_info = Info(
    'stroinadzor_app',
    'Application information',
    registry=registry
)

app_info.info({
    'version': '3.1.0',
    'name': 'StroiNadzorAI',
    'description': 'Professional Construction AI Assistant'
})


# ===== СЧЕТЧИКИ (COUNTERS) =====

# Запросы пользователей
user_requests_total = Counter(
    'stroinadzor_user_requests_total',
    'Total number of user requests',
    ['request_type', 'user_role'],  # Метки: тип запроса, роль пользователя
    registry=registry
)

# OpenAI API вызовы
openai_requests_total = Counter(
    'stroinadzor_openai_requests_total',
    'Total OpenAI API requests',
    ['model', 'request_type'],  # gpt-4o, text/photo/voice
    registry=registry
)

# Токены OpenAI
openai_tokens_total = Counter(
    'stroinadzor_openai_tokens_total',
    'Total OpenAI tokens used',
    ['model', 'token_type'],  # prompt_tokens/completion_tokens
    registry=registry
)

# Кеш
cache_operations_total = Counter(
    'stroinadzor_cache_operations_total',
    'Total cache operations',
    ['operation', 'result'],  # get/set, hit/miss
    registry=registry
)

# PDF генерация
pdf_generated_total = Counter(
    'stroinadzor_pdf_generated_total',
    'Total PDF reports generated',
    registry=registry
)

# Excel экспорты
excel_exported_total = Counter(
    'stroinadzor_excel_exported_total',
    'Total Excel exports',
    ['export_type'],  # requests/photos/analytics
    registry=registry
)

# Ошибки
errors_total = Counter(
    'stroinadzor_errors_total',
    'Total errors',
    ['error_type', 'component'],  # type: ValueError, component: openai_service
    registry=registry
)


# ===== ГИСТОГРАММЫ (HISTOGRAMS) =====

# Время обработки запросов
request_duration_seconds = Histogram(
    'stroinadzor_request_duration_seconds',
    'Request processing time',
    ['request_type'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
    registry=registry
)

# Время OpenAI API
openai_api_duration_seconds = Histogram(
    'stroinadzor_openai_api_duration_seconds',
    'OpenAI API call duration',
    ['model', 'request_type'],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0),
    registry=registry
)

# Размер ответов OpenAI (в токенах)
openai_response_tokens = Histogram(
    'stroinadzor_openai_response_tokens',
    'OpenAI response size in tokens',
    ['model'],
    buckets=(50, 100, 250, 500, 1000, 2000, 4000),
    registry=registry
)

# Размер фото (в байтах)
photo_size_bytes = Histogram(
    'stroinadzor_photo_size_bytes',
    'Photo size in bytes',
    buckets=(100_000, 500_000, 1_000_000, 2_000_000, 5_000_000),
    registry=registry
)


# ===== GAUGES (ТЕКУЩИЕ ЗНАЧЕНИЯ) =====

# Активные пользователи
active_users = Gauge(
    'stroinadzor_active_users',
    'Number of active users',
    ['period'],  # 1h, 24h, 7d
    registry=registry
)

# Размер векторной БД
vector_db_documents = Gauge(
    'stroinadzor_vector_db_documents',
    'Number of documents in vector DB',
    ['collection'],  # sp, gost, snip, cases
    registry=registry
)

# Размер кеша
cache_size = Gauge(
    'stroinadzor_cache_size_keys',
    'Number of keys in cache',
    registry=registry
)

# Rate limit счетчики
rate_limit_remaining = Gauge(
    'stroinadzor_rate_limit_remaining',
    'Remaining rate limit quota',
    ['user_id', 'user_role'],
    registry=registry
)


# ===== ДЕКОРАТОРЫ ДЛЯ АВТОМАТИЧЕСКОГО TRACKING =====

def track_request_time(request_type: str):
    """
    Декоратор для отслеживания времени выполнения запроса

    Usage:
        @track_request_time('text')
        async def handle_text(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                request_duration_seconds.labels(request_type=request_type).observe(duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                request_duration_seconds.labels(request_type=request_type).observe(duration)
                errors_total.labels(
                    error_type=type(e).__name__,
                    component=func.__module__
                ).inc()
                raise
        return wrapper
    return decorator


def track_openai_call(model: str, request_type: str):
    """
    Декоратор для отслеживания OpenAI API вызовов

    Usage:
        @track_openai_call('gpt-4o', 'text')
        async def analyze_text(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            openai_requests_total.labels(
                model=model,
                request_type=request_type
            ).inc()

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                openai_api_duration_seconds.labels(
                    model=model,
                    request_type=request_type
                ).observe(duration)

                return result
            except Exception as e:
                duration = time.time() - start_time
                openai_api_duration_seconds.labels(
                    model=model,
                    request_type=request_type
                ).observe(duration)

                errors_total.labels(
                    error_type=type(e).__name__,
                    component='openai_service'
                ).inc()
                raise
        return wrapper
    return decorator


# ===== HELPER ФУНКЦИИ =====

def record_user_request(request_type: str, user_role: str):
    """Записать запрос пользователя"""
    user_requests_total.labels(
        request_type=request_type,
        user_role=user_role
    ).inc()


def record_cache_operation(operation: str, result: str):
    """Записать операцию с кешем"""
    cache_operations_total.labels(
        operation=operation,
        result=result
    ).inc()


def record_openai_tokens(model: str, prompt_tokens: int, completion_tokens: int):
    """Записать использование токенов OpenAI"""
    openai_tokens_total.labels(model=model, token_type='prompt').inc(prompt_tokens)
    openai_tokens_total.labels(model=model, token_type='completion').inc(completion_tokens)


def record_pdf_generation():
    """Записать генерацию PDF"""
    pdf_generated_total.inc()


def record_excel_export(export_type: str):
    """Записать экспорт Excel"""
    excel_exported_total.labels(export_type=export_type).inc()


def update_active_users(period: str, count: int):
    """Обновить счетчик активных пользователей"""
    active_users.labels(period=period).set(count)


def update_vector_db_size(collection: str, count: int):
    """Обновить размер векторной БД"""
    vector_db_documents.labels(collection=collection).set(count)


def update_cache_size(count: int):
    """Обновить размер кеша"""
    cache_size.set(count)


def update_rate_limit(user_id: int, user_role: str, remaining: int):
    """Обновить оставшийся rate limit"""
    rate_limit_remaining.labels(
        user_id=str(user_id),
        user_role=user_role
    ).set(remaining)


def get_metrics() -> bytes:
    """
    Получить метрики в формате Prometheus

    Returns:
        bytes: Метрики в формате Prometheus
    """
    return generate_latest(registry)


def get_metrics_content_type() -> str:
    """Получить Content-Type для метрик"""
    return CONTENT_TYPE_LATEST


# ===== ПЕРИОДИЧЕСКИЕ ОБНОВЛЕНИЯ =====

async def update_metrics_periodic(db_session, redis_client, vector_service):
    """
    Периодическое обновление метрик (вызывать каждые 60 секунд)

    Args:
        db_session: Database session
        redis_client: Redis client
        vector_service: Vector service
    """
    try:
        from datetime import datetime, timedelta
        from src.database.models import User
        from sqlalchemy import func

        # Активные пользователи за разные периоды
        now = datetime.utcnow()

        # За последний час
        hour_ago = now - timedelta(hours=1)
        active_1h = db_session.query(func.count(User.id)).filter(
            User.last_activity >= hour_ago
        ).scalar() or 0
        update_active_users('1h', active_1h)

        # За последние 24 часа
        day_ago = now - timedelta(days=1)
        active_24h = db_session.query(func.count(User.id)).filter(
            User.last_activity >= day_ago
        ).scalar() or 0
        update_active_users('24h', active_24h)

        # За последние 7 дней
        week_ago = now - timedelta(days=7)
        active_7d = db_session.query(func.count(User.id)).filter(
            User.last_activity >= week_ago
        ).scalar() or 0
        update_active_users('7d', active_7d)

        # Размер векторной БД
        if vector_service:
            stats = vector_service.get_collection_stats()
            for collection, count in stats.items():
                update_vector_db_size(collection, count)

        # Размер кеша Redis
        if redis_client:
            try:
                cache_keys_count = redis_client.dbsize()
                update_cache_size(cache_keys_count)
            except:
                pass

        logger.debug("Metrics updated successfully")

    except Exception as e:
        logger.error(f"Error updating periodic metrics: {e}", exc_info=True)


# ===== ЭКСПОРТ =====

__all__ = [
    'registry',
    'track_request_time',
    'track_openai_call',
    'record_user_request',
    'record_cache_operation',
    'record_openai_tokens',
    'record_pdf_generation',
    'record_excel_export',
    'update_active_users',
    'update_vector_db_size',
    'update_cache_size',
    'update_rate_limit',
    'get_metrics',
    'get_metrics_content_type',
    'update_metrics_periodic',
]
