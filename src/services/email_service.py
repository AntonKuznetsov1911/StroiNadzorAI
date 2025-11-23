"""
Email Notification Service
Сервис для отправки email уведомлений
"""

import logging
from typing import Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import aiosmtplib

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
        pdf_path: Optional[str] = None
    ) -> bool:
        """
        Отправка отчета о дефекте

        Args:
            to: Email получателя
            defect_type: Тип дефекта
            severity: Критичность
            description: Описание
            pdf_path: Путь к PDF отчету

        Returns:
            bool: Успешность отправки
        """
        subject = f"StroiNadzorAI: Отчет о дефекте - {defect_type}"

        body = f"""
        <html>
        <body>
            <h2>Отчет о дефекте</h2>
            <p><strong>Тип дефекта:</strong> {defect_type}</p>
            <p><strong>Критичность:</strong> {severity}</p>
            <p><strong>Описание:</strong></p>
            <p>{description}</p>
            <hr>
            <p><i>Отчет создан автоматически системой StroiNadzorAI</i></p>
        </body>
        </html>
        """

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
        stats: dict
    ) -> bool:
        """
        Отправка ежедневной сводки

        Args:
            to: Email получателя
            stats: Статистика

        Returns:
            bool: Успешность отправки
        """
        subject = "StroiNadzorAI: Ежедневная сводка"

        body = f"""
        <html>
        <body>
            <h2>Ежедневная сводка StroiNadzorAI</h2>
            <h3>Статистика за сегодня:</h3>
            <ul>
                <li>Всего запросов: {stats.get('total_requests', 0)}</li>
                <li>Анализов фото: {stats.get('photo_requests', 0)}</li>
                <li>Голосовых сообщений: {stats.get('voice_requests', 0)}</li>
                <li>Новых пользователей: {stats.get('new_users', 0)}</li>
                <li>Критических дефектов: {stats.get('critical_defects', 0)}</li>
            </ul>
            <hr>
            <p><i>Автоматическая рассылка от StroiNadzorAI</i></p>
        </body>
        </html>
        """

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
