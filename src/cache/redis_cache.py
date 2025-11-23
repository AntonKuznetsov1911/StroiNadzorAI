"""
Redis кеширование для ответов
"""

import json
import hashlib
import logging
from typing import Optional, Any
import redis
from redis.exceptions import RedisError

from config.settings import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache manager"""

    def __init__(self):
        """Инициализация Redis клиента"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Проверка подключения
            self.redis_client.ping()
            logger.info("Redis connection established")
        except RedisError as e:
            logger.warning(f"Redis connection failed: {e}. Cache will be disabled.")
            self.redis_client = None

    def _generate_key(self, prefix: str, data: Any) -> str:
        """
        Генерация ключа для кеша

        Args:
            prefix: Префикс ключа
            data: Данные для хеширования

        Returns:
            str: Ключ для Redis
        """
        if isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)

        hash_obj = hashlib.md5(data_str.encode())
        return f"{prefix}:{hash_obj.hexdigest()}"

    def get(self, key: str) -> Optional[Any]:
        """
        Получить значение из кеша

        Args:
            key: Ключ

        Returns:
            Optional[Any]: Значение или None
        """
        if not self.redis_client:
            return None

        try:
            value = self.redis_client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            logger.debug(f"Cache MISS: {key}")
            return None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Сохранить значение в кеш

        Args:
            key: Ключ
            value: Значение
            ttl: Time to live в секундах

        Returns:
            bool: Успешность операции
        """
        if not self.redis_client:
            return False

        try:
            ttl = ttl or settings.REDIS_CACHE_TTL
            value_str = json.dumps(value)
            self.redis_client.setex(key, ttl, value_str)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except (RedisError, TypeError) as e:
            logger.error(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Удалить значение из кеша

        Args:
            key: Ключ

        Returns:
            bool: Успешность операции
        """
        if not self.redis_client:
            return False

        try:
            self.redis_client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except RedisError as e:
            logger.error(f"Cache delete error: {e}")
            return False

    def get_or_set(self, key: str, callback, ttl: Optional[int] = None) -> Any:
        """
        Получить из кеша или вычислить и сохранить

        Args:
            key: Ключ
            callback: Функция для вычисления значения
            ttl: Time to live в секундах

        Returns:
            Any: Значение
        """
        # Попытка получить из кеша
        cached_value = self.get(key)
        if cached_value is not None:
            return cached_value

        # Вычисление нового значения
        value = callback()

        # Сохранение в кеш
        self.set(key, value, ttl)

        return value

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Инкремент счетчика

        Args:
            key: Ключ
            amount: Величина инкремента

        Returns:
            Optional[int]: Новое значение
        """
        if not self.redis_client:
            return None

        try:
            return self.redis_client.incrby(key, amount)
        except RedisError as e:
            logger.error(f"Cache increment error: {e}")
            return None

    def expire(self, key: str, ttl: int) -> bool:
        """
        Установить TTL для ключа

        Args:
            key: Ключ
            ttl: Time to live в секундах

        Returns:
            bool: Успешность операции
        """
        if not self.redis_client:
            return False

        try:
            self.redis_client.expire(key, ttl)
            return True
        except RedisError as e:
            logger.error(f"Cache expire error: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """
        Удалить все ключи по паттерну

        Args:
            pattern: Паттерн (например, "user:*")

        Returns:
            int: Количество удаленных ключей
        """
        if not self.redis_client:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except RedisError as e:
            logger.error(f"Cache clear pattern error: {e}")
            return 0

    def get_cache_key_for_question(self, question: str) -> str:
        """
        Генерация ключа кеша для текстового вопроса

        Args:
            question: Вопрос

        Returns:
            str: Ключ кеша
        """
        return self._generate_key("question", question.lower().strip())

    def get_cache_key_for_photo(self, photo_hash: str, caption: str = "") -> str:
        """
        Генерация ключа кеша для фотографии

        Args:
            photo_hash: Хеш фото
            caption: Подпись к фото

        Returns:
            str: Ключ кеша
        """
        data = f"{photo_hash}:{caption.lower().strip()}"
        return self._generate_key("photo", data)


# Singleton instance
_cache_instance: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """
    Получить экземпляр кеша (singleton)

    Returns:
        RedisCache: Экземпляр кеша
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance
