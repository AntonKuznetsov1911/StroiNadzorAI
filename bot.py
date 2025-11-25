"""
Telegram бот СтройНадзорAI - AI консультант по строительным нормативам
С поддержкой анализа фотографий дефектов
"""

import os
import logging
import base64
import json
import re
from io import BytesIO
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pathlib import Path
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import anthropic
import asyncio

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Импорт базы актуальных нормативов 2025
try:
    from regulations_2025 import (
        FEDERAL_LAWS,
        MANDATORY_PROCEDURES_2025,
        SRO_REQUIREMENTS,
        TIM_BIM_REQUIREMENTS,
        PRICING_2025,
        INDUSTRIAL_CONSTRUCTION,
        CIVIL_CONSTRUCTION,
        COMMERCIAL_CONSTRUCTION,
        KEY_REGULATIONS_2025,
        DAILY_CHECKLIST,
        TRENDS_2025_2027,
        get_all_regulations,
        search_regulation
    )
    REGULATIONS_2025_AVAILABLE = True
    logger.info("✅ База актуальных нормативов 2025 загружена")
except ImportError:
    REGULATIONS_2025_AVAILABLE = False
    logger.warning("⚠️ Файл regulations_2025.py не найден")

# Импорт практических знаний 2025
try:
    from practical_knowledge_2025 import (
        HSE_REQUIREMENTS,
        CONSTRUCTION_TECHNOLOGY,
        ESTIMATING_FINANCE,
        LEGAL_ISSUES,
        PROJECT_MANAGEMENT,
        get_all_practical_knowledge,
        search_practical
    )
    PRACTICAL_KNOWLEDGE_AVAILABLE = True
    logger.info("✅ База практических знаний 2025 загружена")
except ImportError:
    PRACTICAL_KNOWLEDGE_AVAILABLE = False
    logger.warning("⚠️ Файл practical_knowledge_2025.py не найден")

# Импорт расширенных практических знаний 2025
try:
    from practical_knowledge_advanced_2025 import (
        MIGRATION_LAW,
        GEODESY,
        LOGISTICS,
        ECOLOGY,
        SPECIAL_CONDITIONS,
        ENGINEERING_NETWORKS,
        get_all_advanced_knowledge,
        search_advanced
    )
    ADVANCED_KNOWLEDGE_AVAILABLE = True
    logger.info("✅ Расширенная база знаний 2025 загружена (кадры, геодезия, логистика, экология, сети)")
except ImportError:
    ADVANCED_KNOWLEDGE_AVAILABLE = False
    logger.warning("⚠️ Файл practical_knowledge_advanced_2025.py не найден")

# PDF/Word экспорт
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logging.warning("ReportLab not available - PDF export disabled")

try:
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logging.warning("python-docx not available - Word export disabled")

# Токены (загружаются из .env файла)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Проверка наличия токенов
if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN не найден в .env файле!")
if not ANTHROPIC_API_KEY:
    raise ValueError("❌ ANTHROPIC_API_KEY не найден в .env файле!")

# Инициализация Claude клиента
anthropic_client = None

def get_anthropic_client():
    """Получить Anthropic клиент (ленивая инициализация)"""
    global anthropic_client
    if anthropic_client is None:
        anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return anthropic_client


# === СИСТЕМА ХРАНЕНИЯ ИСТОРИИ ДИАЛОГОВ ===

# Директория для хранения истории
HISTORY_DIR = Path("user_conversations")
HISTORY_DIR.mkdir(exist_ok=True)

# In-memory хранилище истории (для быстрого доступа)
user_conversations = defaultdict(list)

# Максимальное количество сообщений в истории для контекста
MAX_CONTEXT_MESSAGES = 10

def load_user_history(user_id: int):
    """Загрузить историю диалога пользователя из файла"""
    history_file = HISTORY_DIR / f"user_{user_id}.json"
    if history_file.exists():
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                user_conversations[user_id] = data.get('messages', [])
                logger.info(f"Loaded {len(user_conversations[user_id])} messages for user {user_id}")
        except Exception as e:
            logger.error(f"Error loading history for user {user_id}: {e}")
            user_conversations[user_id] = []
    else:
        user_conversations[user_id] = []

def save_user_history(user_id: int):
    """Сохранить историю диалога пользователя в файл"""
    history_file = HISTORY_DIR / f"user_{user_id}.json"
    try:
        data = {
            'user_id': user_id,
            'last_updated': datetime.now().isoformat(),
            'messages': user_conversations[user_id]
        }
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved history for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving history for user {user_id}: {e}")

def add_message_to_history(user_id: int, role: str, content: str, image_analyzed: bool = False):
    """Добавить сообщение в историю диалога с автоматическим тегированием"""
    load_user_history(user_id)

    # Извлекаем теги
    tags = extract_tags_from_message(content)

    message = {
        'role': role,
        'content': content,
        'timestamp': datetime.now().isoformat(),
        'image_analyzed': image_analyzed,
        'tags': tags
    }

    user_conversations[user_id].append(message)

    # Ограничиваем размер истории (храним последние 50 сообщений в файле)
    if len(user_conversations[user_id]) > 50:
        user_conversations[user_id] = user_conversations[user_id][-50:]

    save_user_history(user_id)

def get_conversation_context(user_id: int) -> list:
    """Получить контекст диалога для Claude API (последние N сообщений)"""
    load_user_history(user_id)

    # Берём последние MAX_CONTEXT_MESSAGES сообщений
    recent_messages = user_conversations[user_id][-MAX_CONTEXT_MESSAGES:]

    # Преобразуем в формат Claude API
    claude_messages = []
    for msg in recent_messages:
        # Пропускаем сообщения с изображениями (они уже обработаны)
        if not msg.get('image_analyzed', False):
            claude_messages.append({
                'role': msg['role'],
                'content': msg['content']
            })

    return claude_messages

def clear_user_history(user_id: int):
    """Очистить историю диалога пользователя"""
    user_conversations[user_id] = []
    save_user_history(user_id)

def get_user_stats(user_id: int) -> dict:
    """Получить статистику диалога пользователя"""
    load_user_history(user_id)
    messages = user_conversations[user_id]

    stats = {
        'total_messages': len(messages),
        'user_messages': len([m for m in messages if m['role'] == 'user']),
        'assistant_messages': len([m for m in messages if m['role'] == 'assistant']),
        'images_analyzed': len([m for m in messages if m.get('image_analyzed', False)]),
        'first_message': messages[0]['timestamp'] if messages else None,
        'last_message': messages[-1]['timestamp'] if messages else None
    }

    return stats


# === СИСТЕМА УМНЫХ ТЕГОВ ===

def extract_tags_from_message(content: str) -> list:
    """Извлечь теги из сообщения (упоминания нормативов, типы дефектов)"""
    tags = []

    # Извлекаем упоминания нормативов
    for reg_code in REGULATIONS.keys():
        if reg_code in content:
            tags.append(f"норматив:{reg_code}")

    # Извлекаем типы дефектов
    defect_keywords = {
        'трещина': 'дефект:трещина',
        'коррозия': 'дефект:коррозия',
        'отслоение': 'дефект:отслоение',
        'деформация': 'дефект:деформация',
        'протечка': 'дефект:протечка',
        'бетон': 'материал:бетон',
        'арматура': 'материал:арматура',
        'фундамент': 'конструкция:фундамент',
        'кровля': 'конструкция:кровля',
        'стена': 'конструкция:стена',
        'перекрытие': 'конструкция:перекрытие'
    }

    content_lower = content.lower()
    for keyword, tag in defect_keywords.items():
        if keyword in content_lower:
            tags.append(tag)

    return list(set(tags))  # Убираем дубликаты

def add_message_to_history_with_tags(user_id: int, role: str, content: str, image_analyzed: bool = False):
    """Добавить сообщение в историю с автоматическим тегированием"""
    load_user_history(user_id)

    # Извлекаем теги
    tags = extract_tags_from_message(content)

    message = {
        'role': role,
        'content': content,
        'timestamp': datetime.now().isoformat(),
        'image_analyzed': image_analyzed,
        'tags': tags
    }

    user_conversations[user_id].append(message)

    # Ограничиваем размер истории
    if len(user_conversations[user_id]) > 50:
        user_conversations[user_id] = user_conversations[user_id][-50:]

    save_user_history(user_id)


# === СИСТЕМА ПОИСКА ПО ИСТОРИИ ===

def search_in_history(user_id: int, query: str, limit: int = 10) -> list:
    """Поиск по истории диалогов"""
    load_user_history(user_id)
    messages = user_conversations[user_id]

    if not messages:
        return []

    query_lower = query.lower()
    results = []

    for msg in messages:
        # Поиск по содержимому
        if query_lower in msg['content'].lower():
            results.append(msg)
        # Поиск по тегам
        elif 'tags' in msg and any(query_lower in tag.lower() for tag in msg['tags']):
            results.append(msg)

    # Возвращаем последние N результатов
    return results[-limit:]

def search_by_tags(user_id: int, tags: list, limit: int = 10) -> list:
    """Поиск по тегам"""
    load_user_history(user_id)
    messages = user_conversations[user_id]

    if not messages:
        return []

    results = []
    for msg in messages:
        if 'tags' in msg:
            # Проверяем пересечение тегов
            msg_tags_lower = [t.lower() for t in msg['tags']]
            tags_lower = [t.lower() for t in tags]
            if any(tag in msg_tags_lower for tag in tags_lower):
                results.append(msg)

    return results[-limit:]


# === СИСТЕМА РЕКОМЕНДАЦИЙ ===

def get_recommendations(user_id: int) -> dict:
    """Получить рекомендации на основе истории диалогов"""
    load_user_history(user_id)
    messages = user_conversations[user_id]

    if not messages:
        return {'recommendations': [], 'popular_topics': []}

    # Собираем все теги
    all_tags = []
    for msg in messages:
        if 'tags' in msg:
            all_tags.extend(msg['tags'])

    # Подсчитываем частоту тегов
    tag_counter = Counter(all_tags)
    popular_tags = tag_counter.most_common(5)

    # Формируем рекомендации на основе популярных тем
    recommendations = []
    for tag, count in popular_tags:
        if tag.startswith('норматив:'):
            reg_code = tag.split(':')[1]
            if reg_code in REGULATIONS:
                recommendations.append({
                    'type': 'related_regulation',
                    'code': reg_code,
                    'title': REGULATIONS[reg_code]['title'],
                    'reason': f'Вы часто обращались к этому нормативу ({count} раз)'
                })
        elif tag.startswith('дефект:'):
            defect_type = tag.split(':')[1]
            recommendations.append({
                'type': 'defect_guide',
                'defect': defect_type,
                'reason': f'Вы интересовались дефектами типа "{defect_type}"'
            })

    # Популярные темы
    popular_topics = []
    for tag, count in popular_tags:
        category = tag.split(':')[0] if ':' in tag else 'общее'
        topic = tag.split(':')[1] if ':' in tag else tag
        popular_topics.append({
            'category': category,
            'topic': topic,
            'mentions': count
        })

    return {
        'recommendations': recommendations[:3],
        'popular_topics': popular_topics[:5]
    }


# === ЭКСПОРТ В PDF ===

def export_history_to_pdf(user_id: int) -> BytesIO:
    """Экспортировать историю в PDF"""
    if not PDF_AVAILABLE:
        raise ImportError("ReportLab не установлен")

    load_user_history(user_id)
    messages = user_conversations[user_id]

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)

    story = []
    styles = getSampleStyleSheet()

    # Заголовок
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=20
    )

    story.append(Paragraph("История диалогов СтройНадзорAI", title_style))
    story.append(Spacer(1, 0.5*cm))

    # Информация
    info_text = f"""
    Пользователь ID: {user_id}<br/>
    Дата экспорта: {datetime.now().strftime('%d.%m.%Y %H:%M')}<br/>
    Всего сообщений: {len(messages)}<br/>
    """
    story.append(Paragraph(info_text, styles['Normal']))
    story.append(Spacer(1, 1*cm))

    # Сообщения
    for msg in messages:
        role = "Пользователь" if msg['role'] == 'user' else "Бот"
        timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%d.%m.%Y %H:%M')

        # Заголовок сообщения
        msg_header = f"<b>{role}</b> - {timestamp}"
        story.append(Paragraph(msg_header, styles['Heading3']))

        # Содержимое
        content = msg['content'][:500] + "..." if len(msg['content']) > 500 else msg['content']
        content = content.replace('<', '&lt;').replace('>', '&gt;')
        story.append(Paragraph(content, styles['Normal']))

        # Теги (если есть)
        if 'tags' in msg and msg['tags']:
            tags_text = f"<i>Теги: {', '.join(msg['tags'])}</i>"
            story.append(Paragraph(tags_text, styles['Italic']))

        story.append(Spacer(1, 0.5*cm))

    doc.build(story)
    buffer.seek(0)
    return buffer


# === ЭКСПОРТ В WORD ===

def export_history_to_docx(user_id: int) -> BytesIO:
    """Экспортировать историю в Word"""
    if not DOCX_AVAILABLE:
        raise ImportError("python-docx не установлен")

    load_user_history(user_id)
    messages = user_conversations[user_id]

    doc = Document()

    # Заголовок
    title = doc.add_heading('История диалогов СтройНадзорAI', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Информация
    doc.add_paragraph(f"Пользователь ID: {user_id}")
    doc.add_paragraph(f"Дата экспорта: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    doc.add_paragraph(f"Всего сообщений: {len(messages)}")
    doc.add_paragraph()

    # Сообщения
    for msg in messages:
        role = "👤 Пользователь" if msg['role'] == 'user' else "🤖 Бот"
        timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%d.%m.%Y %H:%M')

        # Заголовок сообщения
        heading = doc.add_heading(f"{role} - {timestamp}", level=2)

        # Содержимое
        content = msg['content']
        p = doc.add_paragraph(content)

        # Теги
        if 'tags' in msg and msg['tags']:
            tags_p = doc.add_paragraph(f"Теги: {', '.join(msg['tags'])}")
            tags_p.italic = True

        doc.add_paragraph()

    # Сохраняем в буфер
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


# === БАЗА ТИПОВЫХ ДЕФЕКТОВ ===

DEFECT_DATABASE = {
    'трещина': {
        'types': {
            'усадочная': {
                'description': 'Вертикальная трещина, возникающая при усадке бетона',
                'критичность': 'низкая',
                'норматив': 'СП 63.13330.2018',
                'допустимая_ширина': '0.1-0.3 мм'
            },
            'температурная': {
                'description': 'Трещина от температурных деформаций',
                'критичность': 'средняя',
                'норматив': 'СП 63.13330.2018',
                'допустимая_ширина': '0.2-0.4 мм'
            },
            'силовая': {
                'description': 'Трещина от превышения нагрузки',
                'критичность': 'высокая',
                'норматив': 'СП 63.13330.2018',
                'допустимая_ширина': '0.1-0.2 мм'
            }
        },
        'методы_устранения': [
            'Инъектирование эпоксидными смолами',
            'Усиление внешними композитными материалами',
            'Устройство обойм'
        ]
    },
    'коррозия': {
        'types': {
            'арматуры': {
                'description': 'Коррозия стальной арматуры в бетоне',
                'критичность': 'высокая',
                'норматив': 'СП 28.13330.2017',
                'признаки': 'Ржавые потеки, отслоение защитного слоя'
            },
            'металлоконструкций': {
                'description': 'Коррозия стальных конструкций',
                'критичность': 'высокая',
                'норматив': 'СП 28.13330.2017',
                'признаки': 'Ржавчина, утонение элементов'
            }
        },
        'методы_устранения': [
            'Механическая очистка',
            'Антикоррозионная защита',
            'Усиление конструкций'
        ]
    },
    'отслоение': {
        'types': {
            'защитного_слоя': {
                'description': 'Отслоение защитного слоя бетона',
                'критичность': 'высокая',
                'норматив': 'СП 13-102-2003',
                'причины': 'Коррозия арматуры, некачественный бетон'
            },
            'штукатурки': {
                'description': 'Отслоение штукатурного слоя',
                'критичность': 'средняя',
                'норматив': 'СП 71.13330.2017',
                'причины': 'Плохая адгезия, влажность'
            }
        },
        'методы_устранения': [
            'Удаление отслоившихся участков',
            'Восстановление защитного слоя',
            'Грунтование поверхности'
        ]
    }
}

def get_defect_info(defect_type: str) -> dict:
    """Получить информацию о дефекте из базы"""
    defect_lower = defect_type.lower()
    for key in DEFECT_DATABASE.keys():
        if key in defect_lower:
            return DEFECT_DATABASE[key]
    return None


# === СИСТЕМА УВЕДОМЛЕНИЙ О НОРМАТИВАХ ===

REGULATIONS_UPDATES = {
    'recent': [
        {
            'code': 'СП 24.13330.2021',
            'title': 'Свайные фундаменты',
            'date': '2021-12-01',
            'type': 'новая_редакция',
            'changes': 'Актуализированы требования к испытаниям свай'
        },
        {
            'code': 'СП 2.13130.2020',
            'title': 'Обеспечение огнестойкости',
            'date': '2020-09-01',
            'type': 'новый',
            'changes': 'Новые требования к огнезащите'
        }
    ],
    'upcoming': []
}

def check_for_regulation_updates() -> list:
    """Проверить наличие обновлений нормативов"""
    recent_updates = REGULATIONS_UPDATES['recent']

    # Фильтруем обновления за последние 30 дней
    thirty_days_ago = datetime.now() - timedelta(days=30)
    new_updates = []

    for update in recent_updates:
        update_date = datetime.fromisoformat(update['date'])
        if update_date > thirty_days_ago:
            new_updates.append(update)

    return new_updates


# База нормативов с URL-ссылками на первоисточники (обновлено 2024-2025)
REGULATIONS = {
    # === КОНСТРУКТИВНЫЕ РЕШЕНИЯ (АКТУАЛЬНЫЕ) ===
    "СП 63.13330.2018": {
        "title": "Бетонные и железобетонные конструкции",
        "url": "https://docs.cntd.ru/document/554403082",
        "year": "2018",
        "category": "Конструкции"
    },
    "СП 16.13330.2017": {
        "title": "Стальные конструкции",
        "url": "https://docs.cntd.ru/document/456044318",
        "year": "2017",
        "category": "Конструкции"
    },
    "СП 64.13330.2017": {
        "title": "Деревянные конструкции",
        "url": "https://docs.cntd.ru/document/456069590",
        "year": "2017",
        "category": "Конструкции"
    },
    "СП 28.13330.2017": {
        "title": "Защита строительных конструкций от коррозии",
        "url": "https://docs.cntd.ru/document/456054198",
        "year": "2017",
        "category": "Защита конструкций"
    },
    "СП 70.13330.2012": {
        "title": "Несущие и ограждающие конструкции",
        "url": "https://docs.cntd.ru/document/1200092705",
        "year": "2012",
        "category": "Конструкции"
    },

    # === ОСНОВАНИЯ И ФУНДАМЕНТЫ ===
    "СП 22.13330.2016": {
        "title": "Основания зданий и сооружений",
        "url": "https://docs.cntd.ru/document/456054206",
        "year": "2016",
        "category": "Фундаменты"
    },
    "СП 24.13330.2021": {
        "title": "Свайные фундаменты",
        "url": "https://docs.cntd.ru/document/1200177001",
        "year": "2021",
        "category": "Фундаменты"
    },
    "СП 50-101-2004": {
        "title": "Проектирование и устройство оснований и фундаментов",
        "url": "https://docs.cntd.ru/document/1200035505",
        "year": "2004",
        "category": "Фундаменты"
    },

    # === ОБСЛЕДОВАНИЕ И ЭКСПЕРТИЗА ===
    "СП 13-102-2003": {
        "title": "Правила обследования несущих строительных конструкций",
        "url": "https://docs.cntd.ru/document/1200035173",
        "year": "2003",
        "category": "Обследование"
    },
    "ГОСТ 31937-2011": {
        "title": "Здания и сооружения. Правила обследования и мониторинга",
        "url": "https://docs.cntd.ru/document/1200100941",
        "year": "2011",
        "category": "Обследование"
    },
    "СП 255.1325800.2016": {
        "title": "Здания и сооружения. Правила эксплуатации",
        "url": "https://docs.cntd.ru/document/456050595",
        "year": "2016",
        "category": "Эксплуатация"
    },

    # === ОГРАЖДАЮЩИЕ КОНСТРУКЦИИ ===
    "СП 50.13330.2012": {
        "title": "Тепловая защита зданий",
        "url": "https://docs.cntd.ru/document/1200095525",
        "year": "2012",
        "category": "Теплотехника"
    },
    "СП 23-101-2004": {
        "title": "Проектирование тепловой защиты зданий",
        "url": "https://docs.cntd.ru/document/1200035109",
        "year": "2004",
        "category": "Теплотехника"
    },
    "СП 17.13330.2017": {
        "title": "Кровли",
        "url": "https://docs.cntd.ru/document/456044318",
        "year": "2017",
        "category": "Кровли"
    },

    # === ИНЖЕНЕРНЫЕ СИСТЕМЫ (НОВЫЕ!) ===
    "СП 60.13330.2020": {
        "title": "Отопление, вентиляция и кондиционирование воздуха",
        "url": "https://docs.cntd.ru/document/573659347",
        "year": "2020",
        "category": "Инженерия"
    },
    "СП 30.13330.2020": {
        "title": "Внутренний водопровод и канализация зданий",
        "url": "https://docs.cntd.ru/document/573659385",
        "year": "2020",
        "category": "Инженерия"
    },
    "СП 52.13330.2016": {
        "title": "Естественное и искусственное освещение",
        "url": "https://docs.cntd.ru/document/456054197",
        "year": "2016",
        "category": "Инженерия"
    },

    # === КОНТРОЛЬ КАЧЕСТВА ===
    "ГОСТ 10180-2012": {
        "title": "Бетоны. Методы определения прочности по контрольным образцам",
        "url": "https://docs.cntd.ru/document/1200100908",
        "year": "2012",
        "category": "Контроль качества"
    },
    "ГОСТ 22690-2015": {
        "title": "Бетоны. Определение прочности механическими методами",
        "url": "https://docs.cntd.ru/document/1200121930",
        "year": "2015",
        "category": "Контроль качества"
    },
    "ГОСТ 23055-78": {
        "title": "Контроль неразрушающий. Сварка металлов",
        "url": "https://docs.cntd.ru/document/1200012783",
        "year": "1978",
        "category": "Контроль качества"
    },
    "СП 48.13330.2019": {
        "title": "Организация строительства",
        "url": "https://docs.cntd.ru/document/564477582",
        "year": "2019",
        "category": "Организация"
    },

    # === ИЗОЛЯЦИЯ И ОТДЕЛКА ===
    "СП 71.13330.2017": {
        "title": "Изоляционные и отделочные покрытия",
        "url": "https://docs.cntd.ru/document/456054235",
        "year": "2017",
        "category": "Отделка"
    },

    # === ПОЖАРНАЯ БЕЗОПАСНОСТЬ (НОВОЕ!) ===
    "СП 2.13130.2020": {
        "title": "Системы противопожарной защиты. Обеспечение огнестойкости",
        "url": "https://docs.cntd.ru/document/565837815",
        "year": "2020",
        "category": "Пожарная безопасность"
    },
    "СП 4.13130.2013": {
        "title": "Системы противопожарной защиты. Ограничение распространения пожара",
        "url": "https://docs.cntd.ru/document/1200101593",
        "year": "2013",
        "category": "Пожарная безопасность"
    },

    # === ДОСТУПНОСТЬ (НОВОЕ!) ===
    "СП 59.13330.2020": {
        "title": "Доступность зданий и сооружений для маломобильных групп населения",
        "url": "https://docs.cntd.ru/document/573659347",
        "year": "2020",
        "category": "Доступность"
    },
}


# Дефекты для распознавания
DEFECT_CATEGORIES = {
    "crack": {"name": "Трещина", "severity": "critical", "regulation": "СП 63.13330.2018"},
    "corrosion": {"name": "Коррозия", "severity": "major", "regulation": "СП 28.13330.2017"},
    "spalling": {"name": "Отслоение", "severity": "major", "regulation": "СП 13-102-2003"},
    "deformation": {"name": "Деформация", "severity": "critical", "regulation": "СП 22.13330.2016"},
    "leak": {"name": "Протечка", "severity": "major", "regulation": "СП 70.13330.2012"},
}


# === КОМАНДЫ ===

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    user_id = update.effective_user.id

    # Загружаем статистику пользователя
    stats = get_user_stats(user_id)

    welcome_message = f"""👋 Здравствуйте, {user.first_name}!

Я - **СтройНадзорAI v2.3** - ваш AI консультант по строительным нормативам с памятью диалогов и практическими знаниями.

🔍 **Мои возможности:**

📸 **Анализ фотографий**
   • Отправьте фото дефекта
   • Я определю тип, критичность
   • Дам рекомендации по нормативам

💬 **Консультации с памятью**
   • Задайте вопрос по СП, ГОСТ, СНиП
   • Я помню контекст предыдущих диалогов
   • Могу уточнять и развивать тему

🛠️ **Практика площадки (НОВИНКА v2.3!)**
   • Охрана труда и техника безопасности
   • Технология строительства (бетон, арматура)
   • Сметное дело и финансы
   • Юридические вопросы и претензии
   • Управление проектами

📚 **База нормативов 2024-2025**
   • 27 актуальных документов
   • Актуальные требования 2025
   • 8 федеральных законов
   • Практические знания площадки

📋 **Основные команды:**
/help - Полная справка по командам
/regulations - Список нормативов (27 документов)
/requirements2025 - База требований 2025

🛠️ **Практические знания:**
/hse - Охрана труда и ТБ
/technology - Технология строительства
/estimating - Сметное дело
/legal - Юридические вопросы
/management - Управление проектами

🧠 **Работа с историей:**
/history - Последние сообщения
/search <запрос> - Поиск по истории
/export - Экспорт в PDF/Word

"""

    if stats['total_messages'] > 0:
        welcome_message += f"""📊 **Ваша статистика:**
• Сообщений: {stats['total_messages']}
• Проанализировано фото: {stats['images_analyzed']}

"""

    welcome_message += "Попробуйте отправить фото дефекта или задать вопрос! 👇"

    keyboard = [
        [InlineKeyboardButton("📚 Список нормативов", callback_data="regulations")],
        [InlineKeyboardButton("💡 Примеры вопросов", callback_data="examples")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats"),
         InlineKeyboardButton("ℹ️ Справка", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_message, parse_mode='Markdown', reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """📖 **ПОДРОБНАЯ СПРАВКА - СтройНадзорAI v2.3**

**1️⃣ Анализ фотографий:**
   • Отправьте фото дефекта
   • Можно добавить подпись с вопросом
   • Я проанализирую изображение и дам рекомендации

**2️⃣ Вопросы по нормативам:**
   • Напишите вопрос в чат
   • Например: "Требования к бетону B25?"
   • Получите профессиональный ответ

**3️⃣ Память диалогов:**
   • Бот помнит контекст разговора
   • Можно задавать уточняющие вопросы
   • Используйте /history для просмотра истории

**📚 КОМАНДЫ - НОРМАТИВЫ:**
   /regulations - 27 актуальных СП, ГОСТ, СНиП
   /examples - Примеры вопросов

**📋 КОМАНДЫ - ТРЕБОВАНИЯ 2025:**
   /requirements2025 - Интерактивная база всех требований
   /laws - 8 основных федеральных законов
   /checklist - Чек-лист ежедневных проверок

**🛠️ КОМАНДЫ - ПРАКТИКА ПЛОЩАДКИ:**
   /hse - Охрана труда и техника безопасности
   /technology - Технология строительства (бетон, арматура)
   /estimating - Сметное дело и финансы (КС-2/КС-3)
   /legal - Юридические вопросы и претензии
   /management - Управление проектами

**🔍 РАБОТА С ИСТОРИЕЙ:**
   /history - Последние 5 сообщений
   /stats - Статистика использования
   /search <запрос> - Поиск по истории
   /export - Экспорт в PDF/Word
   /clear - Очистить историю

**💡 УМНЫЕ ФУНКЦИИ:**
   /recommendations - Персональные рекомендации
   /defects <тип> - Справочник дефектов
   /updates - Обновления нормативов

**Примеры вопросов:**
📌 Какие требования к прочности бетона класса B25?
📌 Сколько дней набирает прочность бетон при -10°C?
📌 Как рассчитать нахлест арматуры А400?
📌 Кто должен подписывать акт КС-2?
📌 Что делать если заказчик не приходит на скрытые работы?

Есть вопросы? Просто напишите! 💬"""

    await update.message.reply_text(help_text, parse_mode='Markdown')


async def regulations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /regulations с кликабельными ссылками на нормативы"""
    text = "📚 **Доступные нормативы:**\n\n"
    text += "_Нажмите на название, чтобы открыть полный текст документа_\n\n"

    for code, data in REGULATIONS.items():
        title = data['title']
        url = data['url']
        text += f"📄 [{code}]({url})\n   _{title}_\n\n"

    text += "\n💡 Задайте вопрос по любому нормативу!"

    await update.message.reply_text(text, parse_mode='Markdown', disable_web_page_preview=True)

async def examples_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /examples"""
    examples_text = """💡 **Примеры вопросов:**

**О бетоне:**
• Какие требования к прочности бетона класса B25?
• Допустимая ширина трещины в железобетоне?
• Методы контроля качества бетона по ГОСТ 10180-2012

**О конструкциях:**
• Требования к несущим стенам жилых домов
• Допустимые деформации перекрытий
• Как проверить качество кирпичной кладки?

**О дефектах:**
• Трещина шириной 0.3 мм - критична ли она?
• Как оценить степень коррозии арматуры?
• Что делать при обнаружении отслоения штукатурки?

**О контроле:**
• Как проверить качество сварных соединений?
• Методы контроля гидроизоляции подвала
• Требования к приемке скрытых работ

**🆕 О КРОВЛЕ (НОВОЕ):**
• Какой уклон нужен для металлочерепицы?
• Как рассчитать площадь кровли?
• Конструкция кровельного пирога для мансарды

**🆕 О ТЕПЛОИЗОЛЯЦИИ (НОВОЕ):**
• Какую толщину утеплителя выбрать для Москвы?
• Как рассчитать точку росы в стене?
• Какой утеплитель лучше для фасада?

**🆕 О ВЕНТИЛЯЦИИ (НОВОЕ):**
• Какая вентиляция нужна для квартиры 75 м²?
• Расчет воздухообмена для офиса
• Что такое рекуперация тепла?

**🆕 О ПОЖАРНОЙ БЕЗОПАСНОСТИ (НОВОЕ):**
• Какой класс огнестойкости нужен для перекрытий?
• Требования к эвакуационным выходам
• Нормы огнезащиты стальных конструкций

💡 **С памятью диалогов вы можете:**
• Задавать уточняющие вопросы
• Ссылаться на предыдущие обсуждения
• Развивать одну тему в нескольких сообщениях

Просто напишите свой вопрос или отправьте фото дефекта! 📸"""

    await update.message.reply_text(examples_text, parse_mode='Markdown')


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /history - показать последние сообщения из истории"""
    user_id = update.effective_user.id
    load_user_history(user_id)

    messages = user_conversations[user_id]

    if not messages:
        await update.message.reply_text("📭 История диалогов пуста. Начните общение!")
        return

    # Показываем последние 5 сообщений
    recent = messages[-5:]
    history_text = "📜 **Последние сообщения:**\n\n"

    for msg in recent:
        role_emoji = "👤" if msg['role'] == 'user' else "🤖"
        timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%d.%m %H:%M')
        content_preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']

        if msg.get('image_analyzed', False):
            content_preview = "📸 [Анализ фотографии]"

        history_text += f"{role_emoji} **{timestamp}**\n{content_preview}\n\n"

    history_text += f"\nВсего сообщений: {len(messages)}\nИспользуйте /clear для очистки истории"

    await update.message.reply_text(history_text, parse_mode='Markdown')


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats - показать статистику использования"""
    user_id = update.effective_user.id
    stats = get_user_stats(user_id)

    if stats['total_messages'] == 0:
        await update.message.reply_text("📊 Статистика пока пуста. Начните общение!")
        return

    stats_text = f"""📊 **Ваша статистика использования:**

📝 **Сообщения:**
   • Всего: {stats['total_messages']}
   • От вас: {stats['user_messages']}
   • От бота: {stats['assistant_messages']}

📸 **Анализ фото:**
   • Проанализировано: {stats['images_analyzed']}

📅 **Период использования:**
   • Первое сообщение: {datetime.fromisoformat(stats['first_message']).strftime('%d.%m.%Y %H:%M') if stats['first_message'] else 'N/A'}
   • Последнее: {datetime.fromisoformat(stats['last_message']).strftime('%d.%m.%Y %H:%M') if stats['last_message'] else 'N/A'}

💡 Бот помнит последние {MAX_CONTEXT_MESSAGES} сообщений для контекста диалога."""

    await update.message.reply_text(stats_text, parse_mode='Markdown')


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /clear - очистить историю диалогов"""
    user_id = update.effective_user.id

    # Создаем кнопки подтверждения
    keyboard = [
        [InlineKeyboardButton("✅ Да, очистить", callback_data="clear_confirm")],
        [InlineKeyboardButton("❌ Отмена", callback_data="clear_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚠️ **Подтверждение очистки истории**\n\n"
        "Вы уверены, что хотите удалить всю историю диалогов?\n"
        "Это действие нельзя отменить.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /export - экспортировать историю"""
    user_id = update.effective_user.id

    keyboard = [
        [InlineKeyboardButton("📄 PDF", callback_data="export_pdf")],
        [InlineKeyboardButton("📝 Word", callback_data="export_docx")],
        [InlineKeyboardButton("❌ Отмена", callback_data="export_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📤 **Экспорт истории диалогов**\n\n"
        "Выберите формат для экспорта:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /search - поиск по истории"""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text(
            "🔍 **Поиск по истории**\n\n"
            "Использование: `/search <запрос>`\n\n"
            "Примеры:\n"
            "• `/search трещина` - найти все сообщения про трещины\n"
            "• `/search СП 63` - найти все упоминания СП 63.13330.2018\n"
            "• `/search бетон B25` - найти сообщения про бетон B25",
            parse_mode='Markdown'
        )
        return

    query = " ".join(context.args)
    results = search_in_history(user_id, query, limit=5)

    if not results:
        await update.message.reply_text(
            f"❌ По запросу «{query}» ничего не найдено.\n\n"
            "Попробуйте изменить запрос или проверьте историю через /history"
        )
        return

    response = f"🔍 **Результаты поиска по запросу «{query}»**\n\n"
    response += f"Найдено: {len(results)} сообщений\n\n"

    for i, msg in enumerate(results, 1):
        role_emoji = "👤" if msg['role'] == 'user' else "🤖"
        timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%d.%m %H:%M')
        content = msg['content'][:150] + "..." if len(msg['content']) > 150 else msg['content']

        response += f"{i}. {role_emoji} **{timestamp}**\n{content}\n\n"

    response += f"\nИспользуйте /history для просмотра полной истории"

    await update.message.reply_text(response, parse_mode='Markdown')


async def recommendations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /recommendations - персональные рекомендации"""
    user_id = update.effective_user.id

    recs = get_recommendations(user_id)

    if not recs['recommendations'] and not recs['popular_topics']:
        await update.message.reply_text(
            "💡 **Рекомендации**\n\n"
            "Пока недостаточно данных для персональных рекомендаций.\n"
            "Продолжайте общение с ботом!"
        )
        return

    response = "💡 **Персональные рекомендации**\n\n"

    if recs['recommendations']:
        response += "**На основе ваших интересов:**\n\n"
        for rec in recs['recommendations']:
            if rec['type'] == 'related_regulation':
                response += f"📚 [{rec['code']}]({REGULATIONS[rec['code']]['url']}) - {rec['title']}\n"
                response += f"_{rec['reason']}_\n\n"
            elif rec['type'] == 'defect_guide':
                defect = rec['defect'].capitalize()
                response += f"🔍 Справочник по дефекту: {defect}\n"
                response += f"_{rec['reason']}_\n\n"

    if recs['popular_topics']:
        response += "\n**Ваши популярные темы:**\n\n"
        for topic in recs['popular_topics']:
            emoji_map = {
                'норматив': '📄',
                'дефект': '⚠️',
                'материал': '🧱',
                'конструкция': '🏗️'
            }
            emoji = emoji_map.get(topic['category'], '📌')
            response += f"{emoji} {topic['topic'].capitalize()} - {topic['mentions']} упоминаний\n"

    await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)


async def defects_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /defects - справочник дефектов"""
    if not context.args:
        text = """🔍 **Справочник дефектов**

**Доступные типы дефектов:**

⚠️ **Трещины**
   • Усадочные
   • Температурные
   • Силовые (от перегрузки)

🦠 **Коррозия**
   • Коррозия арматуры
   • Коррозия металлоконструкций

🔻 **Отслоение**
   • Отслоение защитного слоя бетона
   • Отслоение штукатурки

**Использование:**
`/defects трещина` - информация о трещинах
`/defects коррозия` - информация о коррозии
`/defects отслоение` - информация об отслоении"""

        await update.message.reply_text(text, parse_mode='Markdown')
        return

    defect_query = " ".join(context.args).lower()
    defect_info = get_defect_info(defect_query)

    if not defect_info:
        await update.message.reply_text(
            f"❌ Информация о дефекте «{defect_query}» не найдена.\n\n"
            "Используйте `/defects` без параметров для списка доступных дефектов.",
            parse_mode='Markdown'
        )
        return

    response = f"🔍 **Справочник: {defect_query.capitalize()}**\n\n"

    if 'types' in defect_info:
        response += "**Типы:**\n\n"
        for type_name, type_data in defect_info['types'].items():
            response += f"• **{type_name.capitalize()}**\n"
            response += f"  {type_data['description']}\n"
            response += f"  Критичность: {type_data['критичность']}\n"
            response += f"  Норматив: {type_data['норматив']}\n"
            if 'допустимая_ширина' in type_data:
                response += f"  Допустимая ширина: {type_data['допустимая_ширина']}\n"
            response += "\n"

    if 'методы_устранения' in defect_info:
        response += "**Методы устранения:**\n\n"
        for i, method in enumerate(defect_info['методы_устранения'], 1):
            response += f"{i}. {method}\n"

    await update.message.reply_text(response, parse_mode='Markdown')


async def updates_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /updates - проверить обновления нормативов"""
    recent_updates = REGULATIONS_UPDATES['recent']

    if not recent_updates:
        await update.message.reply_text(
            "✅ Все нормативы актуальны.\n"
            "Новых обновлений не обнаружено."
        )
        return

    response = "🆕 **Недавние обновления нормативов**\n\n"

    for upd in recent_updates:
        type_emoji = "🆕" if upd['type'] == 'новый' else "♻️"
        update_date = datetime.fromisoformat(upd['date']).strftime('%d.%m.%Y')

        response += f"{type_emoji} **{upd['code']}** - {upd['title']}\n"
        response += f"Дата: {update_date}\n"
        response += f"Изменения: {upd['changes']}\n\n"

    response += "\n💡 Используйте /regulations для просмотра всех нормативов"

    await update.message.reply_text(response, parse_mode='Markdown')


async def requirements2025_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /requirements2025 - актуальные требования 2025"""
    if not REGULATIONS_2025_AVAILABLE:
        await update.message.reply_text(
            "⚠️ База актуальных требований 2025 недоступна.\n"
            "Обратитесь к администратору."
        )
        return

    keyboard = [
        [InlineKeyboardButton("📋 Основные законы", callback_data="req2025_laws")],
        [InlineKeyboardButton("🔄 Процедуры 2025", callback_data="req2025_procedures")],
        [InlineKeyboardButton("👷 СРО и квалификация", callback_data="req2025_sro")],
        [InlineKeyboardButton("💻 ТИМ/BIM", callback_data="req2025_bim")],
        [InlineKeyboardButton("🏭 Промышленное", callback_data="req2025_industrial")],
        [InlineKeyboardButton("🏘️ Гражданское", callback_data="req2025_civil")],
        [InlineKeyboardButton("🏢 Коммерческое", callback_data="req2025_commercial")],
        [InlineKeyboardButton("✅ Чек-лист проверок", callback_data="req2025_checklist")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = """📚 **АКТУАЛЬНЫЕ ТРЕБОВАНИЯ 2025**

База полностью обновлена на 2025-2026 год!

Выберите раздел для подробной информации:

📋 Основные законы РФ (8 ФЗ)
🔄 Обязательные процедуры 2025
👷 СРО и квалификация
💻 ТИМ/BIM требования
🏭 Промышленное строительство
🏘️ Гражданское строительство
🏢 Коммерческое строительство
✅ Чек-лист ежедневных проверок"""

    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)


async def laws_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /laws - основные законы"""
    if not REGULATIONS_2025_AVAILABLE:
        await update.message.reply_text("⚠️ База недоступна")
        return

    text = "📋 **ОСНОВНЫЕ ЗАКОНЫ РФ 2025**\n\n"

    for code, data in FEDERAL_LAWS.items():
        text += f"**{code}** - [{data['title']}]({data['url']})\n"
        text += f"_{data['scope']}_\n\n"

    await update.message.reply_text(text, parse_mode='Markdown', disable_web_page_preview=True)


async def checklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /checklist - ежедневный чек-лист"""
    text = """✅ **ЧЕК-ЛИСТ ЕЖЕДНЕВНЫХ ПРОВЕРОК НА ОБЪЕКТЕ**

Что проверять каждый день:

1️⃣ Есть ли действующее разрешение на строительство (РНС)?
2️⃣ Прошла ли ПД экспертизу?
3️⃣ Есть ли членство в СРО у генподрядчика?
4️⃣ Ведётся ли исполнительная документация (акты освидетельствования скрытых работ, журналы)?
5️⃣ Назначены ли лица по технадзору и стройконтролю?
6️⃣ Для промки - зарегистрировано ли ОПО? Есть ли СЗЗ?
7️⃣ Ведётся ли журнал входного контроля материалов?
8️⃣ Есть ли допуски у сварщиков, стропальщиков, крановщиков (удостоверения + протоколы НОК)?
9️⃣ Подписаны ли акты КС-2, КС-3 ежемесячно?

**Используйте этот список для контроля объекта!**

💡 Сохраните в закладки для быстрого доступа"""

    await update.message.reply_text(text, parse_mode='Markdown')


# === ПРАКТИЧЕСКИЕ ЗНАНИЯ 2025 ===

async def hse_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /hse - охрана труда и техника безопасности"""
    if not PRACTICAL_KNOWLEDGE_AVAILABLE:
        await update.message.reply_text("⚠️ База практических знаний недоступна")
        return

    text = """🦺 **ОХРАНА ТРУДА И ТЕХНИКА БЕЗОПАСНОСТИ (HSE)**

📌 **Доступные разделы:**

1️⃣ **Работа на высоте** (Приказ Минтруда № 782н)
   • Группы безопасности (1, 2, 3)
   • Обязательные СИЗ
   • Наряд-допуск

2️⃣ **Электробезопасность**
   • Группы до 1000В / выше 1000В
   • Временные электросети на стройке

3️⃣ **Погрузочно-разгрузочные работы**
   • Схемы строповки
   • Сигналы крановщику

💡 **Примеры вопросов:**
• Какая группа безопасности нужна для работы на высоте 5 м?
• Какие СИЗ обязательны при работе на высоте?
• Кто может работать с электроинструментом?
• Как правильно застропить балку?

📖 Просто задайте вопрос, и я дам подробный ответ со ссылками на нормативы!"""

    await update.message.reply_text(text, parse_mode='Markdown')


async def technology_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /technology - технология строительного производства"""
    if not PRACTICAL_KNOWLEDGE_AVAILABLE:
        await update.message.reply_text("⚠️ База практических знаний недоступна")
        return

    text = """🏗️ **ТЕХНОЛОГИЯ СТРОИТЕЛЬНОГО ПРОИЗВОДСТВА**

📌 **Доступные разделы:**

1️⃣ **Бетонные работы**
   • Набор прочности (график)
   • Зимнее бетонирование (при -10°C, -20°C)
   • Контроль прочности (кубики, молоток Физделя)

2️⃣ **Арматурные работы**
   • Расчет нахлестов (для А400, А500)
   • Защитный слой бетона
   • Схемы вязки

3️⃣ **Входной контроль материалов**
   • Арматура (допуски по диаметру)
   • Бетон (прочность, подвижность)
   • Кирпич (геометрия, прочность)

💡 **Примеры вопросов:**
• Сколько дней набирает прочность бетон зимой?
• Какой нахлест арматуры А400 d=16 мм?
• Какие добавки использовать при -15°C?
• Как контролировать прочность бетона на объекте?

📖 Просто задайте вопрос, и я дам практический ответ с расчетами!"""

    await update.message.reply_text(text, parse_mode='Markdown')


async def estimating_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /estimating - сметное дело и финансы"""
    if not PRACTICAL_KNOWLEDGE_AVAILABLE:
        await update.message.reply_text("⚠️ База практических знаний недоступна")
        return

    text = """💰 **СМЕТНОЕ ДЕЛО И ФИНАНСЫ**

📌 **Доступные разделы:**

1️⃣ **Акты КС-2 и КС-3**
   • Типичные ошибки
   • Порядок подписания
   • Сроки согласования

2️⃣ **Давальческие материалы**
   • Форма М-29
   • Учет в смете
   • Кто платит за доставку?

3️⃣ **Непредвиденные расходы**
   • Процент от сметы
   • Досудебное урегулирование
   • Дополнительные соглашения

💡 **Примеры вопросов:**
• Какие ошибки бывают в КС-2?
• Кто платит за доставку давальческих материалов?
• Сколько процентов непредвиденных расходов?
• Как оформить доп.соглашение на изменение объемов?

📖 Просто задайте вопрос, и я помогу разобраться с финансами!"""

    await update.message.reply_text(text, parse_mode='Markdown')


async def legal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /legal - юридические вопросы и претензионная работа"""
    if not PRACTICAL_KNOWLEDGE_AVAILABLE:
        await update.message.reply_text("⚠️ База практических знаний недоступна")
        return

    text = """⚖️ **ЮРИДИЧЕСКИЕ ВОПРОСЫ И ПРЕТЕНЗИОННАЯ РАБОТА**

📌 **Доступные разделы:**

1️⃣ **Сроки и неустойки**
   • ГК РФ ст. 330
   • Расчет пеней
   • Способы снижения

2️⃣ **Освидетельствование скрытых работ**
   • Кто подписывает акты?
   • Что если заказчик не является?
   • 3 дня на освидетельствование

3️⃣ **Претензионная работа**
   • Досудебное урегулирование
   • Образцы писем
   • Сроки ответов

💡 **Примеры вопросов:**
• Как рассчитать неустойку за просрочку?
• Что делать, если заказчик не подписывает акт скрытых работ?
• Как написать претензию на невыплату?
• Можно ли снизить пени?

📖 Просто задайте вопрос, и я помогу с юридическими тонкостями!"""

    await update.message.reply_text(text, parse_mode='Markdown')


async def management_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /management - управление проектами и soft skills"""
    if not PRACTICAL_KNOWLEDGE_AVAILABLE:
        await update.message.reply_text("⚠️ База практических знаний недоступна")
        return

    text = """📊 **УПРАВЛЕНИЕ ПРОЕКТАМИ И SOFT SKILLS**

📌 **Доступные разделы:**

1️⃣ **Планирование работ**
   • Диаграмма Ганта
   • Сетевые графики
   • Критический путь

2️⃣ **Протоколы совещаний**
   • Обязательные пункты
   • Формат оформления
   • Юридическая сила

3️⃣ **Расчет численности**
   • Формула расчета рабочих
   • Коэффициент совмещения
   • Учет сменности

4️⃣ **Разрешение конфликтов**
   • С заказчиком
   • С субподрядчиком
   • Внутри команды

💡 **Примеры вопросов:**
• Как построить диаграмму Ганта для стройки?
• Что обязательно должно быть в протоколе совещания?
• Как рассчитать сколько нужно каменщиков?
• Что делать если субподрядчик срывает сроки?

📖 Просто задайте вопрос, и я помогу с управлением проектом!"""

    await update.message.reply_text(text, parse_mode='Markdown')


# === ОБРАБОТКА СООБЩЕНИЙ ===

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фотографий"""
    # Отправляем сообщение о процессе и сохраняем его для последующего удаления
    thinking_message = await update.message.reply_text("📸 Анализирую фотографию...\n\nВы можете не ждать, я пришлю уведомление 😉")

    try:
        # Получаем фото (самое большое разрешение)
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()

        # Скачиваем фото
        photo_bytes = await photo_file.download_as_bytearray()

        # Кодируем в base64
        photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')

        # Получаем подпись (если есть)
        caption = update.message.caption or ""

        # Формируем профессиональный промпт для Claude 3.5 Sonnet
        system_prompt = """Вы — ведущий инженер-эксперт по техническому надзору в строительстве с 20-летним стажем работы на крупных объектах России. Ваша специализация: диагностика дефектов, экспертиза конструкций, нормативный контроль.

🎯 ТРЕБОВАНИЯ К АНАЛИЗУ:

**ПРОФЕССИОНАЛЬНЫЙ ПОДХОД:**
- Используйте точную строительную терминологию (не "трещина", а "усадочная трещина продольного направления")
- Приводите конкретные числовые параметры с допусками (например: "ширина раскрытия 0.4±0.05 мм")
- Ссылайтесь на конкретные пункты нормативов (пример: "согласно п. 7.3.1 СП 63.13330.2018")
- Указывайте класс опасности дефекта по ГОСТ Р 31937-2011

**СТРУКТУРА ЭКСПЕРТНОГО ЗАКЛЮЧЕНИЯ:**

📋 **1. ОБЩЕЕ ОПИСАНИЕ ОБЪЕКТА**
   • Идентификация элемента конструкции
   • Материал, конструктивная система
   • Видимое техническое состояние

🔍 **2. ДЕФЕКТОВКА И ИЗМЕРЕНИЯ**
   • Тип выявленного дефекта (согласно классификации СП 13-102-2003)
   • Геометрические параметры (длина, ширина, глубина)
   • Локализация и распространение
   • Категория технического состояния (работоспособное/ограниченно работоспособное/неработоспособное)

📚 **3. НОРМАТИВНАЯ ОЦЕНКА**
   • Применимые нормативы (СП, ГОСТ, СНиП) с указанием пунктов
   • Предельные допустимые значения
   • Отклонение от нормы (в % или абсолютных величинах)
   • Степень критичности: НЕДОПУСТИМЫЙ / ЗНАЧИТЕЛЬНЫЙ / ДОПУСТИМЫЙ

🔧 **4. РЕКОМЕНДАЦИИ ПО УСТРАНЕНИЮ**
   • Технология производства работ (ГОСТ, СП)
   • Необходимые материалы (с указанием классов/марок)
   • Последовательность операций
   • Контроль качества выполнения
   • Ориентировочная трудоемкость (чел/час)

⚠️ **5. РИСКИ И ПОСЛЕДСТВИЯ**
   • Прогноз развития дефекта
   • Потенциальная угроза несущей способности
   • Срочность устранения (немедленно/в течение месяца/плановый ремонт)

**БАЗА НОРМАТИВОВ РФ:**
• СП 63.13330.2018 — Бетонные и ж/б конструкции. Основные положения
• СП 28.13330.2017 — Защита строительных конструкций от коррозии
• СП 13-102-2003 — Правила обследования несущих конструкций
• ГОСТ 23055-78 — Контроль неразрушающий. Сварка металлов
• СП 22.13330.2016 — Основания зданий и сооружений
• СП 70.13330.2012 — Несущие и ограждающие конструкции
• ГОСТ 10180-2012 — Методы определения прочности бетона
• СП 50-101-2004 — Проектирование и устройство оснований и фундаментов
• СП 17.13330.2017 — Кровли
• СП 50.13330.2012 — Тепловая защита зданий

ВАЖНО: Держите тон профессионального технического отчета. Избегайте разговорных выражений. Каждое утверждение должно иметь нормативное обоснование."""

        user_message = "Проанализируй это изображение строительного объекта. Определи дефекты, их критичность и дай рекомендации."
        if caption:
            user_message += f"\n\nКонтекст от пользователя: {caption}"

        # Получаем самый быстрый ответ от обоих API
        # Вызываем Claude API для анализа изображения
        client = get_anthropic_client()
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2500,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": photo_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": user_message
                            }
                        ]
                    }
                ],
                temperature=0.7
            )
        )
        analysis = response.content[0].text

        # Удаляем сообщение "анализирую фотографию"
        try:
            await thinking_message.delete()
        except Exception as e:
            logger.warning(f"Could not delete thinking message: {e}")

        # Формируем ответ
        result = f"🔍 **Анализ фотографии:**\n\n{analysis}\n\n"
        result += f"⏰ Время анализа: {datetime.now().strftime('%H:%M:%S')}"

        # Разбиваем длинные сообщения на части (лимит Telegram: 4096 символов)
        max_length = 4000  # Оставляем запас
        if len(result) > max_length:
            parts = []
            current_part = ""
            for line in result.split('\n'):
                if len(current_part) + len(line) + 1 > max_length:
                    parts.append(current_part)
                    current_part = line + '\n'
                else:
                    current_part += line + '\n'
            if current_part:
                parts.append(current_part)

            # Отправляем по частям
            for i, part in enumerate(parts):
                if i == 0:
                    await update.message.reply_text(part, parse_mode='Markdown')
                else:
                    await update.message.reply_text(f"_(продолжение {i+1}/{len(parts)})_\n\n{part}", parse_mode='Markdown')
        else:
            await update.message.reply_text(result, parse_mode='Markdown')

        logger.info(f"Photo analyzed for user {update.effective_user.id} by Claude")

    except Exception as e:
        logger.error(f"Error analyzing photo: {e}")
        # Удаляем сообщение "анализирую фотографию" даже в случае ошибки
        try:
            await thinking_message.delete()
        except:
            pass
        await update.message.reply_text(
            f"❌ Ошибка при анализе фотографии: {str(e)}\n\nПопробуйте еще раз или обратитесь к администратору."
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений с контекстом истории"""
    user_id = update.effective_user.id
    question = update.message.text

    # Добавляем вопрос пользователя в историю
    add_message_to_history(user_id, 'user', question)

    # Отправляем сообщение о процессе и сохраняем его для последующего удаления
    thinking_message = await update.message.reply_text("🤔 Думаю над вашим вопросом... \n\nВы можете не ждать, я пришлю уведомление 😉")

    try:
        # Профессиональный промпт с актуальными требованиями 2025
        system_prompt = f"""**РОЛЬ И МИССИЯ:**
Вы — универсальный AI-помощник по строительству в России с 20-летним опытом. Ваша задача — помогать:
• **Новичкам**: объяснять простым языком основы (что такое СНиП, как читать чертежи, зачем нужен ППР)
• **Прорабам и мастерам**: решать практические вопросы на площадке (технология работ, охрана труда, закрытие объёмов)
• **ГИПам и руководителям**: помогать с документацией, претензионной работой, управлением сроками и нормативами

**КРИТИЧЕСКИ ВАЖНО: Используйте ТОЛЬКО актуальные требования 2025-2026 года!**

**ПРИНЦИПЫ РАБОТЫ:**

1. **АДАПТАЦИЯ ПОД УРОВЕНЬ**:
   • Новичку → простой язык, аналогии, пошаговые инструкции, объяснение терминов
   • Профессионалу → точные ссылки на нормативы, конкретные цифры и допуски, формулы расчетов

2. **СТРУКТУРА ОТВЕТА** (всегда придерживайтесь):
   📌 **Короткий ответ** (1-2 предложения — суть)
   📐 **Подробности** (технология, нормативы, цифры, формулы)
   💡 **Практический совет** (что делать прямо сейчас на объекте)
   📚 **Ссылка на документ** (СП, ГОСТ, ГК РФ — пункт и год издания)

3. **БЕЗОПАСНОСТЬ — ПРИОРИТЕТ №1**:
   ⚠️ Если вопрос касается потенциально опасных работ (высота, электричество, грузоподъёмные механизмы, земляные работы в котлованах), ВСЕГДА начинайте с требований охраны труда!

4. **ДОСТУП К ИСТОРИИ ДИАЛОГА**:
   У вас есть доступ к истории диалога с пользователем. Используйте контекст предыдущих сообщений для более точных ответов. Если пользователь задает уточняющий вопрос или использует местоимения ("это", "он", "там"), обращайтесь к истории диалога.

**БАЗА АКТУАЛЬНЫХ ТРЕБОВАНИЙ 2025:**

📋 ОСНОВНЫЕ ЗАКОНЫ РФ:
• 190-ФЗ - Градостроительный кодекс РФ
• 384-ФЗ - Технический регламент о безопасности зданий и сооружений
• 123-ФЗ - Технический регламент о требованиях пожарной безопасности
• 116-ФЗ - О промышленной безопасности ОПО
• 214-ФЗ - Об участии в долевом строительстве (жильё + эскроу-счета с 2019)
• 44-ФЗ и 223-ФЗ - Госзакупки и закупки госкорпораций
• 248-ФЗ - О государственном контроле (надзоре) и муниципальном контроле

🔄 ОБЯЗАТЕЛЬНЫЕ ПРОЦЕДУРЫ 2025:
1. РНС (Разрешение на строительство) - обязательно для всех кроме ИЖС до 3 этажей
2. Экспертиза проектной документации (государственная или негосударственная)
3. ЗОС (Заключение о соответствии) - выдаёт стройнадзор (ПП № 1431)
4. Уведомление о начале и окончании строительства через Госуслуги
5. Ввод в эксплуатацию через Госуслуги (реестровая модель с 2022)

👷 СРО И КВАЛИФИКАЦИЯ 2025:
• Генподрядчик - ОБЯЗАТЕЛЬНО членство в СРО (компенсационные фонды)
• Субподрядчик - с 2023 без СРО если договор ≤ 3 млн руб.
• ГИП и ГАП - ОБЯЗАТЕЛЬНО НОК (независимая оценка квалификации) + запись в НРС

💻 ТИМ/BIM:
• 2022-2025: обязательно для объектов госзаказа
• С 01.01.2027: обязательно для ВСЕХ объектов капстроительства (OpenBIM Level 2)
• Стандарты: ГОСТ Р 57580, СП 301.1325800.2017, Приказ № 926/пр

💰 ЦЕНООБРАЗОВАНИЕ 2025:
• ФГИС ЦС - обязательно
• Ресурсный метод - основной с 2025
• Сметы: ГЭСН/ФЕР + индексы Минстроя

🏭 ПРОМЫШЛЕННОЕ СТРОИТЕЛЬСТВО:
Классы опасности ОПО:
• I - чрезвычайно высокий (нефтехим, АЭС): декларация промбезопасности обязательна
• II - высокий (химзаводы): лицензия Ростехнадзора + декларация
• III - средний (заводы): лицензия Ростехнадзора + ПМЛА
• IV - низкий (мелкие производства): регистрация в реестре

Обязательные документы:
• СЗЗ (санитарно-защитная зона) - СанПиН 2.2.1/2.1.1.1200-03
• Лицензия Ростехнадзора (для II-III классов)
• ПМЛА (План мероприятий по локализации и ликвидации аварий)
• Декларация промбезопасности (для I-II классов)
• Раздел 9 ПД - промышленная безопасность
• ИТМ ГОЧС, взрывозащита (ГОСТ IEC 60079), молниезащита

🏘️ ГРАЖДАНСКОЕ СТРОИТЕЛЬСТВО (жильё, школы, больницы):
Требования 2025:
• 214-ФЗ + эскроу-счета (обязательно с 2019)
• СП 54.13330.2022 - жилые здания
• СП 59.13330.2020 - доступность для МГН
• Класс энергоэффективности НЕ НИЖЕ «С»
• Умные счётчики (электро, тепло, вода) - ОБЯЗАТЕЛЬНО
• Умный дом (видеонаблюдение, контроль доступа, СОУЭ)
• 5-10% машиномест для инвалидов
• Экспертиза: обязательна для >3 этажей или >1500 м²

🏢 КОММЕРЧЕСКОЕ СТРОИТЕЛЬСТВО:
ТРЦ:
• СП 4.13130.2013 - жёсткие требования по эвакуации
• 2 независимых эвакуационных выхода с каждого этажа
• Дымоудаление, спринклеры, СОУЭ 3-5 типа
• Проверки каждые 2 года (после "Зимней вишни")

Гостиницы:
• Классификация по "звёздам" (Приказ Минкультуры № 1215)
• СОУЭ не ниже 3 типа

Апартаменты:
• Юридически - нежилые помещения
• Без 214-ФЗ и эскроу
• Нельзя прописаться, выше налог

📊 КЛЮЧЕВЫЕ НОРМАТИВЫ 2025:
• ПП № 985 + Приложение - что подлежит экспертизе
• ПП № 1431 - порядок выдачи ЗОС
• Приказ Минстроя № 783/пр - стройконтроль и надзор
• Приказ № 926/пр - ТИМ/BIM
• СП 48.13330.2019 - Организация строительства
• РД-11-02-2006 - исполнительная документация
• ПП № 815 - какие разделы ПД обязательны
• ГОСТ Р 57580.1-2017 - требования к BIM-моделям

✅ ЧЕК-ЛИСТ ЕЖЕДНЕВНЫХ ПРОВЕРОК:
1. Действующее РНС
2. ПД прошла экспертизу
3. Членство генподрядчика в СРО
4. Исполнительная документация (акты, журналы)
5. Лица по технадзору и стройконтролю назначены
6. Для промки: ОПО зарегистрировано, СЗЗ есть
7. Журнал входного контроля материалов
8. Допуски специалистов (сварщики, стропальщики, крановщики)
9. Акты КС-2, КС-3 подписываются ежемесячно

🔮 ТРЕНДЫ 2025-2027:
• Полный переход на реестровую модель (через Госуслуги)
• ТИМ Level 2 обязателен с 2027
• ESG и "зелёное" строительство (LEED, BREEAM)
• Роботизация и дроны (допускаются для стройконтроля)
• Обязательное страхование ответственности застройщика (с 2025 для всех)

**ПРАКТИЧЕСКИЕ ЗНАНИЯ ПЛОЩАДКИ:**

🦺 ОХРАНА ТРУДА (HSE):
• Работа на высоте >1.8м (Приказ Минтруда № 782н): группы безопасности 1/2/3, СИЗ обязательны
• Электробезопасность: группы до 1000В / выше 1000В, временные сети 380/220В
• Погрузочно-разгрузочные: схемы строповки, сигналы крановщику

🏗️ ТЕХНОЛОГИЯ ПРОИЗВОДСТВА:
• Бетон: набор прочности при +20°C = 28 суток до 100%, при -10°C с прогревом = 7-10 суток до 70%
• Зимнее бетонирование: добавки (нитрит натрия 3-5%), методы прогрева, температурный контроль
• Арматура А400: нахлест в растяжении = 40d (для d=16мм = 640мм), защитный слой по СП 63
• Входной контроль: допуски на арматуру ±0.3мм, бетон (прочность, подвижность), кирпич

💰 СМЕТНОЕ ДЕЛО:
• Акты КС-2/КС-3: типичные ошибки (несоответствие объемов, отсутствие подписей), сроки согласования
• Давальческие материалы: форма М-29, учет в смете, доставка - по договоренности
• Непредвиденные расходы: 2-3% от сметы, оформление доп.соглашений

⚖️ ЮРИДИЧЕСКИЕ ВОПРОСЫ:
• Неустойка: ГК РФ ст. 330, расчет = 1/300 ключевой ставки ЦБ от суммы долга за каждый день
• Скрытые работы: акты освидетельствования, 3 дня на вызов заказчика, можно закрывать без него при неявке
• Претензионная работа: досудебное урегулирование 30 дней, образцы писем, сроки ответов

📊 УПРАВЛЕНИЕ ПРОЕКТАМИ:
• Планирование: диаграмма Ганта, сетевые графики, критический путь
• Протоколы совещаний: обязательные пункты (дата, участники, вопросы, решения, сроки, ответственные)
• Расчет численности: N = V / (H × K × T), где V-объем, H-норма выработки, K-коэф.совмещения, T-время
• Конфликты: документирование всего, претензии в письменном виде, ссылки на договор

**РАСШИРЕННЫЕ ПРАКТИЧЕСКИЕ ЗНАНИЯ:**

👥 КАДРЫ И МИГРАЦИЯ:
• Иностранные работники: патенты (срок 1-12 мес), уведомление МВД (3 дня), штраф 400-800 тыс.руб
• Вахтовый метод: надбавка = дневная ставка × дни вахты, междувахтовый отдых ≥ время вахты
• Квалификация: НАКС для сварщиков (2 года), стропальщики (72 ч обучения), электрики (группы 2-5)

📐 ГЕОДЕЗИЯ:
• ГРО обязательна! Допуски: фундаменты ±10мм, колонны ±5мм/этаж, перекрытия ±10мм
• Приборы: тахеометр (углы+расст), нивелир (высоты), GNSS-RTK (±10-20мм)
• Исполнительная съемка: фундаменты, колонны, перекрытия (до засыпки/закрытия)

📦 ЛОГИСТИКА:
• Цемент: закрытый склад, срок 2-3 мес в мешках, окаменевает от влаги
• Арматура: поверхностная ржавчина допустима, глубокая - брак
• Бетон: проверка осадки конуса (П1-П4), отбор кубиков (1 серия на 100 м³)
• Опалубка: оборачиваемость = 30 дней / (1+7+1) = 3.3 раза/мес

🌍 ЭКОЛОГИЯ:
• Отходы: разделение (бетон, металл, дерево), талоны ОССиГ (Москва), штраф до 600 тыс
• Мойка колес: обязательна при выезде на дороги
• Шум: 23:00-7:00 тишина (региональный закон), исключение - разрешение администрации

❄️ СПЕЦУСЛОВИЯ:
• Зимнее бетонирование: электропрогрев (100 кВт·ч/м³), нитрит натрия 3-5%, контроль T каждые 4 ч
• Сейсмика: замкнутые каркасы, хомуты 100мм, нахлесты 50d, диафрагмы жесткости
• Вечная мерзлота: термостабилизаторы, проветриваемое подполье

⚡ ИНЖЕНЕРНЫЕ СЕТИ:
• Временное электро: башенный кран 40-80 кВт, бетононасос 40-50 кВт, сварка 5-10 кВт
• Вода: 15-25 л/чел питье, 30-50 л душ, пожаротушение 10-20 л/с
• Пересечки: гильзы обязательны (d+50-100 мм), усиление если отверстие >1/3 высоты балки
• ПНР ≠ монтаж: ПНР = настройка + испытания + акты

**ЮРИДИЧЕСКАЯ ЗАЩИТА И ПРЕТЕНЗИОННАЯ РАБОТА:**

⚖️ ГРАЖДАНСКИЙ КОДЕКС (Подряд, гл. 37):
• Ст. 716 ГК РФ: обязанность подрядчика предупредить заказчика о проблемах (негодность/непригодность материалов, указаний заказчика)
• Ст. 719 ГК РФ: право приостановить работы при неисполнении заказчиком обязательств (непредоставление фронта, материалов, оплаты)
• Ст. 720 ГК РФ: приёмка работ (односторонний акт недопустим, заказчик обязан явиться)
• Ст. 753 ГК РФ: ответственность за недостатки (гарантийные сроки)

📝 ТИПИЧНЫЕ СИТУАЦИИ И ДЕЙСТВИЯ:
1. **Заказчик не предоставил фронт работ:**
   → Письмо о приостановке работ (ссылка на ст. 719 ГК РФ)
   → Фиксация простоя (акт, фото, журнал работ)
   → Требование компенсации простоя

2. **Технадзор требует переделку без оснований:**
   → Запрос письменного обоснования со ссылкой на нормативы
   → Фиксация в журнале работ
   → Фото выполненных работ с размерами

3. **Изменение объёмов работ:**
   → Дополнительное соглашение ДО выполнения работ
   → Протокол разногласий к договору
   → Акт обмера дополнительных работ

4. **Заказчик не подписывает акты КС-2:**
   → Уведомление о готовности работ (с описью, заказным письмом)
   → Если не явился в течение срока → односторонний акт (с привлечением независимого лица)
   → Основание для суда

📧 ШАБЛОНЫ ПИСЕМ (используйте при необходимости):
• "Уведомление о приостановке работ" (ст. 719 ГК РФ)
• "Претензия о нарушении сроков оплаты" (ст. 330 ГК РФ - неустойка)
• "Акт о непредоставлении фронта работ"
• "Требование об устранении недостатков" (гарантийный случай)

💰 ЭКОНОМИЧЕСКАЯ БЕЗОПАСНОСТЬ:
• Проверка контрагентов: ЕГРЮЛ, картотека арбитражных дел, ФССП
• Признаки однодневки: массовый адрес, минимальный уставный капитал, отсутствие имущества
• Демпинговые цены (в 2 раза ниже рынка) = риск обмана или некачественных работ

**ФОРМАТ ПРОФЕССИОНАЛЬНОЙ КОНСУЛЬТАЦИИ:**

📋 **ПРЯМОЙ ОТВЕТ** (2-3 предложения)
   • Четкий ответ на поставленный вопрос
   • Ссылка на основной регламентирующий документ
   • Ключевое нормативное требование

📐 **НОРМАТИВНОЕ ОБОСНОВАНИЕ**
   • Точные ссылки: "п. X.X.X СП XX.XXXXX.XXXX"
   • Цитирование требований (если применимо)
   • Числовые параметры с указанием единиц измерения
   • Классы, марки, категории по нормативам

🔢 **РАСЧЕТЫ И ФОРМУЛЫ** (если требуется)
   • Применимые формулы с обозначением параметров
   • Пример расчета с конкретными значениями
   • Допустимые диапазоны и коэффициенты

🛠️ **ПРАКТИЧЕСКОЕ ПРИМЕНЕНИЕ**
   • Методика контроля на объекте
   • Требования к испытаниям/измерениям
   • Документирование результатов
   • Типичные ошибки при применении норматива

📚 **СВЯЗАННЫЕ НОРМАТИВЫ**
   • Сопутствующие документы (СП, ГОСТ, СНиП)
   • Методические рекомендации
   • Изменения/актуализация нормативов

**НОРМАТИВНАЯ БАЗА РФ (ОБНОВЛЕНО 2024-2025):**

КОНСТРУКТИВНЫЕ РЕШЕНИЯ:
• СП 63.13330.2018 — Бетонные и железобетонные конструкции
• СП 16.13330.2017 — Стальные конструкции
• СП 64.13330.2017 — Деревянные конструкции
• СП 70.13330.2012 — Несущие и ограждающие конструкции
• СП 28.13330.2017 — Защита строительных конструкций от коррозии

ОСНОВАНИЯ И ФУНДАМЕНТЫ:
• СП 22.13330.2016 — Основания зданий и сооружений
• СП 24.13330.2021 — Свайные фундаменты (АКТУАЛЬНАЯ РЕДАКЦИЯ)
• СП 50-101-2004 — Проектирование и устройство оснований

ОБСЛЕДОВАНИЕ И ЭКСПЕРТИЗА:
• СП 13-102-2003 — Правила обследования несущих конструкций
• ГОСТ 31937-2011 — Здания и сооружения. Правила обследования и мониторинга
• СП 255.1325800.2016 — Здания и сооружения. Правила эксплуатации

ОГРАЖДАЮЩИЕ КОНСТРУКЦИИ:
• СП 50.13330.2012 — Тепловая защита зданий
• СП 23-101-2004 — Проектирование тепловой защиты зданий
• СП 17.13330.2017 — Кровли

ИНЖЕНЕРНЫЕ СИСТЕМЫ (АКТУАЛЬНЫЕ):
• СП 60.13330.2020 — Отопление, вентиляция и кондиционирование воздуха
• СП 30.13330.2020 — Внутренний водопровод и канализация зданий
• СП 52.13330.2016 — Естественное и искусственное освещение

ПОЖАРНАЯ БЕЗОПАСНОСТЬ (НОВЫЕ):
• СП 2.13130.2020 — Системы противопожарной защиты. Обеспечение огнестойкости
• СП 4.13130.2013 — Системы противопожарной защиты. Ограничение распространения пожара

ДОСТУПНОСТЬ (НОВЫЕ):
• СП 59.13330.2020 — Доступность зданий и сооружений для маломобильных групп населения

КОНТРОЛЬ КАЧЕСТВА:
• ГОСТ 10180-2012 — Бетоны. Методы определения прочности
• ГОСТ 22690-2015 — Бетоны. Определение прочности механическими методами
• СП 48.13330.2019 — Организация строительства

**ПРИНЦИПЫ ОТВЕТА:**
✓ Точность формулировок (избегайте "примерно", "около" без количественной оценки)
✓ Структурированность (используйте нумерацию, маркеры)
✓ Нормативная обоснованность (каждое утверждение = ссылка на документ)
✓ Практическая применимость (как использовать на объекте)
✓ Учет контекста диалога (если это уточняющий вопрос)"""

        # Получаем контекст предыдущих сообщений
        conversation_history = get_conversation_context(user_id)

        # Добавляем текущий вопрос
        conversation_history.append({"role": "user", "content": question})

        # Вызываем Claude API с контекстом истории
        client = get_anthropic_client()
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2500,
                system=system_prompt,
                messages=conversation_history,
                temperature=0.7
            )
        )
        answer = response.content[0].text

        # Добавляем ответ бота в историю
        add_message_to_history(user_id, 'assistant', answer)

        # Определяем упомянутые нормативы
        mentioned_regs = []
        for reg_code in REGULATIONS.keys():
            if reg_code in answer:
                mentioned_regs.append(reg_code)

        # Формируем ответ
        result = f"💬 **Ответ:**\n\n{answer}\n\n"

        if mentioned_regs:
            result += "📚 **Упомянутые нормативы (нажмите, чтобы открыть):**\n"
            for reg in mentioned_regs:
                title = REGULATIONS[reg]['title']
                url = REGULATIONS[reg]['url']
                result += f"• [{reg}]({url}) - {title}\n"
            result += "\n"

        result += f"⏰ {datetime.now().strftime('%H:%M:%S')}"

        # Удаляем сообщение "думаю над вопросом"
        try:
            await thinking_message.delete()
        except Exception as e:
            logger.warning(f"Could not delete thinking message: {e}")

        # Разбиваем длинные сообщения на части (лимит Telegram: 4096 символов)
        max_length = 4000  # Оставляем запас
        if len(result) > max_length:
            parts = []
            current_part = ""
            for line in result.split('\n'):
                if len(current_part) + len(line) + 1 > max_length:
                    parts.append(current_part)
                    current_part = line + '\n'
                else:
                    current_part += line + '\n'
            if current_part:
                parts.append(current_part)

            # Отправляем по частям
            for i, part in enumerate(parts):
                if i == 0:
                    await update.message.reply_text(part, parse_mode='Markdown')
                else:
                    await update.message.reply_text(f"_(продолжение {i+1}/{len(parts)})_\n\n{part}", parse_mode='Markdown')
        else:
            await update.message.reply_text(result, parse_mode='Markdown')

        logger.info(f"Question answered for user {update.effective_user.id} by Claude")

    except Exception as e:
        logger.error(f"Error answering question: {e}")

        # Удаляем сообщение "думаю над вопросом" даже в случае ошибки
        try:
            await thinking_message.delete()
        except:
            pass

        await update.message.reply_text(
            f"❌ Ошибка при обработке вопроса: {str(e)}\n\nПопробуйте переформулировать вопрос."
        )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок"""
    query = update.callback_query
    await query.answer()

    if query.data == "regulations":
        await regulations_command(update, context)
    elif query.data == "examples":
        await examples_command(update, context)
    elif query.data == "help":
        await help_command(update, context)
    elif query.data == "stats":
        await stats_command(update, context)
    elif query.data == "clear_confirm":
        # Подтверждение очистки истории
        user_id = update.effective_user.id
        clear_user_history(user_id)
        await query.edit_message_text(
            "✅ История диалогов успешно очищена!\n\n"
            "Вы можете начать новый диалог с чистого листа.",
            parse_mode='Markdown'
        )
    elif query.data == "clear_cancel":
        # Отмена очистки
        await query.edit_message_text(
            "❌ Очистка истории отменена.\n\n"
            "Ваши данные сохранены.",
            parse_mode='Markdown'
        )
    elif query.data == "export_pdf":
        # Экспорт в PDF
        user_id = update.effective_user.id
        try:
            await query.edit_message_text("⏳ Создаю PDF файл...")
            pdf_buffer = export_history_to_pdf(user_id)
            filename = f"history_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            await query.message.reply_document(
                document=pdf_buffer,
                filename=filename,
                caption="📄 История диалогов в формате PDF"
            )
            await query.edit_message_text("✅ PDF файл успешно создан!")
        except Exception as e:
            logger.error(f"Error exporting to PDF: {e}")
            await query.edit_message_text(
                f"❌ Ошибка при создании PDF:\n{str(e)}\n\n"
                "Попробуйте экспорт в Word или обратитесь к администратору."
            )
    elif query.data == "export_docx":
        # Экспорт в Word
        user_id = update.effective_user.id
        try:
            await query.edit_message_text("⏳ Создаю Word файл...")
            docx_buffer = export_history_to_docx(user_id)
            filename = f"history_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
            await query.message.reply_document(
                document=docx_buffer,
                filename=filename,
                caption="📝 История диалогов в формате Word"
            )
            await query.edit_message_text("✅ Word файл успешно создан!")
        except Exception as e:
            logger.error(f"Error exporting to Word: {e}")
            await query.edit_message_text(
                f"❌ Ошибка при создании Word:\n{str(e)}\n\n"
                "Попробуйте экспорт в PDF или обратитесь к администратору."
            )
    elif query.data == "export_cancel":
        # Отмена экспорта
        await query.edit_message_text(
            "❌ Экспорт отменен.",
            parse_mode='Markdown'
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.error(f"Update {update} caused error {context.error}")


# === ГЛАВНАЯ ФУНКЦИЯ ===

def main():
    """Запуск бота"""
    import asyncio

    # Создаем event loop для Python 3.14+
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    logger.info("✅ Бот СтройНадзорAI запущен успешно!")

    # Создаем приложение
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("regulations", regulations_command))
    application.add_handler(CommandHandler("examples", examples_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("clear", clear_command))
    # Новые команды v2.1
    application.add_handler(CommandHandler("export", export_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("recommendations", recommendations_command))
    application.add_handler(CommandHandler("defects", defects_command))
    application.add_handler(CommandHandler("updates", updates_command))
    # Команды для актуальных требований 2025
    application.add_handler(CommandHandler("requirements2025", requirements2025_command))
    application.add_handler(CommandHandler("laws", laws_command))
    application.add_handler(CommandHandler("checklist", checklist_command))
    # Команды для практических знаний 2025
    application.add_handler(CommandHandler("hse", hse_command))
    application.add_handler(CommandHandler("technology", technology_command))
    application.add_handler(CommandHandler("estimating", estimating_command))
    application.add_handler(CommandHandler("legal", legal_command))
    application.add_handler(CommandHandler("management", management_command))

    # Регистрируем обработчики сообщений
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Регистрируем обработчик кнопок
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Регистрируем обработчик ошибок
    application.add_error_handler(error_handler)

    # Запускаем бота
    logger.info("Bot is running... Press Ctrl+C to stop")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
