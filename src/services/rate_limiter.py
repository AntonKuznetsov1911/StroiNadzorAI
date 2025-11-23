"""
Rate limiting service для защиты от спама
"""

import logging
from typing import Optional
from datetime import datetime, timedelta

from src.cache import get_cache
from config.settings import settings
from src.database.models import User, UserRole

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter для защиты от спама"""

    def __init__(self):
        self.cache = get_cache()

    def _get_key(self, user_id: int) -> str:
        """Получить ключ для rate limiting"""
        return f"rate_limit:user:{user_id}"

    def check_rate_limit(self, user: User) -> tuple[bool, Optional[int]]:
        """
        Проверить rate limit для пользователя

        Args:
            user: User object

        Returns:
            tuple[bool, Optional[int]]: (allowed, seconds_to_wait)
        """
        # Для админов нет ограничений
        if user.role == UserRole.ADMIN:
            return True, None

        # Определяем лимит в зависимости от роли
        if user.role == UserRole.PREMIUM:
            limit = settings.RATE_LIMIT_PREMIUM_REQUESTS
        else:
            limit = settings.RATE_LIMIT_REQUESTS

        key = self._get_key(user.telegram_id)

        # Получаем текущее количество запросов
        current_count = self.cache.get(key)

        if current_count is None:
            # Первый запрос в периоде
            self.cache.set(key, 1, settings.RATE_LIMIT_PERIOD)
            return True, None

        if current_count >= limit:
            # Превышен лимит
            ttl = self.cache.redis_client.ttl(key) if self.cache.redis_client else 3600
            return False, ttl

        # Инкрементируем счетчик
        self.cache.increment(key)
        return True, None

    def get_remaining_requests(self, user: User) -> int:
        """
        Получить количество оставшихся запросов

        Args:
            user: User object

        Returns:
            int: Количество оставшихся запросов
        """
        if user.role == UserRole.ADMIN:
            return 999999  # Бесконечно для админов

        limit = (
            settings.RATE_LIMIT_PREMIUM_REQUESTS
            if user.role == UserRole.PREMIUM
            else settings.RATE_LIMIT_REQUESTS
        )

        key = self._get_key(user.telegram_id)
        current_count = self.cache.get(key) or 0

        return max(0, limit - current_count)

    def reset_rate_limit(self, user_id: int) -> bool:
        """
        Сбросить rate limit для пользователя (админская функция)

        Args:
            user_id: ID пользователя

        Returns:
            bool: Успешность операции
        """
        key = self._get_key(user_id)
        return self.cache.delete(key)


# Singleton instance
_rate_limiter_instance: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Получить экземпляр rate limiter (singleton)

    Returns:
        RateLimiter: Экземпляр rate limiter
    """
    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        _rate_limiter_instance = RateLimiter()
    return _rate_limiter_instance
