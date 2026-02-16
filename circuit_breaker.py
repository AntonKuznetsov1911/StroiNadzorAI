"""
Circuit Breaker — защита от каскадных сбоев внешних API
======================================================

Паттерн Circuit Breaker предотвращает повторные вызовы
нерабочих API, экономя время на таймаутах.

Состояния:
- CLOSED: API работает, запросы проходят нормально
- OPEN: API недоступен, запросы сразу отклоняются
- HALF_OPEN: Пробный запрос для проверки восстановления

Использование:
    breaker = CircuitBreaker(name="grok", failure_threshold=5)
    if breaker.can_execute():
        try:
            result = await call_api()
            breaker.record_success()
        except Exception:
            breaker.record_failure()
    else:
        # API недоступен, используем fallback
        result = fallback_response()
"""

import logging
from time import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit Breaker для одного внешнего сервиса"""

    # Состояния
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 1
    ):
        """
        Args:
            name: Имя сервиса (для логов)
            failure_threshold: Количество ошибок до размыкания
            recovery_timeout: Секунды до попытки восстановления
            half_open_max_calls: Количество пробных запросов в half-open
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = self.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0

        # Статистика
        self.total_calls = 0
        self.total_failures = 0
        self.total_blocked = 0

    def can_execute(self) -> bool:
        """Проверить, можно ли выполнить запрос"""
        self.total_calls += 1

        if self.state == self.CLOSED:
            return True

        if self.state == self.OPEN:
            # Проверяем, прошло ли достаточно времени для восстановления
            if self.last_failure_time and (time() - self.last_failure_time) > self.recovery_timeout:
                self.state = self.HALF_OPEN
                self.half_open_calls = 0
                logger.info(f"🔄 Circuit Breaker [{self.name}]: OPEN -> HALF-OPEN (пробуем восстановление)")
                return True
            self.total_blocked += 1
            return False

        if self.state == self.HALF_OPEN:
            # Разрешаем ограниченное количество пробных запросов
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            self.total_blocked += 1
            return False

        return True

    def record_success(self):
        """Зафиксировать успешный запрос"""
        if self.state == self.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_max_calls:
                self.state = self.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info(f"✅ Circuit Breaker [{self.name}]: HALF-OPEN -> CLOSED (API восстановлен)")
        elif self.state == self.CLOSED:
            # Сбрасываем счётчик ошибок при успехе
            self.failure_count = 0

    def record_failure(self):
        """Зафиксировать ошибку запроса"""
        self.failure_count += 1
        self.total_failures += 1
        self.last_failure_time = time()

        if self.state == self.HALF_OPEN:
            # В half-open одна ошибка возвращает в open
            self.state = self.OPEN
            self.success_count = 0
            logger.warning(f"⚠️ Circuit Breaker [{self.name}]: HALF-OPEN -> OPEN (ошибка при восстановлении)")
        elif self.state == self.CLOSED and self.failure_count >= self.failure_threshold:
            self.state = self.OPEN
            logger.warning(
                f"🔴 Circuit Breaker [{self.name}]: CLOSED -> OPEN "
                f"({self.failure_count} ошибок подряд, блокировка на {self.recovery_timeout}с)"
            )

    def get_stats(self) -> Dict:
        """Получить статистику Circuit Breaker"""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "total_blocked": self.total_blocked,
            "recovery_timeout": self.recovery_timeout,
        }

    def reset(self):
        """Принудительный сброс (для администрирования)"""
        self.state = self.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        logger.info(f"🔄 Circuit Breaker [{self.name}]: принудительный сброс -> CLOSED")


class CircuitBreakerRegistry:
    """Реестр Circuit Breaker'ов для всех внешних API"""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}

    def register(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60
    ) -> CircuitBreaker:
        """Зарегистрировать новый Circuit Breaker"""
        breaker = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
        self._breakers[name] = breaker
        return breaker

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Получить Circuit Breaker по имени"""
        return self._breakers.get(name)

    def get_all_stats(self) -> Dict:
        """Получить статистику всех Circuit Breaker'ов"""
        return {
            name: breaker.get_stats()
            for name, breaker in self._breakers.items()
        }

    def reset_all(self):
        """Сбросить все Circuit Breaker'ы"""
        for breaker in self._breakers.values():
            breaker.reset()


# Глобальный реестр
api_circuit_breakers = CircuitBreakerRegistry()

# Регистрация Circuit Breaker'ов для основных API
grok_breaker = api_circuit_breakers.register("grok", failure_threshold=5, recovery_timeout=60)
claude_breaker = api_circuit_breakers.register("claude", failure_threshold=3, recovery_timeout=90)
gemini_breaker = api_circuit_breakers.register("gemini", failure_threshold=5, recovery_timeout=60)
openai_breaker = api_circuit_breakers.register("openai", failure_threshold=3, recovery_timeout=90)
