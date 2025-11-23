"""
Health Check Endpoints
Endpoints для проверки здоровья сервисов
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config.settings import settings
from src.database import SessionLocal
from src.cache import get_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    """Ответ health check"""
    status: str
    timestamp: str
    version: str
    uptime: str


class DetailedHealthResponse(BaseModel):
    """Детальный ответ health check"""
    status: str
    timestamp: str
    version: str
    components: dict


@router.get("", response_model=HealthResponse)
async def health_check():
    """
    Простой health check

    Returns:
        HealthResponse: Статус системы
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
        "uptime": "operational"
    }


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """
    Детальный health check с проверкой всех компонентов

    Returns:
        DetailedHealthResponse: Детальный статус
    """
    components = {}

    # Проверка базы данных
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        components["database"] = {
            "status": "healthy",
            "message": "PostgreSQL connection OK"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        components["database"] = {
            "status": "unhealthy",
            "message": str(e)
        }

    # Проверка Redis
    try:
        cache = get_cache()
        if cache.redis_client:
            cache.redis_client.ping()
            components["cache"] = {
                "status": "healthy",
                "message": "Redis connection OK"
            }
        else:
            components["cache"] = {
                "status": "disabled",
                "message": "Redis not configured"
            }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        components["cache"] = {
            "status": "unhealthy",
            "message": str(e)
        }

    # Общий статус
    overall_status = "healthy"
    for component in components.values():
        if component["status"] == "unhealthy":
            overall_status = "unhealthy"
            break

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
        "components": components
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check для Kubernetes

    Returns:
        dict: Статус готовности
    """
    # Проверяем критичные компоненты
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()

        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/live")
async def liveness_check():
    """
    Liveness check для Kubernetes

    Returns:
        dict: Статус живучести
    """
    return {"status": "alive"}
