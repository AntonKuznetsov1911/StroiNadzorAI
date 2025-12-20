"""
Интеграция новой AI координации в bot.py
Патч для handle_text и handle_photo с использованием:
- XAI как главный координатор
- OPENAI DALL-E для генерации изображений
- Anthropic Claude как fallback
- Параллельная генерация текста и изображений
"""

import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Импорт новых модулей
from ai_coordinator import (
    analyze_request_and_coordinate,
    generate_text_and_image_parallel,
    get_ai_status
)
from openai_dalle import (
    format_dalle_result,
    is_dalle_available
)

logger = logging.getLogger(__name__)


# === НОВЫЙ ОБРАБОТЧИК ТЕКСТА С AI КООРДИНАЦИЕЙ ===

async def handle_text_with_ai_coordination(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    conversation_history,
    system_prompt: str,
    user_id: int,
    question: str,
    add_message_to_history_async
):
    """
    Обработка текстового сообщения с использованием AI координации

    Args:
        update: Telegram Update
        context: Telegram Context
        conversation_history: История разговора
        system_prompt: Системный промпт
        user_id: ID пользователя
        question: Вопрос пользователя
        add_message_to_history_async: Функция для добавления в историю

    Returns:
        None (отправляет ответ пользователю)
    """
    thinking_message = await update.message.reply_text(
        "🤔 Думаю над вашим вопросом...\n\nВы можете не ждать, я пришлю уведомление 😉"
    )

    try:
        # Используем новую систему координации
        logger.info("🚀 Запуск AI координации...")

        # Проверяем статус AI
        ai_status = get_ai_status()
        logger.info(f"📊 Статус AI: {ai_status}")

        # Координируем запрос
        coordination_result = await analyze_request_and_coordinate(
            user_message=question,
            conversation_history=conversation_history,
            system_prompt=system_prompt
        )

        if coordination_result["error"]:
            # Ошибка - все AI недоступны
            await thinking_message.edit_text(
                f"❌ Извините, AI временно недоступны:\n\n{coordination_result['error']}\n\n"
                "Пожалуйста, попробуйте позже."
            )
            return

        # Получили текстовый ответ
        text_response = coordination_result["text_response"]
        ai_used = coordination_result["ai_used"]

        logger.info(f"✅ Получен ответ от {ai_used.upper()}")

        # Если нужно изображение - запускаем DALL-E
        if coordination_result["needs_image"] and coordination_result["image_prompt"]:
            logger.info("🎨 Запрос требует генерации изображения")

            # Сначала отправляем текстовый ответ
            ai_emoji = "🤖" if ai_used == "xai" else "🧠"
            await thinking_message.edit_text(
                f"💬 **Ответ** ({ai_emoji} {ai_used.upper()}):\n\n{text_response}\n\n"
                f"🎨 **Генерирую изображение...**"
            )

            # Добавляем в историю
            await add_message_to_history_async(user_id, 'user', question)
            await add_message_to_history_async(user_id, 'assistant', text_response)

            # Запускаем генерацию изображения
            if is_dalle_available():
                from openai_dalle import generate_image_dalle

                generating_msg = await update.message.reply_text(
                    "🎨 **Генерирую изображение через DALL-E...**\n"
                    "Это займет 10-30 секунд ⏳"
                )

                try:
                    image_result = await generate_image_dalle(
                        prompt=coordination_result["image_prompt"],
                        size="1024x1024",
                        quality="standard"
                    )

                    if image_result and image_result.get("image_data"):
                        # Удаляем сообщение о генерации
                        try:
                            await generating_msg.delete()
                        except:
                            pass

                        # Отправляем изображение
                        image_result["image_data"].seek(0)
                        caption = format_dalle_result(image_result, question)

                        await update.message.reply_photo(
                            photo=image_result["image_data"],
                            caption=caption,
                            parse_mode="Markdown"
                        )

                        # Добавляем в историю
                        await add_message_to_history_async(
                            user_id,
                            'assistant',
                            f"[Сгенерировано изображение через DALL-E: {question}]"
                        )

                        logger.info("✅ Изображение успешно отправлено")
                    else:
                        await generating_msg.edit_text(
                            "❌ Не удалось сгенерировать изображение через DALL-E"
                        )

                except Exception as e:
                    logger.error(f"❌ Ошибка генерации DALL-E: {e}")
                    await generating_msg.edit_text(
                        f"❌ Ошибка генерации изображения:\n{str(e)}"
                    )
            else:
                await update.message.reply_text(
                    "⚠️ DALL-E недоступен (нет OPENAI_API_KEY)\n\n"
                    "Текстовое описание выше содержит все необходимые детали."
                )

        else:
            # Только текстовый ответ, без изображения
            try:
                await thinking_message.delete()
            except:
                pass

            # Выбираем эмодзи в зависимости от использованного AI
            ai_emoji = "🤖" if ai_used == "xai" else "🧠"

            await update.message.reply_text(
                f"💬 **Ответ** ({ai_emoji} {ai_used.upper()}):\n\n{text_response}",
                parse_mode="Markdown"
            )

            # Добавляем в историю
            await add_message_to_history_async(user_id, 'user', question)
            await add_message_to_history_async(user_id, 'assistant', text_response)

            logger.info("✅ Ответ отправлен пользователю")

    except Exception as e:
        logger.error(f"❌ Критическая ошибка обработки: {e}")
        import traceback
        traceback.print_exc()

        try:
            await thinking_message.delete()
        except:
            pass

        await update.message.reply_text(
            f"❌ Произошла ошибка при обработке запроса:\n\n{str(e)}\n\n"
            "Пожалуйста, попробуйте еще раз."
        )


# === КОМАНДА ДЛЯ ПРОВЕРКИ СТАТУСА AI ===

async def ai_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /ai_status - показать статус всех AI сервисов
    """
    status = get_ai_status()

    status_text = "🤖 **Статус AI Сервисов**\n\n"

    # XAI
    if status["xai_available"]:
        status_text += "✅ **XAI (Grok)**: Доступен (главный AI)\n"
    else:
        status_text += "❌ **XAI (Grok)**: Недоступен\n"

    # OpenAI
    if status["openai_available"]:
        status_text += "✅ **OpenAI (DALL-E)**: Доступен (генерация изображений)\n"
    else:
        status_text += "❌ **OpenAI (DALL-E)**: Недоступен\n"

    # Anthropic
    if status["anthropic_available"]:
        status_text += "✅ **Anthropic (Claude)**: Доступен (резервный AI)\n"
    else:
        status_text += "❌ **Anthropic (Claude)**: Недоступен\n"

    status_text += "\n---\n"

    # Рекомендации
    if status["xai_available"]:
        status_text += "✅ Основной AI работает нормально"
    else:
        if status["anthropic_available"]:
            status_text += "⚠️ Основной AI недоступен, используется резервный Claude"
        else:
            status_text += "❌ Все AI сервисы недоступны"

    await update.message.reply_text(status_text, parse_mode="Markdown")


# === ТЕСТОВАЯ ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЯ ===

async def test_dalle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /test_dalle - тест генерации изображения через DALL-E
    """
    if not is_dalle_available():
        await update.message.reply_text(
            "❌ DALL-E недоступен\n\n"
            "Проверьте, что OPENAI_API_KEY установлен в .env файле"
        )
        return

    test_msg = await update.message.reply_text(
        "🧪 Запуск тестовой генерации DALL-E...\n"
        "Генерирую тестовую схему фундамента..."
    )

    try:
        from openai_dalle import generate_image_dalle

        result = await generate_image_dalle(
            prompt="Technical construction diagram showing concrete foundation cross-section with reinforcement, professional blueprint style",
            size="1024x1024",
            quality="standard"
        )

        if result and result.get("image_data"):
            await test_msg.edit_text("✅ Тест успешен! Отправляю изображение...")

            result["image_data"].seek(0)
            await update.message.reply_photo(
                photo=result["image_data"],
                caption=f"🧪 **Тестовая генерация DALL-E**\n\n{format_dalle_result(result, 'Test')}",
                parse_mode="Markdown"
            )

            await test_msg.delete()
        else:
            await test_msg.edit_text("❌ Тест провален: изображение не сгенерировано")

    except Exception as e:
        await test_msg.edit_text(f"❌ Ошибка теста:\n\n{str(e)}")
        logger.error(f"Test DALL-E error: {e}")


# === ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ ДЛЯ ИНТЕГРАЦИИ В bot.py ===

"""
Чтобы интегрировать новую систему в bot.py:

1. Добавьте в начало bot.py после других импортов:

    from bot_ai_integration import (
        handle_text_with_ai_coordination,
        ai_status_command,
        test_dalle_command
    )

2. В функции handle_text замените блок генерации ответа на:

    await handle_text_with_ai_coordination(
        update=update,
        context=context,
        conversation_history=conversation_history,
        system_prompt=system_prompt,
        user_id=user_id,
        question=question,
        add_message_to_history_async=add_message_to_history_async
    )

3. Добавьте команды в функцию main():

    application.add_handler(CommandHandler("ai_status", ai_status_command))
    application.add_handler(CommandHandler("test_dalle", test_dalle_command))

4. Обновите текст команды /help для включения новых команд
"""
