"""
Main Telegram Bot Application
Модернизированный бот с полной функциональностью
"""

import asyncio
import logging
from telegram.ext import Application

from config.settings import settings
from src.utils.logger import setup_logging
from .handlers import setup_handlers

logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """
    Post initialization hook

    Args:
        application: Telegram Application
    """
    logger.info("Bot initialization completed")
    logger.info(f"Bot username: @{application.bot.username}")


async def post_shutdown(application: Application) -> None:
    """
    Post shutdown hook

    Args:
        application: Telegram Application
    """
    logger.info("Bot shutdown completed")


def start_bot() -> None:
    """
    Запуск Telegram бота
    """
    # Настройка логирования
    setup_logging()

    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Using webhook: {settings.USE_WEBHOOK}")

    # Создаем приложение
    application = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Регистрируем обработчики
    setup_handlers(application)

    # Запускаем бота
    if settings.USE_WEBHOOK and settings.TELEGRAM_WEBHOOK_URL:
        # Webhook mode (для production)
        logger.info(f"Starting webhook on {settings.TELEGRAM_WEBHOOK_URL}")

        application.run_webhook(
            listen=settings.API_HOST,
            port=settings.API_PORT,
            url_path=settings.TELEGRAM_WEBHOOK_PATH,
            webhook_url=f"{settings.TELEGRAM_WEBHOOK_URL}{settings.TELEGRAM_WEBHOOK_PATH}"
        )
    else:
        # Polling mode (для development)
        logger.info("Starting polling mode...")
        application.run_polling(
            allowed_updates=["message", "callback_query", "inline_query"],
            drop_pending_updates=True
        )


if __name__ == "__main__":
    start_bot()
