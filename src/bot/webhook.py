"""
Webhook Handler для Telegram Bot
Обработка webhook запросов от Telegram
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from telegram import Update

from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["Webhook"])


@router.post("/telegram")
async def telegram_webhook(request: Request):
    """
    Webhook endpoint для Telegram

    Args:
        request: FastAPI Request

    Returns:
        dict: Статус обработки
    """
    try:
        # Получаем JSON данные
        data = await request.json()

        # Создаем Update объект
        update = Update.de_json(data, None)  # Bot будет передан позже

        # Здесь должна быть логика обработки update
        # через Application.process_update()

        logger.debug(f"Received webhook update: {update.update_id}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/telegram")
async def telegram_webhook_info():
    """
    Информация о webhook

    Returns:
        dict: Информация о webhook
    """
    if settings.USE_WEBHOOK:
        return {
            "status": "enabled",
            "url": f"{settings.TELEGRAM_WEBHOOK_URL}{settings.TELEGRAM_WEBHOOK_PATH}",
            "path": settings.TELEGRAM_WEBHOOK_PATH
        }
    else:
        return {
            "status": "disabled",
            "mode": "polling"
        }
