"""
Wrapper для умного выбора модели
Вызывается в начале handle_text и handle_photo
Если возвращает результат - используется он, иначе продолжается обычная обработка через Grok
"""

import logging
from typing import Optional, Dict
import asyncio

logger = logging.getLogger(__name__)


async def smart_model_selection_text(
    question: str,
    user_id: int,
    thinking_message,
    update,
    context
) -> Optional[Dict]:
    """
    Умный выбор модели для текстовых сообщений

    Returns:
        Dict с результатом или None (если нужно использовать Grok)
    """
    try:
        from model_selector import ModelSelector
        from optimized_handlers import handle_with_claude_technical, handle_with_gemini_image, handle_with_grok
        from optimized_prompts import CLAUDE_SYSTEM_PROMPT_TECHNICAL, GEMINI_IMAGE_PROMPT_SYSTEM, GROK_SYSTEM_PROMPT_GENERAL
        from history_manager import get_user_history, add_message_to_history_async

        selector = ModelSelector()
        decision = selector.classify_request(question, has_photo=False)

        logger.info(f"🤖 Умный выбор: {decision['model']}")
        logger.info(f"💡 {decision['reason']}")
        logger.info(f"💰 Стоимость: ${decision['estimated_cost']:.3f}")

        # CLAUDE - технические вопросы
        if decision["model"] == "claude_technical":
            try:
                conversation_history = await get_user_history(user_id, limit=10)

                answer = await handle_with_claude_technical(
                    question=question,
                    user_id=user_id,
                    conversation_history=conversation_history,
                    system_prompt=CLAUDE_SYSTEM_PROMPT_TECHNICAL
                )

                # Удаляем thinking message
                try:
                    await thinking_message.delete()
                except Exception:
                    pass

                # Отправляем ответ
                await update.message.reply_text(
                    f"{answer}\n\n_✨ Claude Sonnet 4.5_",
                    parse_mode="Markdown"
                )

                # Сохраняем
                await add_message_to_history_async(user_id, 'assistant', answer)

                logger.info("✅ Ответ отправлен (Claude)")
                return {"success": True, "model": "claude"}

            except Exception as e:
                logger.error(f"❌ Ошибка Claude: {e}")
                return None  # Fallback на Grok

        # GEMINI - генерация чертежей
        elif decision["model"] == "gemini_image":
            try:
                await thinking_message.edit_text(
                    "🎨 Генерирую технический чертёж...\n\n"
                    "🟣 Gemini 2.5 Flash Image создаёт изображение"
                )

                result = await handle_with_gemini_image(
                    question=question,
                    image_prompt_system=GEMINI_IMAGE_PROMPT_SYSTEM
                )

                try:
                    await thinking_message.delete()
                except Exception:
                    pass

                # Если получили изображение - отправляем его
                if result.get('image_data'):
                    result['image_data'].seek(0)  # Перемещаем указатель в начало

                    caption = f"🎨 **Технический чертёж**\n\n"
                    if result.get('description'):
                        caption += f"{result['description']}\n\n"
                    caption += "_✨ Gemini 2.5 Flash Image_"

                    await update.message.reply_photo(
                        photo=result['image_data'],
                        caption=caption,
                        parse_mode="Markdown"
                    )

                    await add_message_to_history_async(user_id, 'assistant', f"[Чертёж сгенерирован: {question}]")
                    logger.info("✅ Изображение отправлено (Gemini)")
                else:
                    # Если изображение не получено - отправляем текстовое описание
                    await update.message.reply_text(
                        f"📐 **ТЕХНИЧЕСКОЕ ОПИСАНИЕ**\n\n{result.get('description', 'Не удалось создать изображение')}\n\n_✨ Gemini 2.5 Flash_",
                        parse_mode="Markdown"
                    )

                    await add_message_to_history_async(user_id, 'assistant', f"[Описание чертежа: {question}]")
                    logger.info("✅ Описание отправлено (Gemini)")

                return {"success": True, "model": "gemini_image"}

            except Exception as e:
                logger.error(f"❌ Ошибка генерации чертежа: {e}")
                return None

        # GROK - простые вопросы и web search
        elif decision["model"] == "grok_general":
            try:
                conversation_history = await get_user_history(user_id, limit=10)

                answer = await handle_with_grok(
                    question=question,
                    user_id=user_id,
                    conversation_history=conversation_history,
                    system_prompt=GROK_SYSTEM_PROMPT_GENERAL,
                    needs_web_search=decision.get("needs_web_search", False)
                )

                # Удаляем thinking message
                try:
                    await thinking_message.delete()
                except Exception:
                    pass

                # Отправляем ответ
                await update.message.reply_text(
                    f"{answer}\n\n_✨ Grok {'(Web Search)' if decision.get('needs_web_search') else ''}_",
                    parse_mode="Markdown"
                )

                # Сохраняем
                await add_message_to_history_async(user_id, 'assistant', answer)

                logger.info("✅ Ответ отправлен (Grok)")
                return {"success": True, "model": "grok"}

            except Exception as e:
                logger.error(f"❌ Ошибка Grok: {e}")
                return None  # Fallback на старый обработчик

        # Если модель не распознана - возвращаем None
        return None  # Продолжить с существующим обработчиком

    except ImportError:
        logger.warning("⚠️ Модули оптимизации не найдены - используется Grok")
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка умного выбора: {e}")
        return None


async def smart_model_selection_photo(
    question: str,
    photo_file_id: str,
    update,
    context
) -> Optional[Dict]:
    """
    Умный выбор модели для фото

    Returns:
        Dict с результатом или None (если нужно использовать Grok)
    """
    try:
        from model_selector import ModelSelector
        from optimized_handlers import handle_with_gemini_vision
        from optimized_prompts import GEMINI_VISION_PROMPT_DEFECTS

        selector = ModelSelector()
        decision = selector.classify_request(question, has_photo=True)

        logger.info(f"📸 Умный выбор для фото: {decision['model']}")

        # GEMINI - анализ дефектов
        if decision["model"] == "gemini_vision":
            try:
                analysis = await handle_with_gemini_vision(
                    question=question,
                    photo_file_id=photo_file_id,
                    bot=context.bot,
                    system_prompt=GEMINI_VISION_PROMPT_DEFECTS
                )

                await update.message.reply_text(
                    f"{analysis}\n\n_✨ Gemini Vision_",
                    parse_mode="Markdown"
                )

                logger.info("✅ Анализ отправлен (Gemini)")
                return {"success": True, "model": "gemini"}

            except Exception as e:
                logger.error(f"❌ Ошибка Gemini: {e}")
                return None

        return None  # Продолжить с Grok

    except ImportError:
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка выбора модели для фото: {e}")
        return None
