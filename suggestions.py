"""
Модуль предложений по улучшению бота
Версия 1.0 - Сбор предложений от пользователей

Пользователи могут отправлять предложения по улучшению бота.
Все предложения сохраняются в suggestions.log для последующего анализа.
"""

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

logger = logging.getLogger(__name__)

# Состояния
WAITING_FOR_SUGGESTION = 1


async def suggestions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню предложений"""

    query = update.callback_query
    if query:
        await query.answer()

        keyboard = [
            [InlineKeyboardButton("✍️ Отправить предложение", callback_data="send_suggestion")],
            [InlineKeyboardButton("« Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "💡 **ПРЕДЛОЖЕНИЯ ПО УЛУЧШЕНИЮ**\n\n"
            "Здесь вы можете предложить:\n"
            "• Новые функции для бота\n"
            "• Улучшения существующих возможностей\n"
            "• Исправления неудобств\n"
            "• Новые калькуляторы или документы\n"
            "• Любые другие идеи\n\n"
            "Все предложения сохраняются и рассматриваются!"
        )

        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        keyboard = [
            [InlineKeyboardButton("✍️ Отправить предложение", callback_data="send_suggestion")],
            [InlineKeyboardButton("« Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "💡 **ПРЕДЛОЖЕНИЯ ПО УЛУЧШЕНИЮ**\n\n"
            "Здесь вы можете предложить:\n"
            "• Новые функции для бота\n"
            "• Улучшения существующих возможностей\n"
            "• Исправления неудобств\n"
            "• Новые калькуляторы или документы\n"
            "• Любые другие идеи\n\n"
            "Все предложения сохраняются и рассматриваются!"
        )

        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def start_suggestion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает процесс отправки предложения"""

    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton("« Отмена", callback_data="cancel_suggestion")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "✍️ Опишите ваше предложение:\n\n"
        "Можете написать всё что угодно - идеи, улучшения, новые функции.\n"
        "Постарайтесь быть максимально конкретными.\n\n"
        "Отправьте сообщение с вашим предложением:",
        reply_markup=reply_markup
    )

    return WAITING_FOR_SUGGESTION


async def receive_suggestion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает и сохраняет предложение"""

    user = update.effective_user
    suggestion_text = update.message.text

    # Сохраняем в лог файл
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = f"""
{'='*80}
ДАТА: {timestamp}
ПОЛЬЗОВАТЕЛЬ: {user.id} (@{user.username or 'без username'}) - {user.full_name}
ПРЕДЛОЖЕНИЕ:
{suggestion_text}
{'='*80}

"""

    try:
        with open("suggestions.log", "a", encoding="utf-8") as f:
            f.write(log_entry)
        logger.info(f"✅ Предложение сохранено от пользователя {user.id}")

        keyboard = [[InlineKeyboardButton("« Главное меню", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "✅ Спасибо за ваше предложение!\n\n"
            "Оно успешно сохранено и будет рассмотрено.\n"
            "Мы стараемся учитывать пожелания пользователей при развитии бота.\n\n"
            "💡 Если у вас есть ещё идеи - всегда можете вернуться в это меню!",
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"❌ Ошибка сохранения предложения: {e}")

        await update.message.reply_text(
            "⚠️ Произошла ошибка при сохранении предложения.\n"
            "Попробуйте ещё раз позже."
        )

    return ConversationHandler.END


async def cancel_suggestion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменяет отправку предложения"""

    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton("« Главное меню", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "❌ Отправка предложения отменена.\n\n"
        "Вы можете вернуться в меню предложений в любое время!",
        reply_markup=reply_markup
    )

    return ConversationHandler.END


def create_suggestions_handler():
    """Создаёт ConversationHandler для предложений"""

    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_suggestion, pattern="^send_suggestion$")
        ],
        states={
            WAITING_FOR_SUGGESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_suggestion)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_suggestion, pattern="^cancel_suggestion$")
        ],
        per_chat=True,
        per_user=True
    )
