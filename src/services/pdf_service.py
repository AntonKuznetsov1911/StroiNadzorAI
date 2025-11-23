"""
PDF Reports Generation Service
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import io

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
    )
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logging.warning("ReportLab not installed. PDF generation will be disabled.")

from config.settings import settings

logger = logging.getLogger(__name__)


class PDFReportService:
    """Сервис для генерации PDF отчетов"""

    def __init__(self):
        """Инициализация сервиса"""
        if not REPORTLAB_AVAILABLE:
            logger.warning("PDF service initialized without ReportLab")
            return

        # Создаем директорию для отчетов
        self.reports_dir = Path(settings.UPLOAD_DIR) / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_defect_report(
        self,
        title: str,
        defect_type: str,
        severity: str,
        analysis: str,
        recommendations: str,
        photo_paths: Optional[List[str]] = None,
        regulations: Optional[List[str]] = None,
        user_name: Optional[str] = None,
        project_name: Optional[str] = None,
        location: Optional[str] = None
    ) -> str:
        """
        Генерация PDF отчета о дефекте

        Args:
            title: Заголовок отчета
            defect_type: Тип дефекта
            severity: Критичность
            analysis: Анализ дефекта
            recommendations: Рекомендации
            photo_paths: Пути к фотографиям
            regulations: Список нормативов
            user_name: Имя пользователя
            project_name: Название проекта
            location: Местоположение

        Returns:
            str: Путь к созданному PDF файлу
        """
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("ReportLab is not installed")

        # Генерируем имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"defect_report_{timestamp}.pdf"
        filepath = self.reports_dir / filename

        # Создаем PDF
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        # Стили
        styles = getSampleStyleSheet()
        story = []

        # Заголовок
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
        )
        story.append(Paragraph(f"<b>Отчет о дефекте: {title}</b>", title_style))
        story.append(Spacer(1, 0.5*cm))

        # Метаданные
        meta_data = [
            ["Дата создания:", datetime.now().strftime("%d.%m.%Y %H:%M")],
            ["Тип дефекта:", defect_type or "Не определен"],
            ["Критичность:", severity or "Не определена"],
        ]

        if user_name:
            meta_data.append(["Инспектор:", user_name])
        if project_name:
            meta_data.append(["Проект:", project_name])
        if location:
            meta_data.append(["Местоположение:", location])

        meta_table = Table(meta_data, colWidths=[5*cm, 12*cm])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))

        story.append(meta_table)
        story.append(Spacer(1, 1*cm))

        # Фотографии
        if photo_paths:
            story.append(Paragraph("<b>Фотографии дефекта:</b>", styles['Heading2']))
            story.append(Spacer(1, 0.3*cm))

            for photo_path in photo_paths[:3]:  # Максимум 3 фото
                try:
                    img = Image(photo_path, width=15*cm, height=11*cm)
                    story.append(img)
                    story.append(Spacer(1, 0.5*cm))
                except Exception as e:
                    logger.error(f"Error adding image to PDF: {e}")

        # Анализ
        story.append(Paragraph("<b>Детальный анализ:</b>", styles['Heading2']))
        story.append(Spacer(1, 0.3*cm))
        for line in analysis.split('\n'):
            if line.strip():
                story.append(Paragraph(line, styles['BodyText']))
        story.append(Spacer(1, 0.5*cm))

        # Рекомендации
        story.append(Paragraph("<b>Рекомендации по устранению:</b>", styles['Heading2']))
        story.append(Spacer(1, 0.3*cm))
        for line in recommendations.split('\n'):
            if line.strip():
                story.append(Paragraph(line, styles['BodyText']))
        story.append(Spacer(1, 0.5*cm))

        # Нормативы
        if regulations:
            story.append(Paragraph("<b>Применимые нормативы:</b>", styles['Heading2']))
            story.append(Spacer(1, 0.3*cm))
            for reg in regulations:
                story.append(Paragraph(f"• {reg}", styles['BodyText']))
            story.append(Spacer(1, 0.5*cm))

        # Футер
        story.append(Spacer(1, 2*cm))
        footer_text = f"<i>Отчет сгенерирован системой StroiNadzorAI v{settings.APP_VERSION}</i>"
        story.append(Paragraph(footer_text, styles['Italic']))

        # Генерируем PDF
        try:
            doc.build(story)
            logger.info(f"PDF report generated: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Error generating PDF report: {e}")
            raise

    def generate_project_report(
        self,
        project_name: str,
        description: str,
        defects: List[dict],
        statistics: dict
    ) -> str:
        """
        Генерация PDF отчета по проекту

        Args:
            project_name: Название проекта
            description: Описание проекта
            defects: Список дефектов
            statistics: Статистика

        Returns:
            str: Путь к созданному PDF файлу
        """
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("ReportLab is not installed")

        # Генерируем имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"project_report_{timestamp}.pdf"
        filepath = self.reports_dir / filename

        # Создаем PDF
        doc = SimpleDocTemplate(str(filepath), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Заголовок
        story.append(Paragraph(f"<b>Отчет по проекту: {project_name}</b>", styles['Title']))
        story.append(Spacer(1, 1*cm))

        # Описание
        if description:
            story.append(Paragraph("<b>Описание:</b>", styles['Heading2']))
            story.append(Paragraph(description, styles['BodyText']))
            story.append(Spacer(1, 0.5*cm))

        # Статистика
        story.append(Paragraph("<b>Статистика:</b>", styles['Heading2']))
        stats_data = [
            ["Всего дефектов:", str(statistics.get('total', 0))],
            ["Критических:", str(statistics.get('critical', 0))],
            ["Значительных:", str(statistics.get('major', 0))],
            ["Незначительных:", str(statistics.get('minor', 0))],
        ]

        stats_table = Table(stats_data, colWidths=[8*cm, 8*cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))

        story.append(stats_table)
        story.append(Spacer(1, 1*cm))

        # Список дефектов
        story.append(Paragraph("<b>Список дефектов:</b>", styles['Heading2']))
        story.append(Spacer(1, 0.3*cm))

        for i, defect in enumerate(defects, 1):
            story.append(Paragraph(
                f"<b>{i}. {defect.get('title', 'Без названия')}</b> - {defect.get('severity', 'N/A')}",
                styles['Heading3']
            ))
            story.append(Paragraph(defect.get('description', 'Нет описания'), styles['BodyText']))
            story.append(Spacer(1, 0.5*cm))

        # Генерируем PDF
        try:
            doc.build(story)
            logger.info(f"Project PDF report generated: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Error generating project PDF report: {e}")
            raise


# Singleton instance
_pdf_service_instance: Optional[PDFReportService] = None


def get_pdf_service() -> PDFReportService:
    """
    Получить экземпляр PDF service (singleton)

    Returns:
        PDFReportService: Экземпляр сервиса
    """
    global _pdf_service_instance
    if _pdf_service_instance is None:
        _pdf_service_instance = PDFReportService()
    return _pdf_service_instance
