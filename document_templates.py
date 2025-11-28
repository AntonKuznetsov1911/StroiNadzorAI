"""
Модуль для генерации строительных документов по шаблонам
Соответствует ГОСТ, СП и формам КС
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

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
        "description": "Акт освидетельствования скрытых работ (фундамент) по форме КС-3",
        "params": ["object_name", "contractor", "date", "foundation_type", "volume_m3", "concrete_class", "inspector_name"]
    },
    "complaint_contractor": {
        "name": "Претензия подрядчику",
        "description": "Официальная претензия по выявленным дефектам",
        "params": ["object_name", "contractor", "date", "defect_description", "deadline", "penalty", "sender_name"]
    },
    "safety_plan": {
        "name": "План мероприятий по охране труда",
        "description": "План ОТ и ТБ на объекте по СП 12-135-2003",
        "params": ["object_name", "start_date", "end_date", "responsible_person", "worker_count"]
    },
    "hidden_works_act": {
        "name": "Акт освидетельствования скрытых работ",
        "description": "Универсальный акт для скрытых работ по форме КС-3",
        "params": ["object_name", "contractor", "date", "work_type", "volume", "standards", "inspector_name"]
    },
}


def add_table_border(table):
    """Добавляет границы ко всем ячейкам таблицы"""
    tbl = table._tbl
    tblPr = tbl.tblPr
    if tblPr is None:
        tblPr = OxmlElement('w:tblPr')
        tbl.insert(0, tblPr)

    tblBorders = OxmlElement('w:tblBorders')
    for border_name in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        border = OxmlElement(f'w:{border_name}')
        border.set(qn('w:val'), 'single')
        border.set(qn('w:sz'), '4')
        border.set(qn('w:space'), '0')
        border.set(qn('w:color'), '000000')
        tblBorders.append(border)

    tblPr.append(tblBorders)


def generate_acceptance_foundation(doc: Document, params: dict):
    """Генерация акта приёмки фундамента по форме КС-3"""

    # Заголовок
    heading = doc.add_heading('АКТ ОСВИДЕТЕЛЬСТВОВАНИЯ СКРЫТЫХ РАБОТ', level=0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

    subheading = doc.add_paragraph('(приёмка фундамента)')
    subheading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subheading.runs[0].font.size = Pt(11)

    doc.add_paragraph()

    # Шапка документа
    p = doc.add_paragraph()
    p.add_run(f'№ _______ от {params.get("date", "___________")}').bold = True
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    doc.add_paragraph()

    # Основная информация
    doc.add_paragraph(f'Объект: {params.get("object_name", "_________________________")}')
    doc.add_paragraph(f'Подрядчик: {params.get("contractor", "_________________________")}')
    doc.add_paragraph(f'Заказчик: _________________________')

    doc.add_paragraph()

    # Основной текст
    doc.add_paragraph(
        'Комиссия в составе представителей заказчика, подрядчика и технического надзора '
        'произвела осмотр работ по устройству фундамента и установила следующее:'
    )

    doc.add_paragraph()

    # Таблица с данными работ
    table = doc.add_table(rows=8, cols=2)
    add_table_border(table)
    table.style = 'Table Grid'

    rows_data = [
        ('Наименование работ', f'Устройство {params.get("foundation_type", "монолитного железобетонного")} фундамента'),
        ('Объём выполненных работ', f'{params.get("volume_m3", "___")} м³'),
        ('Класс бетона', params.get("concrete_class", "В25 (М350)")),
        ('Применённые материалы', 'Бетон, арматура класса A500C, гидроизоляция'),
        ('Нормативные документы', 'СП 70.13330.2012, СП 63.13330.2018, ГОСТ 13580-85'),
        ('Отступления от проекта', 'Отсутствуют'),
        ('Дефекты и недоделки', 'Не выявлены'),
        ('Заключение комиссии', 'Работы выполнены в соответствии с проектом и СНиП. Допускаются к закрытию.')
    ]

    for i, (label, value) in enumerate(rows_data):
        table.rows[i].cells[0].text = label
        table.rows[i].cells[1].text = value
        table.rows[i].cells[0].paragraphs[0].runs[0].font.bold = True

    doc.add_paragraph()

    # Подписи
    doc.add_paragraph('ПОДПИСИ ЧЛЕНОВ КОМИССИИ:')
    doc.add_paragraph()

    sign_table = doc.add_table(rows=4, cols=4)
    add_table_border(sign_table)

    sign_table.rows[0].cells[0].text = 'Должность'
    sign_table.rows[0].cells[1].text = 'ФИО'
    sign_table.rows[0].cells[2].text = 'Подпись'
    sign_table.rows[0].cells[3].text = 'Дата'

    for cell in sign_table.rows[0].cells:
        cell.paragraphs[0].runs[0].font.bold = True

    sign_table.rows[1].cells[0].text = 'Представитель заказчика'
    sign_table.rows[1].cells[1].text = '_________________'

    sign_table.rows[2].cells[0].text = 'Представитель подрядчика'
    sign_table.rows[2].cells[1].text = '_________________'

    sign_table.rows[3].cells[0].text = 'Технический надзор'
    sign_table.rows[3].cells[1].text = params.get("inspector_name", "_________________")

    doc.add_paragraph()
    p = doc.add_paragraph('Работы разрешается закрыть.')
    p.runs[0].font.bold = True
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def generate_complaint_contractor(doc: Document, params: dict):
    """Генерация претензии подрядчику"""

    # Шапка
    p = doc.add_paragraph()
    p.add_run('ПРЕТЕНЗИЯ').bold = True
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.runs[0]
    run.font.size = Pt(16)

    doc.add_paragraph()

    p = doc.add_paragraph()
    p.add_run(f'№ _______ от {params.get("date", "___________")}').bold = True
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    doc.add_paragraph()

    # Кому
    doc.add_paragraph(f'Подрядчику: {params.get("contractor", "_________________________")}')
    doc.add_paragraph(f'От заказчика: {params.get("sender_name", "_________________________")}')
    doc.add_paragraph(f'Объект: {params.get("object_name", "_________________________")}')

    doc.add_paragraph()

    # Основной текст
    doc.add_paragraph(
        'В ходе контроля качества выполненных работ на объекте были выявлены следующие дефекты и нарушения:'
    )

    doc.add_paragraph()

    # Описание дефектов
    p = doc.add_paragraph(f'{params.get("defect_description", "___________________________")}')
    p.paragraph_format.left_indent = Inches(0.5)

    doc.add_paragraph()

    doc.add_paragraph(
        'Указанные нарушения являются отступлением от проектной документации, СНиП и строительных норм. '
        'Данные дефекты снижают качество выполненных работ и могут повлиять на эксплуатационные характеристики объекта.'
    )

    doc.add_paragraph()

    # Требования
    p = doc.add_paragraph('ТРЕБУЕМ:')
    p.runs[0].font.bold = True

    doc.add_paragraph(
        f'1. Устранить выявленные дефекты в срок до {params.get("deadline", "___________")}'
    )
    doc.add_paragraph(
        '2. Предоставить письменное подтверждение выполнения работ по устранению дефектов'
    )
    doc.add_paragraph(
        '3. Обеспечить повторную приёмку выполненных работ с участием представителей заказчика'
    )

    doc.add_paragraph()

    penalty = params.get("penalty", "")
    if penalty:
        doc.add_paragraph(
            f'В случае невыполнения требований в установленный срок будут применены штрафные санкции '
            f'в размере {penalty} в соответствии с условиями договора.'
        )

    doc.add_paragraph()
    doc.add_paragraph()

    # Подписи
    doc.add_paragraph(f'Подпись заказчика: ___________________ ({params.get("sender_name", "")})')
    doc.add_paragraph()
    doc.add_paragraph('Дата получения подрядчиком: ___________________')


def generate_safety_plan(doc: Document, params: dict):
    """Генерация плана мероприятий по охране труда"""

    # Заголовок
    heading = doc.add_heading('ПЛАН МЕРОПРИЯТИЙ', level=0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

    subheading = doc.add_heading('по охране труда и технике безопасности', level=1)
    subheading.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()

    # Информация об объекте
    doc.add_paragraph(f'Объект: {params.get("object_name", "_________________________")}')
    doc.add_paragraph(
        f'Период проведения работ: с {params.get("start_date", "___________")} '
        f'по {params.get("end_date", "___________")}'
    )
    doc.add_paragraph(f'Ответственное лицо: {params.get("responsible_person", "_________________________")}')
    doc.add_paragraph(f'Численность работников: {params.get("worker_count", "___")} чел.')

    doc.add_paragraph()

    # Нормативная база
    p = doc.add_paragraph('Настоящий план разработан в соответствии с:')
    p.runs[0].font.bold = True

    doc.add_paragraph('• СП 12-135-2003 «Безопасность труда в строительстве»')
    doc.add_paragraph('• Трудовым кодексом РФ')
    doc.add_paragraph('• ГОСТ 12.0.004-2015 «ССБТ. Организация обучения безопасности труда»')

    doc.add_paragraph()

    # Таблица мероприятий
    p = doc.add_paragraph('МЕРОПРИЯТИЯ ПО ОХРАНЕ ТРУДА:')
    p.runs[0].font.bold = True

    doc.add_paragraph()

    table = doc.add_table(rows=11, cols=4)
    add_table_border(table)
    table.style = 'Table Grid'

    # Заголовки
    headers = ['№', 'Наименование мероприятия', 'Срок выполнения', 'Ответственный']
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = header
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Мероприятия
    measures = [
        ('1', 'Проведение вводного инструктажа для всех работников', 'До начала работ', 'Инженер по ОТ'),
        ('2', 'Проведение первичного инструктажа на рабочем месте', 'Первый рабочий день', 'Прораб'),
        ('3', 'Обеспечение работников СИЗ (каски, спецодежда, обувь)', 'До начала работ', 'Снабженец'),
        ('4', 'Ограждение опасных зон на строительной площадке', 'Постоянно', 'Прораб'),
        ('5', 'Проверка исправности лесов, подмостей, лестниц', 'Ежедневно', 'Мастер'),
        ('6', 'Контроль применения СИЗ работниками', 'Ежедневно', 'Прораб'),
        ('7', 'Проверка электроинструмента и электрооборудования', 'Перед использованием', 'Электрик'),
        ('8', 'Обеспечение первичными средствами пожаротушения', 'До начала работ', 'Прораб'),
        ('9', 'Организация питьевого режима', 'Постоянно', 'Прораб'),
        ('10', 'Повторный инструктаж по ОТ', 'Каждые 3 месяца', 'Инженер по ОТ'),
    ]

    for i, (num, measure, deadline, responsible) in enumerate(measures, start=1):
        table.rows[i].cells[0].text = num
        table.rows[i].cells[1].text = measure
        table.rows[i].cells[2].text = deadline
        table.rows[i].cells[3].text = responsible

    doc.add_paragraph()

    # Подписи
    doc.add_paragraph()
    doc.add_paragraph(
        f'Ответственный за выполнение плана: ___________________ ({params.get("responsible_person", "")})'
    )
    doc.add_paragraph()
    doc.add_paragraph(f'Дата утверждения: {params.get("start_date", "___________")}')


def generate_hidden_works_act(doc: Document, params: dict):
    """Генерация универсального акта освидетельствования скрытых работ"""

    # Заголовок
    heading = doc.add_heading('АКТ ОСВИДЕТЕЛЬСТВОВАНИЯ СКРЫТЫХ РАБОТ', level=0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()

    # Шапка документа
    p = doc.add_paragraph()
    p.add_run(f'№ _______ от {params.get("date", "___________")}').bold = True
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    doc.add_paragraph()

    # Основная информация
    doc.add_paragraph(f'Объект: {params.get("object_name", "_________________________")}')
    doc.add_paragraph(f'Подрядчик: {params.get("contractor", "_________________________")}')
    doc.add_paragraph(f'Заказчик: _________________________')

    doc.add_paragraph()

    # Основной текст
    doc.add_paragraph(
        'Комиссия в составе представителей заказчика, подрядчика и технического надзора '
        f'произвела осмотр выполненных работ: {params.get("work_type", "_________________________")}'
    )

    doc.add_paragraph()

    # Таблица с данными
    table = doc.add_table(rows=7, cols=2)
    add_table_border(table)
    table.style = 'Table Grid'

    rows_data = [
        ('Наименование работ', params.get("work_type", "_________________________")),
        ('Объём выполненных работ', params.get("volume", "_________________________")),
        ('Применённые материалы', '_________________________'),
        ('Нормативные документы', params.get("standards", "СП, ГОСТ, СНиП")),
        ('Отступления от проекта', 'Отсутствуют / _________________________'),
        ('Выявленные дефекты', 'Не выявлены / _________________________'),
        ('Заключение комиссии', 'Работы выполнены качественно, соответствуют проекту. Допускаются к закрытию.')
    ]

    for i, (label, value) in enumerate(rows_data):
        table.rows[i].cells[0].text = label
        table.rows[i].cells[1].text = value
        table.rows[i].cells[0].paragraphs[0].runs[0].font.bold = True

    doc.add_paragraph()

    # Фотофиксация
    doc.add_paragraph('Приложения: фотофиксация выполненных работ (при наличии)')

    doc.add_paragraph()

    # Подписи
    doc.add_paragraph('ПОДПИСИ ЧЛЕНОВ КОМИССИИ:')
    doc.add_paragraph()

    sign_table = doc.add_table(rows=4, cols=4)
    add_table_border(sign_table)

    sign_table.rows[0].cells[0].text = 'Должность'
    sign_table.rows[0].cells[1].text = 'ФИО'
    sign_table.rows[0].cells[2].text = 'Подпись'
    sign_table.rows[0].cells[3].text = 'Дата'

    for cell in sign_table.rows[0].cells:
        cell.paragraphs[0].runs[0].font.bold = True

    sign_table.rows[1].cells[0].text = 'Представитель заказчика'
    sign_table.rows[1].cells[1].text = '_________________'

    sign_table.rows[2].cells[0].text = 'Представитель подрядчика'
    sign_table.rows[2].cells[1].text = '_________________'

    sign_table.rows[3].cells[0].text = 'Технический надзор'
    sign_table.rows[3].cells[1].text = params.get("inspector_name", "_________________")

    doc.add_paragraph()
    p = doc.add_paragraph('Работы разрешается закрыть.')
    p.runs[0].font.bold = True
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER


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
        if template_id not in DOCUMENT_TEMPLATES:
            return {
                "success": False,
                "filepath": "",
                "error": "Шаблон не найден"
            }

        doc = Document()

        # Устанавливаем стандартные поля документа
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(0.8)
            section.bottom_margin = Inches(0.8)
            section.left_margin = Inches(1.0)
            section.right_margin = Inches(0.6)

        # Вызываем соответствующую функцию генерации
        if template_id == "acceptance_foundation":
            generate_acceptance_foundation(doc, params)
        elif template_id == "complaint_contractor":
            generate_complaint_contractor(doc, params)
        elif template_id == "safety_plan":
            generate_safety_plan(doc, params)
        elif template_id == "hidden_works_act":
            generate_hidden_works_act(doc, params)
        else:
            return {
                "success": False,
                "filepath": "",
                "error": "Неизвестный тип шаблона"
            }

        # Сохраняем документ
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
