"""
Background Tasks - Фоновые задачи для Celery
PDF генерация, отправка email, аналитика
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from src.celery_app import celery_app
from src.database import get_db
from src.database.models import User, Request, PDFReport, Analytics
from src.services.pdf_service import get_pdf_service
from src.services.email_service import get_email_service
from src.services.excel_service import get_excel_service
from src.monitoring.metrics import (
    record_pdf_generation,
    record_excel_export,
    update_metrics_periodic
)

logger = logging.getLogger(__name__)


# ===== PDF ГЕНЕРАЦИЯ =====

@celery_app.task(name='src.tasks.pdf.generate_defect_report_async', bind=True, max_retries=3)
def generate_defect_report_async(
    self,
    request_id: int,
    user_id: int,
    notify_email: Optional[str] = None
):
    """
    Асинхронная генерация PDF отчета о дефекте

    Args:
        request_id: ID запроса
        user_id: ID пользователя
        notify_email: Email для уведомления (опционально)
    """
    try:
        db = next(get_db())
        pdf_service = get_pdf_service()
        email_service = get_email_service()

        # Получаем запрос
        request = db.query(Request).filter(Request.id == request_id).first()
        if not request:
            raise ValueError(f"Request {request_id} not found")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Генерируем PDF
        pdf_path = pdf_service.generate_defect_report(
            title=f"Дефект #{request_id}",
            defect_type=request.defect_type or "Не определен",
            severity=request.defect_severity.value if request.defect_severity else "Не определена",
            analysis=request.response_text,
            recommendations="См. анализ выше",
            regulations=request.mentioned_regulations,
            user_name=user.first_name
        )

        # Записываем в БД
        pdf_report = PDFReport(
            request_id=request_id,
            user_id=user_id,
            file_path=pdf_path,
            file_size=len(open(pdf_path, 'rb').read())
        )
        db.add(pdf_report)
        db.commit()

        # Метрика
        record_pdf_generation()

        # Отправляем на email если указан
        if notify_email:
            email_service.send_defect_report(
                to=notify_email,
                defect_type=request.defect_type or "Не определен",
                severity=request.defect_severity.value if request.defect_severity else "Не определена",
                description=request.response_text[:200],
                pdf_path=pdf_path
            )

        logger.info(f"PDF report generated for request {request_id}")
        return {'pdf_path': pdf_path, 'pdf_id': pdf_report.id}

    except Exception as e:
        logger.error(f"Error generating PDF report: {e}", exc_info=True)
        # Retry с экспоненциальной задержкой
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


# ===== EMAIL ОТПРАВКА =====

@celery_app.task(name='src.tasks.email.send_defect_notification', bind=True, max_retries=3)
def send_defect_notification(
    self,
    user_id: int,
    defect_type: str,
    severity: str,
    description: str,
    pdf_path: Optional[str] = None
):
    """
    Отправка уведомления о дефекте на email

    Args:
        user_id: ID пользователя
        defect_type: Тип дефекта
        severity: Критичность
        description: Описание
        pdf_path: Путь к PDF (опционально)
    """
    try:
        db = next(get_db())
        email_service = get_email_service()

        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.email:
            logger.warning(f"User {user_id} has no email")
            return

        email_service.send_defect_report(
            to=user.email,
            defect_type=defect_type,
            severity=severity,
            description=description,
            pdf_path=pdf_path
        )

        logger.info(f"Defect notification sent to {user.email}")
        return {'sent': True, 'email': user.email}

    except Exception as e:
        logger.error(f"Error sending email notification: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(name='src.tasks.email.send_daily_summary')
def send_daily_summary(admin_email: str):
    """
    Отправка ежедневной сводки администратору

    Args:
        admin_email: Email администратора
    """
    try:
        db = next(get_db())
        email_service = get_email_service()

        from sqlalchemy import func

        # Статистика за вчера
        yesterday = datetime.utcnow().date() - timedelta(days=1)

        total_requests = db.query(func.count(Request.id)).filter(
            func.date(Request.created_at) == yesterday
        ).scalar() or 0

        new_users = db.query(func.count(User.id)).filter(
            func.date(User.created_at) == yesterday
        ).scalar() or 0

        # Отправляем сводку
        email_service.send_daily_summary(
            to=admin_email,
            date=yesterday,
            total_requests=total_requests,
            new_users=new_users
        )

        logger.info(f"Daily summary sent to {admin_email}")
        return {'sent': True, 'date': str(yesterday)}

    except Exception as e:
        logger.error(f"Error sending daily summary: {e}", exc_info=True)
        raise


# ===== АНАЛИТИКА =====

@celery_app.task(name='src.tasks.analytics.generate_daily_analytics')
def generate_daily_analytics():
    """
    Генерация ежедневной аналитики
    """
    try:
        db = next(get_db())

        from sqlalchemy import func

        yesterday = datetime.utcnow().date() - timedelta(days=1)

        # Запросы
        total_requests = db.query(func.count(Request.id)).filter(
            func.date(Request.created_at) == yesterday
        ).scalar() or 0

        photo_requests = db.query(func.count(Request.id)).filter(
            func.date(Request.created_at) == yesterday,
            Request.request_type == 'PHOTO'
        ).scalar() or 0

        text_requests = db.query(func.count(Request.id)).filter(
            func.date(Request.created_at) == yesterday,
            Request.request_type == 'TEXT'
        ).scalar() or 0

        # Пользователи
        active_users = db.query(func.count(User.id.distinct())).join(Request).filter(
            func.date(Request.created_at) == yesterday
        ).scalar() or 0

        # Средн��е время обработки
        avg_time = db.query(func.avg(Request.processing_time)).filter(
            func.date(Request.created_at) == yesterday
        ).scalar() or 0

        # Cache hit rate
        cached = db.query(func.count(Request.id)).filter(
            func.date(Request.created_at) == yesterday,
            Request.cached == True
        ).scalar() or 0

        cache_hit_rate = (cached / total_requests * 100) if total_requests > 0 else 0

        # Сохраняем аналитику
        analytics = Analytics(
            date=yesterday,
            period_type='daily',
            total_requests=total_requests,
            photo_requests=photo_requests,
            text_requests=text_requests,
            active_users=active_users,
            avg_processing_time=avg_time,
            cache_hit_rate=cache_hit_rate
        )
        db.add(analytics)
        db.commit()

        logger.info(f"Daily analytics generated for {yesterday}")
        return {'date': str(yesterday), 'requests': total_requests}

    except Exception as e:
        logger.error(f"Error generating analytics: {e}", exc_info=True)
        raise


# ===== EXCEL ЭКСПОРТ =====

@celery_app.task(name='src.tasks.excel.export_user_data_async', bind=True)
def export_user_data_async(
    self,
    user_id: int,
    export_type: str,
    notify_telegram_id: Optional[int] = None
):
    """
    Асинхронный экспорт данных пользователя в Excel

    Args:
        user_id: ID пользователя
        export_type: Тип экспорта (requests/photos/analytics)
        notify_telegram_id: Telegram ID для уведомления
    """
    try:
        db = next(get_db())
        excel_service = get_excel_service()

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Получаем данные
        if export_type == "requests":
            requests = db.query(Request).filter(Request.user_id == user_id).all()
            data = [{
                "ID": r.id,
                "Тип": r.request_type.value,
                "Дата": r.created_at.strftime('%d.%m.%Y %H:%M'),
                "Дефект": r.defect_type or "-",
                "Критичность": r.defect_severity.value if r.defect_severity else "-",
            } for r in requests]
        elif export_type == "analytics":
            data = [{
                "Всего запросов": user.total_requests,
                "Анализов фото": user.total_photos,
                "Голосовых": user.total_voice,
            }]
        else:
            raise ValueError(f"Unknown export type: {export_type}")

        # Экспортируем
        filename = f"{export_type}_{user.telegram_id}_{int(datetime.utcnow().timestamp())}.xlsx"
        excel_path = excel_service.export_requests(data, filename)

        # Метрика
        record_excel_export(export_type)

        logger.info(f"Excel export completed for user {user_id}")
        return {'excel_path': excel_path, 'filename': filename}

    except Exception as e:
        logger.error(f"Error exporting to Excel: {e}", exc_info=True)
        raise


# ===== MAINTENANCE =====

@celery_app.task(name='src.tasks.maintenance.cleanup_old_cache')
def cleanup_old_cache():
    """Очистка старого кеша (запускается ночью)"""
    try:
        from src.cache import get_cache

        cache = get_cache()
        # Redis автоматически удаляет по TTL, но можно добавить дополнительную логику

        logger.info("Cache cleanup completed")
        return {'status': 'completed'}

    except Exception as e:
        logger.error(f"Error cleaning cache: {e}", exc_info=True)
        raise


@celery_app.task(name='src.tasks.monitoring.update_metrics')
def update_metrics():
    """Обновление метрик Prometheus"""
    try:
        from src.services.vector_service import get_vector_service
        from src.cache import get_cache

        db = next(get_db())
        vector_service = get_vector_service()
        cache = get_cache()

        # Обновляем метрики
        import asyncio
        asyncio.run(update_metrics_periodic(db, cache.client, vector_service))

        return {'status': 'updated'}

    except Exception as e:
        logger.error(f"Error updating metrics: {e}", exc_info=True)
        raise


# ===== ОТЧЕТЫ =====

@celery_app.task(name='src.tasks.reports.send_daily_reports')
def send_daily_reports():
    """Отправка ежедневных отчетов администраторам"""
    try:
        db = next(get_db())

        # Получаем админов
        admins = db.query(User).filter(User.role == 'ADMIN', User.email != None).all()

        for admin in admins:
            send_daily_summary.delay(admin.email)

        logger.info(f"Daily reports scheduled for {len(admins)} admins")
        return {'admins': len(admins)}

    except Exception as e:
        logger.error(f"Error sending daily reports: {e}", exc_info=True)
        raise
