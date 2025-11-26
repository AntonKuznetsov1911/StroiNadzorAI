"""
Модуль для работы с PostgreSQL базой данных
Хранение истории диалогов пользователей
"""

import os
import asyncpg
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# DATABASE_URL из переменных окружения Railway
DATABASE_URL = os.getenv("DATABASE_URL")

# Pool соединений
pool: Optional[asyncpg.Pool] = None


async def init_db():
    """
    Инициализация PostgreSQL базы данных
    Создание таблиц если их нет
    """
    global pool

    if not DATABASE_URL:
        logger.warning("⚠️ DATABASE_URL не найден. PostgreSQL не будет использоваться.")
        return False

    try:
        # Создаем pool соединений
        pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=10,
            command_timeout=60
        )

        # Создаем таблицы
        async with pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                    image_analyzed BOOLEAN DEFAULT FALSE,
                    tags TEXT[] DEFAULT '{}'
                )
            ''')

            # Индексы для быстрого поиска
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_id ON messages(user_id);
                CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_tags ON messages USING GIN(tags);
            ''')

        logger.info("✅ PostgreSQL база данных инициализирована")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка инициализации PostgreSQL: {e}")
        return False


async def save_message(
    user_id: int,
    role: str,
    content: str,
    image_analyzed: bool = False,
    tags: List[str] = None
):
    """
    Сохранить сообщение в БД
    """
    if not pool:
        return False

    try:
        async with pool.acquire() as conn:
            await conn.execute(
                '''INSERT INTO messages (user_id, role, content, image_analyzed, tags)
                   VALUES ($1, $2, $3, $4, $5)''',
                user_id, role, content, image_analyzed, tags or []
            )
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения сообщения в БД: {e}")
        return False


async def get_user_messages(
    user_id: int,
    limit: int = 50
) -> List[Dict]:
    """
    Получить последние N сообщений пользователя
    """
    if not pool:
        return []

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                '''SELECT role, content, timestamp, image_analyzed, tags
                   FROM messages
                   WHERE user_id = $1
                   ORDER BY timestamp DESC
                   LIMIT $2''',
                user_id, limit
            )

            # Возвращаем в обратном порядке (от старых к новым)
            return [
                {
                    'role': row['role'],
                    'content': row['content'],
                    'timestamp': row['timestamp'].isoformat(),
                    'image_analyzed': row['image_analyzed'],
                    'tags': row['tags']
                }
                for row in reversed(rows)
            ]
    except Exception as e:
        logger.error(f"Ошибка получения сообщений из БД: {e}")
        return []


async def search_messages(
    user_id: int,
    query: str,
    limit: int = 10
) -> List[Dict]:
    """
    Полнотекстовый поиск по сообщениям пользователя
    """
    if not pool:
        return []

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                '''SELECT role, content, timestamp
                   FROM messages
                   WHERE user_id = $1 AND content ILIKE $2
                   ORDER BY timestamp DESC
                   LIMIT $3''',
                user_id, f'%{query}%', limit
            )

            return [
                {
                    'role': row['role'],
                    'content': row['content'],
                    'timestamp': row['timestamp'].isoformat()
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Ошибка поиска в БД: {e}")
        return []


async def get_user_tags(user_id: int) -> List[str]:
    """
    Получить все теги пользователя для рекомендаций
    """
    if not pool:
        return []

    try:
        async with pool.acquire() as conn:
            result = await conn.fetchval(
                '''SELECT array_agg(DISTINCT tag)
                   FROM messages, unnest(tags) AS tag
                   WHERE user_id = $1 AND tags IS NOT NULL''',
                user_id
            )
            return result or []
    except Exception as e:
        logger.error(f"Ошибка получения тегов из БД: {e}")
        return []


async def clear_user_history(user_id: int) -> bool:
    """
    Очистить историю пользователя
    """
    if not pool:
        return False

    try:
        async with pool.acquire() as conn:
            await conn.execute(
                'DELETE FROM messages WHERE user_id = $1',
                user_id
            )
        return True
    except Exception as e:
        logger.error(f"Ошибка очистки истории в БД: {e}")
        return False


async def get_total_messages(user_id: int) -> int:
    """
    Получить общее количество сообщений пользователя
    """
    if not pool:
        return 0

    try:
        async with pool.acquire() as conn:
            count = await conn.fetchval(
                'SELECT COUNT(*) FROM messages WHERE user_id = $1',
                user_id
            )
            return count or 0
    except Exception as e:
        logger.error(f"Ошибка подсчета сообщений в БД: {e}")
        return 0


async def close_db():
    """
    Закрыть pool соединений при остановке бота
    """
    global pool
    if pool:
        await pool.close()
        logger.info("✅ PostgreSQL соединения закрыты")
