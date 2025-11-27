"""
Email Notification Service
Сервис для отправки email уведомлений
"""

import logging
from typing import Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path
from datetime import datetime
import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config.settings import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Сервис для отправки email"""

    def __init__(self):
        """Инициализация сервиса"""
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_from = settings.SMTP_FROM or settings.SMTP_USER

        # Настройка Jinja2 для шаблонов
        template_dir = Path(__file__).parent.parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )

    def is_configured(self) -> bool:
        """Проверка настроек email"""
        return all([
            self.smtp_host,
            self.smtp_port,
            self.smtp_user,
            self.smtp_password
        ])

    async def send_email(
        self,
        to: str | List[str],
        subject: str,
        body: str,
        html: bool = False,
        attachments: Optional[List[tuple[str, bytes]]] = None
    ) -> bool:
        """
        Отправка email

        Args:
            to: Email получателя или список получателей
            subject: Тема письма
            body: Тело письма
            html: Использовать HTML формат
            attachments: Список вложений (filename, data)

        Returns:
            bool: Успешность отправки
        """
        if not self.is_configured():
            logger.warning("Email service is not configured")
            return False

        try:
            # Создаем сообщение
            message = MIMEMultipart()
            message["From"] = self.smtp_from
            message["To"] = to if isinstance(to, str) else ", ".join(to)
            message["Subject"] = subject

            # Добавляем тело письма
            if html:
                message.attach(MIMEText(body, "html"))
            else:
                message.attach(MIMEText(body, "plain"))

            # Добавляем вложения
            if attachments:
                for filename, data in attachments:
                    attachment = MIMEApplication(data, Name=filename)
                    attachment['Content-Disposition'] = f'attachment; filename="{filename}"'
                    message.attach(attachment)

            # Отправляем
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                start_tls=True
            )

            logger.info(f"Email sent successfully to {to}")
            return True

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    async def send_defect_report(
        self,
        to: str,
        defect_type: str,
        severity: str,
        description: str,
        pdf_path: Optional[str] = None,
        location: Optional[str] = None,
        recommendations: Optional[str] = None,
        normatives: Optional[List[str]] = None
    ) -> bool:
        """
        Отправка отчета о дефекте

        Args:
            to: Email получателя
            defect_type: Тип дефекта
            severity: Критичность (CRITICAL, HIGH, MEDIUM, LOW)
            description: Описание
            pdf_path: Путь к PDF отчету
            location: Местоположение дефекта
            recommendations: Рекомендации по устранению
            normatives: Список нормативов

        Returns:
            bool: Успешность отправки
        """
        subject = f"StroiNadzorAI: Отчет о дефекте - {defect_type}"

        # Рендерим шаблон
        template = self.jinja_env.get_template('email/defect_report.html')
        body = template.render(
            title=subject,
            defect_type=defect_type,
            severity=severity,
            description=description,
            location=location,
            date=datetime.now().strftime("%d.%m.%Y %H:%M"),
            recommendations=recommendations,
            normatives=normatives or [],
            has_attachment=bool(pdf_path)
        )

        attachments = []
        if pdf_path:
            try:
                with open(pdf_path, 'rb') as f:
                    attachments.append(("defect_report.pdf", f.read()))
            except Exception as e:
                logger.error(f"Error reading PDF: {e}")

        return await self.send_email(
            to=to,
            subject=subject,
            body=body,
            html=True,
            attachments=attachments if attachments else None
        )

    async def send_daily_summary(
        self,
        to: str,
        stats: dict,
        top_defects: Optional[List[dict]] = None,
        active_users: Optional[List[dict]] = None
    ) -> bool:
        """
        Отправка ежедневной сводки

        Args:
            to: Email получателя
            stats: Статистика за день
            top_defects: Топ дефектов
            active_users: Активные пользователи

        Returns:
            bool: Успешность отправки
        """
        subject = "StroiNadzorAI: Ежедневная сводка"

        # Рендерим шаблон
        template = self.jinja_env.get_template('email/daily_summary.html')
        body = template.render(
            title=subject,
            date=datetime.now().strftime("%d.%m.%Y"),
            stats=stats,
            top_defects=top_defects or [],
            active_users=active_users or []
        )

        return await self.send_email(
            to=to,
            subject=subject,
            body=body,
            html=True
        )

    async def send_premium_notification(
        self,
        to: str,
        action: str,
        plan_type: Optional[str] = None,
        expiry_date: Optional[str] = None,
        days_left: Optional[int] = None,
        expired_date: Optional[str] = None,
        renewal_link: Optional[str] = None
    ) -> bool:
        """
        Отправка уведомления о Premium подписке

        Args:
            to: Email получателя
            action: Тип действия (activated, expiring, expired)
            plan_type: Тип плана (monthly, yearly)
            expiry_date: Дата истечения
            days_left: Дней до истечения
            expired_date: Дата истечения (прошедшая)
            renewal_link: Ссылка на продление

        Returns:
            bool: Успешность отправки
        """
        subject_map = {
            'activated': "StroiNadzorAI: Premium подписка активирована!",
            'expiring': "StroiNadzorAI: Подписка скоро истекает",
            'expired': "StroiNadzorAI: Подписка истекла"
        }
        subject = subject_map.get(action, "StroiNadzorAI: Уведомление о подписке")

        # Рендерим шаблон
        template = self.jinja_env.get_template('email/premium_notification.html')
        body = template.render(
            title=subject,
            action=action,
            plan_type=plan_type,
            expiry_date=expiry_date,
            days_left=days_left,
            expired_date=expired_date,
            renewal_link=renewal_link or "https://t.me/YourBotName"
        )

        return await self.send_email(
            to=to,
            subject=subject,
            body=body,
            html=True
        )


# Singleton instance
_email_service_instance: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """
    Получить экземпляр email service (singleton)

    Returns:
        EmailService: Экземпляр сервиса
    """
    global _email_service_instance
    if _email_service_instance is None:
        _email_service_instance = EmailService()
    return _email_service_instance
