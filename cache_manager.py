"""
Модуль кэширования ответов v3.9
Redis для хранения популярных вопросов и ответов
Экономия API токенов на повторяющихся вопросах
"""

import os
import json
import hashlib
import logging
from time import time
from typing import Optional, Dict, Any
from datetime import timedelta

logger = logging.getLogger(__name__)

# Попробуем импортировать Redis
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("⚠️ Redis не установлен. Кэширование будет работать в памяти.")

# Локальный кэш в памяти (фолбэк если Redis недоступен)
MEMORY_CACHE: Dict[str, Any] = {}
CACHE_STATS = {
    'hits': 0,
    'misses': 0,
    'total_saved_tokens': 0
}

# Redis клиент (тип указывается условно)
redis_client = None  # type: Optional[Any]


# ========================================
# ИНИЦИАЛИЗАЦИЯ
# ========================================

async def init_cache():
    """Инициализация Redis или локального кэша"""
    global redis_client

    if not REDIS_AVAILABLE:
        logger.info("📦 Используется локальный кэш в памяти")
        return True

    redis_url = os.getenv("REDIS_URL") or os.getenv("REDIS_TLS_URL")

    if not redis_url:
        logger.warning("⚠️ REDIS_URL не найден. Используется локальный кэш.")
        return True

    try:
        # Подключаемся к Redis
        redis_client = await aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )

        # Проверяем соединение
        await redis_client.ping()
        logger.info("✅ Redis подключен успешно")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка подключения к Redis: {e}")
        logger.info("📦 Переключаемся на локальный кэш")
        redis_client = None
        return True


async def close_cache():
    """Закрыть соединение с Redis"""
    global redis_client

    if redis_client:
        await redis_client.close()
        logger.info("Redis соединение закрыто")


# ========================================
# ФУНКЦИИ КЭШИРОВАНИЯ
# ========================================

def generate_cache_key(question: str, user_context: Optional[str] = None) -> str:
    """
    Генерация ключа кэша на основе вопроса

    Args:
        question: Вопрос пользователя
        user_context: Дополнительный контекст (роль пользователя и т.д.)

    Returns:
        SHA-256 хэш ключа (первые 32 символа)
    """
    # Нормализуем вопрос
    normalized = question.lower().strip()

    # Убираем лишние пробелы
    normalized = ' '.join(normalized.split())

    # Добавляем контекст если есть
    if user_context:
        normalized = f"{user_context}:{normalized}"

    # Генерируем хэш (SHA-256 вместо MD5 для надёжности)
    return hashlib.sha256(normalized.encode()).hexdigest()[:32]


async def get_cached_answer(question: str, user_context: Optional[str] = None) -> Optional[str]:
    """
    Получить ответ из кэша

    Args:
        question: Вопрос пользователя
        user_context: Контекст

    Returns:
        Кэшированный ответ или None
    """
    cache_key = f"qa:{generate_cache_key(question, user_context)}"

    try:
        # Пробуем Redis
        if redis_client:
            answer = await redis_client.get(cache_key)

            if answer:
                CACHE_STATS['hits'] += 1
                logger.info(f"✅ Cache HIT: {cache_key[:16]}...")

                # Увеличиваем счётчик использований
                await redis_client.incr(f"{cache_key}:count")

                return answer

        # Локальный кэш (с проверкой TTL)
        elif cache_key in MEMORY_CACHE:
            entry = MEMORY_CACHE[cache_key]
            # Проверяем TTL — если запись просрочена, удаляем
            if entry.get('expires_at') and entry['expires_at'] < time():
                del MEMORY_CACHE[cache_key]
                CACHE_STATS['misses'] += 1
                return None
            CACHE_STATS['hits'] += 1
            entry['count'] = entry.get('count', 0) + 1
            logger.info(f"✅ Memory cache HIT: {cache_key[:16]}...")
            return entry['answer']

        # Кэш мисс
        CACHE_STATS['misses'] += 1
        return None

    except Exception as e:
        logger.error(f"Ошибка получения из кэша: {e}")
        return None


async def set_cached_answer(
    question: str,
    answer: str,
    user_context: Optional[str] = None,
    ttl_hours: int = 168  # 7 дней по умолчанию
) -> bool:
    """
    Сохранить ответ в кэш

    Args:
        question: Вопрос
        answer: Ответ
        user_context: Контекст
        ttl_hours: Время жизни в часах (по умолчанию 7 дней)

    Returns:
        True если успешно сохранено
    """
    cache_key = f"qa:{generate_cache_key(question, user_context)}"

    try:
        # Сохраняем в Redis
        if redis_client:
            ttl = timedelta(hours=ttl_hours)

            # Сохраняем ответ
            await redis_client.setex(
                cache_key,
                int(ttl.total_seconds()),
                answer
            )

            # Инициализируем счётчик
            count_key = f"{cache_key}:count"
            await redis_client.setex(
                count_key,
                int(ttl.total_seconds()),
                "0"
            )

            logger.info(f"💾 Ответ сохранён в Redis: {cache_key[:16]}... (TTL: {ttl_hours}h)")
            return True

        # Локальный кэш (с TTL)
        else:
            MEMORY_CACHE[cache_key] = {
                'answer': answer,
                'question': question,
                'count': 0,
                'expires_at': time() + (ttl_hours * 3600)
            }

            # Очищаем просроченные записи + ограничиваем размер
            _cleanup_expired_cache()
            if len(MEMORY_CACHE) > 1000:
                # Удаляем самый старый элемент
                oldest_key = next(iter(MEMORY_CACHE))
                del MEMORY_CACHE[oldest_key]

            logger.info(f"💾 Ответ сохранён в памяти: {cache_key[:16]}... (TTL: {ttl_hours}h)")
            return True

    except Exception as e:
        logger.error(f"Ошибка сохранения в кэш: {e}")
        return False


def _cleanup_expired_cache():
    """Удалить просроченные записи из локального кэша"""
    now = time()
    expired_keys = [
        key for key, data in MEMORY_CACHE.items()
        if data.get('expires_at') and data['expires_at'] < now
    ]
    for key in expired_keys:
        del MEMORY_CACHE[key]
    if expired_keys:
        logger.debug(f"🧹 Очищено {len(expired_keys)} просроченных записей из кэша")


async def get_popular_questions(limit: int = 10) -> list:
    """
    Получить самые популярные вопросы

    Args:
        limit: Количество вопросов

    Returns:
        Список популярных вопросов
    """
    try:
        if redis_client:
            # Получаем все ключи счётчиков
            pattern = "qa:*:count"
            cursor = "0"
            popular = []

            # Сканируем Redis
            while True:
                cursor, keys = await redis_client.scan(
                    cursor,
                    match=pattern,
                    count=100
                )

                for key in keys:
                    count = await redis_client.get(key)
                    if count and int(count) > 0:
                        # Получаем оригинальный ключ
                        original_key = key.replace(':count', '')
                        answer = await redis_client.get(original_key)

                        if answer:
                            popular.append({
                                'count': int(count),
                                'answer_preview': answer[:100] + '...' if len(answer) > 100 else answer
                            })

                if cursor == "0":
                    break

            # Сортируем по популярности
            popular.sort(key=lambda x: x['count'], reverse=True)
            return popular[:limit]

        else:
            # Из локального кэша
            sorted_items = sorted(
                MEMORY_CACHE.items(),
                key=lambda x: x[1].get('count', 0),
                reverse=True
            )

            return [
                {
                    'question': item[1]['question'],
                    'count': item[1].get('count', 0)
                }
                for _, item in sorted_items[:limit]
            ]

    except Exception as e:
        logger.error(f"Ошибка получения популярных вопросов: {e}")
        return []


async def clear_cache():
    """Очистить весь кэш"""
    global MEMORY_CACHE

    try:
        if redis_client:
            # Очищаем все qa: ключи
            pattern = "qa:*"
            cursor = "0"

            while True:
                cursor, keys = await redis_client.scan(
                    cursor,
                    match=pattern,
                    count=100
                )

                if keys:
                    await redis_client.delete(*keys)

                if cursor == "0":
                    break

            logger.info("✅ Redis кэш очищен")
        else:
            MEMORY_CACHE.clear()
            logger.info("✅ Локальный кэш очищен")

        return True

    except Exception as e:
        logger.error(f"Ошибка очистки кэша: {e}")
        return False


def get_cache_stats() -> dict:
    """Получить статистику кэша"""
    hit_rate = 0
    if CACHE_STATS['hits'] + CACHE_STATS['misses'] > 0:
        hit_rate = CACHE_STATS['hits'] / (CACHE_STATS['hits'] + CACHE_STATS['misses']) * 100

    return {
        'hits': CACHE_STATS['hits'],
        'misses': CACHE_STATS['misses'],
        'hit_rate': f"{hit_rate:.1f}%",
        'cache_type': 'Redis' if redis_client else 'Memory',
        'memory_cache_size': len(MEMORY_CACHE) if not redis_client else 0
    }


# ========================================
# СЕМАНТИЧЕСКИЙ ПОИСК (простая версия)
# ========================================

def calculate_similarity(text1: str, text2: str) -> float:
    """
    Простое вычисление похожести двух текстов
    Использует Jaccard similarity на основе слов

    Args:
        text1: Первый текст
        text2: Второй текст

    Returns:
        Коэффициент похожести от 0 до 1
    """
    # Нормализуем тексты
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    # Jaccard similarity
    intersection = len(words1 & words2)
    union = len(words1 | words2)

    if union == 0:
        return 0.0

    return intersection / union


async def find_similar_cached_question(question: str, threshold: float = 0.7) -> Optional[str]:
    """
    Найти похожий вопрос в кэше

    Args:
        question: Вопрос пользователя
        threshold: Порог похожести (0-1)

    Returns:
        Кэшированный ответ или None
    """
    try:
        if not redis_client and not MEMORY_CACHE:
            return None

        # Ищем в локальном кэше
        if MEMORY_CACHE:
            best_similarity = 0
            best_answer = None

            now = time()
            for cache_key, data in MEMORY_CACHE.items():
                # Пропускаем просроченные записи
                if data.get('expires_at') and data['expires_at'] < now:
                    continue
                cached_question = data.get('question', '')
                similarity = calculate_similarity(question, cached_question)

                if similarity > best_similarity and similarity >= threshold:
                    best_similarity = similarity
                    best_answer = data['answer']

            if best_answer:
                logger.info(f"🔍 Найден похожий вопрос (similarity: {best_similarity:.2f})")
                return best_answer

        return None

    except Exception as e:
        logger.error(f"Ошибка поиска похожих вопросов: {e}")
        return None
