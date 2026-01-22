"""
Telegram бот СтройНадзорAI - AI консультант по строительным нормативам
С поддержкой технического анализа фотографий
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

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, BotCommand, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
import asyncio

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
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

# ============================================================================
# ОПТИМИЗАЦИЯ: Умный выбор моделей AI
# ============================================================================
try:
    from model_selector import ModelSelector, should_use_web_search, extract_regulation_codes
    MODEL_SELECTOR_AVAILABLE = True
    logger.info("✅ ModelSelector загружен - умный выбор AI моделей активен")
except ImportError:
    MODEL_SELECTOR_AVAILABLE = False
    logger.warning("⚠️ model_selector.py не найден - используется только Grok")

try:
    from optimized_prompts import (
        CLAUDE_SYSTEM_PROMPT_TECHNICAL,
        CLAUDE_DALLE_PROMPT_CREATOR,
        GROK_SYSTEM_PROMPT_GENERAL,
        GEMINI_VISION_PROMPT_DEFECTS
    )
    OPTIMIZED_PROMPTS_AVAILABLE = True
    logger.info("✅ Оптимизированные промпты загружены")
except ImportError:
    OPTIMIZED_PROMPTS_AVAILABLE = False
    logger.warning("⚠️ optimized_prompts.py не найден - используются стандартные промпты")

try:
    from optimized_handlers import (
        handle_with_claude_technical,
        handle_with_gemini_vision,
        handle_with_gemini_image,
        handle_with_grok
    )
    OPTIMIZED_HANDLERS_AVAILABLE = True
    logger.info("✅ Оптимизированные обработчики загружены (Claude, Gemini Vision, Gemini Image, Grok)")
except ImportError:
    OPTIMIZED_HANDLERS_AVAILABLE = False
    logger.warning("⚠️ optimized_handlers.py не найден - используются стандартные обработчики")

try:
    from smart_model_wrapper import smart_model_selection_text, smart_model_selection_photo
    SMART_WRAPPER_AVAILABLE = True
    logger.info("✅ Smart wrapper загружен - умный выбор моделей активен!")
except ImportError:
    SMART_WRAPPER_AVAILABLE = False
    logger.warning("⚠️ smart_model_wrapper.py не найден")

# Импорт справочника строителя
try:
    from builder_reference import (
        get_builder_skills_context,
        search_builder_reference,
        is_builder_question,
        BUILDER_TOPICS
    )
    BUILDER_REFERENCE_AVAILABLE = True
    logger.info("✅ Справочник строителя загружен")
except ImportError:
    BUILDER_REFERENCE_AVAILABLE = False
    logger.warning("⚠️ Файл builder_reference.py не найден")

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

# PostgreSQL Database
try:
    from database import (
        init_db,
        save_message,
        get_user_messages,
        search_messages as db_search_messages,
        get_user_tags,
        clear_user_history as db_clear_history,
        get_total_messages,
        close_db
    )
    DATABASE_AVAILABLE = True
    logger.info("✅ PostgreSQL модуль загружен")
except ImportError:
    DATABASE_AVAILABLE = False
    logger.warning("⚠️ PostgreSQL не доступен, используется JSON")

# Улучшения v3.0
try:
    from improvements_v3 import (
        create_answer_buttons,
        create_quick_actions_menu,
        create_reply_suggestions_keyboard,
        create_calculators_menu,
        create_regulations_category_menu,
        create_region_selection_menu,
        create_related_questions_buttons,
        generate_smart_related_questions_prompt,
        parse_generated_questions,
        get_improved_help_text,
        REGULATIONS_CATEGORIES,
        CALCULATORS,
        REGIONS
    )
    IMPROVEMENTS_V3_AVAILABLE = True
    logger.info("✅ Модуль улучшений v3.0 загружен")
except ImportError:
    IMPROVEMENTS_V3_AVAILABLE = False
    logger.warning("⚠️ Модуль improvements_v3.py не найден")

# Калькуляторы
try:
    from calculators import (
        calculate_concrete,
        calculate_reinforcement,
        calculate_formwork,
        calculate_electrical,
        calculate_water,
        calculate_winter_heating,
        calculate_brick,
        calculate_tile,
        calculate_paint,
        calculate_wall_area,
        calculate_roof,
        calculate_plaster,
        calculate_wallpaper,
        calculate_laminate,
        calculate_insulation,
        calculate_foundation,
        calculate_stairs,
        calculate_drywall,
        calculate_earthwork,
        calculate_labor,
        format_calculator_result
    )
    CALCULATORS_AVAILABLE = True
    logger.info("✅ Модуль калькуляторов загружен (21 калькулятор)")
except ImportError:
    CALCULATORS_AVAILABLE = False
    logger.warning("⚠️ Модуль calculators.py не найден")

# Интерактивные обработчики калькуляторов v4.0
try:
    from calculator_handlers import (
        create_concrete_calculator_handler,
        create_rebar_calculator_handler,
        create_formwork_calculator_handler,
        create_electrical_calculator_handler,
        create_water_calculator_handler,
        create_winter_calculator_handler,
        create_math_calculator_handler,
        create_brick_calculator_handler,
        create_tile_calculator_handler,
        create_paint_calculator_handler,
        create_wall_area_calculator_handler,
        create_roof_calculator_handler,
        create_plaster_calculator_handler,
        create_wallpaper_calculator_handler,
        create_laminate_calculator_handler,
        create_insulation_calculator_handler,
        create_foundation_calculator_handler,
        create_stairs_calculator_handler,
        create_drywall_calculator_handler,
        create_earthwork_calculator_handler,
        create_labor_calculator_handler,
        quick_concrete,
        quick_math
    )
    CALCULATOR_HANDLERS_AVAILABLE = True
    logger.info("✅ Интерактивные калькуляторы v4.0 (все 21) загружены")
except ImportError:
    CALCULATOR_HANDLERS_AVAILABLE = False
    logger.warning("⚠️ Модуль calculator_handlers.py не найден")

# Интерактивные обработчики документов v1.0
try:
    from document_handlers import (
        create_acceptance_foundation_handler,
        create_complaint_contractor_handler,
        create_safety_plan_handler,
        create_hidden_works_act_handler,
    )
    DOCUMENT_HANDLERS_AVAILABLE = True
    logger.info("✅ Интерактивные обработчики документов v1.0 (все 4) загружены")
except ImportError as e:
    DOCUMENT_HANDLERS_AVAILABLE = False
    logger.warning(f"⚠️ Модуль document_handlers.py не найден: {e}")

# Модуль веб-поиска нормативов
try:
    from web_search import perform_web_search, should_perform_web_search
    WEB_SEARCH_AVAILABLE = True
    logger.info("✅ Модуль веб-поиска нормативов загружен (docs.cntd.ru, minstroyrf.gov.ru)")
except ImportError as e:
    WEB_SEARCH_AVAILABLE = False
    logger.warning(f"⚠️ Модуль web_search.py не найден: {e}")

# Модуль погоды (Яндекс Погода API)
try:
    from weather import get_weather, is_weather_query
    WEATHER_AVAILABLE = True
    logger.info("✅ Модуль погоды загружен (Яндекс Погода API)")
except ImportError as e:
    WEATHER_AVAILABLE = False
    logger.warning(f"⚠️ Модуль weather.py не найден: {e}")

# Модуль генерации изображений
try:
    from image_generator import (
        generate_construction_image,
        should_generate_image,
        format_generation_result
    )
    IMAGE_GENERATION_AVAILABLE = True
    logger.info("✅ Модуль генерации изображений загружен (Gemini AI)")
except ImportError as e:
    IMAGE_GENERATION_AVAILABLE = False
    logger.warning(f"⚠️ Модуль image_generator.py не найден: {e}")

# Gemini Vision для анализа изображений v4.0
try:
    from gemini_vision import (
        initialize_gemini_vision,
        is_gemini_available,
        analyze_construction_image
    )
    gemini_vision_analyzer = initialize_gemini_vision()
    GEMINI_VISION_AVAILABLE = is_gemini_available()
    if GEMINI_VISION_AVAILABLE:
        logger.info("✅ Gemini 2.5 Flash Vision загружен (анализ фото)")
    else:
        logger.warning("⚠️ Gemini Vision недоступен (нужен GEMINI_API_KEY)")
except ImportError as e:
    GEMINI_VISION_AVAILABLE = False
    gemini_vision_analyzer = None
    logger.warning(f"⚠️ Модуль gemini_vision.py не найден: {e}")

# Режим разработчика v3.0 - автовыбор локальной/облачной версии
is_developer = None
try:
    # Сначала пробуем загрузить ЛОКАЛЬНУЮ версию (с git автопушем)
    from dev_mode_local import create_dev_mode_handler, is_developer
    DEV_MODE_AVAILABLE = True
    logger.info("✅ Режим разработчика v3.0 ЛОКАЛЬНЫЙ загружен (с git автопушем)")
except ImportError:
    try:
        # Если не получилось (нет git) - загружаем ОБЛАЧНУЮ версию (только анализ)
        from dev_mode import create_dev_mode_handler, is_developer
        DEV_MODE_AVAILABLE = True
        logger.info("✅ Режим разработчика v2.0 ОБЛАЧНЫЙ загружен (без git)")
    except ImportError as e:
        DEV_MODE_AVAILABLE = False
        is_developer = lambda user_id: False  # Заглушка, если модули не загружены
        logger.warning(f"⚠️ Модули dev_mode не найдены: {e}")

# Автоприменение изменений v1.0 - кнопка "Применить изменения" после ответов
try:
    from auto_apply import add_apply_button, should_show_apply_button, handle_apply_changes
    AUTO_APPLY_AVAILABLE = True
    logger.info("✅ Автоприменение изменений v1.0 загружено")
except ImportError as e:
    AUTO_APPLY_AVAILABLE = False
    logger.warning(f"⚠️ Модуль auto_apply.py не найден: {e}")

# Предложения по улучшению v1.0
try:
    from suggestions import suggestions_menu, create_suggestions_handler
    SUGGESTIONS_AVAILABLE = True
    logger.info("✅ Модуль предложений v1.0 загружен")
except ImportError as e:
    SUGGESTIONS_AVAILABLE = False
    logger.warning(f"⚠️ Модуль suggestions.py не найден: {e}")

# Обработчик голосовых сообщений v3.9
try:
    from voice_handler import process_voice_message
    VOICE_HANDLER_AVAILABLE = True
    logger.info("✅ Обработчик голосовых сообщений v3.9 загружен")
except ImportError:
    VOICE_HANDLER_AVAILABLE = False
    logger.warning("⚠️ Модуль voice_handler.py не найден")

# Шаблоны документов v3.9
try:
    from document_templates import DOCUMENT_TEMPLATES, generate_document
    TEMPLATES_AVAILABLE = True
    logger.info(f"✅ Шаблоны документов v3.9 загружены ({len(DOCUMENT_TEMPLATES)} шаблонов)")
except ImportError:
    TEMPLATES_AVAILABLE = False
    logger.warning("⚠️ Модуль document_templates.py не найден")

# Управление проектами v3.9
try:
    from project_manager import get_user_projects, create_project, load_project, Project
    PROJECTS_AVAILABLE = True
    logger.info("✅ Управление проектами v3.9 загружено")
except ImportError:
    PROJECTS_AVAILABLE = False
    logger.warning("⚠️ Модуль project_manager.py не найден")

# Режимы работы по ролям v3.2
try:
    from role_modes import (
        role_command,
        handle_role_selection,
        get_user_role,
        get_role_system_prompt
    )
    ROLES_AVAILABLE = True
    logger.info("✅ Режимы работы по ролям v3.2 загружены")
except ImportError:
    ROLES_AVAILABLE = False
    logger.warning("⚠️ Модуль role_modes.py не найден")

# Управление историей v3.5
try:
    from history_manager import (
        history_command,
        stats_command,
        search_command,
        export_command,
        clear_history_command,
        handle_history_callback
    )
    HISTORY_MANAGER_AVAILABLE = True
    logger.info("✅ Управление историей v3.5 загружено (поиск + экспорт)")
except ImportError:
    HISTORY_MANAGER_AVAILABLE = False
    logger.warning("⚠️ Модуль history_manager.py не найден")

# Сохранённые расчёты v3.6
try:
    from saved_calculations import (
        saved_command,
        handle_saved_callback
    )
    SAVED_CALCS_AVAILABLE = True
    logger.info("✅ Сохранённые расчёты v3.6 загружены")
except ImportError:
    SAVED_CALCS_AVAILABLE = False
    logger.warning("⚠️ Модуль saved_calculations.py не найден")

# База часто задаваемых вопросов (FAQ) v3.7
try:
    from faq import (
        faq_command,
        faq_search_command,
        handle_faq_callback,
        get_total_faq_count
    )
    FAQ_AVAILABLE = True
    logger.info("✅ FAQ v3.7 загружен")
except ImportError:
    FAQ_AVAILABLE = False
    logger.warning("⚠️ Модуль faq.py не найден")

# Кэширование ответов v3.8
try:
    from cache_manager import (
        init_cache,
        close_cache,
        get_cached_answer,
        set_cached_answer,
        find_similar_cached_question,
        get_cache_stats
    )
    CACHE_AVAILABLE = True
    logger.info("✅ Cache manager v3.8 загружен")
except ImportError:
    CACHE_AVAILABLE = False
    logger.warning("⚠️ Модуль cache_manager.py не найден")

# Планировщик работ v3.8
try:
    from work_planner import (
        planner_command,
        plan_calc_command,
        handle_planner_callback
    )
    PLANNER_AVAILABLE = True
    logger.info("✅ Work planner v3.8 загружен")
except ImportError:
    PLANNER_AVAILABLE = False
    logger.warning("⚠️ Модуль work_planner.py не найден")

# Gemini Image Generation (новый API с реальной генерацией изображений)
try:
    from gemini_image_gen import (
        initialize_gemini_generator,
        GeminiImageGenerator,
        generate_construction_image_gemini,
        is_image_generation_available
    )
    GEMINI_AVAILABLE = True
    logger.info("✅ Gemini Image Generator модуль загружен (с поддержкой генерации)")
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("⚠️ Модуль gemini_image_gen.py не найден")

# Оптимизированные промпты и селектор моделей v5.0
try:
    from optimized_prompts import (
        CLAUDE_SYSTEM_PROMPT_TECHNICAL,
        GROK_SYSTEM_PROMPT_GENERAL,
        GEMINI_IMAGE_PROMPT_SYSTEM,
        GEMINI_VISION_PROMPT_DEFECTS,
        WEB_SEARCH_DECISION_PROMPT
    )
    from model_selector import ModelSelector
    OPTIMIZED_PROMPTS_AVAILABLE = True
    model_selector = ModelSelector()
    logger.info("✅ Оптимизированные промпты и селектор моделей v5.0 загружены")
except ImportError as e:
    OPTIMIZED_PROMPTS_AVAILABLE = False
    model_selector = None
    logger.warning(f"⚠️ Модули optimized_prompts/model_selector не найдены: {e}")

# Интерактивные калькуляторы v4.0 - УДАЛЁН дублирующий импорт
# Все калькуляторы импортируются из calculator_handlers.py (строка 257)
# interactive_calculators.py - устаревший модуль, не используется
INTERACTIVE_CALCS_AVAILABLE = True  # Калькуляторы доступны через calculator_handlers

# Категоризация нормативов v1.0
try:
    from regulations_categories import (
        get_categories_keyboard,
        get_regulations_by_category,
        search_regulations_by_keyword,
        get_all_regulations_text
    )
    REGULATIONS_CATEGORIES_AVAILABLE = True
    logger.info("✅ Категоризация нормативов v1.0 загружена")
except ImportError:
    REGULATIONS_CATEGORIES_AVAILABLE = False
    logger.warning("⚠️ Модуль regulations_categories.py не найден")

# Контекстные подсказки v1.0
try:
    from context_hints import (
        is_short_question,
        get_context_hints,
        format_hint_response
    )
    CONTEXT_HINTS_AVAILABLE = True
    logger.info("✅ Контекстные подсказки v1.0 загружены")
except ImportError:
    CONTEXT_HINTS_AVAILABLE = False
    logger.warning("⚠️ Модуль context_hints.py не найден")

# Импорт xAI клиента
from xai_client import XAIClient, call_xai_with_retry

# Импорт Gemini Live API (голосовой ассистент)
try:
    from gemini_live_bot_integration import start_voice_chat_command
    VOICE_ASSISTANT_AVAILABLE = True
    logger.info("✅ Gemini Live API (голосовой ассистент) загружен")
except ImportError as e:
    VOICE_ASSISTANT_AVAILABLE = False
    logger.warning(f"⚠️ Gemini Live API недоступен: {e}")

# Импорт OpenAI Realtime API (альтернативный голосовой ассистент)
try:
    from openai_realtime_bot_integration import start_realtime_chat_command
    OPENAI_REALTIME_AVAILABLE = True
    logger.info("✅ OpenAI Realtime API (голосовой ассистент) загружен")
except ImportError as e:
    OPENAI_REALTIME_AVAILABLE = False
    logger.warning(f"⚠️ OpenAI Realtime API недоступен: {e}")

# LLM Council - Совет AI моделей для сложных вопросов (Karpathy's approach)
try:
    from llm_council import (
        LLMCouncil,
        get_llm_council,
        is_council_available,
        is_complex_question
    )
    LLM_COUNCIL_AVAILABLE = is_council_available()
    if LLM_COUNCIL_AVAILABLE:
        logger.info("✅ LLM Council загружен (Grok + Claude + Gemini)")
    else:
        logger.warning("⚠️ LLM Council недоступен (нужно минимум 2 AI модели)")
except ImportError as e:
    LLM_COUNCIL_AVAILABLE = False
    logger.warning(f"⚠️ Модуль llm_council.py не найден: {e}")

# Токены (загружаются из .env файла)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Проверка наличия токенов
if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN не найден в .env файле!")
if not XAI_API_KEY:
    raise ValueError("❌ XAI_API_KEY не найден в .env файле!")
if not ANTHROPIC_API_KEY:
    logger.warning("⚠️ ANTHROPIC_API_KEY не найден - функции Claude будут недоступны")

# Инициализация xAI клиента
grok_client = None

def get_grok_client():
    """Получить xAI Grok клиент (ленивая инициализация)"""
    global grok_client
    if grok_client is None:
        grok_client = XAIClient(api_key=XAI_API_KEY)
    return grok_client

# Инициализация Gemini генератора
gemini_generator = None

def get_gemini_generator():
    """Получить Gemini генератор (ленивая инициализация)"""
    global gemini_generator
    if gemini_generator is None and GEMINI_AVAILABLE:
        gemini_generator = initialize_gemini_generator()
    return gemini_generator


# === RATE LIMITING СИСТЕМА ===

# Хранилище времени запросов пользователей
user_request_times = defaultdict(list)

# Настройки rate limiting
RATE_LIMIT_MAX_REQUESTS = 10  # Максимум запросов
RATE_LIMIT_WINDOW_SECONDS = 60  # За 60 секунд

# 🎯 НАСТРОЙКА STREAMING РЕЖИМА
# True = ответы появляются постепенно (как в ChatGPT)
# False = ответы приходят сразу целиком (классический режим)
STREAMING_ENABLED = False  # По умолчанию ВЫКЛЮЧЕН

# 🤖 КОНФИГУРАЦИЯ AI МОДЕЛЕЙ (xAI Grok)
# Основная модель: grok-4-1-fast
#   - Улучшенная reasoning способность для глубокого анализа
#   - Используется для технических вопросов, анализа фото и документов
#   - Более точные и профессиональные ответы
# Быстрая модель: grok-4-1-fast
#   - Для классификации запросов и простых вопросов
#   - Быстрая генерация ответов
# Fallback: Claude Sonnet 4.5 (при недоступности Grok)

def check_rate_limit(user_id: int) -> bool:
    """
    Проверка rate limit для пользователя
    Returns: True если запрос разрешен, False если превышен лимит
    """
    now = datetime.now()
    cutoff = now - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)

    # Очистка старых запросов
    user_request_times[user_id] = [
        t for t in user_request_times[user_id] if t > cutoff
    ]

    # Проверка лимита
    if len(user_request_times[user_id]) >= RATE_LIMIT_MAX_REQUESTS:
        logger.warning(f"Rate limit exceeded for user {user_id}")
        return False

    # Добавляем новый запрос
    user_request_times[user_id].append(now)
    return True


# === УЛУЧШЕННАЯ ОБРАБОТКА AI API С FALLBACK НА CLAUDE ===

import time
from anthropic import Anthropic

# Инициализация Claude клиента (резервный)
claude_client = None

def get_claude_client():
    """Получить Claude клиент (ленивая инициализация)"""
    global claude_client
    if claude_client is None and ANTHROPIC_API_KEY:
        claude_client = Anthropic(api_key=ANTHROPIC_API_KEY)
    return claude_client

def call_grok_with_retry(client, model, messages, max_tokens, temperature, search_parameters=None):
    """
    Вызов xAI Grok API с автоматическим fallback на Claude при сбое

    Логика:
    1. Пытается использовать xAI Grok (основной)
    2. Если ошибка - автоматически переключается на Claude (резерв)
    3. Логирует какой API был использован

    Args:
        search_parameters: Параметры поиска {"mode": "auto", "return_citations": True, "sources": [{"type": "web"}, {"type": "news"}, {"type": "x"}]}]
    """
    # Сначала пытаемся Grok
    try:
        response = call_xai_with_retry(
            client=client,
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            search_parameters=search_parameters
        )
        logger.info("✅ Ответ получен от xAI Grok")
        return response
    except Exception as grok_error:
        logger.warning(f"⚠️ xAI Grok недоступен: {str(grok_error)}")

        # Fallback на Claude
        if not ANTHROPIC_API_KEY:
            logger.error("❌ Claude API также недоступен (нет ключа)")
            raise Exception("⚠️ AI сервисы временно недоступны. Попробуйте позже.")

        try:
            logger.info("🔄 Переключение на Claude Sonnet 4.5 (резерв)...")
            claude = get_claude_client()

            # Преобразуем формат messages для Claude
            claude_messages = []
            system_prompt = None

            for msg in messages:
                if msg.get("role") == "system":
                    system_prompt = msg.get("content")
                else:
                    claude_messages.append(msg)

            # Вызываем Claude
            claude_response = claude.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else "Вы — эксперт по строительным нормативам РФ.",
                messages=claude_messages
            )

            # Преобразуем ответ Claude в формат совместимый с Grok
            response = {
                "choices": [{
                    "message": {
                        "content": claude_response.content[0].text
                    }
                }]
            }

            logger.info("✅ Ответ получен от Claude Sonnet 4.5 (резерв)")
            return response

        except Exception as claude_error:
            logger.error(f"❌ Claude также недоступен: {str(claude_error)}")
            raise Exception("⚠️ Оба AI сервиса (Grok и Claude) временно недоступны. Попробуйте позже.")


async def call_grok_with_streaming(client, model, messages, max_tokens, temperature, search_parameters=None):
    """
    Вызов xAI Grok API с streaming режимом (постепенная отдача ответа)

    Args:
        client: XAIClient instance
        model: Модель для использования
        messages: Список сообщений
        max_tokens: Максимум токенов
        temperature: Температура
        search_parameters: Параметры поиска {"mode": "auto", "return_citations": True, "sources": [{"type": "web"}, {"type": "news"}, {"type": "x"}]}]

    Yields:
        str - части текста по мере получения от API
    """
    try:
        # Используем streaming метод xAI
        async for chunk in client.chat_completions_create_stream(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            search_parameters=search_parameters
        ):
            yield chunk

    except Exception as grok_error:
        logger.warning(f"⚠️ xAI Grok streaming недоступен: {str(grok_error)}")

        # Fallback на обычный режим без streaming
        logger.info("🔄 Переключение на обычный режим без streaming...")
        response = call_grok_with_retry(
            client=client,
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            search_parameters=search_parameters
        )
        # Отдаём весь ответ целиком
        yield response["choices"][0]["message"]["content"]


# === СИСТЕМА КЛАССИФИКАЦИИ НАМЕРЕНИЙ (INTENT CLASSIFICATION) ===

def classify_user_intent(user_message: str) -> dict:
    """
    Быстрая классификация намерения пользователя с помощью Haiku.
    Возвращает тип запроса для выбора оптимальной модели.

    Типы:
    - simple_save: сохранение, подтверждение, простая фиксация
    - simple_question: простой вопрос, требующий краткого ответа
    - technical_question: технический вопрос, требующий экспертизы
    - complex_analysis: сложный анализ, расчеты, детальная экспертиза
    """
    try:
        client = get_grok_client()

        classification_prompt = f"""Определи тип запроса пользователя. Ответь ТОЛЬКО одним словом:

ТИПЫ ЗАПРОСОВ:
- simple_save: если пользователь просит сохранить, зафиксировать, записать информацию, или просто подтверждает ("да", "ок", "сохрани")
- simple_question: простой вопрос, требующий краткого ответа без глубокой технической экспертизы
- technical_question: технический вопрос по нормативам, СНиП, расчетам, требующий ссылок на документы
- complex_analysis: сложная задача с расчетами, многофакторным анализом, детальной экспертизой

Запрос пользователя: "{user_message}"

Ответь ТОЛЬКО одним словом из списка выше:"""

        response = call_grok_with_retry(
            client,
            model="grok-4-1-fast",  # Быстрая модель для классификации
            max_tokens=50,
            temperature=0.1,
            messages=[{"role": "user", "content": classification_prompt}]
        )

        intent_type = response["choices"][0]["message"]["content"].strip().lower()

        # Валидация ответа
        valid_types = ["simple_save", "simple_question", "technical_question", "complex_analysis"]
        if intent_type not in valid_types:
            # По умолчанию считаем технический вопрос
            intent_type = "technical_question"

        # Выбор модели на основе типа запроса
        if intent_type == "simple_save" or intent_type == "simple_question":
            model = "grok-4-1-fast"  # Быстрая модель для простых запросов
            max_tokens = 1000
        elif intent_type == "technical_question":
            model = "grok-4-1-fast"  # Reasoning модель для технических вопросов
            max_tokens = 5000
        else:  # complex_analysis
            model = "grok-4-1-fast"  # Reasoning модель для сложного анализа
            max_tokens = 8000

        logger.info(f"📊 Intent: {intent_type} → Model: {model}")

        return {
            "intent": intent_type,
            "model": model,
            "max_tokens": max_tokens
        }

    except Exception as e:
        logger.error(f"Error in intent classification: {e}")
        # При ошибке используем Grok Reasoning для надежности
        return {
            "intent": "technical_question",
            "model": "grok-4-1-fast",
            "max_tokens": 5000
        }


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

async def add_message_to_history_async(user_id: int, role: str, content: str, image_analyzed: bool = False):
    """Добавить сообщение в историю (PostgreSQL с fallback на JSON)"""
    # Извлекаем теги
    tags = extract_tags_from_message(content)

    # Сохраняем в PostgreSQL если доступен
    if DATABASE_AVAILABLE:
        try:
            await save_message(user_id, role, content, image_analyzed, tags)
            # Обновляем in-memory кеш
            load_user_history(user_id)
            message = {
                'role': role,
                'content': content,
                'timestamp': datetime.now().isoformat(),
                'image_analyzed': image_analyzed,
                'tags': tags
            }
            user_conversations[user_id].append(message)
            if len(user_conversations[user_id]) > 50:
                user_conversations[user_id] = user_conversations[user_id][-50:]
            return
        except Exception as e:
            logger.error(f"PostgreSQL save failed, falling back to JSON: {e}")

    # Fallback на JSON
    load_user_history(user_id)
    message = {
        'role': role,
        'content': content,
        'timestamp': datetime.now().isoformat(),
        'image_analyzed': image_analyzed,
        'tags': tags
    }
    user_conversations[user_id].append(message)
    if len(user_conversations[user_id]) > 50:
        user_conversations[user_id] = user_conversations[user_id][-50:]
    save_user_history(user_id)

def add_message_to_history(user_id: int, role: str, content: str, image_analyzed: bool = False):
    """Синхронная обертка для совместимости"""
    load_user_history(user_id)
    tags = extract_tags_from_message(content)
    message = {
        'role': role,
        'content': content,
        'timestamp': datetime.now().isoformat(),
        'image_analyzed': image_analyzed,
        'tags': tags
    }
    user_conversations[user_id].append(message)
    if len(user_conversations[user_id]) > 50:
        user_conversations[user_id] = user_conversations[user_id][-50:]
    save_user_history(user_id)

def get_conversation_context(user_id: int) -> list:
    """Получить контекст диалога для Claude API (последние N сообщений)"""
    load_user_history(user_id)

    # Берём последние MAX_CONTEXT_MESSAGES сообщений
    recent_messages = user_conversations[user_id][-MAX_CONTEXT_MESSAGES:]

    # Преобразуем в формат Claude API
    grok_messages = []
    for msg in recent_messages:
        # Пропускаем сообщения с изображениями (они уже обработаны)
        if not msg.get('image_analyzed', False):
            grok_messages.append({
                'role': msg['role'],
                'content': msg['content']
            })

    return grok_messages

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

    # Извлекаем ключевые слова
    keywords = {
        'бетон': 'материал:бетон',
        'арматура': 'материал:арматура',
        'фундамент': 'конструкция:фундамент',
        'кровля': 'конструкция:кровля',
        'стена': 'конструкция:стена',
        'перекрытие': 'конструкция:перекрытие'
    }

    content_lower = content.lower()
    for keyword, tag in keywords.items():
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


# База нормативов с URL-ссылками на первоисточники (обновлено 26.11.2025 - проверено на docs.cntd.ru)
REGULATIONS = {
    # === КОНСТРУКТИВНЫЕ РЕШЕНИЯ ===

    "СП 63.13330.2018": {
        "title": "Бетонные и железобетонные конструкции. Основные положения",
        "url": "https://docs.cntd.ru/document/554403082",
        "year": "2018",
        "status": "Действует",
        "category": "Конструкции",
        "replaced": "СНиП 52-01-2003"
    },

    "СП 16.13330.2017": {
        "title": "Стальные конструкции",
        "url": "https://docs.cntd.ru/document/456044318",
        "year": "2017",
        "status": "Действует",
        "category": "Конструкции",
        "replaced": "СНиП II-23-81*"
    },

    "СП 64.13330.2017": {
        "title": "Деревянные конструкции",
        "url": "https://docs.cntd.ru/document/456069590",
        "year": "2017",
        "status": "Действует",
        "category": "Конструкции",
        "replaced": "СНиП II-25-80"
    },

    "СП 15.13330.2020": {
        "title": "Каменные и армокаменные конструкции",
        "url": "https://docs.cntd.ru/document/573659385",
        "year": "2020",
        "status": "Действует",
        "category": "Конструкции",
        "replaced": "СП 15.13330.2012"
    },

    "СП 28.13330.2017": {
        "title": "Защита строительных конструкций от коррозии",
        "url": "https://docs.cntd.ru/document/456054198",
        "year": "2017",
        "status": "Действует",
        "category": "Защита конструкций"
    },

    "СП 266.1325800.2016": {
        "title": "Конструкции сталежелезобетонные",
        "url": "https://docs.cntd.ru/document/456069588",
        "year": "2016",
        "status": "Действует",
        "category": "Конструкции"
    },

    # === ОСНОВАНИЯ И ФУНДАМЕНТЫ ===

    "СП 22.13330.2016": {
        "title": "Основания зданий и сооружений",
        "url": "https://docs.cntd.ru/document/456054206",
        "year": "2016",
        "status": "Действует",
        "category": "Фундаменты",
        "replaced": "СНиП 2.02.01-83*"
    },

    "СП 24.13330.2021": {
        "title": "Свайные фундаменты",
        "url": "https://docs.cntd.ru/document/1200177001",
        "year": "2021",
        "status": "Действует",
        "category": "Фундаменты",
        "replaced": "СП 24.13330.2011"
    },

    "СП 50-101-2004": {
        "title": "Проектирование и устройство оснований и фундаментов зданий и сооружений",
        "url": "https://docs.cntd.ru/document/1200035505",
        "year": "2004",
        "status": "Действует",
        "category": "Фундаменты"
    },

    "СП 45.13330.2017": {
        "title": "Земляные сооружения, основания и фундаменты",
        "url": "https://docs.cntd.ru/document/456069576",
        "year": "2017",
        "status": "Действует",
        "category": "Фундаменты"
    },

    # === ОБСЛЕДОВАНИЕ И МОНИТОРИНГ ===

    "СП 13-102-2003": {
        "title": "Правила обследования несущих строительных конструкций зданий и сооружений",
        "url": "https://docs.cntd.ru/document/1200035173",
        "year": "2003",
        "status": "Действует",
        "category": "Обследование"
    },

    "ГОСТ 31937-2011": {
        "title": "Здания и сооружения. Правила обследования и мониторинга технического состояния",
        "url": "https://docs.cntd.ru/document/1200100941",
        "year": "2011",
        "status": "Действует",
        "category": "Обследование"
    },

    "СП 255.1325800.2016": {
        "title": "Здания и сооружения. Правила эксплуатации. Основные положения",
        "url": "https://docs.cntd.ru/document/456050595",
        "year": "2016",
        "status": "Действует",
        "category": "Эксплуатация"
    },

    # === ТЕПЛОТЕХНИКА ===

    "СП 50.13330.2012": {
        "title": "Тепловая защита зданий",
        "url": "https://docs.cntd.ru/document/1200095525",
        "year": "2012",
        "status": "Действует (с изм. 2015)",
        "category": "Теплотехника",
        "replaced": "СНиП 23-02-2003"
    },

    "СП 23-101-2004": {
        "title": "Проектирование тепловой защиты зданий",
        "url": "https://docs.cntd.ru/document/1200035109",
        "year": "2004",
        "status": "Действует",
        "category": "Теплотехника"
    },

    # === КРОВЛИ И ГИДРОИЗОЛЯЦИЯ ===

    "СП 17.13330.2017": {
        "title": "Кровли",
        "url": "https://docs.cntd.ru/document/456044318",
        "year": "2017",
        "status": "Действует",
        "category": "Кровли",
        "replaced": "СНиП II-26-76"
    },

    "СП 71.13330.2017": {
        "title": "Изоляционные и отделочные покрытия",
        "url": "https://docs.cntd.ru/document/456054235",
        "year": "2017",
        "status": "Действует",
        "category": "Изоляция"
    },

    # === ИНЖЕНЕРНЫЕ СИСТЕМЫ ===

    "СП 60.13330.2020": {
        "title": "Отопление, вентиляция и кондиционирование воздуха",
        "url": "https://docs.cntd.ru/document/573659347",
        "year": "2020",
        "status": "Действует",
        "category": "Инженерия",
        "replaced": "СП 60.13330.2016"
    },

    "СП 30.13330.2020": {
        "title": "Внутренний водопровод и канализация зданий",
        "url": "https://docs.cntd.ru/document/573659385",
        "year": "2020",
        "status": "Действует",
        "category": "Инженерия",
        "replaced": "СП 30.13330.2016"
    },

    "СП 52.13330.2016": {
        "title": "Естественное и искусственное освещение",
        "url": "https://docs.cntd.ru/document/456054197",
        "year": "2016",
        "status": "Действует",
        "category": "Инженерия",
        "replaced": "СНиП 23-05-95*"
    },

    "СП 73.13330.2016": {
        "title": "Внутренние санитарно-технические системы зданий",
        "url": "https://docs.cntd.ru/document/456069601",
        "year": "2016",
        "status": "Действует",
        "category": "Инженерия"
    },

    # === ПОЖАРНАЯ БЕЗОПАСНОСТЬ ===

    "СП 2.13130.2020": {
        "title": "Системы противопожарной защиты. Обеспечение огнестойкости объектов защиты",
        "url": "https://docs.cntd.ru/document/565837297",
        "year": "2020",
        "status": "Действует",
        "category": "Пожарная безопасность",
        "replaced": "СП 2.13130.2012"
    },

    "СП 4.13130.2013": {
        "title": "Системы противопожарной защиты. Ограничение распространения пожара на объектах защиты. Требования к объемно-планировочным и конструктивным решениям",
        "url": "https://docs.cntd.ru/document/1200096437",
        "year": "2013",
        "status": "Действует (с изм. 2021)",
        "category": "Пожарная безопасность"
    },

    "СП 5.13130.2009": {
        "title": "Системы противопожарной защиты. Установки пожарной сигнализации и пожаротушения автоматические",
        "url": "https://docs.cntd.ru/document/1200071872",
        "year": "2009",
        "status": "Действует (с изм. 2017)",
        "category": "Пожарная безопасность"
    },

    # === ДОСТУПНОСТЬ ДЛЯ МГН ===

    "СП 59.13330.2020": {
        "title": "Доступность зданий и сооружений для маломобильных групп населения",
        "url": "https://docs.cntd.ru/document/573659347",
        "year": "2020",
        "status": "Действует",
        "category": "Доступность",
        "replaced": "СП 59.13330.2016"
    },

    # === КОНТРОЛЬ КАЧЕСТВА ===

    "ГОСТ 10180-2012": {
        "title": "Бетоны. Методы определения прочности по контрольным образцам",
        "url": "https://docs.cntd.ru/document/1200100908",
        "year": "2012",
        "status": "Действует",
        "category": "Контроль качества"
    },

    "ГОСТ 22690-2015": {
        "title": "Бетоны. Определение прочности механическими методами неразрушающего контроля",
        "url": "https://docs.cntd.ru/document/1200121930",
        "year": "2015",
        "status": "Действует",
        "category": "Контроль качества"
    },

    "ГОСТ 18105-2018": {
        "title": "Бетоны. Правила контроля и оценки прочности",
        "url": "https://docs.cntd.ru/document/1200161950",
        "year": "2018",
        "status": "Действует",
        "category": "Контроль качества",
        "replaced": "ГОСТ 18105-2010"
    },

    "ГОСТ 23055-78": {
        "title": "Контроль неразрушающий. Сварка металлов плавлением. Классификация сварных соединений по результатам радиографического контроля",
        "url": "https://docs.cntd.ru/document/1200012783",
        "year": "1978",
        "status": "Действует",
        "category": "Контроль качества"
    },

    "ГОСТ 5781-82": {
        "title": "Сталь горячекатаная для армирования железобетонных конструкций. Технические условия",
        "url": "https://docs.cntd.ru/document/1200005050",
        "year": "1982",
        "status": "Действует (с изм. 2021)",
        "category": "Материалы"
    },

    # === НАГРУЗКИ И ВОЗДЕЙСТВИЯ ===

    "СП 20.13330.2016": {
        "title": "Нагрузки и воздействия",
        "url": "https://docs.cntd.ru/document/456028291",
        "year": "2016",
        "status": "Действует",
        "category": "Расчёты",
        "replaced": "СНиП 2.01.07-85*"
    },

    # === ОХРАНА ТРУДА И БЕЗОПАСНОСТЬ ===

    "СП 12-136-2002": {
        "title": "Безопасность труда в строительстве. Решения по охране труда и промышленной безопасности в проектах организации строительства и проектах производства работ",
        "url": "https://docs.cntd.ru/document/1200000308",
        "year": "2002",
        "status": "Действует",
        "category": "Охрана труда"
    },

    # === СЕЙСМОСТОЙКОСТЬ ===

    "СП 14.13330.2018": {
        "title": "Строительство в сейсмических районах",
        "url": "https://docs.cntd.ru/document/550565571",
        "year": "2018",
        "status": "Действует",
        "category": "Сейсмика",
        "replaced": "СП 14.13330.2014"
    },

    # === КЛИМАТОЛОГИЯ ===

    "СП 131.13330.2020": {
        "title": "Строительная климатология",
        "url": "https://docs.cntd.ru/document/573659347",
        "year": "2020",
        "status": "Действует",
        "category": "Климат",
        "replaced": "СП 131.13330.2018"
    },

    # === ТЕХНОЛОГИЯ БЕТОНА ===

    "ГОСТ 7473-2010": {
        "title": "Смеси бетонные. Технические условия",
        "url": "https://docs.cntd.ru/document/1200084776",
        "year": "2010",
        "status": "Действует",
        "category": "Материалы"
    },

    # === ОГНЕЗАЩИТА ===

    "СП 293.1325800.2017": {
        "title": "Системы огнезащиты. Узлы строительных конструкций. Правила проектирования",
        "url": "https://docs.cntd.ru/document/456082449",
        "year": "2017",
        "status": "Действует",
        "category": "Пожарная безопасность"
    },

    # === ЗЕЛЕНЫЕ СТАНДАРТЫ ===

    "ГОСТ Р 57345-2016": {
        "title": "Зеленые стандарты. Здания жилые и общественные. Рейтинговая система оценки устойчивости среды обитания",
        "url": "https://docs.cntd.ru/document/1200145289",
        "year": "2016",
        "status": "Действует",
        "category": "Экология"
    },

    # === ЭНЕРГОЭФФЕКТИВНОСТЬ ===

    "СП 345.1325800.2017": {
        "title": "Здания жилые и общественные. Правила проектирования тепловой защиты",
        "url": "https://docs.cntd.ru/document/456054206",
        "year": "2017",
        "status": "Действует",
        "category": "Энергоэффективность"
    },

    # === ОРГАНИЗАЦИЯ СТРОИТЕЛЬСТВА ===

    "СП 48.13330.2019": {
        "title": "Организация строительства",
        "url": "https://docs.cntd.ru/document/564477582",
        "year": "2019",
        "status": "Действует",
        "category": "Организация",
        "replaced": "СП 48.13330.2011"
    },

    "СП 70.13330.2012": {
        "title": "Несущие и ограждающие конструкции",
        "url": "https://docs.cntd.ru/document/1200092705",
        "year": "2012",
        "status": "Действует (с изм. 2020)",
        "category": "Проектирование"
    },

    # === ПРОЕКТИРОВАНИЕ ЗДАНИЙ (АКТУАЛЬНЫЕ 2024-2025) ===

    "СП 54.13330.2022": {
        "title": "Здания жилые многоквартирные",
        "url": "https://docs.cntd.ru/document/1300540989",
        "year": "2022",
        "status": "Действует с 01.09.2023",
        "category": "Жилые здания",
        "replaced": "СП 54.13330.2016"
    },

    "СП 118.13330.2022": {
        "title": "Общественные здания и сооружения",
        "url": "https://docs.cntd.ru/document/1300540990",
        "year": "2022",
        "status": "Действует с 01.09.2023",
        "category": "Общественные здания",
        "replaced": "СП 118.13330.2012*"
    },

    "СП 56.13330.2021": {
        "title": "Производственные здания",
        "url": "https://docs.cntd.ru/document/1200177025",
        "year": "2021",
        "status": "Действует",
        "category": "Промышленные здания",
        "replaced": "СП 56.13330.2011"
    },

    # === СЕЙСМОСТОЙКОСТЬ ===

    "СП 14.13330.2018": {
        "title": "Строительство в сейсмических районах",
        "url": "https://docs.cntd.ru/document/554402860",
        "year": "2018",
        "status": "Действует",
        "category": "Сейсмостойкость",
        "replaced": "СП 14.13330.2014"
    },

    # === ГЕОТЕХНИКА ===

    "СП 22.13330.2016": {
        "title": "Основания зданий и сооружений",
        "url": "https://docs.cntd.ru/document/456054206",
        "year": "2016",
        "status": "Действует",
        "category": "Геотехника"
    },

    "СП 47.13330.2016": {
        "title": "Инженерные изыскания для строительства. Основные положения",
        "url": "https://docs.cntd.ru/document/456050589",
        "year": "2016",
        "status": "Действует (с изм. 2020)",
        "category": "Изыскания"
    },

    # === ЭНЕРГОЭФФЕКТИВНОСТЬ ===

    "СП 230.1325800.2015": {
        "title": "Конструкции ограждающие зданий. Характеристики теплотехнических неоднородностей",
        "url": "https://docs.cntd.ru/document/1200123147",
        "year": "2015",
        "status": "Действует",
        "category": "Энергоэффективность"
    },

    "СП 345.1325800.2017": {
        "title": "Здания жилые и общественные. Правила проектирования тепловой защиты",
        "url": "https://docs.cntd.ru/document/456069587",
        "year": "2017",
        "status": "Действует",
        "category": "Энергоэффективность"
    }
}


# === ПОСТОЯННАЯ КЛАВИАТУРА ===

def get_main_keyboard():
    """Создать постоянную клавиатуру с кнопками"""
    keyboard = [
        [KeyboardButton("🎤 Real-time чат")],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Напишите вопрос или нажмите кнопку..."
    )


# === КОМАНДЫ ===

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    user_id = update.effective_user.id

    # Загружаем статистику пользователя
    stats = get_user_stats(user_id)

    welcome_message = f"""👋 Здравствуйте, {user.first_name}!

Я — *СтройНадзорAI v3.0* — профессиональный инженерно-нормативный AI-ассистент по строительству РФ.

🎯 *Уровень экспертизы:* 20+ лет инженерного опыта

━━━━━━━━━━━━━━━━━━━━━━
🔹 *ВОЗМОЖНОСТИ*
━━━━━━━━━━━━━━━━━━━━━━

🎤 *Голосовой ассистент*
   • Отправьте голосовое — отвечу голосом
   • Whisper + GPT-4 + TTS

📸 *Анализ фото объекта*
   • Техническая экспертиза
   • Выявление дефектов по ГОСТ
   • Рекомендации по устранению

🏛️ *Совет AI* (для сложных вопросов)
   • Grok — технический анализ
   • Claude — детальная экспертиза
   • Gemini — практические решения

🧮 *21 строительный калькулятор*
   • Бетон, арматура, опалубка
   • Кирпич, плитка, краска
   • Кровля, фундамент, лестницы

━━━━━━━━━━━━━━━━━━━━━━
🔹 *БАЗА ЗНАНИЙ*
━━━━━━━━━━━━━━━━━━━━━━

📚 *Нормативы РФ:*
   СП • ГОСТ • СНиП • ФЗ • ПУЭ • СанПиН

📖 *Справочники:*
   Байков, Цытович, Кудишин и др.

⚖️ *Практика:*
   Технадзор • Экспертиза • Суды

━━━━━━━━━━━━━━━━━━━━━━
🔹 *КОМАНДЫ*
━━━━━━━━━━━━━━━━━━━━━━

/realtime\\_chat — Голосовой чат
/calculators — Калькуляторы
/regulations — Нормативы
/templates — Шаблоны документов
/help — Полная справка

"""

    if stats['total_messages'] > 0:
        welcome_message += f"""📊 *Ваша статистика:*
• Сообщений: {stats['total_messages']}
• Проанализировано фото: {stats['images_analyzed']}

"""

    # Показываем активный проект (если есть)
    if PROJECTS_AVAILABLE:
        current_project = context.user_data.get("current_project")
        if current_project:
            welcome_message += f"📁 *Активный проект:* {current_project}\n"
            welcome_message += "_(все диалоги сохраняются в проект)_\n\n"

    welcome_message += "Попробуйте отправить фото объекта или задать вопрос! 👇"

    # Inline меню под сообщением
    inline_keyboard = [
        [InlineKeyboardButton("🎤 Real-time чат", callback_data="realtime_chat_start")],
        [InlineKeyboardButton("📁 Проект", callback_data="project_menu"),
         InlineKeyboardButton("🧮 Калькуляторы", callback_data="calculators_menu")],
        [InlineKeyboardButton("📚 Нормативы", callback_data="regulations"),
         InlineKeyboardButton("❓ Частые вопросы", callback_data="faq_menu")],
        [InlineKeyboardButton("📋 Шаблоны", callback_data="templates"),
         InlineKeyboardButton("👔 Выбрать роль", callback_data="role")],
        [InlineKeyboardButton("💡 Предложения", callback_data="suggestions"),
         InlineKeyboardButton("🔧 Разработчик", callback_data="dev_mode")],
        [InlineKeyboardButton("📝 Примеры вопросов", callback_data="examples"),
         InlineKeyboardButton("ℹ️ Справка", callback_data="help")]
    ]
    inline_markup = InlineKeyboardMarkup(inline_keyboard)

    # Отправляем приветствие с inline меню и постоянной клавиатурой
    await update.message.reply_text(
        welcome_message,
        parse_mode='Markdown',
        reply_markup=inline_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """📖 *СПРАВКА — СтройНадзорAI v3.0*

*🎤 ГОЛОСОВОЙ АССИСТЕНТ:*
   /realtime\\_chat — Начать голосовой чат
   • Отправьте голосовое → получите голосовой ответ
   • Whisper (распознавание) + GPT-4 + TTS (озвучка)

*📸 АНАЛИЗ ФОТО:*
   • Отправьте фото объекта/дефекта
   • Добавьте подпись с вопросом
   • Получите экспертизу по ГОСТ

*🏛️ СОВЕТ AI* (для сложных вопросов):
   /council вопрос — Опрос 3-х AI моделей
   • Grok — технический анализ
   • Claude — детальная экспертиза
   • Gemini — практические решения
   • Автоматически для сложных вопросов

*📚 КОМАНДЫ - НОРМАТИВЫ:*
   /regulations - 27 актуальных СП, ГОСТ, СНиП
   /regulations_menu - Категории нормативов (удобная навигация!)
   /examples - Примеры вопросов

*📋 КОМАНДЫ - ТРЕБОВАНИЯ 2025:*
   /requirements2025 - Интерактивная база всех требований
   /laws - 8 основных федеральных законов
   /checklist - Чек-лист ежедневных проверок

*🛠️ КОМАНДЫ - ПРАКТИКА ПЛОЩАДКИ:*
   /hse - Охрана труда и техника безопасности
   /technology - Технология строительства (бетон, арматура)
   /estimating - Сметное дело и финансы (КС-2/КС-3)
   /legal - Юридические вопросы и претензии
   /management - Управление проектами

*🔍 РАБОТА С ИСТОРИЕЙ v3.5:*
   /history - Последние 5 диалогов + кнопки действий
   /stats - Подробная статистика использования
   /search запрос - Поиск по истории диалогов
   /export - Экспорт истории (TXT/Markdown)
   /clear - Очистить историю

*💡 УМНЫЕ ФУНКЦИИ v5.0:*
   /calculators - Меню калькуляторов
   /realtime_chat - Голосовой ассистент (OpenAI)
   /saved - Сохранённые расчёты калькуляторов
   /templates - Шаблоны документов
   /role - Выбор режима работы (прораб/ГИП/ОТК)

*❓ БЫСТРЫЕ ОТВЕТЫ v3.7:*
   /faq - База часто задаваемых вопросов (20+ ответов)
   /faq_search запрос - Поиск готовых ответов

*Примеры вопросов:*
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


async def council_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /council - принудительное использование LLM Council
    
    Позволяет задать вопрос Совету AI моделей (Grok + Claude + Gemini),
    которые дадут свои ответы, оценят друг друга, и сформируют
    консенсусный ответ высокого качества.
    """
    if not LLM_COUNCIL_AVAILABLE:
        await update.message.reply_text(
            "❌ **LLM Council недоступен**\n\n"
            "Для работы Совета AI нужно минимум 2 модели:\n"
            "• Grok (XAI_API_KEY)\n"
            "• Claude (ANTHROPIC_API_KEY)\n"
            "• Gemini (GEMINI_API_KEY)\n\n"
            "Проверьте настройки API ключей.",
            parse_mode="Markdown"
        )
        return
    
    # Получаем вопрос после команды /council
    args = context.args
    if not args:
        # Показываем справку
        await update.message.reply_text(
            "🏛️ **LLM Council — Совет AI моделей**\n\n"
            "Отправляет ваш вопрос нескольким AI моделям, которые:\n"
            "1️⃣ Дают независимые ответы (Grok, Claude, Gemini)\n"
            "2️⃣ Оценивают ответы друг друга\n"
            "3️⃣ Формируют консенсусный ответ\n\n"
            "**Использование:**\n"
            "`/council Ваш сложный технический вопрос`\n\n"
            "**Пример:**\n"
            "`/council Как правильно армировать плиту перекрытия по СП 63.13330?`\n\n"
            "⏱️ Время ответа: 30-60 сек (опрос 3 моделей)\n"
            "🎯 Качество: максимальное (консенсус экспертов)",
            parse_mode="Markdown"
        )
        return
    
    question = " ".join(args)
    user_id = update.effective_user.id
    
    # Добавляем вопрос в историю
    await add_message_to_history_async(user_id, 'user', f"[COUNCIL] {question}")
    
    # Отправляем сообщение о начале работы Совета
    council_msg = await update.message.reply_text(
        "🏛️ **Совет AI собирается...**\n\n"
        "⏳ Этап 1/3: Получаю мнения экспертов\n"
        "• Grok — технический анализ\n"
        "• Claude — детальная экспертиза\n"
        "• Gemini — практические рекомендации\n\n"
        "_Это займёт 30-60 секунд..._",
        parse_mode="Markdown"
    )
    
    try:
        council = get_llm_council()
        if not council:
            await council_msg.edit_text(
                "❌ Не удалось инициализировать Совет AI",
                parse_mode="Markdown"
            )
            return
        
        # Получаем контекст диалога
        conversation_history = get_conversation_context(user_id)
        context_text = ""
        if conversation_history:
            # Берём последние 3 сообщения как контекст
            recent = conversation_history[-3:]
            context_text = "\n".join([f"{m['role']}: {m['content'][:200]}" for m in recent])
        
        # Запускаем полную консультацию
        result = await council.consult(question, context=context_text, skip_review=False)
        
        if result["success"]:
            # Обновляем сообщение с результатом
            final_answer = result["final_answer"]
            duration = result["duration_seconds"]
            models = result["models_used"]
            
            # Добавляем метаинформацию
            footer = f"\n\n---\n⏱️ _Время: {duration:.1f} сек | Модели: {', '.join(models)}_"
            
            # Ограничиваем длину сообщения для Telegram (4096 символов)
            max_len = 4000 - len(footer)
            if len(final_answer) > max_len:
                final_answer = final_answer[:max_len] + "..."
            
            await council_msg.edit_text(
                final_answer + footer,
                parse_mode="Markdown"
            )
            
            # Сохраняем ответ в историю
            await add_message_to_history_async(user_id, 'assistant', final_answer)
            
            logger.info(f"✅ LLM Council: ответ за {duration:.1f} сек для user {user_id}")
        else:
            await council_msg.edit_text(
                f"❌ **Ошибка Совета AI**\n\n{result.get('final_answer', 'Неизвестная ошибка')}",
                parse_mode="Markdown"
            )
    
    except Exception as e:
        logger.error(f"Council command error: {e}")
        await council_msg.edit_text(
            f"❌ **Ошибка при работе Совета AI**\n\n`{str(e)}`",
            parse_mode="Markdown"
        )


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

**Анализ фотографий:**
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

Просто напишите свой вопрос или отправьте фото объекта! 📸"""

    await update.message.reply_text(examples_text, parse_mode='Markdown')


async def visualize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /visualize - визуализация дефектов с помощью Gemini AI"""

    if not GEMINI_AVAILABLE:
        await update.message.reply_text(
            "⚠️ Функция визуализации недоступна. Модуль Gemini не загружен."
        )
        return

    generator = initialize_gemini_generator()
    if not generator:
        await update.message.reply_text(
            "⚠️ Gemini API недоступен. Проверьте настройки GEMINI_API_KEY."
        )
        return

    # Если есть аргументы - генерируем визуализацию дефекта
    if context.args:
        defect_description = " ".join(context.args)

        generating_msg = await update.message.reply_text(
            "🎨 Генерирую визуализацию дефекта...\n"
            "Это займет 15-30 секунд"
        )

        try:
            # Генерируем изображение дефекта
            result = await generator.visualize_defect(
                defect_description=defect_description
            )

            if result and result.get("image_data"):
                # Удаляем сообщение о генерации
                try:
                    await generating_msg.delete()
                except:
                    pass

                # Формируем подпись
                caption = f"""🎨 **ВИЗУАЛИЗАЦИЯ ДЕФЕКТА**

**Описание:** {defect_description}

{result.get('text', '')}

---
🤖 _Сгенерировано с помощью Gemini AI_"""

                # Отправляем изображение
                result["image_data"].seek(0)
                await update.message.reply_photo(
                    photo=result["image_data"],
                    caption=caption[:1024],  # Ограничение Telegram
                    parse_mode='Markdown'
                )
            else:
                await generating_msg.edit_text(
                    "❌ Не удалось создать визуализацию. Попробуйте переформулировать запрос."
                )

        except Exception as e:
            logger.error(f"Ошибка визуализации дефекта: {e}")
            await generating_msg.edit_text(
                f"❌ Произошла ошибка: {str(e)}"
            )

        return

    # Если аргументов нет - показываем справку
    help_text = """🎨 **ВИЗУАЛИЗАЦИЯ ДЕФЕКТОВ - Gemini AI**

Эта команда создает детальные технические описания для визуализации строительных дефектов.

**Как использовать:**

1️⃣ **Анализ фотографии дефекта:**
   • Отправьте фото с подписью /visualize
   • Получите детальное описание для визуализации
   • ИИ выделит ключевые зоны и проблемные участки

2️⃣ **Визуализация по описанию:**
   • /visualize [описание дефекта]
   • Например: `/visualize трещина в бетонной колонне шириной 2мм`
   • Получите техническое описание для схемы

3️⃣ **Сравнение до/после:**
   • Отправьте фото с подписью `/visualize compare`
   • Идеально для отчетов о ремонте

**Что вы получите:**
✅ Техническое описание дефекта
✅ Рекомендации по цветовому выделению зон
✅ Размеры и масштаб проблемных участков
✅ Структурированные данные для создания схем

**Примеры:**
📌 `/visualize трещина в несущей стене`
📌 Отправьте фото с подписью `/visualize`
📌 `/visualize отслоение штукатурки 50x30см`

*Отправьте фото или описание дефекта для визуализации!* 🎯"""

    await update.message.reply_text(help_text, parse_mode='Markdown')


async def handle_photo_with_visualization(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фотографий для визуализации через Gemini"""

    if not GEMINI_AVAILABLE:
        return False

    caption = update.message.caption or ""

    # Проверяем, запрошена ли визуализация
    if "/visualize" not in caption.lower():
        return False

    generator = get_gemini_generator()
    if not generator:
        await update.message.reply_text(
            "⚠️ Gemini API недоступен в данный момент."
        )
        return True

    # Получаем фото
    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    photo_bytes = await photo_file.download_as_bytearray()

    await update.message.reply_text("🎨 Анализирую изображение для визуализации...")

    try:
        # Определяем тип запроса
        is_comparison = "compare" in caption.lower() or "сравнен" in caption.lower()

        if is_comparison:
            # Сравнительная визуализация
            description = await generator.create_comparison_description(
                before_image=bytes(photo_bytes),
                defect_info=caption.replace("/visualize", "").replace("compare", "").strip()
            )
        else:
            # Обычный анализ для визуализации
            description = await generator.analyze_and_visualize_defect(
                image_bytes=bytes(photo_bytes),
                analysis_text=caption.replace("/visualize", "").strip()
            )

        if description:
            response_text = f"""🎨 **ТЕХНИЧЕСКОЕ ОПИСАНИЕ ДЛЯ ВИЗУАЛИЗАЦИИ**

{description}

---
💡 *Это описание можно использовать для создания технических схем, диаграмм и аннотированных изображений дефектов.*
"""
            await update.message.reply_text(response_text, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "❌ Не удалось создать описание визуализации. Попробуйте снова."
            )

    except Exception as e:
        logger.error(f"Ошибка визуализации: {e}")
        await update.message.reply_text(
            f"❌ Произошла ошибка при создании визуализации: {str(e)}"
        )

    return True


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

    if recs['popular_topics']:
        response += "\n**Ваши популярные темы:**\n\n"
        for topic in recs['popular_topics']:
            emoji_map = {
                'норматив': '📄',
                'материал': '🧱',
                'конструкция': '🏗️'
            }
            emoji = emoji_map.get(topic['category'], '📌')
            response += f"{emoji} {topic['topic'].capitalize()} - {topic['mentions']} упоминаний\n"

    await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)


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


# === НОВЫЕ КОМАНДЫ v3.9 ===

async def templates_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /templates - показать шаблоны документов"""
    if not TEMPLATES_AVAILABLE:
        await update.message.reply_text("⚠️ Шаблоны документов недоступны")
        return

    keyboard = []
    for template_id, info in DOCUMENT_TEMPLATES.items():
        keyboard.append([
            InlineKeyboardButton(
                text=info["name"],
                callback_data=f"template_{template_id}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📄 **ШАБЛОНЫ ДОКУМЕНТОВ**\n\n"
        "Выберите тип документа для генерации:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def handle_template_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, template_id: str):
    """Обработчик выбора шаблона документа"""
    query = update.callback_query
    await query.answer()

    if template_id not in DOCUMENT_TEMPLATES:
        await query.edit_message_text("❌ Шаблон не найден")
        return

    template_info = DOCUMENT_TEMPLATES[template_id]

    # Формируем список параметров для отображения пользователю
    params_display = template_info.get("params_display", template_info["params"])
    params_list = "\n".join([f"• {param}" for param in params_display])

    # Отправляем информацию о шаблоне с выбором действия
    message_text = (
        f"📄 **{template_info['name']}**\n\n"
        f"{template_info['description']}\n\n"
        f"**Необходимые данные:**\n{params_list}\n\n"
        "Выберите действие:"
    )

    # Кнопки выбора: скачать пустой или заполнить с ботом
    keyboard = [
        [InlineKeyboardButton("📥 Скачать пустой шаблон", callback_data=f"download_empty_{template_id}")],
        [InlineKeyboardButton("✏️ Заполнить с ботом", callback_data=f"fill_{template_id}")],
        [InlineKeyboardButton("« Назад к шаблонам", callback_data="templates")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def handle_download_empty_template(update: Update, context: ContextTypes.DEFAULT_TYPE, template_id: str):
    """Обработчик скачивания пустого шаблона"""
    query = update.callback_query
    await query.answer()

    if template_id not in DOCUMENT_TEMPLATES:
        await query.edit_message_text("❌ Шаблон не найден")
        return

    template_info = DOCUMENT_TEMPLATES[template_id]

    # Создаем пустой документ с заполнителями
    params = {param: "___________" for param in template_info["params"]}

    # Генерируем документ
    result = generate_document(template_id, params)

    if not result["success"]:
        await query.edit_message_text(f"❌ Ошибка генерации документа: {result['error']}")
        return

    # Отправляем пустой шаблон
    with open(result["filepath"], 'rb') as doc_file:
        await update.effective_chat.send_document(
            document=doc_file,
            filename=os.path.basename(result["filepath"]),
            caption=f"📄 **Пустой шаблон**: {template_info['name']}\n\n"
                    f"Заполните документ вручную, заменив подчёркивания на ваши данные.",
            parse_mode="Markdown"
        )

    # Кнопка назад к шаблонам
    keyboard = [[InlineKeyboardButton("« Назад к шаблонам", callback_data="templates")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"✅ Пустой шаблон отправлен!\n\nЧто дальше?",
        reply_markup=reply_markup
    )


async def projects_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /projects - показать проекты пользователя"""
    if not PROJECTS_AVAILABLE:
        await update.message.reply_text("⚠️ Управление проектами недоступно")
        return

    user_id = update.effective_user.id
    projects = get_user_projects(user_id)

    if not projects:
        await update.message.reply_text(
            "📁 У вас пока нет проектов.\n\n"
            "Создайте новый проект:\n"
            "`/new_project Название проекта`",
            parse_mode="Markdown"
        )
        return

    keyboard = []
    for project_name in projects:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📁 {project_name}",
                callback_data=f"proj_open_{project_name}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="➕ Создать новый проект",
            callback_data="proj_new"
        )
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"📁 **ВАШИ ПРОЕКТЫ** ({len(projects)})\n\n"
        "Выберите проект для работы:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def new_project_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /new_project - создать новый проект"""
    if not PROJECTS_AVAILABLE:
        await update.message.reply_text("⚠️ Управление проектами недоступно")
        return

    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text(
            "❌ Укажите название проекта:\n"
            "`/new_project Название проекта`",
            parse_mode="Markdown"
        )
        return

    project_name = " ".join(context.args)
    result = create_project(user_id, project_name)

    if result["success"]:
        context.user_data["current_project"] = project_name
        await update.message.reply_text(
            f"✅ Проект **{project_name}** создан и активирован!\n\n"
            "📌 Все ваши вопросы и ответы теперь сохраняются в проект.\n\n"
            "Доступные команды:\n"
            "• `/project_info` - информация о проекте\n"
            "• `/project_log` - журнал работы\n"
            "• `/set_project` - переключить проект\n"
            "• `/projects` - список проектов",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ Ошибка создания проекта:\n{result.get('error', '')}"
        )


async def set_project_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /set_project - установить активный проект"""
    if not PROJECTS_AVAILABLE:
        await update.message.reply_text("⚠️ Управление проектами недоступно")
        return

    user_id = update.effective_user.id
    projects = get_user_projects(user_id)

    if not projects:
        await update.message.reply_text(
            "📁 У вас нет проектов.\n\n"
            "Создайте новый: `/new_project Название`",
            parse_mode="Markdown"
        )
        return

    if context.args:
        # Установить проект по названию
        project_name = " ".join(context.args)
        if project_name in projects:
            context.user_data["current_project"] = project_name
            project = load_project(user_id, project_name)
            await update.message.reply_text(
                f"✅ Активный проект: **{project_name}**\n\n"
                f"{project.get_log_summary()}\n\n"
                "Все вопросы и ответы сохраняются в этот проект.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"❌ Проект '{project_name}' не найден.")
    else:
        # Показать меню выбора
        keyboard = []
        for proj in projects:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📁 {proj}",
                    callback_data=f"setproj_{proj}"
                )
            ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        current = context.user_data.get("current_project", "Не выбран")
        await update.message.reply_text(
            f"**ВЫБОР АКТИВНОГО ПРОЕКТА**\n\n"
            f"Текущий проект: {current}\n\n"
            "Выберите проект для работы:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )


async def project_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /project_info - информация об активном проекте"""
    if not PROJECTS_AVAILABLE:
        await update.message.reply_text("⚠️ Управление проектами недоступно")
        return

    current_project_name = context.user_data.get("current_project")
    if not current_project_name:
        await update.message.reply_text(
            "❌ Нет активного проекта.\n\n"
            "Выберите проект: `/set_project`",
            parse_mode="Markdown"
        )
        return

    user_id = update.effective_user.id
    project = load_project(user_id, current_project_name)

    if not project:
        await update.message.reply_text("❌ Ошибка загрузки проекта")
        return

    info = project.get_project_summary()
    log_summary = project.get_log_summary()

    await update.message.reply_text(
        f"{info}\n\n"
        f"📊 **Журнал работы:** {log_summary}",
        parse_mode="Markdown"
    )


async def project_log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /project_log - журнал работы над проектом"""
    if not PROJECTS_AVAILABLE:
        await update.message.reply_text("⚠️ Управление проектами недоступно")
        return

    current_project_name = context.user_data.get("current_project")
    if not current_project_name:
        await update.message.reply_text(
            "❌ Нет активного проекта.\n\n"
            "Выберите проект: `/set_project`",
            parse_mode="Markdown"
        )
        return

    user_id = update.effective_user.id
    project = load_project(user_id, current_project_name)

    if not project:
        await update.message.reply_text("❌ Ошибка загрузки проекта")
        return

    log = project.get_conversation_log()

    if not log:
        await update.message.reply_text("📋 Журнал работы пуст")
        return

    # Показываем последние 10 записей
    recent_log = log[-10:]
    response = f"📋 **ЖУРНАЛ: {current_project_name}**\n\n"
    response += f"Всего записей: {len(log)}\n"
    response += f"Показаны последние {len(recent_log)} записей:\n\n"

    for i, entry in enumerate(recent_log, 1):
        timestamp = entry["timestamp"][:16].replace("T", " ")
        question = entry.get("question", "")[:50]
        response += f"{i}. {timestamp}\n   Q: {question}...\n\n"

    response += "\n💡 Для экспорта полного журнала используйте `/export_project`"

    await update.message.reply_text(response, parse_mode="Markdown")


# === ОБРАБОТКА СООБЩЕНИЙ ===

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фотографий"""
    user_id = update.effective_user.id

    # Проверка rate limit
    if not check_rate_limit(user_id):
        await update.message.reply_text(
            "⏱️ Слишком много запросов!\n\n"
            f"Вы можете отправлять до {RATE_LIMIT_MAX_REQUESTS} запросов в минуту.\n"
            "Пожалуйста, подождите немного и попробуйте снова."
        )
        return

    # Проверяем, нужна ли визуализация через Gemini
    if await handle_photo_with_visualization(update, context):
        return

    # Отправляем сообщение о процессе и сохраняем его для последующего удаления
    thinking_message = await update.message.reply_text("📸 Анализирую фотографию...\n\nВы можете не ждать, я пришлю уведомление 😉")

    try:
        # Получаем фото (самое большое разрешение)
        photo = update.message.photo[-1]
        caption_text = update.message.caption or "Проанализируй это фото"

        # ============================================================================
        # ОПТИМИЗАЦИЯ: Умный выбор модели для фото (Gemini для дефектов)
        # ============================================================================
        if SMART_WRAPPER_AVAILABLE:
            smart_result = await smart_model_selection_photo(
                question=caption_text,
                photo_file_id=photo.file_id,
                update=update,
                context=context
            )

            # Если умный выбор обработал фото - выходим
            if smart_result and smart_result.get("success"):
                try:
                    await thinking_message.delete()
                except:
                    pass
                return  # Ответ уже отправлен

        # Если умный выбор не сработал - продолжаем с Grok/Gemini по стандартной логике

        # Проверяем размер фото
        if photo.file_size and photo.file_size > 20 * 1024 * 1024:  # 20 МБ
            await thinking_message.edit_text(
                f"❌ **Фото слишком большое**\n\n"
                f"📊 Размер: {photo.file_size / (1024 * 1024):.1f} МБ\n"
                f"📏 Максимум: 20 МБ\n\n"
                f"💡 Сожмите изображение перед отправкой"
            )
            return

        photo_file = await photo.get_file()

        # Скачиваем фото
        photo_bytes = await photo_file.download_as_bytearray()

        # Кодируем в base64
        photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')

        # Получаем подпись (если есть)
        caption = update.message.caption or ""

        # ============================================
        # ВЫБОР AI ДВИЖКА ДЛЯ АНАЛИЗА ФОТО
        # ============================================
        # Приоритет: 1) Gemini 2.5 Flash (быстрее, дешевле)
        #            2) xAI Grok (fallback)

        # Пробуем Gemini Vision сначала
        if GEMINI_VISION_AVAILABLE and gemini_vision_analyzer:
            try:
                logger.info("📸 Используем Gemini 2.5 Flash для анализа фото")

                # Анализируем через Gemini
                analysis_result = await gemini_vision_analyzer.analyze_defect_photo(
                    image_data=bytes(photo_bytes),
                    user_prompt=caption if caption else None
                )

                if analysis_result:
                    # Удаляем сообщение "анализирую фотографию"
                    try:
                        await thinking_message.delete()
                    except Exception as e:
                        logger.warning(f"Could not delete thinking message: {e}")

                    # Формируем ответ
                    result = f"🔍 **Анализ фотографии (Gemini 2.5 Flash):**\n\n{analysis_result}\n\n"
                    result += f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"

                    # Разбиваем длинные сообщения на части
                    max_length = 4000
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

                        for part in parts:
                            await update.message.reply_text(
                                part,
                                parse_mode='Markdown'
                            )
                    else:
                        await update.message.reply_text(
                            result,
                            parse_mode='Markdown'
                        )

                    # Сохраняем в историю
                    if HISTORY_MANAGER_AVAILABLE:
                        await history_manager.add_to_history(
                            user_id=user_id,
                            message_type="photo",
                            content=caption if caption else "Фото без подписи",
                            response=analysis_result,
                            metadata={"ai_model": "gemini-2.5-flash"}
                        )

                    logger.info(f"✅ Фото проанализировано через Gemini для пользователя {user_id}")
                    return  # Выходим, анализ выполнен

            except Exception as e:
                logger.warning(f"⚠️ Gemini Vision не удалось: {e}. Переключаемся на Grok")
                # Продолжаем к Grok fallback

        # Если Gemini недоступен или не сработал - используем Grok
        logger.info("📸 Используем xAI Grok для анализа фото (fallback)")

        # Формируем профессиональный промпт для Grok
        system_prompt = """Вы — СтройНадзорAI v2.3, AI-эксперт по техническому надзору в строительстве РФ.

📱 ФОРМАТИРОВАНИЕ ДЛЯ ТЕЛЕФОНА:
• Пользователь на мобильном устройстве!
• Максимум 30-35 символов в строке
• НЕ используйте широкие таблицы и ASCII-схемы
• Используйте вертикальные списки и простые символы → ↓ •

📸 АНАЛИЗ ИЗОБРАЖЕНИЙ - КРИТИЧЕСКИ ВАЖНО:

🎯 ПРИНЦИП ОБЪЕКТИВНОСТИ:
• Проведите БЕСПРИСТРАСТНЫЙ анализ фотографии
• НЕ предполагайте наличие дефектов заранее
• Если конструкция в норме — прямо укажите это
• Дефектами считайте ТОЛЬКО явные отклонения от нормативов

📋 СТРУКТУРА ОТВЕТА (кратко, до 300 слов):

**Анализ:**
• Тип элемента (фундамент/стена/перекрытие/кровля)
• Материал (бетон/кирпич/металл/дерево)
• Состояние: ✅ норма / ⚠️ дефект выявлен

**Если дефект обнаружен:**
• Тип дефекта (трещина/коррозия/отслоение/деформация)
• Критичность: низкая/средняя/высокая
• Расположение (где именно на элементе)
• Параметры (ширина, длина, глубина - если видно)

**Нормативы** (только при дефектах):
• СП 63.13330.2018 — для бетона/ж.б (трещины, прочность)
• СП 13-102-2003 — правила обследования
• СП 28.13330.2017 — защита от коррозии
• ГОСТ Р 31937-2011 — классы технического состояния

**Рекомендации:**
• Если норма: краткие советы по эксплуатации
• Если дефект: метод устранения (инъектирование/усиление/замена)

🔧 УЧЁТ НАВЫКОВ СТРОИТЕЛЯ:
• Адаптируйте рекомендации под уровень квалификации пользователя
• Для начинающих: давайте пошаговые инструкции с указанием инструментов
• Для опытных: сосредоточьтесь на технических деталях и нормативах

💡 ПРАКТИЧЕСКИЙ ПОДХОД:
• Используйте строительную терминологию
• При дефектах указывайте числа с допусками
• Если неясно — запросите дополнительные фото
• Держите дружелюбный тон, структурируйте (bullets, emojis)

ВАЖНО: Объективность превыше всего. Если дефектов нет — так и напишите. Не ищите проблемы там, где их нет!"""

        user_message = "Проведите объективный технический осмотр изображения. Опишите состояние конструкции и укажите, есть ли дефекты или нарушения строительных норм."
        if caption:
            user_message += f"\n\nДополнительная информация от пользователя: {caption}"

        # Вызываем xAI Grok API для анализа изображения с retry logic
        client = get_grok_client()
        loop = asyncio.get_event_loop()

        # Включаем web_search для анализа фото (поиск информации о дефектах)
        search_params = {
            "mode": "auto", "return_citations": True, "sources": [{"type": "web"}, {"type": "news"}, {"type": "x"}]}

        response = await loop.run_in_executor(
            None,
            lambda: call_grok_with_retry(
                client,
                model="grok-4-1-fast",  # Reasoning модель для анализа изображений
                max_tokens=6000,
                temperature=0.7,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
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
                search_parameters=search_params
            )
        )
        analysis = response["choices"][0]["message"]["content"]

        # Удаляем сообщение "анализирую фотографию"
        try:
            await thinking_message.delete()
        except Exception as e:
            logger.warning(f"Could not delete thinking message: {e}")

        # Формируем ответ
        result = f"🔍 **Анализ фотографии:**\n\n{analysis}\n\n"
        result += f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"

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

            # Отправляем по частям БЕЗ parse_mode (избегаем ошибок парсинга)
            for i, part in enumerate(parts):
                # Добавляем кнопку "Применить изменения" к последней части (только для разработчика)
                part_reply_markup = None
                user_id = update.effective_user.id
                if i == len(parts) - 1 and AUTO_APPLY_AVAILABLE and should_show_apply_button(analysis) and is_developer(user_id):
                    part_reply_markup = add_apply_button()

                if i == 0:
                    await update.message.reply_text(part, reply_markup=part_reply_markup)
                else:
                    await update.message.reply_text(
                        f"(продолжение {i+1}/{len(parts)})\n\n{part}",
                        reply_markup=part_reply_markup
                    )
        else:
            # Отправляем БЕЗ parse_mode для избежания ошибок "can't parse entities"
            await update.message.reply_text(result)

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


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка голосовых сообщений"""
    if not VOICE_HANDLER_AVAILABLE:
        await update.message.reply_text("⚠️ Голосовые сообщения недоступны")
        return

    user_id = update.effective_user.id
    thinking_msg = await update.message.reply_text("🎤 Распознаю голосовое сообщение...")

    try:
        voice_file_id = update.message.voice.file_id
        result = await process_voice_message(
            bot=context.bot,
            voice_file_id=voice_file_id,
            user_id=user_id
        )

        if result["success"]:
            recognized_text = result["text"]

            # Показываем распознанный текст
            await thinking_msg.edit_text(
                f"✅ Распознано:\n\n{recognized_text}\n\n⏳ Обрабатываю запрос..."
            )

            # Сохраняем распознанный текст в context для handle_text
            context.user_data['_voice_recognized_text'] = recognized_text

            # Обрабатываем как текстовый вопрос
            await handle_text(update, context)

        else:
            error_msg = result.get("error", "Неизвестная ошибка")
            await thinking_msg.edit_text(
                f"❌ Ошибка распознавания:\n{error_msg}\n\n"
                "Попробуйте записать голосовое сообщение ещё раз или напишите текстом."
            )

    except Exception as e:
        logger.error(f"Ошибка обработки голоса: {e}")
        try:
            await thinking_msg.delete()
        except:
            pass
        await update.message.reply_text(
            f"❌ Ошибка: {str(e)}\n\nПожалуйста, напишите ваш вопрос текстом."
        )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка загрузки файлов с анализом и экспертным заключением"""
    user_id = update.effective_user.id
    current_project_name = context.user_data.get("current_project")

    # Если нет активного проекта - предлагаем создать
    if not PROJECTS_AVAILABLE or not current_project_name:
        await update.message.reply_text(
            "📁 Для анализа документов создайте или выберите проект:\n"
            "Нажмите кнопку **📁 Проект** в главном меню",
            parse_mode="Markdown"
        )
        return

    project = load_project(user_id, current_project_name)
    if not project:
        await update.message.reply_text("❌ Проект не найден")
        return

    try:
        # Проверяем размер файла
        file_size = update.message.document.file_size
        max_size = 20 * 1024 * 1024  # 20 МБ - лимит Telegram Bot API

        if file_size > max_size:
            await update.message.reply_text(
                f"❌ **Файл слишком большой**\n\n"
                f"📊 Размер файла: {file_size / (1024 * 1024):.1f} МБ\n"
                f"📏 Максимальный размер: 20 МБ\n\n"
                f"💡 **Решения:**\n"
                f"• Сожмите PDF (онлайн-сервисы: ilovepdf.com, smallpdf.com)\n"
                f"• Разбейте документ на части\n"
                f"• Удалите ненужные страницы"
            )
            return

        # Скачиваем файл
        file = await update.message.document.get_file()
        file_name = update.message.document.file_name
        file_path = f"temp_{user_id}_{file_name}"
        await file.download_to_drive(file_path)

        description = update.message.caption or ""
        file_type = update.message.document.mime_type or "unknown"

        # Определяем тип документа
        is_pdf = file_name.lower().endswith('.pdf') or 'pdf' in file_type.lower()

        # Сообщение о начале анализа
        thinking_msg = await update.message.reply_text(
            f"📄 Получен документ: **{file_name}**\n\n"
            f"⏳ Анализирую документ...",
            parse_mode="Markdown"
        )

        # Анализируем PDF
        expert_opinion = None
        if is_pdf:
            try:
                # Извлекаем текст из PDF
                import PyPDF2
                pdf_text = ""
                with open(file_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    num_pages = len(pdf_reader.pages)

                    # Читаем максимум первые 10 страниц
                    max_pages = min(num_pages, 10)
                    for page_num in range(max_pages):
                        page = pdf_reader.pages[page_num]
                        pdf_text += page.extract_text() + "\n"

                # Ограничиваем размер текста
                pdf_text = pdf_text[:15000]  # ~3000 токенов

                if pdf_text.strip():
                    # Формируем промпт для анализа
                    analysis_prompt = f"""Вы — ведущий инженер-эксперт по строительным нормативам РФ с 20-летним опытом.

📋 **ЗАДАЧА:** Проанализируйте предоставленный строительный документ и дайте экспертное заключение.

{'📝 **ЗАПРОС ПОЛЬЗОВАТЕЛЯ:** ' + description if description else ''}

🎯 **ТРЕБОВАНИЯ К АНАЛИЗУ:**

1. **ИДЕНТИФИКАЦИЯ ДОКУМЕНТА:**
   • Определите тип документа (проект, смета, акт, заключение, экспертиза, и т.д.)
   • Укажите основные реквизиты (если есть)
   • Определите объект строительства

2. **СОДЕРЖАНИЕ:**
   • Кратко опишите основное содержание (3-5 пунктов)
   • Выделите ключевые технические решения
   • Укажите применённые нормативы

3. **ЭКСПЕРТНАЯ ОЦЕНКА:**
   • Соответствие актуальным нормативам 2024-2025
   • Выявленные проблемы или несоответствия (если есть)
   • Что требует особого внимания

4. **РЕКОМЕНДАЦИИ:**
   • Что нужно проверить дополнительно
   • Какие документы могут потребоваться
   • Практические советы по применению

**ВАЖНО:**
- Если документ частично нечитаем - укажите это
- Ссылайтесь на конкретные СП/ГОСТ с пунктами
- Будьте объективны и конкретны

---

📄 **ТЕКСТ ДОКУМЕНТА:**

{pdf_text}"""

                    # Отправляем на анализ Grok
                    client = get_grok_client()
                    loop = asyncio.get_event_loop()

                    # Включаем web_search для анализа документов (поиск нормативов)
                    search_params = {
                        "mode": "auto", "return_citations": True, "sources": [{"type": "web"}, {"type": "news"}, {"type": "x"}]}

                    response = await loop.run_in_executor(
                        None,
                        lambda: call_grok_with_retry(
                            client,
                            model="grok-4-1-fast",  # Reasoning модель для анализа документов
                            max_tokens=6000,
                            temperature=0.3,
                            messages=[
                                {"role": "system", "content": "Вы — эксперт по строительным нормативам РФ. Даёте профессиональные заключения по документам."},
                                {"role": "user", "content": analysis_prompt}
                            ],
                            search_parameters=search_params
                        )
                    )
                    expert_opinion = response["choices"][0]["message"]["content"]

                    # Сохраняем анализ в проект
                    if expert_opinion:
                        project.add_conversation_entry(
                            f"[ДОКУМЕНТ] {file_name}" + (f": {description}" if description else ""),
                            expert_opinion,
                            "document_analysis"
                        )

            except ImportError:
                expert_opinion = "⚠️ Для анализа PDF установите библиотеку PyPDF2:\n`pip install PyPDF2`"
            except Exception as e:
                logger.error(f"Ошибка анализа PDF: {e}")
                expert_opinion = f"⚠️ Не удалось проанализировать PDF: {str(e)}"

        # Сохраняем файл в проект
        result = project.add_file(file_path, file_type, description)

        # Удаляем временный файл
        import os
        os.remove(file_path)

        # Удаляем сообщение "анализирую"
        try:
            await thinking_msg.delete()
        except:
            pass

        # Формируем ответ
        response_text = f"✅ **Документ добавлен в проект:** {current_project_name}\n\n"
        response_text += f"📄 **Файл:** {file_name}\n"

        if result["success"]:
            file_info = result["file_info"]
            response_text += f"💾 **Размер:** {file_info['size_bytes'] / 1024:.1f} КБ\n"
            if description:
                response_text += f"📝 **Описание:** {description}\n"

        # Добавляем экспертное заключение
        if expert_opinion and is_pdf:
            response_text += f"\n{'='*40}\n\n"
            response_text += f"🎓 **ЭКСПЕРТНОЕ ЗАКЛЮЧЕНИЕ:**\n\n{expert_opinion}"

        # Отправляем ответ частями если нужно (БЕЗ parse_mode для избежания ошибок парсинга)
        max_length = 4000
        if len(response_text) > max_length:
            parts = [response_text[i:i+max_length] for i in range(0, len(response_text), max_length)]
            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(response_text)

    except Exception as e:
        logger.error(f"Ошибка обработки документа: {e}")
        await update.message.reply_text(f"❌ Ошибка обработки: {str(e)}")


async def handle_project_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка создания нового проекта"""
    user_id = update.effective_user.id
    project_name = update.message.text.strip()

    context.user_data["waiting_for_project_name"] = False

    if PROJECTS_AVAILABLE:
        result = create_project(user_id, project_name)
        if result["success"]:
            context.user_data["current_project"] = project_name

            keyboard = [[InlineKeyboardButton("« К проектам", callback_data="project_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"✅ **Проект создан:** {project_name}\n\n"
                "📌 Проект активирован!\n"
                "Все ваши вопросы и ответы теперь сохраняются в этот проект.\n\n"
                "Можете начинать работу!",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"❌ Ошибка создания проекта: {result.get('error', '')}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений с контекстом истории"""
    user_id = update.effective_user.id
    # Проверяем, есть ли распознанный текст из голосового сообщения
    question = context.user_data.pop('_voice_recognized_text', None) or update.message.text

    # Обработка кнопки "🎤 Real-time чат"
    if question and question.strip() == "🎤 Real-time чат":
        if OPENAI_REALTIME_AVAILABLE:
            await start_realtime_chat_command(update, context)
        else:
            await update.message.reply_text(
                "❌ **Real-time чат недоступен**\n\n"
                "Требуется OPENAI_API_KEY.\n"
                "Попробуйте команду: /realtime_chat",
                parse_mode="Markdown"
            )
        return

    # Проверка ожидания названия проекта
    if context.user_data.get("waiting_for_project_name"):
        await handle_project_creation(update, context)
        return

    # Проверка ожидания заметки
    if context.user_data.get("waiting_for_note"):
        project_name = context.user_data["waiting_for_note"]
        context.user_data["waiting_for_note"] = None
        note_text = question.strip()

        if PROJECTS_AVAILABLE:
            project = load_project(user_id, project_name)
            if project:
                # Сохраняем заметку как отдельную запись
                project.add_conversation_entry(
                    f"[ЗАМЕТКА] {note_text[:50]}...",
                    note_text,
                    "note"
                )

                keyboard = [[InlineKeyboardButton("« К проекту", callback_data=f"proj_open_{project_name}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    f"✅ Заметка добавлена в проект **{project_name}**",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("❌ Ошибка загрузки проекта")


    # === СТАРАЯ ОБРАБОТКА ШАБЛОНОВ (ЗАМЕНЕНА НА ИНТЕРАКТИВНЫЕ ОБРАБОТЧИКИ v1.0) ===
    # Теперь используются ConversationHandler из document_handlers.py
    # Эта секция оставлена для совместимости, но больше не используется
    #
    # if context.user_data.get("waiting_for_template_params"):
    #     ... (старый код удалён)

    # Проверка rate limit
    if not check_rate_limit(user_id):
        await update.message.reply_text(
            "⏱️ Слишком много запросов!\n\n"
            f"Вы можете отправлять до {RATE_LIMIT_MAX_REQUESTS} запросов в минуту.\n"
            "Пожалуйста, подождите немного и попробуйте снова."
        )
        return

    # Добавляем вопрос пользователя в историю
    await add_message_to_history_async(user_id, 'user', question)

    # ============================================================================
    # LLM COUNCIL: Автоматическое определение сложных вопросов
    # ============================================================================
    if LLM_COUNCIL_AVAILABLE:
        is_complex, complexity_reason = is_complex_question(question)
        
        if is_complex:
            logger.info(f"🏛️ LLM Council: Сложный вопрос обнаружен - {complexity_reason}")
            
            # Отправляем сообщение о работе Совета
            council_thinking = await update.message.reply_text(
                "🏛️ **Сложный вопрос — собираю Совет AI...**\n\n"
                f"📊 Причина: _{complexity_reason}_\n\n"
                "⏳ Этап 1/3: Получаю мнения экспертов\n"
                "• Grok — технический анализ\n"
                "• Claude — детальная экспертиза\n"
                "• Gemini — практические рекомендации\n\n"
                "_Это займёт 30-60 секунд для максимального качества..._",
                parse_mode="Markdown"
            )
            
            try:
                council = get_llm_council()
                if council:
                    # Получаем контекст диалога
                    conversation_history = get_conversation_context(user_id)
                    context_text = ""
                    if conversation_history:
                        recent = conversation_history[-3:]
                        context_text = "\n".join([f"{m['role']}: {m['content'][:200]}" for m in recent])
                    
                    # Запускаем консультацию (skip_review=True для ускорения)
                    result = await council.consult(question, context=context_text, skip_review=True)
                    
                    if result["success"]:
                        final_answer = result["final_answer"]
                        duration = result["duration_seconds"]
                        models = result["models_used"]
                        
                        footer = f"\n\n---\n🏛️ _Совет AI: {', '.join(models)} | {duration:.1f} сек_"
                        
                        max_len = 4000 - len(footer)
                        if len(final_answer) > max_len:
                            final_answer = final_answer[:max_len] + "..."
                        
                        await council_thinking.edit_text(
                            final_answer + footer,
                            parse_mode="Markdown"
                        )
                        
                        await add_message_to_history_async(user_id, 'assistant', final_answer)
                        logger.info(f"✅ LLM Council auto: ответ за {duration:.1f} сек для user {user_id}")
                        return  # Ответ от Совета отправлен
                    else:
                        # Совет не смог ответить - продолжаем обычную обработку
                        await council_thinking.delete()
                        logger.warning("LLM Council: не удалось получить ответ, fallback to single model")
                else:
                    await council_thinking.delete()
            except Exception as e:
                logger.error(f"LLM Council auto error: {e}")
                try:
                    await council_thinking.delete()
                except:
                    pass
                # Продолжаем обычную обработку

    # Отправляем сообщение о процессе и сохраняем его для последующего удаления
    thinking_text = "🤔 Думаю над вашим вопросом... \n\nВы можете не ждать, я пришлю уведомление 😉"

    # Если работаем в проекте - указываем это
    if PROJECTS_AVAILABLE:
        active_project = context.user_data.get("current_project")
        if active_project:
            thinking_text = f"🤔 Анализирую в контексте проекта **{active_project}**...\n\nВы можете не ждать, я пришлю уведомление 😉"

    thinking_message = await update.message.reply_text(thinking_text, parse_mode="Markdown")

    try:
        # ============================================================================
        # ОПТИМИЗАЦИЯ: Умный выбор модели (Claude/Gemini/Grok)
        # ============================================================================
        if SMART_WRAPPER_AVAILABLE:
            smart_result = await smart_model_selection_text(
                question=question,
                user_id=user_id,
                thinking_message=thinking_message,
                update=update,
                context=context
            )

            # Если умный выбор обработал запрос - выходим
            if smart_result and smart_result.get("success"):
                return  # Ответ уже отправлен

        # Если умный выбор не сработал или недоступен - продолжаем с Grok

        # ВАЖНО: главный режим — единый универсальный промпт с авто-адаптацией.
        # Роли (/role) остаются как функция интерфейса, но НЕ должны переопределять system_prompt.
        # Поэтому здесь не подставляем role-based промпт.
        system_prompt = ""  # будет установлен ниже перед вызовом модели

        # --- Legacy блок промпта (оставлен как «текст-справка», не влияет на работу бота) ---
        """


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

        # --- конец legacy блока ---

        # Проверяем активный проект и адаптируем промпт
        if PROJECTS_AVAILABLE:
            current_project_name = context.user_data.get("current_project")
            if current_project_name:
                # Загружаем проект для получения контекста
                project = load_project(user_id, current_project_name)
                if project:
                    project_log_count = len(project.get_conversation_log())

                    # Добавляем специальные инструкции для работы в проекте
                    system_prompt += f"""

🎯 **ВАЖНО: Вы работаете в контексте проекта "{current_project_name}"!**

📋 **ОСОБЕННОСТИ РАБОТЫ В ПРОЕКТЕ:**

1. **АДАПТИВНАЯ ДЛИНА ОТВЕТА** - подстраивайтесь под тип запроса:

   📝 **КОРОТКИЙ ОТВЕТ** (1-3 предложения) если пользователь:
   • Просит сохранить файл/фото/документ
   • Отправляет информацию для фиксации
   • Делает заметку или комментарий
   • Подтверждает что-то ("да", "сохрани", "запиши")

   Пример: "✅ Сохранил. Фото фундамента от 28.11.2025 - видны трещины в зоне стыка."

   📚 **РАЗВЁРНУТЫЙ ОТВЕТ** (полная структура) если:
   • Задан технический вопрос
   • Требуется экспертиза или анализ
   • Просят объяснить или посоветовать
   • Нужна ссылка на нормативы

2. **КОНТЕКСТ ПРОЕКТА:**
   • В проекте уже {project_log_count} записей - используйте предыдущий контекст
   • Помните о чём говорили раньше в рамках ЭТОГО проекта
   • Ссылайтесь на прошлые обсуждения если уместно

3. **ЕСТЕСТВЕННЫЙ ДИАЛОГ:**
   • Общайтесь как живой AI-ассистент проекта, а не как справочник
   • Используйте "я сохранил", "я заметил", "как мы обсуждали ранее"
   • Будьте лаконичны когда нужно просто зафиксировать информацию

4. **ПРИМЕРЫ ПРАВИЛЬНОГО ПОВЕДЕНИЯ:**

   ❌ ПЛОХО (на запрос "сохрани эту смету"):
   "📌 Короткий ответ: Я сохранил смету в проект.
   📐 Подробности: Смета сохранена в базе данных проекта {current_project_name}...
   💡 Практический совет: Рекомендую также сохранить копию в облаке...
   📚 Ссылки: СП 48.13330.2019..."

   ✅ ХОРОШО:
   "✅ Сохранил смету. Бюджет объекта: 15.2 млн руб, срок 4 мес."

   ❌ ПЛОХО (на вопрос "какой бетон нужен для фундамента"):
   "Бетон В25"

   ✅ ХОРОШО:
   "📌 Для фундамента нужен бетон класса В25 (М350)

   📐 Подробности:
   • Марка по морозостойкости: F150-F200
   • Водонепроницаемость: W6-W8
   • Подвижность: П3-П4 для укладки в опалубку

   💡 На площадке: проверяйте осадку конуса при приёмке (должна быть 10-15 см для П3)

   📚 СП 63.13330.2018 п.5.3.2 - требования к бетону фундаментов"

**ГЛАВНОЕ ПРАВИЛО: Анализируйте намерение пользователя и отвечайте соразмерно запросу!**
"""

        # Получаем контекст предыдущих сообщений
        conversation_history = get_conversation_context(user_id)

        # Добавляем текущий вопрос
        conversation_history.append({"role": "user", "content": question})

        # 🤖 УМНЫЙ ВЫБОР МОДЕЛИ: Определяем намерение пользователя
        intent_info = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: classify_user_intent(question)
        )

        selected_model = intent_info["model"]
        selected_max_tokens = intent_info["max_tokens"]
        intent_type = intent_info.get("intent_type", "technical_question")

        # 🌐 ИНСТРУМЕНТЫ ПОИСКА: Включаем для ВСЕХ запросов (всегда проверяем актуальность в интернете)
        search_params = {
            "mode": "auto", "return_citations": True, "sources": [{"type": "web"}, {"type": "news"}, {"type": "x"}]}  # Поиск в интернете
        logger.info("🌐 Grok Tools включены для всех запросов: live_search")

        # Универсальный системный промпт v5.0 (оптимизирован)
        # Использует промпты из optimized_prompts.py
        if OPTIMIZED_PROMPTS_AVAILABLE:
            system_prompt = GROK_SYSTEM_PROMPT_GENERAL
            logger.info("📝 Используется оптимизированный промпт v5.0")
        else:
            system_prompt = """Вы — «СтройНадзорAI» v5.0, AI-ассистент по строительству в РФ.

🎯 ПРИНЦИПЫ: краткость, точность, практичность, безопасность.
📱 ФОРМАТ: для телефона, 35 символов в строке, эмодзи в начале разделов.
📌 СТРУКТУРА: Суть → Детали → Действия → Контроль.
🌐 ПОИСК: live_search для актуальных данных.
⚠️ БЕЗОПАСНОСТЬ: на первом месте для опасных работ."""

        # 🌤️ ПОГОДА: Проверяем, является ли это запросом о погоде
        if WEATHER_AVAILABLE and is_weather_query(question):
            try:
                logger.info("🌤️ Обнаружен запрос о погоде")
                weather_response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: get_weather(question)
                )

                if weather_response:
                    # Удаляем thinking message
                    try:
                        await thinking_message.delete()
                    except:
                        pass

                    # Отправляем погоду
                    await update.message.reply_text(weather_response, parse_mode="Markdown")

                    # Добавляем в историю
                    await add_message_to_history_async(user_id, 'user', question)
                    await add_message_to_history_async(user_id, 'assistant', weather_response)

                    logger.info("✅ Погода отправлена пользователю")
                    return  # Прерываем обработку
            except Exception as e:
                logger.error(f"Ошибка получения погоды: {e}")
                # Продолжаем обычную обработку если погода не получена

        # 🌐 ВЕБ-ПОИСК: Теперь выполняется через Grok инструменты (live_search)
        # Старый механизм perform_live_search отключен - Grok сам ищет актуальную информацию

        # 🎨 ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ: Проверяем, нужна ли генерация
        # ОТКЛЮЧЕНО: Теперь обрабатывается через smart_model_wrapper → gemini_image
        if False and GEMINI_AVAILABLE and should_generate_image(question):
            logger.info("🎨 Обнаружен запрос на генерацию изображения")

            # Отправляем сообщение о генерации
            generating_msg = await update.message.reply_text(
                "📐 Генерирую технический чертёж через DALL-E 3...\n\n"
                "Шаг 1/2: xAI Grok создаёт детальный промпт\n"
                "• С точными размерами и цифрами\n"
                "• С аннотациями на русском\n"
                "• В стиле технической документации"
            )

            try:
                # Шаг 1: Получаем детальный промпт от xAI Grok
                client = get_grok_client()

                # Используем оптимизированный промпт из optimized_prompts.py
                blueprint_system_prompt = GEMINI_IMAGE_PROMPT_SYSTEM if OPTIMIZED_PROMPTS_AVAILABLE else """Ты — эксперт по созданию ТЕХНИЧЕСКИХ промптов для DALL-E 3 по ГОСТ.
📐 ОБЯЗАТЕЛЬНО: размеры в мм/м, штриховка по ГОСТ 2.306, русские подписи, масштаб.
Формат: [Английский DALL-E prompt] ---ОПИСАНИЕ--- [Описание на русском]"""

                prompt_messages = [
                    {
                        "role": "system",
                        "content": blueprint_system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"Создай детальный промпт для DALL-E 3 на основе запроса: {question}"
                    }
                ]

                logger.info("📝 Запрашиваем детальный технический промпт у xAI Grok...")
                grok_response = await client.chat_completions_create_async(
                    model="grok-3",
                    messages=prompt_messages,
                    max_tokens=1500,  # Увеличено для детальных технических промптов с размерами
                    temperature=0.5  # Снижено для большей точности и конкретики
                )

                grok_full_response = grok_response['choices'][0]['message']['content'].strip()

                # Разделяем промпт для DALL-E и описание для пользователя
                if "---ОПИСАНИЕ---" in grok_full_response:
                    parts = grok_full_response.split("---ОПИСАНИЕ---")
                    dalle_prompt = parts[0].strip()
                    russian_description = parts[1].strip() if len(parts) > 1 else ""
                else:
                    dalle_prompt = grok_full_response
                    russian_description = ""

                logger.info(f"✅ Промпт от Grok получен: {dalle_prompt[:100]}...")

                # Обновляем сообщение
                await generating_msg.edit_text(
                    "📐 Генерирую технический чертёж через DALL-E 3...\n\n"
                    "✅ Шаг 1/2: Детальный промпт готов\n"
                    "⏳ Шаг 2/2: DALL-E 3 рисует чертёж с размерами..."
                )

                # Шаг 2: Генерируем изображение через DALL-E с промптом от Grok
                # Используем HD качество для технических чертежей с размерами
                result = await generate_construction_image_gemini(
                    dalle_prompt,
                    size="1024x1024",
                    quality="hd"  # Высокое качество для чёткости цифр и линий
                )

                if result and result.get("image_data"):
                    # Удаляем сообщение о генерации
                    try:
                        await generating_msg.delete()
                        await thinking_message.delete()
                    except:
                        pass

                    # Отправляем изображение
                    result["image_data"].seek(0)

                    # Используем русское описание от Grok (адаптировано для телефона)
                    if russian_description:
                        caption = f"🎨 **Сгенерировано DALL-E 3**\n\n{russian_description}\n\n"
                        caption += "💡 *Координация: xAI Grok + OpenAI DALL-E 3*"
                    else:
                        # Fallback если описание не получено
                        caption = f"🎨 **Изображение сгенерировано через DALL-E 3**\n\n"
                        caption += f"📝 **Промпт от xAI Grok:**\n_{dalle_prompt[:100]}..._\n\n"
                        caption += "💡 *Координация: xAI Grok + OpenAI DALL-E 3*"

                    await update.message.reply_photo(
                        photo=result["image_data"],
                        caption=caption,
                        parse_mode="Markdown"
                    )

                    # Добавляем в историю
                    await add_message_to_history_async(user_id, 'user', question)
                    await add_message_to_history_async(user_id, 'assistant', f"[Сгенерировано изображение с промптом от xAI Grok]")

                    logger.info(f"✅ Изображение сгенерировано и отправлено")

                    # НЕ прерываем обработку - продолжаем генерировать текстовый ответ от Grok
                    # Создаем новое thinking сообщение для текстового ответа
                    thinking_message = await update.message.reply_text("⏳ Готовлю текстовое описание...")
                else:
                    await generating_msg.edit_text("❌ Не удалось сгенерировать изображение")
            except Exception as e:
                logger.error(f"Ошибка генерации: {e}")
                await generating_msg.edit_text(f"❌ Ошибка: {str(e)}")

        # 🎯 ГЕНЕРАЦИЯ ОТВЕТА (с выбором режима)
        client = get_grok_client()
        loop = asyncio.get_event_loop()
        # Добавляем system prompt в начало истории
        messages_with_system = [{"role": "system", "content": system_prompt}] + conversation_history

        answer = ""

        # === STREAMING РЕЖИМ (постепенное появление текста) ===
        if STREAMING_ENABLED:
            streaming_msg = await update.message.reply_text("⏳ Генерирую ответ...")

            try:
                # Удаляем thinking message
                try:
                    await thinking_message.delete()
                except:
                    pass

                # Переменные для streaming
                last_update_time = 0
                last_update_length = 0
                update_interval = 0.15  # Обновляем каждые 0.15 секунды - быстро и плавно
                chars_threshold = 8  # Или каждые 8 новых символов
                typing_action_interval = 3  # Индикатор "печатает" раз в 3 секунды
                last_typing_action = 0

                logger.info("🚀 Начинаем двухфазную генерацию...")

                # ФАЗА 1: Быстрое начало (первые 300-500 токенов от быстрой модели)
                first_phase_answer = ""
                logger.info("📝 Фаза 1: Быстрая модель для начала ответа...")

                async for chunk in call_grok_with_streaming(
                    client,
                    model="grok-4-1-fast",  # Быстрая модель
                    messages=messages_with_system,
                    max_tokens=500,  # Только начало
                    temperature=0.7,
                    search_parameters=search_params
                ):
                    first_phase_answer += chunk
                    answer += chunk

                    # Обновляем сообщение часто для видимости печатания
                    import time
                    current_time = time.time()
                    chars_diff = len(answer) - last_update_length

                    if current_time - last_update_time >= update_interval or chars_diff >= chars_threshold:
                        try:
                            display_text = f"{answer}▊"  # Курсор печатания
                            await streaming_msg.edit_text(display_text[:4096])
                            last_update_time = current_time
                            last_update_length = len(answer)

                            # Показываем индикатор печатания редко (не замедляет)
                            if current_time - last_typing_action >= typing_action_interval:
                                await update.message.chat.send_action("typing")
                                last_typing_action = current_time
                        except Exception:
                            pass

                logger.info(f"✅ Фаза 1 завершена: {len(first_phase_answer)} символов")

                # ФАЗА 2: Продолжение от основной модели (если нужен развернутый ответ)
                # Запускаем только если: 1) первая фаза дала достаточно текста И 2) выбрана полная модель (не быстрая)
                if len(first_phase_answer) >= 400 and selected_model != "grok-4-1-fast":
                    logger.info("📝 Фаза 2: Основная модель для продолжения...")

                    # Создаём промпт для продолжения
                    continuation_messages = messages_with_system + [
                        {"role": "assistant", "content": first_phase_answer},
                        {"role": "user", "content": "Продолжи ответ, добавь детали, примеры и ссылки на нормативы."}
                    ]

                    async for chunk in call_grok_with_streaming(
                        client,
                        model=selected_model,  # Основная модель
                        messages=continuation_messages,
                        max_tokens=selected_max_tokens - 500,
                        temperature=0.7,
                        search_parameters=search_params
                    ):
                        answer += chunk

                        # Обновляем сообщение часто
                        import time
                        current_time = time.time()
                        chars_diff = len(answer) - last_update_length

                        if current_time - last_update_time >= update_interval or chars_diff >= chars_threshold:
                            try:
                                display_text = f"{answer}▊"
                                await streaming_msg.edit_text(display_text[:4096])
                                last_update_time = current_time
                                last_update_length = len(answer)

                                # Показываем индикатор печатания редко (не замедляет)
                                if current_time - last_typing_action >= typing_action_interval:
                                    await update.message.chat.send_action("typing")
                                    last_typing_action = current_time
                            except Exception:
                                pass

                    logger.info("✅ Фаза 2 завершена")

                # Финальное обновление без курсора
                try:
                    # Если ответ короче 4096 символов - обновляем сообщение
                    if len(answer) <= 4096:
                        await streaming_msg.edit_text(answer)
                    else:
                        # Если ответ длинный - отправляем полную версию в новом сообщении
                        await streaming_msg.edit_text(f"{answer[:4000]}...\n\n⚠️ Ответ был слишком длинным. Полная версия ниже:")
                        # Отправляем полный ответ в отдельном сообщении
                        chunks = [answer[i:i+4000] for i in range(0, len(answer), 4000)]
                        for chunk in chunks:
                            await update.message.reply_text(chunk)
                except Exception as e:
                    logger.error(f"Ошибка финального обновления streaming: {e}")
                    # Fallback: отправляем полный ответ в любом случае
                    try:
                        chunks = [answer[i:i+4000] for i in range(0, len(answer), 4000)]
                        for chunk in chunks:
                            await update.message.reply_text(chunk)
                    except:
                        pass

            except Exception as stream_error:
                logger.error(f"❌ Ошибка streaming: {stream_error}")
                # Fallback на обычный режим
                try:
                    await streaming_msg.delete()
                except:
                    pass

                thinking_message = await update.message.reply_text("🤔 Думаю над вашим вопросом...")

                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: call_grok_with_retry(
                        client,
                        model=selected_model,
                        max_tokens=selected_max_tokens,
                        temperature=0.7,
                        messages=messages_with_system,
                        search_parameters=search_params
                    )
                )
                answer = response["choices"][0]["message"]["content"]

                try:
                    await thinking_message.delete()
                except:
                    pass

        # === ОБЫЧНЫЙ РЕЖИМ (классический - ответ приходит сразу целиком) ===
        else:
            logger.info("📝 Обычный режим: генерация ответа без streaming...")

            response = await loop.run_in_executor(
                None,
                lambda: call_grok_with_retry(
                    client,
                    model=selected_model,
                    max_tokens=selected_max_tokens,
                    temperature=0.7,
                    messages=messages_with_system,
                    search_parameters=search_params
                )
            )
            answer = response["choices"][0]["message"]["content"]

            try:
                await thinking_message.delete()
            except:
                pass

        # Добавляем ответ бота в историю
        await add_message_to_history_async(user_id, 'assistant', answer)

        # 🎯 ГЕНЕРАЦИЯ УМНЫХ СВЯЗАННЫХ ВОПРОСОВ (v3.1) - в фоне
        related_questions = []
        if IMPROVEMENTS_V3_AVAILABLE:
            try:
                # Создаём промпт для генерации связанных вопросов
                related_q_prompt = generate_smart_related_questions_prompt(question, answer)

                # Генерируем вопросы используя тот же API
                loop = asyncio.get_event_loop()
                related_response = await loop.run_in_executor(
                    None,
                    lambda: call_grok_with_retry(
                        client,
                        model="grok-4-1-fast",  # Используем быструю модель
                        max_tokens=300,
                        temperature=0.8,
                        messages=[{"role": "user", "content": related_q_prompt}]
                    )
                )
                related_q_text = related_response["choices"][0]["message"]["content"]

                # Парсим сгенерированные вопросы
                related_questions = parse_generated_questions(related_q_text)

                # Сохраняем в контексте пользователя для обработки кликов
                if related_questions:
                    context.user_data["related_questions"] = related_questions
                    logger.info(f"✅ Сгенерировано {len(related_questions)} связанных вопросов")

            except Exception as e:
                logger.error(f"❌ Ошибка генерации связанных вопросов: {e}")
                related_questions = []

        # Сохраняем в активный проект (если есть)
        project_saved = False
        saved_project_name = None
        if PROJECTS_AVAILABLE:
            current_project_name = context.user_data.get("current_project")
            if current_project_name:
                try:
                    project = load_project(user_id, current_project_name)
                    if project:
                        project.add_conversation_entry(question, answer, "qa")
                        logger.info(f"✅ Диалог сохранён в проект: {current_project_name}")
                        project_saved = True
                        saved_project_name = current_project_name
                except Exception as e:
                    logger.error(f"❌ Ошибка сохранения в проект: {e}")

        # Определяем упомянутые нормативы
        mentioned_regs = []
        for reg_code in REGULATIONS.keys():
            if reg_code in answer:
                mentioned_regs.append(reg_code)

        # Формируем финальный ответ
        # По умолчанию показываем только ответ (как в примере: всё остальное можно раскрыть/скрыть кнопками)
        result = answer

        # Веб-поиск теперь выполняется через инструменты Grok (live_search)

        # Сохраняем доп.информацию в context.user_data, чтобы можно было «раскрыть» по кнопке
        context.user_data["last_answer"] = answer
        context.user_data["last_question"] = question
        context.user_data["last_mentioned_regs"] = mentioned_regs

        # Доп.данные про проект тоже сохраняем отдельно — показывать будем только по запросу
        context.user_data["last_project_saved"] = bool(project_saved)
        context.user_data["last_saved_project_name"] = saved_project_name if project_saved else None

        # Создаём подсказки в стиле GigaChat (reply keyboard над полем ввода)
        reply_markup = None
        if IMPROVEMENTS_V3_AVAILABLE:
            reply_markup = create_reply_suggestions_keyboard(related_questions=related_questions)

        # Добавляем кнопку "Применить изменения" если в ответе есть код (только для разработчика)
        user_id = update.effective_user.id
        if AUTO_APPLY_AVAILABLE and should_show_apply_button(answer) and is_developer(user_id):
            reply_markup = add_apply_button(reply_markup)

        # Обновляем streaming сообщение финальным ответом с кнопками
        max_length = 4000  # Лимит Telegram
        if len(result) > max_length:
            # Если сообщение слишком длинное, удаляем streaming_msg и отправляем по частям
            try:
                await streaming_msg.delete()
            except:
                pass

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
                part_reply_markup = None
                if i == len(parts) - 1:
                    part_reply_markup = reply_markup

                if i == 0:
                    await update.message.reply_text(part, reply_markup=part_reply_markup)
                else:
                    await update.message.reply_text(
                        f"(продолжение {i+1}/{len(parts)})\n\n{part}",
                        reply_markup=part_reply_markup
                    )
        else:
            # Обновляем streaming сообщение финальным ответом с кнопками
            try:
                await streaming_msg.edit_text(result, reply_markup=reply_markup)
            except Exception as e:
                # Если не удалось отредактировать, отправляем новое сообщение
                logger.warning(f"Could not edit streaming message: {e}")
                try:
                    await streaming_msg.delete()
                except:
                    pass
                await update.message.reply_text(result, reply_markup=reply_markup)

        logger.info(f"Question answered for user {update.effective_user.id} by Claude")

    except Exception as e:
        logger.error(f"Error answering question: {e}")

        # Удаляем сообщение "думаю над вопросом" даже в случае ошибки
        try:
            await thinking_message.delete()
        except:
            pass

        # Удаляем streaming_msg если он существует
        try:
            if 'streaming_msg' in locals():
                await streaming_msg.delete()
        except:
            pass

        await update.message.reply_text(
            f"❌ Ошибка при обработке вопроса: {str(e)}\n\nПопробуйте переформулировать вопрос."
        )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок"""
    query = update.callback_query


# (removed unused inline-menu helper)

    # Пропускаем callbacks которые относятся к ConversationHandler калькуляторов
    calculator_prefixes = [
        "concrete_class_", "concrete_wastage_",
        "rebar_diameter_", "rebar_spacing_", "rebar_type_",
        "formwork_type_", "formwork_duration_",
        "elec_", "water_", "winter_method_"
    ]
    if any(query.data.startswith(prefix) for prefix in calculator_prefixes):
        # Не обрабатываем здесь - пусть обработает ConversationHandler
        return

    # Специальная обработка для голосового ассистента (Gemini Live)
    if query.data == "voice_chat_start":
        await query.answer("🎤 Запускаю голосовой ассистент...")

        if VOICE_ASSISTANT_AVAILABLE:
            sent_message = await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="🎤 Инициализация голосового ассистента..."
            )
            adapted_update = Update(
                update_id=update.update_id,
                message=sent_message
            )
            await start_voice_chat_command(adapted_update, context)
        else:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="❌ **Голосовой ассистент Gemini недоступен**\n\n"
                    "Попробуйте OpenAI: /realtime_chat",
                parse_mode="Markdown"
            )
        return

    # Обработка realtime_chat_start теперь в ConversationHandler (openai_realtime_bot_integration.py)

    await query.answer()

    if query.data == "regulations":
        # Создаём адаптированный update для вызова команды
        adapted_update = Update(
            update_id=update.update_id,
            message=query.message
        )
        await regulations_command(adapted_update, context)
    elif query.data == "examples":
        # Создаём адаптированный update для вызова команды
        adapted_update = Update(
            update_id=update.update_id,
            message=query.message
        )
        await examples_command(adapted_update, context)
    elif query.data == "help":
        # Создаём адаптированный update для вызова команды
        adapted_update = Update(
            update_id=update.update_id,
            message=query.message
        )
        await help_command(adapted_update, context)
    elif query.data == "stats":
        # Создаём адаптированный update для вызова команды
        adapted_update = Update(
            update_id=update.update_id,
            message=query.message
        )
        await stats_command(adapted_update, context)
    elif query.data == "calculators_menu":
        # Кнопка "Калькуляторы" из главного меню
        if CALCULATORS_AVAILABLE and IMPROVEMENTS_V3_AVAILABLE:
            keyboard = create_calculators_menu()
            await query.edit_message_text(
                "🧮 **СТРОИТЕЛЬНЫЕ КАЛЬКУЛЯТОРЫ**\n\n"
                "Выберите калькулятор:",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("⚠️ Модуль калькуляторов недоступен.")
    elif query.data == "faq_menu":
        # Кнопка "Частые вопросы" из главного меню
        if FAQ_AVAILABLE:
            # Создаём адаптированный update для вызова команды
            adapted_update = Update(
                update_id=update.update_id,
                message=query.message
            )
            await faq_command(adapted_update, context)
        else:
            await query.edit_message_text("⚠️ Модуль FAQ недоступен.")
    elif query.data == "templates":
        # Кнопка "Шаблоны" из главного меню
        if TEMPLATES_AVAILABLE:
            keyboard = []
            for template_id, info in DOCUMENT_TEMPLATES.items():
                keyboard.append([
                    InlineKeyboardButton(
                        text=info["name"],
                        callback_data=f"template_{template_id}"
                    )
                ])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📄 **ШАБЛОНЫ ДОКУМЕНТОВ**\n\n"
                "Выберите тип документа для генерации:",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("⚠️ Модуль шаблонов недоступен.")
    elif query.data == "role":
        # Кнопка "Выбрать роль" из главного меню
        if ROLES_AVAILABLE:
            # Создаём адаптированный update для вызова команды
            adapted_update = Update(
                update_id=update.update_id,
                message=query.message
            )
            await role_command(adapted_update, context)
        else:
            await query.edit_message_text("⚠️ Модуль ролей недоступен.")
    elif query.data == "suggestions":
        # Кнопка "Предложения" из главного меню
        if SUGGESTIONS_AVAILABLE:
            await suggestions_menu(update, context)
        else:
            await query.edit_message_text("⚠️ Модуль предложений недоступен.")
    elif query.data == "dev_mode":
        # Кнопка "Разработчик" из главного меню
        await query.edit_message_text(
            "🔧 **РЕЖИМ РАЗРАБОТЧИКА**\n\n"
            "Для входа в режим разработчика используйте команду /dev\n\n"
            "Режим разработчика позволяет:\n"
            "• Отправлять запросы на изменение кода\n"
            "• Получать готовые решения от AI\n"
            "• (Локально) Автоматически применять и пушить изменения\n\n"
            "Введите: /dev",
            parse_mode="Markdown"
        )
    elif query.data == "project_menu":
        # Кнопка "Проект" из главного меню
        if PROJECTS_AVAILABLE:
            user_id = update.effective_user.id
            projects = get_user_projects(user_id)
            current_project = context.user_data.get("current_project")

            keyboard = [
                [InlineKeyboardButton("➕ Создать новый проект", callback_data="proj_create"),
                 InlineKeyboardButton("📂 Мои проекты", callback_data="proj_list")]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            status_text = f"**📁 УПРАВЛЕНИЕ ПРОЕКТАМИ**\n\n"
            if current_project:
                status_text += f"✅ Активный проект: **{current_project}**\n\n"
            else:
                status_text += "Активный проект: _не выбран_\n\n"

            status_text += f"Всего проектов: {len(projects)}\n\n"
            status_text += "Выберите действие:"

            await query.edit_message_text(
                status_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("⚠️ Модуль проектов недоступен.")
    elif query.data == "proj_list":
        # Список всех проектов пользователя
        if PROJECTS_AVAILABLE:
            user_id = update.effective_user.id
            projects = get_user_projects(user_id)
            current_project = context.user_data.get("current_project")

            keyboard = []

            if not projects:
                keyboard.append([
                    InlineKeyboardButton("➕ Создать первый проект", callback_data="proj_create")
                ])
            else:
                # Список существующих проектов
                for proj in projects:
                    emoji = "✅ " if proj == current_project else "📁 "
                    keyboard.append([
                        InlineKeyboardButton(
                            text=f"{emoji}{proj}",
                            callback_data=f"proj_open_{proj}"
                        )
                    ])

            # Кнопка назад
            keyboard.append([
                InlineKeyboardButton("« Назад к меню проектов", callback_data="project_menu")
            ])

            reply_markup = InlineKeyboardMarkup(keyboard)

            status_text = f"**📂 МОИ ПРОЕКТЫ**\n\n"
            if current_project:
                status_text += f"✅ Активный: **{current_project}**\n\n"

            if projects:
                status_text += f"Всего проектов: {len(projects)}\n\n"
                status_text += "Выберите проект для работы:"
            else:
                status_text += "У вас пока нет проектов.\n\n"
                status_text += "Создайте первый проект для начала работы!"

            await query.edit_message_text(
                status_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("⚠️ Модуль проектов недоступен.")
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

    # === ОБРАБОТЧИКИ КНОПОК v3.0 ===

    elif query.data == "clarify":
        # Кнопка "Уточнить"
        await query.edit_message_text(
            "🔍 **Уточняющие вопросы:**\n\n"
            "Вы можете задать дополнительный вопрос по теме.\n\n"
            "Например:\n"
            "• Какие ещё требования?\n"
            "• Покажи расчёт\n"
            "• Какие документы нужны?\n"
            "• Что если изменить параметры?\n\n"
            "Просто напишите ваш вопрос в чат!",
            parse_mode='Markdown'
        )

    elif query.data == "example":
        # Кнопка "Пример"
        await query.edit_message_text(
            "💡 **Практический пример:**\n\n"
            "Чтобы получить пример по вашей теме, напишите:\n\n"
            "• \"Покажи пример расчёта\"\n"
            "• \"Дай практический пример\"\n"
            "• \"Как это применить на практике?\"\n\n"
            "Я предоставлю конкретный пример с цифрами и расчётами!",
            parse_mode='Markdown'
        )

    # legacy callbacks (раньше был отдельный экран связанных вопросов)
    elif query.data == "show_related_questions":
        await query.answer("ℹ️ Связанные вопросы теперь сразу под ответом", show_alert=True)

    elif query.data == "hide_related_questions":
        await query.answer("ℹ️ Связанные вопросы теперь сразу под ответом", show_alert=True)

    elif query.data.startswith("related_q_"):
        # Клик на связанный вопрос - отправляем его как новый вопрос
        try:
            question_index = int(query.data.split("_")[-1])
            related_questions = context.user_data.get("related_questions", [])

            if question_index < len(related_questions):
                selected_question = related_questions[question_index]

                # Отправляем вопрос от имени пользователя
                await query.answer(f"Задаю вопрос: {selected_question[:50]}...")

                # Создаём фейковое сообщение с вопросом для обработки
                from telegram import Message, Chat, User as TelegramUser
                fake_message = Message(
                    message_id=0,
                    date=datetime.now(),
                    chat=query.message.chat,
                    from_user=query.from_user,
                    text=selected_question
                )
                fake_update = Update(update_id=0, message=fake_message)

                # Обрабатываем как обычный текстовый вопрос
                await handle_text(fake_update, context)
                logger.info(f"✅ Обработан связанный вопрос #{question_index}")
            else:
                await query.answer("⚠️ Вопрос не найден", show_alert=True)
        except Exception as e:
            logger.error(f"❌ Ошибка обработки связанного вопроса: {e}")
            await query.answer("⚠️ Ошибка обработки вопроса", show_alert=True)


    # ===== New inline "menu in one row" actions =====

    elif query.data == "answer_hide":
        # Скрыть «функции» (кнопки под сообщением) и оставить только текст ответа.
        # Это аналог системной кнопки Telegram «скрыть клавиатуру», но для InlineKeyboard.
        try:
            await query.edit_message_reply_markup(reply_markup=None)
            await query.answer("🫥 Скрыто")
        except Exception as e:
            logger.error(f"❌ Ошибка answer_hide: {e}")
            await query.answer("⚠️ Не удалось скрыть кнопки", show_alert=True)

    elif query.data == "answer_menu":
        # Показать/вернуть меню под ответ
        if not IMPROVEMENTS_V3_AVAILABLE:
            await query.answer("⚠️ Функция недоступна", show_alert=True)
            return

        related_questions = context.user_data.get("related_questions", [])
        keyboard = create_answer_buttons(related_questions=related_questions)
        try:
            await query.edit_message_reply_markup(reply_markup=keyboard)
            await query.answer("☰ Меню")
        except Exception as e:
            logger.error(f"❌ Ошибка answer_menu: {e}")
            await query.answer("⚠️ Не удалось показать меню", show_alert=True)

    elif query.data == "answer_more":
        # Попросить модель дать ещё одну версию ответа
        original_q = context.user_data.get("last_question")
        last_answer = context.user_data.get("last_answer")
        if not original_q:
            await query.answer("⚠️ Не найден исходный вопрос", show_alert=True)
            return

        await query.answer("🔁 Генерирую ещё вариант…")

        try:
            # Отправляем короткий follow-up промпт в общий обработчик (как новый вопрос)
            followup = (
                f"Дай альтернативную версию ответа на вопрос: {original_q}\n\n"
                f"Текущий ответ (для контекста):\n{last_answer}\n\n"
                "Сделай по-другому: другая структура/формулировки, но без выдуманных фактов."
            )

            from telegram import Message, Update
            fake_message = Message(
                message_id=0,
                date=datetime.now(),
                chat=query.message.chat,
                from_user=query.from_user,
                text=followup,
            )
            fake_update = Update(update_id=0, message=fake_message)
            await handle_text(fake_update, context)
        except Exception as e:
            logger.error(f"❌ Ошибка answer_more: {e}")
            await query.answer("⚠️ Не удалось сгенерировать вариант", show_alert=True)

    elif query.data == "answer_edit":
        # Подсказка пользователю как уточнить/переоформить запрос
        await query.answer("✏️", show_alert=False)
        try:
            await query.message.reply_text(
                "✏️ Напишите уточнение одним сообщением — я переработаю ответ.\n\n"
                "Примеры:\n"
                "• «Сделай короче и по пунктам»\n"
                "• «Дай 2 варианта решения»\n"
                "• «Укажи риски и как проверить качество»"
            )
        except Exception as e:
            logger.error(f"❌ Ошибка answer_edit: {e}")

    elif query.data == "show_regulations":
        # Кнопка "Нормативы" - показать категории
        if IMPROVEMENTS_V3_AVAILABLE:
            keyboard = create_regulations_category_menu()
            await query.edit_message_text(
                "📚 **НОРМАТИВНЫЕ ДОКУМЕНТЫ**\n\n"
                "Выберите категорию для просмотра документов:",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "📚 Используйте команду /regulations для просмотра всех нормативов.",
                parse_mode='Markdown'
            )

    elif query.data == "calculator":
        # Кнопка "Калькулятор" - показать меню калькуляторов
        if CALCULATORS_AVAILABLE:
            keyboard = create_calculators_menu()
            await query.edit_message_text(
                "🧮 **СТРОИТЕЛЬНЫЕ КАЛЬКУЛЯТОРЫ**\n\n"
                "Выберите нужный калькулятор:",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "⚠️ Модуль калькуляторов недоступен.",
                parse_mode='Markdown'
            )

    elif query.data == "save_query":
        # Кнопка "Сохранить"
        await query.edit_message_text(
            "💾 **Сохранение запроса**\n\n"
            "Функция сохранения будет доступна в следующем обновлении (v3.1).\n\n"
            "Запланировано:\n"
            "• Сохранение избранных запросов\n"
            "• Быстрый доступ к сохранённым\n"
            "• Экспорт в PDF/Word\n\n"
            "Следите за обновлениями!",
            parse_mode='Markdown'
        )

    # === ИНТЕРАКТИВНЫЕ КАЛЬКУЛЯТОРЫ v5.0 ===
    # ВАЖНО: calc_concrete и calc_reinforcement обрабатываются ConversationHandler
    # из calculator_handlers.py - НЕ дублировать здесь!

    elif query.data == "calc_brick":
        await query.edit_message_text(
            "🧱 **КАЛЬКУЛЯТОР КИРПИЧА/БЛОКОВ**\n\n"
            "Используйте пошаговый режим через меню или:\n"
            "`/calc_brick длина высота толщина тип проёмы`\n\n"
            "**Пример:**\n"
            "`/calc_brick 10 3 0.25 single 5`\n\n"
            "Параметры:\n"
            "• Длина и высота стены (м)\n"
            "• Толщина: 0.12, 0.25, 0.38, 0.51 м\n"
            "• Тип: single, one_and_half, double\n"
            "• Площадь проёмов (м²)",
            parse_mode='Markdown'
        )

    elif query.data == "calc_tile":
        await query.edit_message_text(
            "🔲 **КАЛЬКУЛЯТОР ПЛИТКИ**\n\n"
            "Используйте пошаговый режим через меню или:\n"
            "`/calc_tile длина ширина размер_плитки запас`\n\n"
            "**Пример:**\n"
            "`/calc_tile 5 4 0.3 10`\n\n"
            "Параметры:\n"
            "• Размеры помещения (м)\n"
            "• Размер плитки (м, например 0.3 для 30×30 см)\n"
            "• Запас на подрезку (%)",
            parse_mode='Markdown'
        )

    elif query.data == "calc_paint":
        await query.edit_message_text(
            "🎨 **КАЛЬКУЛЯТОР КРАСКИ**\n\n"
            "Используйте пошаговый режим через меню или:\n"
            "`/calc_paint площадь тип поверхность слои`\n\n"
            "**Пример:**\n"
            "`/calc_paint 50 water smooth 2`\n\n"
            "Параметры:\n"
            "• Площадь (м²)\n"
            "• Тип: water, oil, latex\n"
            "• Поверхность: smooth, rough, porous\n"
            "• Количество слоёв",
            parse_mode='Markdown'
        )

    elif query.data == "calc_wall_area":
        await query.edit_message_text(
            "📐 **КАЛЬКУЛЯТОР ПЛОЩАДИ СТЕН**\n\n"
            "Используйте пошаговый режим через меню или:\n"
            "`/calc_wall_area длина ширина высота окна двери`\n\n"
            "**Пример:**\n"
            "`/calc_wall_area 5 4 2.7 2 1`\n\n"
            "Параметры:\n"
            "• Размеры помещения (м)\n"
            "• Количество окон\n"
            "• Количество дверей",
            parse_mode='Markdown'
        )

    elif query.data == "calc_roof":
        await query.edit_message_text(
            "🏠 **КАЛЬКУЛЯТОР КРОВЛИ**\n\n"
            "Используйте пошаговый режим через меню или:\n"
            "`/calc_roof длина ширина тип угол свес`\n\n"
            "**Пример:**\n"
            "`/calc_roof 10 8 gable 30 0.5`\n\n"
            "Параметры:\n"
            "• Размеры здания (м)\n"
            "• Тип: flat, gable, hip\n"
            "• Угол наклона (градусы)\n"
            "• Свес (м)",
            parse_mode='Markdown'
        )

    elif query.data == "calc_plaster":
        await query.edit_message_text(
            "🧱 **КАЛЬКУЛЯТОР ШТУКАТУРКИ**\n\n"
            "Используйте пошаговый режим через меню или:\n"
            "`/calc_plaster площадь толщина тип`\n\n"
            "**Пример:**\n"
            "`/calc_plaster 100 0.02 cement`\n\n"
            "Параметры:\n"
            "• Площадь (м²)\n"
            "• Толщина слоя (м, например 0.02 для 20 мм)\n"
            "• Тип: cement, gypsum, decorative",
            parse_mode='Markdown'
        )

    elif query.data == "calc_wallpaper":
        await query.edit_message_text(
            "🖼️ **КАЛЬКУЛЯТОР ОБОЕВ**\n\n"
            "Используйте пошаговый режим через меню или:\n"
            "`/calc_wallpaper площадь длина_рулона ширина раппорт запас`\n\n"
            "**Пример:**\n"
            "`/calc_wallpaper 50 10 0.53 0 10`\n\n"
            "Параметры:\n"
            "• Площадь стен (м²)\n"
            "• Размеры рулона (м)\n"
            "• Раппорт рисунка (м, 0 если без рисунка)\n"
            "• Запас (%)",
            parse_mode='Markdown'
        )

    elif query.data == "calc_laminate":
        await query.edit_message_text(
            "🪵 **КАЛЬКУЛЯТОР ЛАМИНАТА**\n\n"
            "Используйте пошаговый режим через меню или:\n"
            "`/calc_laminate длина ширина длина_доски ширина_доски запас`\n\n"
            "**Пример:**\n"
            "`/calc_laminate 5 4 1.28 0.192 7`\n\n"
            "Параметры:\n"
            "• Размеры помещения (м)\n"
            "• Размеры доски (м)\n"
            "• Запас на подрезку (%)",
            parse_mode='Markdown'
        )

    elif query.data == "calc_insulation":
        await query.edit_message_text(
            "🧊 **КАЛЬКУЛЯТОР УТЕПЛИТЕЛЯ**\n\n"
            "Используйте пошаговый режим через меню или:\n"
            "`/calc_insulation площадь толщина тип`\n\n"
            "**Пример:**\n"
            "`/calc_insulation 100 0.1 mineral_wool`\n\n"
            "Параметры:\n"
            "• Площадь (м²)\n"
            "• Толщина (м, например 0.1 для 100 мм)\n"
            "• Тип: mineral_wool, polystyrene, penoplex",
            parse_mode='Markdown'
        )

    elif query.data == "calc_foundation":
        await query.edit_message_text(
            "⚓ **КАЛЬКУЛЯТОР ФУНДАМЕНТА**\n\n"
            "Используйте пошаговый режим через меню или:\n"
            "`/calc_foundation длина ширина глубина тип`\n\n"
            "**Пример:**\n"
            "`/calc_foundation 10 8 1.5 strip`\n\n"
            "Параметры:\n"
            "• Размеры фундамента (м)\n"
            "• Глубина заложения (м)\n"
            "• Тип: strip, slab, pile",
            parse_mode='Markdown'
        )

    elif query.data == "calc_stairs":
        await query.edit_message_text(
            "🪜 **КАЛЬКУЛЯТОР ЛЕСТНИЦЫ**\n\n"
            "Используйте пошаговый режим через меню или:\n"
            "`/calc_stairs высота_этажа ширина_проступи высота_подступенка ширина_лестницы`\n\n"
            "**Пример:**\n"
            "`/calc_stairs 3 0.3 0.15 1`\n\n"
            "Параметры:\n"
            "• Высота этажа (м)\n"
            "• Ширина проступи (м)\n"
            "• Высота подступенка (м)\n"
            "• Ширина лестницы (м)",
            parse_mode='Markdown'
        )

    elif query.data == "calc_drywall":
        await query.edit_message_text(
            "📐 **КАЛЬКУЛЯТОР ГИПСОКАРТОНА**\n\n"
            "Используйте пошаговый режим через меню или:\n"
            "`/calc_drywall длина ширина высота потолок`\n\n"
            "**Пример:**\n"
            "`/calc_drywall 5 4 2.7 1`\n\n"
            "Параметры:\n"
            "• Размеры помещения (м)\n"
            "• Потолок: 1 - да, 0 - нет",
            parse_mode='Markdown'
        )

    elif query.data == "calc_earthwork":
        await query.edit_message_text(
            "🚜 **КАЛЬКУЛЯТОР ЗЕМЛЯНЫХ РАБОТ**\n\n"
            "Используйте пошаговый режим через меню или:\n"
            "`/calc_earthwork длина ширина глубина тип_грунта`\n\n"
            "**Пример:**\n"
            "`/calc_earthwork 20 15 2 clay`\n\n"
            "Параметры:\n"
            "• Размеры котлована (м)\n"
            "• Глубина (м)\n"
            "• Тип грунта: clay, sand, rock",
            parse_mode='Markdown'
        )

    elif query.data == "calc_labor":
        await query.edit_message_text(
            "👷 **КАЛЬКУЛЯТОР ТРУДОЗАТРАТ**\n\n"
            "Используйте пошаговый режим через меню или:\n"
            "`/calc_labor тип_работы объём единица`\n\n"
            "**Пример:**\n"
            "`/calc_labor concrete 50 m3`\n\n"
            "Параметры:\n"
            "• Тип: concrete, masonry, plaster, paint, tile, roof\n"
            "• Объём работ\n"
            "• Единица: m3, m2, m",
            parse_mode='Markdown'
        )

    # Обработчики категорий нормативов
    elif query.data.startswith("reg_cat_"):
        category = query.data.replace("reg_cat_", "")
        category_names = {
            "structures": "🏗️ Конструкции",
            "foundations": "⚓ Основания и фундаменты",
            "enclosures": "🧱 Ограждающие конструкции",
            "engineering": "⚡ Инженерные системы",
            "fire": "🔥 Пожарная безопасность",
            "quality": "✅ Контроль качества",
            "inspection": "🔍 Обследование",
            "accessibility": "♿ Доступность"
        }

        if IMPROVEMENTS_V3_AVAILABLE:
            from improvements_v3 import REGULATIONS_CATEGORIES
            cat_name = category_names.get(category, "Категория")

            if category in ["structures", "foundations", "enclosures", "engineering",
                          "fire", "quality", "inspection", "accessibility"]:
                # Преобразуем английское название в русское для поиска в словаре
                rus_cat = {
                    "structures": "Конструкции",
                    "foundations": "Основания и фундаменты",
                    "enclosures": "Ограждающие конструкции",
                    "engineering": "Инженерные системы",
                    "fire": "Пожарная безопасность",
                    "quality": "Контроль качества",
                    "inspection": "Обследование",
                    "accessibility": "Доступность"
                }

                cat_rus = rus_cat.get(category)
                if cat_rus and cat_rus in REGULATIONS_CATEGORIES:
                    docs = REGULATIONS_CATEGORIES[cat_rus]
                    text = f"📚 **{cat_name}**\n\n"
                    for doc_name, doc_info in docs.items():
                        text += f"**{doc_name}**\n"
                        text += f"_{doc_info['description']}_\n"
                        if 'link' in doc_info:
                            text += f"🔗 [Открыть документ]({doc_info['link']})\n"
                        text += "\n"

                    await query.edit_message_text(text, parse_mode='Markdown', disable_web_page_preview=True)
                else:
                    await query.edit_message_text(f"⚠️ Документы категории '{cat_name}' не найдены.")
            else:
                await query.edit_message_text("⚠️ Неизвестная категория.")
        else:
            await query.edit_message_text("⚠️ Модуль категорий недоступен.")

    # Обработчики выбора региона
    elif query.data.startswith("region_"):
        region = query.data.replace("region_", "")
        region_names = {
            "moscow": "Москва и МО",
            "spb": "Санкт-Петербург",
            "sochi": "Сочи",
            "yakutsk": "Якутск",
            "kamchatka": "Камчатка"
        }

        region_name = region_names.get(region, "Регион")
        # В будущем здесь будет сохранение региона в БД
        await query.edit_message_text(
            f"✅ **Регион выбран: {region_name}**\n\n"
            "Теперь я буду учитывать региональные особенности в своих ответах:\n"
            "• Климатическая зона\n"
            "• Коэффициенты стоимости работ\n"
            "• Сейсмичность\n"
            "• Температурные условия\n\n"
            "💡 _Функция сохранения региона будет доступна в v3.1_",
            parse_mode='Markdown'
        )

    # === ОБРАБОТЧИКИ v3.2 ===

    # Обработчики шаблонов документов
    elif query.data.startswith("template_"):
        if TEMPLATES_AVAILABLE:
            template_id = query.data.replace("template_", "")
            await handle_template_selection(update, context, template_id)
        else:
            await query.edit_message_text("⚠️ Модуль шаблонов недоступен.")

    # Обработчики скачивания пустого шаблона
    elif query.data.startswith("download_empty_"):
        if TEMPLATES_AVAILABLE:
            template_id = query.data.replace("download_empty_", "")
            await handle_download_empty_template(update, context, template_id)
        else:
            await query.edit_message_text("⚠️ Модуль шаблонов недоступен.")

    # Обработчики выбора роли
    elif query.data.startswith("role_"):
        if ROLES_AVAILABLE:
            role_id = query.data.replace("role_", "")
            await handle_role_selection(update, context, role_id)
        else:
            await query.edit_message_text("⚠️ Модуль ролей недоступен.")

    # Обработчики выбора проекта
    elif query.data.startswith("setproj_"):
        if PROJECTS_AVAILABLE:
            project_name = query.data.replace("setproj_", "")
            user_id = update.effective_user.id
            context.user_data["current_project"] = project_name
            project = load_project(user_id, project_name)
            await query.edit_message_text(
                f"✅ Активный проект установлен: **{project_name}**\n\n"
                f"{project.get_log_summary()}\n\n"
                "📌 Все ваши вопросы и ответы теперь сохраняются в этот проект.",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("⚠️ Модуль проектов недоступен.")
    elif query.data == "proj_create":
        # Создание нового проекта через диалог
        if PROJECTS_AVAILABLE:
            await query.edit_message_text(
                "📝 **СОЗДАНИЕ ПРОЕКТА**\n\n"
                "Введите название проекта:\n\n"
                "_Например: Реконструкция ТЦ Мега, Строительство жилого дома, Ремонт моста_",
                parse_mode="Markdown"
            )
            context.user_data["waiting_for_project_name"] = True
        else:
            await query.edit_message_text("⚠️ Модуль проектов недоступен.")
    elif query.data.startswith("proj_open_"):
        # Открытие существующего проекта
        if PROJECTS_AVAILABLE:
            project_name = query.data.replace("proj_open_", "")
            user_id = update.effective_user.id
            project = load_project(user_id, project_name)

            if project:
                context.user_data["current_project"] = project_name

                # Создаём меню проекта
                keyboard = [
                    [InlineKeyboardButton("📊 Информация", callback_data=f"proj_info_{project_name}"),
                     InlineKeyboardButton("📋 Журнал", callback_data=f"proj_log_{project_name}")],
                    [InlineKeyboardButton("📁 Файлы", callback_data=f"proj_files_{project_name}"),
                     InlineKeyboardButton("📝 Добавить заметку", callback_data=f"proj_note_{project_name}")],
                    [InlineKeyboardButton("📦 Экспорт проекта", callback_data=f"proj_export_{project_name}")],
                    [InlineKeyboardButton("« Назад к проектам", callback_data="project_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                info_text = f"📁 **ПРОЕКТ: {project_name}**\n\n"
                info_text += f"✅ Проект активирован\n\n"
                info_text += f"{project.get_log_summary()}\n\n"
                info_text += "Что вы хотите сделать?"

                await query.edit_message_text(
                    info_text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text("❌ Ошибка загрузки проекта")
        else:
            await query.edit_message_text("⚠️ Модуль проектов недоступен.")
    elif query.data.startswith("proj_info_"):
        # Информация о проекте
        if PROJECTS_AVAILABLE:
            project_name = query.data.replace("proj_info_", "")
            user_id = update.effective_user.id
            project = load_project(user_id, project_name)

            if project:
                info = project.get_project_summary()
                log_summary = project.get_log_summary()

                keyboard = [[InlineKeyboardButton("« Назад", callback_data=f"proj_open_{project_name}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    f"{info}\n\n📊 **Журнал работы:** {log_summary}",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text("❌ Ошибка загрузки проекта")
        else:
            await query.edit_message_text("⚠️ Модуль проектов недоступен.")
    elif query.data.startswith("proj_log_"):
        # Журнал проекта
        if PROJECTS_AVAILABLE:
            project_name = query.data.replace("proj_log_", "")
            user_id = update.effective_user.id
            project = load_project(user_id, project_name)

            if project:
                log = project.get_conversation_log()

                keyboard = []

                if not log:
                    keyboard.append([InlineKeyboardButton("« Назад", callback_data=f"proj_open_{project_name}")])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(
                        "📋 Журнал работы пуст",
                        reply_markup=reply_markup
                    )
                else:
                    # Последние 10 записей
                    recent_log = log[-10:]
                    response = f"📋 **ЖУРНАЛ: {project_name}**\n\n"
                    response += f"Всего записей: {len(log)}\n"
                    response += f"Последние {len(recent_log)} записей:\n\n"

                    # Создаём кнопки для каждой записи
                    start_index = len(log) - len(recent_log)
                    for i, entry in enumerate(recent_log, start=start_index):
                        timestamp = entry["timestamp"][:16].replace("T", " ")
                        question = entry.get("question", "")[:40]
                        response += f"{i+1}. {timestamp}\n   Q: {question}...\n\n"

                        # Добавляем кнопку для просмотра этой записи
                        keyboard.append([
                            InlineKeyboardButton(
                                f"📖 Запись #{i+1}",
                                callback_data=f"proj_entry_{project_name}_{i}"
                            )
                        ])

                    keyboard.append([InlineKeyboardButton("« Назад", callback_data=f"proj_open_{project_name}")])
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await query.edit_message_text(
                        response,
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
            else:
                await query.edit_message_text("❌ Ошибка загрузки проекта")
        else:
            await query.edit_message_text("⚠️ Модуль проектов недоступен.")
    elif query.data.startswith("proj_entry_"):
        # Просмотр конкретной записи из журнала
        if PROJECTS_AVAILABLE:
            parts = query.data.replace("proj_entry_", "").rsplit("_", 1)
            project_name = parts[0]
            entry_index = int(parts[1])
            user_id = update.effective_user.id
            project = load_project(user_id, project_name)

            if project:
                log = project.get_conversation_log()
                if 0 <= entry_index < len(log):
                    entry = log[entry_index]
                    timestamp = entry["timestamp"][:19].replace("T", " ")
                    question = entry.get("question", "Нет вопроса")
                    answer = entry.get("answer", "Нет ответа")
                    entry_type = entry.get("type", "qa")

                    response = f"📖 **ЗАПИСЬ #{entry_index+1}**\n\n"
                    response += f"⏰ {timestamp}\n"
                    response += f"📂 Тип: {entry_type}\n\n"
                    response += f"**❓ Вопрос:**\n{question}\n\n"
                    response += f"**💬 Ответ:**\n{answer[:3000]}"  # Ограничение на длину

                    if len(answer) > 3000:
                        response += "\n\n_...ответ обрезан, полный текст сохранён в проекте_"

                    keyboard = [
                        [InlineKeyboardButton("🔄 Повторно отправить", callback_data=f"proj_resend_{project_name}_{entry_index}")],
                        [InlineKeyboardButton("« К журналу", callback_data=f"proj_log_{project_name}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await query.edit_message_text(
                        response,
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                else:
                    await query.edit_message_text("❌ Запись не найдена")
            else:
                await query.edit_message_text("❌ Ошибка загрузки проекта")
        else:
            await query.edit_message_text("⚠️ Модуль проектов недоступен.")
    elif query.data.startswith("proj_resend_"):
        # Повторная отправка записи из журнала
        if PROJECTS_AVAILABLE:
            parts = query.data.replace("proj_resend_", "").rsplit("_", 1)
            project_name = parts[0]
            entry_index = int(parts[1])
            user_id = update.effective_user.id
            project = load_project(user_id, project_name)

            if project:
                log = project.get_conversation_log()
                if 0 <= entry_index < len(log):
                    entry = log[entry_index]
                    question = entry.get("question", "Нет вопроса")
                    answer = entry.get("answer", "Нет ответа")

                    # Отправляем информацию как новое сообщение
                    await query.answer("📨 Отправляю информацию...")

                    full_message = f"📂 **Из проекта:** {project_name}\n\n"
                    full_message += f"**❓ Вопрос:**\n{question}\n\n"
                    full_message += f"**💬 Ответ:**\n{answer}"

                    # Разбиваем на части если слишком длинное
                    max_length = 4000
                    if len(full_message) > max_length:
                        # Отправляем по частям
                        await query.message.reply_text(
                            f"📂 **Из проекта:** {project_name}\n\n**❓ Вопрос:**\n{question}",
                            parse_mode="Markdown"
                        )

                        # Делим ответ на части
                        chunks = [answer[i:i+max_length] for i in range(0, len(answer), max_length)]
                        for i, chunk in enumerate(chunks):
                            prefix = f"**💬 Ответ (часть {i+1}/{len(chunks)}):**\n" if len(chunks) > 1 else "**💬 Ответ:**\n"
                            await query.message.reply_text(
                                prefix + chunk,
                                parse_mode="Markdown"
                            )
                    else:
                        await query.message.reply_text(full_message, parse_mode="Markdown")

                    # Возвращаемся к записи
                    keyboard = [
                        [InlineKeyboardButton("« К журналу", callback_data=f"proj_log_{project_name}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_reply_markup(reply_markup=reply_markup)
                else:
                    await query.answer("❌ Запись не найдена", show_alert=True)
            else:
                await query.answer("❌ Ошибка загрузки проекта", show_alert=True)
        else:
            await query.answer("⚠️ Модуль проектов недоступен", show_alert=True)
    elif query.data.startswith("proj_files_"):
        # Файлы проекта
        if PROJECTS_AVAILABLE:
            project_name = query.data.replace("proj_files_", "")
            user_id = update.effective_user.id
            project = load_project(user_id, project_name)

            if project:
                files = project.list_files()

                keyboard = [[InlineKeyboardButton("« Назад", callback_data=f"proj_open_{project_name}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                if not files:
                    await query.edit_message_text(
                        "📁 В проекте пока нет файлов\n\n"
                        "Отправьте файл с подписью для добавления в проект",
                        reply_markup=reply_markup
                    )
                else:
                    response = f"📁 **ФАЙЛЫ ПРОЕКТА: {project_name}**\n\n"
                    response += f"Всего файлов: {len(files)}\n\n"

                    for i, file_info in enumerate(files, 1):
                        name = file_info["original_name"]
                        size_mb = file_info["size_bytes"] / 1024 / 1024
                        file_type = file_info["type"]
                        response += f"{i}. {name}\n"
                        response += f"   Тип: {file_type} | Размер: {size_mb:.2f} МБ\n\n"

                    await query.edit_message_text(
                        response,
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
            else:
                await query.edit_message_text("❌ Ошибка загрузки проекта")
        else:
            await query.edit_message_text("⚠️ Модуль проектов недоступен.")
    elif query.data.startswith("proj_note_"):
        # Добавление заметки
        if PROJECTS_AVAILABLE:
            project_name = query.data.replace("proj_note_", "")
            await query.edit_message_text(
                f"📝 **ДОБАВЛЕНИЕ ЗАМЕТКИ**\n\n"
                f"Проект: {project_name}\n\n"
                "Введите текст заметки:",
                parse_mode="Markdown"
            )
            context.user_data["waiting_for_note"] = project_name
        else:
            await query.edit_message_text("⚠️ Модуль проектов недоступен.")
    elif query.data.startswith("proj_export_"):
        # Экспорт проекта
        if PROJECTS_AVAILABLE:
            project_name = query.data.replace("proj_export_", "")
            user_id = update.effective_user.id

            await query.edit_message_text("⏳ Подготавливаю экспорт проекта...")

            try:
                project = load_project(user_id, project_name)
                if project:
                    # Экспортируем проект в JSON
                    export_data = {
                        "project_name": project_name,
                        "metadata": project.metadata,
                        "exported_at": datetime.now().isoformat()
                    }

                    # Создаём текстовый файл для экспорта
                    export_text = f"📁 ПРОЕКТ: {project_name}\n"
                    export_text += f"Экспортирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                    export_text += "=" * 50 + "\n\n"

                    # Информация о проекте
                    export_text += f"{project.get_project_summary()}\n\n"
                    export_text += "=" * 50 + "\n\n"

                    # Журнал работы
                    log = project.get_conversation_log()
                    export_text += f"📋 ЖУРНАЛ РАБОТЫ ({len(log)} записей)\n\n"

                    for i, entry in enumerate(log, 1):
                        timestamp = entry["timestamp"][:16].replace("T", " ")
                        question = entry.get("question", "")
                        answer = entry.get("answer", "")
                        export_text += f"═══ Запись #{i} ═══\n"
                        export_text += f"⏰ {timestamp}\n\n"
                        export_text += f"❓ ВОПРОС:\n{question}\n\n"
                        export_text += f"💬 ОТВЕТ:\n{answer}\n\n"
                        export_text += "-" * 50 + "\n\n"

                    # Список файлов
                    files = project.list_files()
                    if files:
                        export_text += "=" * 50 + "\n\n"
                        export_text += f"📁 ФАЙЛЫ ПРОЕКТА ({len(files)})\n\n"
                        for file_info in files:
                            export_text += f"• {file_info['original_name']}\n"
                            export_text += f"  Тип: {file_info['type']}\n"
                            export_text += f"  Размер: {file_info['size_bytes'] / 1024 / 1024:.2f} МБ\n"
                            export_text += f"  Добавлен: {file_info['added_at'][:16]}\n\n"

                    # Отправляем файл
                    from io import BytesIO
                    buffer = BytesIO(export_text.encode('utf-8'))
                    buffer.seek(0)
                    filename = f"{project_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"

                    await query.message.reply_document(
                        document=buffer,
                        filename=filename,
                        caption=f"📦 Экспорт проекта: **{project_name}**\n\n"
                                f"Записей: {len(log)} | Файлов: {len(files)}",
                        parse_mode="Markdown"
                    )

                    keyboard = [[InlineKeyboardButton("« Назад", callback_data=f"proj_open_{project_name}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await query.edit_message_text(
                        "✅ Проект экспортирован!",
                        reply_markup=reply_markup
                    )
                else:
                    await query.edit_message_text("❌ Ошибка загрузки проекта")
            except Exception as e:
                logger.error(f"Ошибка экспорта проекта: {e}")
                await query.edit_message_text(f"❌ Ошибка экспорта: {str(e)}")
        else:
            await query.edit_message_text("⚠️ Модуль проектов недоступен.")
    elif query.data == "ignore":
        # Игнорируем разделитель
        await query.answer()


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.error(f"Update {update} caused error {context.error}")


# === НОВЫЕ КОМАНДЫ v3.0 ===

async def calculators_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /calculators - Показать меню калькуляторов"""
    if not CALCULATORS_AVAILABLE:
        await update.message.reply_text(
            "⚠️ Модуль калькуляторов недоступен.\n\nОбратитесь к администратору."
        )
        return

    calc_text = """🧮 **КАЛЬКУЛЯТОРЫ v5.0**

Все калькуляторы с пошаговым вводом данных!

**Основные конструкции:**
🏗️ Бетон - объём, марка, материалы
🔧 Арматура - количество, вес
📦 Опалубка - площадь, оборачиваемость
⚓ Фундамент - комплексный расчет

**Материалы отделки:**
🧱 Кирпич/блоки - с учетом проёмов
🔲 Плитка - плитка + клей + затирка
🧱 Штукатурка - расход смеси
🎨 Краска - расход по слоям
🧊 Утеплитель - толщина + площадь
🏠 Кровля - площадь скатов

**Коммуникации:**
⚡ Электроснабжение - мощность
💧 Водоснабжение - расход воды
❄️ Зимний прогрев - прогрев бетона

Выберите калькулятор из меню ниже:"""

    if IMPROVEMENTS_V3_AVAILABLE:
        keyboard = create_calculators_menu()
        await update.message.reply_text(calc_text, parse_mode='Markdown', reply_markup=keyboard)
    else:
        await update.message.reply_text(calc_text, parse_mode='Markdown')


async def region_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /region - Выбор региона"""
    if not IMPROVEMENTS_V3_AVAILABLE:
        await update.message.reply_text(
            "⚠️ Функция региональных настроек недоступна."
        )
        return

    region_text = """📍 **РЕГИОНАЛЬНЫЕ НАСТРОЙКИ**

Выберите ваш регион для учёта климатических особенностей:

• Климатические коэффициенты
• Температурные зоны
• Сейсмичность
• Стоимость работ

Выберите регион из списка:"""

    keyboard = create_region_selection_menu()
    await update.message.reply_text(region_text, parse_mode='Markdown', reply_markup=keyboard)


async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /generate - Генерация изображений через Gemini AI"""
    if not GEMINI_AVAILABLE:
        await update.message.reply_text(
            "⚠️ Функция генерации изображений недоступна.\n\n"
            "Проверьте наличие GEMINI_API_KEY в переменных окружения."
        )
        return

    # Проверяем аргументы команды
    if not context.args:
        await update.message.reply_text(
            "🎨 **ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ - Gemini AI**\n\n"
            "Использование:\n"
            "`/generate описание изображения`\n\n"
            "**Примеры:**\n"
            "• `/generate схема фундамента с армированием`\n"
            "• `/generate узел соединения балки и колонны`\n"
            "• `/generate арматурный каркас перекрытия`\n"
            "• `/generate электрическая схема квартиры`\n"
            "• `/generate схема водопровода в доме`\n\n"
            "Также можно просто написать:\n"
            "\"нарисуй трещину в стене\" - бот автоматически сгенерирует",
            parse_mode="Markdown"
        )
        return

    # Получаем описание
    user_request = " ".join(context.args)

    # Отправляем сообщение о процессе
    generating_message = await update.message.reply_text(
        "🎨 Генерирую изображение...\n"
        "Это займет 15-30 секунд\n\n"
        "💡 Используется Gemini AI"
    )

    try:
        # Генерируем изображение через Gemini
        result = await generate_construction_image_gemini(user_request)

        if result and result.get("image_data"):
            # Удаляем сообщение о генерации
            try:
                await generating_message.delete()
            except:
                pass

            # Формируем подпись
            caption = f"""🎨 **СГЕНЕРИРОВАННОЕ ИЗОБРАЖЕНИЕ**

**Запрос:** {user_request}

{result.get('text', '')[:500] if result.get('text') else ''}

---
🤖 _Модель: {result.get('model', 'Gemini AI')}_"""

            # Отправляем изображение
            result["image_data"].seek(0)
            await update.message.reply_photo(
                photo=result["image_data"],
                caption=caption[:1024],  # Ограничение Telegram
                parse_mode="Markdown"
            )

            logger.info(f"✅ Изображение отправлено пользователю {update.effective_user.id}")
        else:
            await generating_message.edit_text(
                "❌ Не удалось создать изображение.\n\n"
                "Возможные причины:\n"
                "• Проблемы с Gemini API\n"
                "• Запрос не подходит для генерации\n"
                "• Временная недоступность сервиса\n\n"
                "Попробуйте изменить описание или повторите попытку позже."
            )

    except Exception as e:
        logger.error(f"Ошибка генерации изображения: {e}")
        await generating_message.edit_text(
            f"❌ Ошибка генерации:\n`{str(e)}`\n\n"
            "Проверьте наличие GEMINI_API_KEY в переменных окружения.",
            parse_mode="Markdown"
        )


# === ГЛАВНАЯ ФУНКЦИЯ ===

async def setup_bot_menu(application):
    """Установка постоянного меню команд бота"""
    commands = [
        BotCommand("start", "🏠 Главное меню"),
        BotCommand("help", "📖 Справка по всем командам"),
        # BotCommand("generate", "🎨 Генерация схем (Gemini AI)"),  # Отключено
        # BotCommand("visualize", "🎨 Визуализация дефектов (Gemini AI)"),  # Отключено
        BotCommand("calculators", "🧮 Калькуляторы"),
        BotCommand("regulations", "📚 Нормативы (27 документов)"),
        BotCommand("regulations_menu", "📖 Категории нормативов"),
        BotCommand("faq", "❓ Частые вопросы"),
        BotCommand("templates", "📄 Шаблоны документов"),
        BotCommand("projects", "📁 Мои проекты"),
        BotCommand("role", "👔 Выбрать роль"),
        BotCommand("history", "📜 История диалогов"),
        BotCommand("stats", "📊 Статистика"),
        BotCommand("hse", "🦺 Охрана труда"),
        BotCommand("technology", "🏗️ Технология строительства"),
        BotCommand("estimating", "💰 Сметное дело"),
        BotCommand("legal", "⚖️ Юридические вопросы"),
        BotCommand("management", "📈 Управление проектами"),
        BotCommand("suggestions", "💡 Предложения по улучшению"),
        BotCommand("dev", "🔧 Режим разработчика"),
    ]

    await application.bot.set_my_commands(commands)
    logger.info("✅ Меню команд бота установлено")


def main():
    """Запуск бота"""
    import asyncio

    # Создаем event loop для Python 3.14+
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Инициализируем PostgreSQL базу данных
    if DATABASE_AVAILABLE:
        try:
            loop.run_until_complete(init_db())
        except Exception as e:
            logger.error(f"Ошибка инициализации PostgreSQL: {e}")
            logger.info("Продолжаем работу с JSON хранилищем")

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

    # Новые команды v3.0
    application.add_handler(CommandHandler("calculators", calculators_command))
    application.add_handler(CommandHandler("region", region_command))

    # LLM Council - Совет AI моделей (Karpathy's approach)
    if LLM_COUNCIL_AVAILABLE:
        application.add_handler(CommandHandler("council", council_command))
        logger.info("✅ Команда /council зарегистрирована")

    # === ИНТЕРАКТИВНЫЕ КАЛЬКУЛЯТОРЫ v4.0 ===
    # Интерактивные калькуляторы вызываются через меню /calculators и команды
    if CALCULATOR_HANDLERS_AVAILABLE:
        # Основные 7 калькуляторов
        application.add_handler(create_concrete_calculator_handler())
        application.add_handler(create_rebar_calculator_handler())
        application.add_handler(create_formwork_calculator_handler())
        application.add_handler(create_electrical_calculator_handler())
        application.add_handler(create_water_calculator_handler())
        application.add_handler(create_winter_calculator_handler())
        application.add_handler(create_math_calculator_handler())

        # Новые 14 калькуляторов
        application.add_handler(create_brick_calculator_handler())
        application.add_handler(create_tile_calculator_handler())
        application.add_handler(create_paint_calculator_handler())
        application.add_handler(create_wall_area_calculator_handler())
        application.add_handler(create_roof_calculator_handler())
        application.add_handler(create_plaster_calculator_handler())
        application.add_handler(create_wallpaper_calculator_handler())
        application.add_handler(create_laminate_calculator_handler())
        application.add_handler(create_insulation_calculator_handler())
        application.add_handler(create_foundation_calculator_handler())
        application.add_handler(create_stairs_calculator_handler())
        application.add_handler(create_drywall_calculator_handler())
        application.add_handler(create_earthwork_calculator_handler())
        application.add_handler(create_labor_calculator_handler())

        # Быстрые команды для расчёта одной строкой
        application.add_handler(CommandHandler("calc_concrete", quick_concrete))
        application.add_handler(CommandHandler("calc_math", quick_math))

        logger.info("✅ Интерактивные калькуляторы v4.0 зарегистрированы (все 21 + быстрые команды)")

    # УДАЛЕНО: дублирование калькуляторов создавало конфликт ConversationHandler
    # Старая система interactive_calculators.py больше не используется

    # === КАТЕГОРИЗАЦИЯ НОРМАТИВОВ v1.0 ===
    if REGULATIONS_CATEGORIES_AVAILABLE:
        async def regulations_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Команда /regulations_menu - категории нормативов"""
            keyboard = get_categories_keyboard()
            await update.message.reply_text(
                "📚 **КАТЕГОРИИ НОРМАТИВОВ**\n\n"
                "Выберите категорию для просмотра документов:\n\n"
                "_27 документов разделены на 7 удобных категорий_",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

        application.add_handler(CommandHandler("regulations_menu", regulations_menu_command))

        # Callback handler для категорий нормативов
        async def handle_regulations_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Обработчик callback для категорий нормативов"""
            query = update.callback_query
            await query.answer()

            callback_data = query.data

            if callback_data.startswith("cat_"):
                category_id = callback_data.replace("cat_", "")

                if category_id == "all":
                    # Показать все нормативы
                    text = get_all_regulations_text()
                    await query.edit_message_text(text, parse_mode='Markdown')
                else:
                    # Показать нормативы категории
                    text = get_regulations_by_category(category_id)
                    if text:
                        # Кнопка "Назад"
                        keyboard = [[InlineKeyboardButton("⬅️ Назад к категориям", callback_data="cat_back")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

            elif callback_data == "cat_back":
                # Вернуться к категориям
                keyboard = get_categories_keyboard()
                await query.edit_message_text(
                    "📚 **КАТЕГОРИИ НОРМАТИВОВ**\n\n"
                    "Выберите категорию для просмотра документов:\n\n"
                    "_27 документов разделены на 7 удобных категорий_",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )

        application.add_handler(CallbackQueryHandler(handle_regulations_callback, pattern="^cat_"))
        logger.info("✅ Команда /regulations_menu зарегистрирована (категории нормативов)")

    # === ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ - Gemini AI ===
    if GEMINI_AVAILABLE:
        application.add_handler(CommandHandler("generate", generate_command))
        logger.info("✅ Команда /generate зарегистрирована (Gemini AI)")

    # === ВИЗУАЛИЗАЦИЯ ДЕФЕКТОВ - Gemini AI ===
    if GEMINI_AVAILABLE:
        application.add_handler(CommandHandler("visualize", visualize_command))
        logger.info("✅ Команда /visualize зарегистрирована (Gemini AI)")

    # === НОВЫЕ КОМАНДЫ v3.9 ===
    if TEMPLATES_AVAILABLE:
        application.add_handler(CommandHandler("templates", templates_command))
        logger.info("✅ Команда /templates зарегистрирована")

    if PROJECTS_AVAILABLE:
        application.add_handler(CommandHandler("projects", projects_command))
        application.add_handler(CommandHandler("new_project", new_project_command))
        application.add_handler(CommandHandler("set_project", set_project_command))
        application.add_handler(CommandHandler("project_info", project_info_command))
        application.add_handler(CommandHandler("project_log", project_log_command))
        logger.info("✅ Команды управления проектами зарегистрированы (5 команд)")

    if ROLES_AVAILABLE:
        application.add_handler(CommandHandler("role", role_command))
        logger.info("✅ Команда /role зарегистрирована")

    # === ПРЕДЛОЖЕНИЯ ПО УЛУЧШЕНИЮ v1.0 ===
    if SUGGESTIONS_AVAILABLE:
        # Добавляем команду /suggestions для быстрого доступа
        async def suggestions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Команда /suggestions - открывает меню предложений"""
            await suggestions_menu(update, context)

        application.add_handler(CommandHandler("suggestions", suggestions_command))
        logger.info("✅ Команда /suggestions зарегистрирована")

    # === УПРАВЛЕНИЕ ИСТОРИЕЙ v3.5 ===
    if HISTORY_MANAGER_AVAILABLE:
        application.add_handler(CommandHandler("history", history_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("search", search_command))
        application.add_handler(CommandHandler("export", export_command))
        application.add_handler(CommandHandler("clear", clear_history_command))
        # Обработчик callback для работы с историей
        application.add_handler(CallbackQueryHandler(handle_history_callback, pattern="^hist_|^export_|^clear_"))
        logger.info("✅ Управление историей v3.5 зарегистрировано (5 команд)")

    # === СОХРАНЁННЫЕ РАСЧЁТЫ v3.6 ===
    if SAVED_CALCS_AVAILABLE:
        application.add_handler(CommandHandler("saved", saved_command))
        # Обработчик callback для сохранённых расчётов
        application.add_handler(CallbackQueryHandler(handle_saved_callback, pattern="^saved_"))
        logger.info("✅ Сохранённые расчёты v3.6 зарегистрированы")

    # === БАЗА ЧАСТЫХ ВОПРОСОВ (FAQ) v3.7 ===
    if FAQ_AVAILABLE:
        application.add_handler(CommandHandler("faq", faq_command))
        application.add_handler(CommandHandler("faq_search", faq_search_command))
        # Обработчик callback для FAQ
        application.add_handler(CallbackQueryHandler(handle_faq_callback, pattern="^faq_"))
        logger.info(f"✅ FAQ v3.7 зарегистрирован ({get_total_faq_count()} вопросов)")

    # === ПЛАНИРОВЩИК РАБОТ v3.8 ===
    if PLANNER_AVAILABLE:
        application.add_handler(CommandHandler("planner", planner_command))
        application.add_handler(CommandHandler("plan_calc", plan_calc_command))
        # Обработчик callback для планировщика
        application.add_handler(CallbackQueryHandler(handle_planner_callback, pattern="^plan_"))
        logger.info("✅ Work planner v3.8 зарегистрирован")

    # УДАЛЕНО: дублирующаяся регистрация калькуляторов v3.5
    # Все 21 калькулятор уже зарегистрированы выше в блоке v4.0

    # === ИНТЕРАКТИВНЫЕ ОБРАБОТЧИКИ ДОКУМЕНТОВ v1.0 ===
    if DOCUMENT_HANDLERS_AVAILABLE:
        # ConversationHandler для всех 4 шаблонов документов
        application.add_handler(create_acceptance_foundation_handler())
        application.add_handler(create_complaint_contractor_handler())
        application.add_handler(create_safety_plan_handler())
        application.add_handler(create_hidden_works_act_handler())
        logger.info("✅ Все 4 интерактивных обработчика документов зарегистрированы (v1.0)")

    # === РЕЖИМ РАЗРАБОТЧИКА v1.0 ===
    if DEV_MODE_AVAILABLE:
        # ConversationHandler для режима разработчика
        application.add_handler(create_dev_mode_handler())
        logger.info("✅ Режим разработчика v1.0 зарегистрирован")

    # Регистрируем обработчики сообщений
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # === ГОЛОСОВЫЕ СООБЩЕНИЯ v3.9 ===
    if VOICE_HANDLER_AVAILABLE:
        application.add_handler(MessageHandler(filters.VOICE, handle_voice))
        logger.info("✅ Обработчик голосовых сообщений зарегистрирован")

    # === ЗАГРУЗКА ДОКУМЕНТОВ В ПРОЕКТЫ v3.9 ===
    if PROJECTS_AVAILABLE:
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
        logger.info("✅ Обработчик документов зарегистрирован")

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # === АВТОПРИМЕНЕНИЕ ИЗМЕНЕНИЙ v1.0 ===
    if AUTO_APPLY_AVAILABLE:
        application.add_handler(CallbackQueryHandler(handle_apply_changes, pattern="^apply_changes"))
        logger.info("✅ Обработчик автоприменения изменений зарегистрирован")

    # === ПРЕДЛОЖЕНИЯ ПО УЛУЧШЕНИЮ v1.0 ===
    if SUGGESTIONS_AVAILABLE:
        application.add_handler(create_suggestions_handler())
        logger.info("✅ Обработчик предложений зарегистрирован")

    # === GEMINI LIVE API - ГОЛОСОВОЙ АССИСТЕНТ ===
    if VOICE_ASSISTANT_AVAILABLE:
        try:
            from gemini_live_bot_integration import (
                register_voice_assistant_handlers,
                init_voice_assistant
            )
            # Инициализация голосового ассистента
            init_voice_assistant()
            # Регистрация обработчиков (ConversationHandler для голосовых сессий)
            register_voice_assistant_handlers(application)
            logger.info("✅ Gemini Live API (голосовой ассистент) активирован")
        except Exception as e:
            logger.error(f"❌ Ошибка активации голосового ассистента: {e}")

    # === OPENAI REALTIME API - АЛЬТЕРНАТИВНЫЙ ГОЛОСОВОЙ АССИСТЕНТ ===
    if OPENAI_REALTIME_AVAILABLE:
        try:
            from openai_realtime_bot_integration import (
                register_realtime_assistant_handlers,
                init_realtime_assistant
            )
            # Инициализация OpenAI Realtime ассистента
            init_realtime_assistant()
            # Регистрация обработчиков
            register_realtime_assistant_handlers(application)
            logger.info("✅ OpenAI Realtime API (голосовой ассистент) активирован")
        except Exception as e:
            logger.error(f"❌ Ошибка активации OpenAI Realtime: {e}")

    # Регистрируем обработчик кнопок
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Регистрируем обработчик ошибок
    application.add_error_handler(error_handler)

    # Устанавливаем меню команд бота
    loop.run_until_complete(setup_bot_menu(application))

    # Запускаем бота
    logger.info("Bot is running... Press Ctrl+C to stop")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()