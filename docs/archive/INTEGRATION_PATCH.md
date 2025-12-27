# ПАТЧ ДЛЯ ИНТЕГРАЦИИ УМНОГО ВЫБОРА МОДЕЛЕЙ

## Что нужно сделать в bot.py

### 1. Найти функцию `handle_text` (строка ~3446)

### 2. После строки `thinking_message = await update.message.reply_text(thinking_text, parse_mode="Markdown")`

Добавить следующий блок кода:

```python
        # ============================================================================
        # ОПТИМИЗАЦИЯ: Умный выбор модели на основе типа запроса
        # ============================================================================

        if MODEL_SELECTOR_AVAILABLE and OPTIMIZED_HANDLERS_AVAILABLE:
            try:
                # Используем умный селектор модели
                selector = ModelSelector()
                decision = selector.classify_request(question, has_photo=False)

                logger.info(f"🤖 Выбрана модель: {decision['model']}")
                logger.info(f"💡 Причина: {decision['reason']}")
                logger.info(f"💰 Стоимость: ${decision['estimated_cost']:.3f}")

                # Получаем историю разговора
                conversation_history = await get_user_history(user_id, limit=10)

                # CLAUDE - технические вопросы
                if decision["model"] == "claude_technical":
                    if OPTIMIZED_PROMPTS_AVAILABLE:
                        system_prompt = CLAUDE_SYSTEM_PROMPT_TECHNICAL
                    else:
                        system_prompt = "Вы — эксперт по строительным нормативам РФ."

                    try:
                        answer = await handle_with_claude_technical(
                            question=question,
                            user_id=user_id,
                            conversation_history=conversation_history,
                            system_prompt=system_prompt
                        )

                        # Удаляем thinking message
                        try:
                            await thinking_message.delete()
                        except:
                            pass

                        # Отправляем ответ
                        await update.message.reply_text(
                            f"💬 {answer}\n\n_Ответ от Claude Sonnet 4.5_",
                            parse_mode="Markdown"
                        )

                        # Сохраняем в историю
                        await add_message_to_history_async(user_id, 'assistant', answer)

                        logger.info("✅ Ответ отправлен (Claude)")
                        return

                    except Exception as e:
                        logger.error(f"❌ Ошибка Claude: {e}")
                        # Продолжим с Grok как fallback

                # CLAUDE + DALL-E - генерация чертежей
                elif decision["model"] == "claude_dalle":
                    if OPTIMIZED_PROMPTS_AVAILABLE:
                        dalle_prompt_system = CLAUDE_DALLE_PROMPT_CREATOR
                    else:
                        dalle_prompt_system = "Создай промпт для DALL-E."

                    try:
                        # Обновляем сообщение
                        await thinking_message.edit_text(
                            "📐 Генерирую технический чертёж...\n\n"
                            "Шаг 1/2: Claude создаёт промпт по ГОСТ"
                        )

                        result = await handle_with_claude_dalle(
                            question=question,
                            dalle_prompt_creator_system=dalle_prompt_system
                        )

                        # Удаляем thinking message
                        try:
                            await thinking_message.delete()
                        except:
                            pass

                        # Отправляем изображение
                        await update.message.reply_photo(
                            photo=result["image_url"],
                            caption=f"{result['description']}\n\n_Чертёж создан: Claude + DALL-E 3_"
                        )

                        # Сохраняем в историю
                        await add_message_to_history_async(user_id, 'assistant', f"[Сгенерирован чертёж: {question}]")

                        logger.info("✅ Чертёж отправлен (Claude→DALL-E)")
                        return

                    except Exception as e:
                        logger.error(f"❌ Ошибка генерации чертежа: {e}")
                        # Продолжим с Grok

                # GROK - для всех остальных случаев (простые вопросы, web search)
                # Код ниже продолжает обычную обработку через Grok...

            except Exception as e:
                logger.error(f"❌ Ошибка умного выбора модели: {e}")
                # Продолжаем с обычной обработкой через Grok

        # Если MODEL_SELECTOR не доступен или произошла ошибка - используем Grok
```

### 3. После этого блока продолжается обычная обработка через Grok

Весь существующий код с Grok остаётся без изменений - он будет использоваться как fallback и для простых вопросов.

---

## Для handle_photo (анализ фото)

### Найти функцию `handle_photo` (строка ~2863)

### После получения фото, перед вызовом AI, добавить:

```python
        # ============================================================================
        # ОПТИМИЗАЦИЯ: Gemini Vision для анализа дефектов
        # ============================================================================

        if MODEL_SELECTOR_AVAILABLE and OPTIMIZED_HANDLERS_AVAILABLE:
            try:
                selector = ModelSelector()
                decision = selector.classify_request(caption_text or "Анализ фото", has_photo=True)

                # Если это дефект -> Gemini
                if decision["model"] == "gemini_vision":
                    logger.info("🟣 Используем Gemini Vision для анализа дефекта")

                    try:
                        if OPTIMIZED_PROMPTS_AVAILABLE:
                            system_prompt = GEMINI_VISION_PROMPT_DEFECTS
                        else:
                            system_prompt = "Проанализируй фото дефекта"

                        analysis = await handle_with_gemini_vision(
                            question=caption_text or "Проанализируй это фото",
                            photo_file_id=photo.file_id,
                            bot=context.bot,
                            system_prompt=system_prompt
                        )

                        # Отправляем анализ
                        await update.message.reply_text(
                            f"🔍 **АНАЛИЗ ДЕФЕКТА:**\n\n{analysis}\n\n_Анализ от Gemini Vision_",
                            parse_mode="Markdown"
                        )

                        logger.info("✅ Анализ отправлен (Gemini)")
                        return

                    except Exception as e:
                        logger.error(f"❌ Ошибка Gemini: {e}")
                        # Продолжим с Grok

            except Exception as e:
                logger.error(f"❌ Ошибка выбора модели для фото: {e}")

        # Продолжается обычная обработка через Grok...
```

---

## ВНИМАНИЕ

Не нужно удалять существующий код с Grok! Он остаётся как:
1. Fallback при ошибках других моделей
2. Обработчик простых вопросов (70% запросов)
3. Web search через встроенные инструменты Grok

Умный выбор модели работает ДО вызова Grok и перехватывает только:
- Технические вопросы → Claude
- Генерацию чертежей → Claude + DALL-E
- Анализ дефектов на фото → Gemini

Всё остальное идёт через Grok как обычно.
