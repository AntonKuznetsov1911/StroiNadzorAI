"""
Настройка логирования
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime

from config.settings import settings


class JSONFormatter(logging.Formatter):
    """Форматтер для JSON логов"""

    def format(self, record: logging.LogRecord) -> str:
        """
        Форматирование лог записи в JSON

        Args:
            record: Запись лога

        Returns:
            str: JSON строка
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Добавляем exception info если есть
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Добавляем дополнительные поля
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging() -> None:
    """
    Настройка системы логирования
    """
    # Создаем директорию для логов
    log_dir = Path(settings.LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Получаем root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # Удаляем существующие handlers
    root_logger.handlers.clear()

    # Console handler (обычный формат)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # File handler (JSON формат)
    try:
        # Парсим rotation и retention из строк
        rotation_mb = int(settings.LOG_ROTATION.split()[0])
        max_bytes = rotation_mb * 1024 * 1024

        file_handler = RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=max_bytes,
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

        if settings.ENVIRONMENT == "production":
            # В production используем JSON формат
            json_formatter = JSONFormatter()
            file_handler.setFormatter(json_formatter)
        else:
            # В development обычный формат
            file_handler.setFormatter(console_format)

        root_logger.addHandler(file_handler)

    except Exception as e:
        root_logger.error(f"Failed to setup file logging: {e}")

    # Настраиваем уровни для сторонних библиотек
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    root_logger.info("Logging configured successfully")
    root_logger.info(f"Environment: {settings.ENVIRONMENT}")
    root_logger.info(f"Log level: {settings.LOG_LEVEL}")
