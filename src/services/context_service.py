"""
Context Service для запоминания разговоров с пользователями
Сохраняет историю диалога для более контекстных ответов
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from src.database.models import User, Request
from src.cache import get_cache

logger = logging.getLogger(__name__)


class ContextService:
    """
    Сервис для управления контекстом разговора
    Запоминает последние N сообщений пользователя для контекстных ответов
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.cache = get_cache()
        self.max_context_messages = 10  # Последние 10 сообщений
        self.context_ttl = 3600 * 2  # 2 часа TTL

        logger.info("ContextService initialized")

    def get_conversation_history(
        self,
        db: Session,
        user_id: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Получить историю разговора пользователя

        Args:
            db: Database session
            user_id: ID пользователя
            limit: Количество последних сообщений

        Returns:
            List[Dict]: История в формате [{"role": "user/assistant", "content": "..."}]
        """
        try:
            # Проверяем кеш
            cache_key = f"context:user:{user_id}"
            cached_context = self.cache.get(cache_key)

            if cached_context:
                return cached_context[-limit:]

            # Получаем из БД
            requests = db.query(Request).filter(
                Request.user_id == user_id
            ).order_by(
                Request.created_at.desc()
            ).limit(limit).all()

            # Форматируем в формат OpenAI
            history = []
            for req in reversed(requests):  # Обратный порядок - от старых к новым
                # Вопрос пользователя
                user_message = req.message_text or req.caption or "Анализ фотографии"
                history.append({
                    "role": "user",
                    "content": user_message[:500]  # Ограничиваем длину
                })

                # Ответ ассистента
                if req.response_text:
                    history.append({
                        "role": "assistant",
                        "content": req.response_text[:1000]  # Ограничиваем длину
                    })

            # Сохраняем в кеш
            self.cache.set(cache_key, history, ttl=self.context_ttl)

            return history

        except Exception as e:
            logger.error(f"Error getting conversation history: {e}", exc_info=True)
            return []

    def add_message(
        self,
        user_id: int,
        role: str,
        content: str
    ):
        """
        Добавить сообщение в контекст

        Args:
            user_id: ID пользователя
            role: Роль (user/assistant)
            content: Содержание сообщения
        """
        try:
            cache_key = f"context:user:{user_id}"
            history = self.cache.get(cache_key) or []

            history.append({
                "role": role,
                "content": content[:1000],  # Ограничиваем длину
                "timestamp": datetime.utcnow().isoformat()
            })

            # Оставляем только последние N сообщений
            if len(history) > self.max_context_messages * 2:  # *2 потому что user+assistant
                history = history[-self.max_context_messages * 2:]

            self.cache.set(cache_key, history, ttl=self.context_ttl)

        except Exception as e:
            logger.error(f"Error adding message to context: {e}", exc_info=True)

    def clear_context(self, user_id: int):
        """Очистить контекст пользователя"""
        try:
            cache_key = f"context:user:{user_id}"
            self.cache.delete(cache_key)
            logger.info(f"Context cleared for user {user_id}")
        except Exception as e:
            logger.error(f"Error clearing context: {e}", exc_info=True)

    def get_context_summary(
        self,
        db: Session,
        user_id: int
    ) -> Optional[str]:
        """
        Получить краткое резюме контекста разговора

        Args:
            db: Database session
            user_id: ID пользователя

        Returns:
            Optional[str]: Краткое описание темы разговора
        """
        try:
            history = self.get_conversation_history(db, user_id, limit=5)

            if not history:
                return None

            # Собираем последние вопросы пользователя
            user_questions = [
                msg['content'] for msg in history
                if msg['role'] == 'user'
            ]

            if not user_questions:
                return None

            # Простое резюме - последние темы
            summary = f"Предыдущие вопросы: {', '.join(user_questions[-3:])}"
            return summary[:200]

        except Exception as e:
            logger.error(f"Error getting context summary: {e}", exc_info=True)
            return None


# Singleton instance
_context_service_instance = None


def get_context_service() -> ContextService:
    """Получить singleton instance ContextService"""
    global _context_service_instance
    if _context_service_instance is None:
        _context_service_instance = ContextService()
    return _context_service_instance
