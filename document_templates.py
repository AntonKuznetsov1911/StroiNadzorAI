"""
Модуль для генерации строительных документов по шаблонам
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

logger = logging.getLogger(__name__)

# Папка для сгенерированных документов
DOCUMENTS_DIR = Path("generated_documents")
DOCUMENTS_DIR.mkdir(exist_ok=True)


# ==========================
# ШАБЛОНЫ ДОКУМЕНТОВ
# ==========================

DOCUMENT_TEMPLATES = {
    "acceptance_foundation": {
        "name": "Акт приёмки фундамента",
        "description": "Акт освидетельствования скрытых работ (фундамент)",
        "params": ["object_name", "contractor", "date", "foundation_type", "volume_m3", "concrete_class", "inspector_name"]
    },
    "complaint_contractor": {
        "name": "Претензия подрядчику",
        "description": "Официальная претензия по выявленным дефектам",
        "params": ["object_name", "contractor", "date", "defect_description", "deadline", "penalty", "sender_name"]
    },
    "safety_plan": {
        "name": "План мероприятий по охране труда",
        "description": "План ОТ и ТБ на объекте",
        "params": ["object_name", "start_date", "end_date", "responsible_person", "worker_count"]
    },
    "hidden_works_act": {
        "name": "Акт освидетельствования скрытых работ",
        "description": "Универсальный акт для скрытых работ",
        "params": ["object_name", "contractor", "date", "work_type", "volume", "standards", "inspector_name"]
    },
}


def generate_document(template_id: str, params: dict) -> dict:
    """
    Генерирует документ по шаблону

    Args:
        template_id: ID шаблона
        params: параметры для заполнения

    Returns:
        dict: {"success": bool, "filepath": str, "error": str}
    """
    try:
        doc = Document()
        
        # Базовая генерация документа
        heading = doc.add_heading(DOCUMENT_TEMPLATES[template_id]["name"].upper(), level=0)
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_paragraph(f"Дата: {params.get('date', datetime.now().strftime('%d.%m.%Y'))}")
        doc.add_paragraph(f"Объект: {params.get('object_name', '_____________')}")
        
        for key, value in params.items():
            if key not in ['date', 'object_name']:
                doc.add_paragraph(f"{key}: {value}")
        
        filename = f"{template_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        filepath = DOCUMENTS_DIR / filename
        doc.save(filepath)
        
        logger.info(f"✅ Документ создан: {filepath}")
        return {
            "success": True,
            "filepath": str(filepath),
            "error": ""
        }
    except Exception as e:
        logger.error(f"❌ Ошибка генерации документа: {e}")
        return {
            "success": False,
            "filepath": "",
            "error": str(e)
        }
