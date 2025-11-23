"""
FastAPI Admin Panel Main Application
"""

import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List

from config.settings import settings
from src.utils.logger import setup_logging
from src.database import get_db, init_db
from src.database.models import User, Request, Project, Analytics
from .schemas import (
    UserResponse, RequestResponse, ProjectResponse,
    AnalyticsResponse, StatsResponse
)

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)

# Создаем FastAPI app
app = FastAPI(
    title=settings.APP_NAME + " Admin API",
    description="Administrative API for StroiNadzorAI Bot",
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.API_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === EVENTS ===

@app.on_event("startup")
async def startup_event():
    """Startup event"""
    logger.info(f"Starting {settings.APP_NAME} Admin API v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Инициализация базы данных
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event"""
    logger.info("Shutting down Admin API")


# === HEALTH CHECK ===

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    # TODO: Implement actual metrics
    return {"metrics": "prometheus_format"}


# === USERS API ===

@app.get("/api/users", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all users"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/api/users/telegram/{telegram_id}", response_model=UserResponse)
async def get_user_by_telegram_id(telegram_id: int, db: Session = Depends(get_db)):
    """Get user by Telegram ID"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# === REQUESTS API ===

@app.get("/api/requests", response_model=List[RequestResponse])
async def get_requests(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all requests"""
    requests = db.query(Request).order_by(Request.created_at.desc()).offset(skip).limit(limit).all()
    return requests


@app.get("/api/requests/{request_id}", response_model=RequestResponse)
async def get_request(request_id: int, db: Session = Depends(get_db)):
    """Get request by ID"""
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return request


@app.get("/api/users/{user_id}/requests", response_model=List[RequestResponse])
async def get_user_requests(
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get requests by user"""
    requests = (
        db.query(Request)
        .filter(Request.user_id == user_id)
        .order_by(Request.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return requests


# === PROJECTS API ===

@app.get("/api/projects", response_model=List[ProjectResponse])
async def get_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all projects"""
    projects = db.query(Project).offset(skip).limit(limit).all()
    return projects


@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get project by ID"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# === ANALYTICS API ===

@app.get("/api/analytics", response_model=List[AnalyticsResponse])
async def get_analytics(
    period_type: str = "daily",
    limit: int = 30,
    db: Session = Depends(get_db)
):
    """Get analytics data"""
    analytics = (
        db.query(Analytics)
        .filter(Analytics.period_type == period_type)
        .order_by(Analytics.date.desc())
        .limit(limit)
        .all()
    )
    return analytics


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    """Get overall statistics"""
    from sqlalchemy import func
    from datetime import datetime, timedelta

    # Общая статистика
    total_users = db.query(func.count(User.id)).scalar()
    total_requests = db.query(func.count(Request.id)).scalar()
    total_projects = db.query(func.count(Project.id)).scalar()

    # Статистика за сегодня
    today = datetime.utcnow().date()
    today_requests = (
        db.query(func.count(Request.id))
        .filter(func.date(Request.created_at) == today)
        .scalar()
    )

    # Новые пользователи за неделю
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users_week = (
        db.query(func.count(User.id))
        .filter(User.created_at >= week_ago)
        .scalar()
    )

    # Средняя скорость обработки
    avg_processing_time = (
        db.query(func.avg(Request.processing_time))
        .filter(Request.cached == False)
        .scalar()
    )

    # Cache hit rate
    total_non_cached = db.query(func.count(Request.id)).filter(Request.cached == False).scalar()
    total_cached = db.query(func.count(Request.id)).filter(Request.cached == True).scalar()
    cache_hit_rate = total_cached / (total_cached + total_non_cached) if (total_cached + total_non_cached) > 0 else 0

    return {
        "total_users": total_users or 0,
        "total_requests": total_requests or 0,
        "total_projects": total_projects or 0,
        "today_requests": today_requests or 0,
        "new_users_week": new_users_week or 0,
        "avg_processing_time": round(avg_processing_time or 0, 2),
        "cache_hit_rate": round(cache_hit_rate * 100, 2)
    }


# === ERROR HANDLERS ===

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=settings.LOG_LEVEL.lower()
    )
