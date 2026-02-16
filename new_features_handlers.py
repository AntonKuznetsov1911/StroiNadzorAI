"""
Обработчики новых функций v3.9
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Импортируем модули
try:
    from voice_handler import process_voice_message
    VOICE_AVAILABLE = True
except Exception:
    VOICE_AVAILABLE = False

try:
    from document_templates import DOCUMENT_TEMPLATES, generate_document
    TEMPLATES_AVAILABLE = True
except Exception:
    TEMPLATES_AVAILABLE = False

try:
    from project_manager import get_user_projects, create_project, load_project
    PROJECTS_AVAILABLE = True
except Exception:
    PROJECTS_AVAILABLE = False


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка голосовых сообщений"""
    if not VOICE_AVAILABLE:
        await update.message.reply_text("Голосовые сообщения недоступны")
        return
    
    user_id = update.effective_user.id
    await update.message.reply_text("🎤 Распознаю голосовое сообщение...")
    
    try:
        voice_file_id = update.message.voice.file_id
        result = await process_voice_message(
            bot=context.bot,
            voice_file_id=voice_file_id,
            user_id=user_id
        )
        
        if result["success"]:
            await update.message.reply_text(
                f"✅ Распознано: {result['text']}"
            )
        else:
            await update.message.reply_text(
                f"❌ Ошибка: {result.get('error', '')}"
            )
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def templates_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /templates"""
    if not TEMPLATES_AVAILABLE:
        await update.message.reply_text("Шаблоны недоступны")
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
        "📄 Выберите шаблон документа:",
        reply_markup=reply_markup
    )


async def projects_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /projects"""
    if not PROJECTS_AVAILABLE:
        await update.message.reply_text("Проекты недоступны")
        return
    
    user_id = update.effective_user.id
    projects = get_user_projects(user_id)
    
    if not projects:
        await update.message.reply_text(
            "У вас нет проектов.\n\nСоздать: /new_project Название"
        )
        return
    
    keyboard = []
    for project_name in projects:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📁 {project_name}",
                callback_data=f"proj_{project_name}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"📁 Ваши проекты ({len(projects)}):",
        reply_markup=reply_markup
    )
