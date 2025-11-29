"""
Интерактивные обработчики для заполнения шаблонов документов
Версия 1.0 - Диалоговое заполнение с возможностью скачать или скопировать
"""

import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from docx import Document as DocxDocument
from document_templates import generate_document, DOCUMENT_TEMPLATES

logger = logging.getLogger(__name__)

# ========================================
# СОСТОЯНИЯ ДЛЯ ConversationHandler
# ========================================

# Акт приёмки фундамента
ACT_NUMBER, OBJECT_NAME, CONTRACTOR, CUSTOMER, DATE, FOUNDATION_TYPE, VOLUME, CONCRETE_CLASS, INSPECTOR, DEFECTS = range(10)

# Претензия подрядчику
COMPLAINT_NUMBER, COMPLAINT_DATE, CONTRACTOR_NAME, CONTRACTOR_ADDR, SENDER_NAME, SENDER_ADDR, CONTRACT_NUM, CONTRACT_DATE, DEFECT_DESC, DEADLINE, PENALTY = range(11)

# План охраны труда
PLAN_OBJECT, PLAN_YEAR, PLAN_RESPONSIBLE, PLAN_WORKERS, PLAN_BUDGET = range(5)

# Акт освидетельствования
HIDDEN_ACT_NUMBER, HIDDEN_OBJECT, HIDDEN_CONTRACTOR, HIDDEN_CUSTOMER, HIDDEN_DATE, HIDDEN_WORK_TYPE, HIDDEN_VOLUME, HIDDEN_STANDARDS, HIDDEN_INSPECTOR, HIDDEN_COMPLIANCE = range(10)


# ========================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ========================================

def extract_text_from_docx(filepath: str) -> str:
    """Извлечь текст из DOCX документа для копирования"""
    try:
        doc = DocxDocument(filepath)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        logger.error(f"Ошибка извлечения текста из DOCX: {e}")
        return ""


async def send_document_result(update: Update, context: ContextTypes.DEFAULT_TYPE, template_id: str, params: dict):
    """Генерирует и отправляет документ с текстом для копирования"""

    # Генерируем документ
    result = generate_document(template_id, params)

    if not result["success"]:
        await update.message.reply_text(f"❌ Ошибка генерации документа: {result['error']}")
        return ConversationHandler.END

    filepath = result["filepath"]

    # Извлекаем текст для копирования
    doc_text = extract_text_from_docx(filepath)

    # Отправляем документ
    template_info = DOCUMENT_TEMPLATES[template_id]
    with open(filepath, 'rb') as doc_file:
        await update.message.reply_document(
            document=doc_file,
            filename=os.path.basename(filepath),
            caption=f"✅ **Документ готов!**\n\n📄 {template_info['name']}",
            parse_mode="Markdown"
        )

    # Отправляем текст документа для копирования (частями если длинный)
    MAX_LENGTH = 4000
    if len(doc_text) <= MAX_LENGTH:
        await update.message.reply_text(
            f"📋 **ТЕКСТ ДОКУМЕНТА:**\n\n{doc_text}",
            parse_mode="Markdown"
        )
    else:
        # Разбиваем на части
        parts = [doc_text[i:i+MAX_LENGTH] for i in range(0, len(doc_text), MAX_LENGTH)]
        for i, part in enumerate(parts, 1):
            await update.message.reply_text(
                f"📋 **ТЕКСТ ДОКУМЕНТА (часть {i}/{len(parts)}):**\n\n{part}",
                parse_mode="Markdown"
            )

    # Кнопки для действий
    keyboard = [
        [InlineKeyboardButton("✏️ Заполнить заново", callback_data=f"fill_{template_id}")],
        [InlineKeyboardButton("« Назад к шаблонам", callback_data="templates")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Что вы хотите сделать?",
        reply_markup=reply_markup
    )

    return ConversationHandler.END


# ========================================
# АКТ ПРИЁМКИ ФУНДАМЕНТА
# ========================================

async def acceptance_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало заполнения акта приёмки фундамента"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📝 **ЗАПОЛНЕНИЕ АКТА ПРИЁМКИ ФУНДАМЕНТА**\n\n"
        "Я задам вам 10 вопросов для заполнения документа.\n\n"
        "1️⃣ Введите **номер акта** (например: 123):",
        parse_mode="Markdown"
    )

    return ACT_NUMBER


async def acceptance_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["act_number"] = update.message.text
    await update.message.reply_text("2️⃣ Введите **наименование объекта** (например: ЖК Солнечный, ул. Ленина 10):")
    return OBJECT_NAME


async def acceptance_object(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["object_name"] = update.message.text
    await update.message.reply_text("3️⃣ Введите **подрядчика** (название организации, ФИО представителя):")
    return CONTRACTOR


async def acceptance_contractor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contractor"] = update.message.text
    await update.message.reply_text("4️⃣ Введите **заказчика** (название организации, ФИО представителя):")
    return CUSTOMER


async def acceptance_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["customer"] = update.message.text
    await update.message.reply_text("5️⃣ Введите **дату** (например: 29.11.2025 или просто год 2025):")
    return DATE


async def acceptance_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["date"] = update.message.text
    await update.message.reply_text("6️⃣ Введите **тип фундамента** (ленточный/свайный/плитный):")
    return FOUNDATION_TYPE


async def acceptance_foundation_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["foundation_type"] = update.message.text
    await update.message.reply_text("7️⃣ Введите **объём бетона** в м³ (например: 150):")
    return VOLUME


async def acceptance_volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["volume_m3"] = update.message.text
    await update.message.reply_text("8️⃣ Введите **класс бетона** (например: В25 или В22,5):")
    return CONCRETE_CLASS


async def acceptance_concrete_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["concrete_class"] = update.message.text
    await update.message.reply_text("9️⃣ Введите **ФИО инспектора технического надзора**:")
    return INSPECTOR


async def acceptance_inspector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["inspector_name"] = update.message.text
    await update.message.reply_text("🔟 Введите **выявленные дефекты** (если нет, напишите 'нет' или 'отсутствуют'):")
    return DEFECTS


async def acceptance_defects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Последний параметр - генерируем документ"""
    context.user_data["defects"] = update.message.text

    await update.message.reply_text("⏳ Генерирую документ...")

    params = {
        "act_number": context.user_data["act_number"],
        "object_name": context.user_data["object_name"],
        "contractor": context.user_data["contractor"],
        "customer": context.user_data["customer"],
        "date": context.user_data["date"],
        "foundation_type": context.user_data["foundation_type"],
        "volume_m3": context.user_data["volume_m3"],
        "concrete_class": context.user_data["concrete_class"],
        "inspector_name": context.user_data["inspector_name"],
        "defects": context.user_data["defects"]
    }

    return await send_document_result(update, context, "acceptance_foundation", params)


# ========================================
# ПРЕТЕНЗИЯ ПОДРЯДЧИКУ
# ========================================

async def complaint_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало заполнения претензии"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📝 **ЗАПОЛНЕНИЕ ПРЕТЕНЗИИ ПОДРЯДЧИКУ**\n\n"
        "Я задам вам 11 вопросов для заполнения документа.\n\n"
        "1️⃣ Введите **номер претензии** (например: 45):",
        parse_mode="Markdown"
    )

    return COMPLAINT_NUMBER


async def complaint_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["complaint_number"] = update.message.text
    await update.message.reply_text("2️⃣ Введите **дату претензии** (например: 29.11.2025):")
    return COMPLAINT_DATE


async def complaint_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["complaint_date"] = update.message.text
    await update.message.reply_text("3️⃣ Введите **наименование подрядчика** (ООО или ИП):")
    return CONTRACTOR_NAME


async def complaint_contractor_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contractor_name"] = update.message.text
    await update.message.reply_text("4️⃣ Введите **юридический адрес подрядчика**:")
    return CONTRACTOR_ADDR


async def complaint_contractor_addr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contractor_address"] = update.message.text
    await update.message.reply_text("5️⃣ Введите **ваше наименование/ФИО** (отправитель претензии):")
    return SENDER_NAME


async def complaint_sender_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sender_name"] = update.message.text
    await update.message.reply_text("6️⃣ Введите **ваш юридический адрес**:")
    return SENDER_ADDR


async def complaint_sender_addr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sender_address"] = update.message.text
    await update.message.reply_text("7️⃣ Введите **номер договора** (например: 123/2025):")
    return CONTRACT_NUM


async def complaint_contract_num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contract_number"] = update.message.text
    await update.message.reply_text("8️⃣ Введите **дату договора** (например: 15.01.2025):")
    return CONTRACT_DATE


async def complaint_contract_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contract_date"] = update.message.text
    await update.message.reply_text("9️⃣ Опишите **выявленные дефекты и нарушения**:")
    return DEFECT_DESC


async def complaint_defect_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["defect_description"] = update.message.text
    await update.message.reply_text("🔟 Введите **срок устранения недостатков** (в рабочих днях, например: 14):")
    return DEADLINE


async def complaint_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["deadline_days"] = update.message.text
    await update.message.reply_text("1️⃣1️⃣ Введите **размер штрафа** в процентах (например: 5):")
    return PENALTY


async def complaint_penalty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Последний параметр - генерируем документ"""
    context.user_data["penalty_percent"] = update.message.text

    await update.message.reply_text("⏳ Генерирую документ...")

    params = {
        "complaint_number": context.user_data["complaint_number"],
        "date": context.user_data["complaint_date"],
        "contractor_name": context.user_data["contractor_name"],
        "contractor_address": context.user_data["contractor_address"],
        "sender_name": context.user_data["sender_name"],
        "sender_address": context.user_data["sender_address"],
        "contract_number": context.user_data["contract_number"],
        "contract_date": context.user_data["contract_date"],
        "defect_description": context.user_data["defect_description"],
        "deadline_days": context.user_data["deadline_days"],
        "penalty_percent": context.user_data["penalty_percent"]
    }

    return await send_document_result(update, context, "complaint_contractor", params)


# ========================================
# ПЛАН ОХРАНЫ ТРУДА
# ========================================

async def safety_plan_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало заполнения плана ОТ"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📝 **ЗАПОЛНЕНИЕ ПЛАНА МЕРОПРИЯТИЙ ПО ОХРАНЕ ТРУДА**\n\n"
        "Я задам вам 5 вопросов для заполнения документа.\n\n"
        "1️⃣ Введите **наименование объекта**:",
        parse_mode="Markdown"
    )

    return PLAN_OBJECT


async def safety_plan_object(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["plan_object_name"] = update.message.text
    await update.message.reply_text("2️⃣ Введите **год** (например: 2025):")
    return PLAN_YEAR


async def safety_plan_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["plan_year"] = update.message.text
    await update.message.reply_text("3️⃣ Введите **ФИО ответственного лица**:")
    return PLAN_RESPONSIBLE


async def safety_plan_responsible(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["plan_responsible_person"] = update.message.text
    await update.message.reply_text("4️⃣ Введите **численность работников** (например: 50):")
    return PLAN_WORKERS


async def safety_plan_workers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["plan_worker_count"] = update.message.text
    await update.message.reply_text("5️⃣ Введите **общий бюджет** в рублях (например: 220000):")
    return PLAN_BUDGET


async def safety_plan_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Последний параметр - генерируем документ"""
    context.user_data["plan_total_budget"] = update.message.text

    await update.message.reply_text("⏳ Генерирую документ...")

    params = {
        "object_name": context.user_data["plan_object_name"],
        "year": context.user_data["plan_year"],
        "responsible_person": context.user_data["plan_responsible_person"],
        "worker_count": context.user_data["plan_worker_count"],
        "total_budget": context.user_data["plan_total_budget"]
    }

    return await send_document_result(update, context, "safety_plan", params)


# ========================================
# АКТ ОСВИДЕТЕЛЬСТВОВАНИЯ СКРЫТЫХ РАБОТ
# ========================================

async def hidden_works_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало заполнения акта освидетельствования"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📝 **ЗАПОЛНЕНИЕ АКТА ОСВИДЕТЕЛЬСТВОВАНИЯ СКРЫТЫХ РАБОТ**\n\n"
        "Я задам вам 10 вопросов для заполнения документа.\n\n"
        "1️⃣ Введите **номер акта** (например: 75):",
        parse_mode="Markdown"
    )

    return HIDDEN_ACT_NUMBER


async def hidden_act_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hidden_act_number"] = update.message.text
    await update.message.reply_text("2️⃣ Введите **наименование объекта**:")
    return HIDDEN_OBJECT


async def hidden_object(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hidden_object_name"] = update.message.text
    await update.message.reply_text("3️⃣ Введите **подрядчика** (организация, представитель):")
    return HIDDEN_CONTRACTOR


async def hidden_contractor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hidden_contractor"] = update.message.text
    await update.message.reply_text("4️⃣ Введите **заказчика** (организация, представитель):")
    return HIDDEN_CUSTOMER


async def hidden_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hidden_customer"] = update.message.text
    await update.message.reply_text("5️⃣ Введите **дату** (например: 29.11.2025):")
    return HIDDEN_DATE


async def hidden_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hidden_date"] = update.message.text
    await update.message.reply_text("6️⃣ Введите **вид работ** (например: Устройство фундамента, армирование):")
    return HIDDEN_WORK_TYPE


async def hidden_work_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hidden_work_type"] = update.message.text
    await update.message.reply_text("7️⃣ Введите **объём работ** (например: 100 м³):")
    return HIDDEN_VOLUME


async def hidden_volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hidden_volume"] = update.message.text
    await update.message.reply_text("8️⃣ Введите **применяемые нормативы** (например: СП 70.13330.2025, ГОСТ 10180-2023):")
    return HIDDEN_STANDARDS


async def hidden_standards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hidden_standards"] = update.message.text
    await update.message.reply_text("9️⃣ Введите **ФИО инспектора проектной организации**:")
    return HIDDEN_INSPECTOR


async def hidden_inspector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hidden_inspector_name"] = update.message.text
    await update.message.reply_text("🔟 Соответствует ли проекту? (введите 'Да' или опишите несоответствия):")
    return HIDDEN_COMPLIANCE


async def hidden_compliance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Последний параметр - генерируем документ"""
    context.user_data["hidden_project_compliance"] = update.message.text

    await update.message.reply_text("⏳ Генерирую документ...")

    params = {
        "act_number": context.user_data["hidden_act_number"],
        "object_name": context.user_data["hidden_object_name"],
        "contractor": context.user_data["hidden_contractor"],
        "customer": context.user_data["hidden_customer"],
        "date": context.user_data["hidden_date"],
        "work_type": context.user_data["hidden_work_type"],
        "volume": context.user_data["hidden_volume"],
        "standards": context.user_data["hidden_standards"],
        "inspector_name": context.user_data["hidden_inspector_name"],
        "project_compliance": context.user_data["hidden_project_compliance"]
    }

    return await send_document_result(update, context, "hidden_works_act", params)


# ========================================
# ОТМЕНА ЗАПОЛНЕНИЯ
# ========================================

async def cancel_filling(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена процесса заполнения"""
    await update.message.reply_text(
        "❌ Заполнение отменено.\n\n"
        "Используйте /templates чтобы начать заново."
    )
    return ConversationHandler.END


# ========================================
# СОЗДАНИЕ ConversationHandler'ов
# ========================================

def create_acceptance_foundation_handler():
    """ConversationHandler для акта приёмки фундамента"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(acceptance_start, pattern="^fill_acceptance_foundation$")],
        states={
            ACT_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, acceptance_number)],
            OBJECT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, acceptance_object)],
            CONTRACTOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, acceptance_contractor)],
            CUSTOMER: [MessageHandler(filters.TEXT & ~filters.COMMAND, acceptance_customer)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, acceptance_date)],
            FOUNDATION_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, acceptance_foundation_type)],
            VOLUME: [MessageHandler(filters.TEXT & ~filters.COMMAND, acceptance_volume)],
            CONCRETE_CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, acceptance_concrete_class)],
            INSPECTOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, acceptance_inspector)],
            DEFECTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, acceptance_defects)],
        },
        fallbacks=[CommandHandler("cancel", cancel_filling)],
        per_chat=True,
        per_user=True
    )


def create_complaint_contractor_handler():
    """ConversationHandler для претензии подрядчику"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(complaint_start, pattern="^fill_complaint_contractor$")],
        states={
            COMPLAINT_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_number)],
            COMPLAINT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_date)],
            CONTRACTOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_contractor_name)],
            CONTRACTOR_ADDR: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_contractor_addr)],
            SENDER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_sender_name)],
            SENDER_ADDR: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_sender_addr)],
            CONTRACT_NUM: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_contract_num)],
            CONTRACT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_contract_date)],
            DEFECT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_defect_desc)],
            DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_deadline)],
            PENALTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_penalty)],
        },
        fallbacks=[CommandHandler("cancel", cancel_filling)],
        per_chat=True,
        per_user=True
    )


def create_safety_plan_handler():
    """ConversationHandler для плана охраны труда"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(safety_plan_start, pattern="^fill_safety_plan$")],
        states={
            PLAN_OBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, safety_plan_object)],
            PLAN_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, safety_plan_year)],
            PLAN_RESPONSIBLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, safety_plan_responsible)],
            PLAN_WORKERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, safety_plan_workers)],
            PLAN_BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, safety_plan_budget)],
        },
        fallbacks=[CommandHandler("cancel", cancel_filling)],
        per_chat=True,
        per_user=True
    )


def create_hidden_works_act_handler():
    """ConversationHandler для акта освидетельствования скрытых работ"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(hidden_works_start, pattern="^fill_hidden_works_act$")],
        states={
            HIDDEN_ACT_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, hidden_act_number)],
            HIDDEN_OBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, hidden_object)],
            HIDDEN_CONTRACTOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, hidden_contractor)],
            HIDDEN_CUSTOMER: [MessageHandler(filters.TEXT & ~filters.COMMAND, hidden_customer)],
            HIDDEN_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, hidden_date)],
            HIDDEN_WORK_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, hidden_work_type)],
            HIDDEN_VOLUME: [MessageHandler(filters.TEXT & ~filters.COMMAND, hidden_volume)],
            HIDDEN_STANDARDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, hidden_standards)],
            HIDDEN_INSPECTOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, hidden_inspector)],
            HIDDEN_COMPLIANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, hidden_compliance)],
        },
        fallbacks=[CommandHandler("cancel", cancel_filling)],
        per_chat=True,
        per_user=True
    )
