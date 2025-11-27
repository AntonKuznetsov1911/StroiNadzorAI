"""
Claude AI Service - Professional Chief Foreman Expert
Anthropic Claude API integration with RAG and Context Memory
"""

import logging
import time
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from anthropic import Anthropic, AsyncAnthropic

from config.settings import settings
from src.services.vector_service import get_vector_service
from src.services.context_service import get_context_service
from data.construction_knowledge import get_knowledge_context

logger = logging.getLogger(__name__)


class ClaudeServiceV2:
    """
    Claude AI Service с экспертными промптами главного прораба
    Интеграция: RAG + Context Memory + База знаний
    """

    def __init__(self):
        """Инициализация"""
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY if hasattr(settings, 'ANTHROPIC_API_KEY') else settings.OPENAI_API_KEY)
        self.async_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY if hasattr(settings, 'ANTHROPIC_API_KEY') else settings.OPENAI_API_KEY)

        self.vector_service = get_vector_service()
        self.context_service = get_context_service()

        # Модель Claude
        self.model = "claude-sonnet-4-5-20250929"  # Claude Sonnet 4.5
        self.max_tokens = 4000

        # Системный промпт ГЛАВНОГО ПРОРАБА
        self.expert_system_prompt = """Ты - ГЛАВНЫЙ ПРОРАБ с 25-летним опытом в строительстве и техническом надзоре.

🏗️ ТВОЙ ОПЫТ:
- Строительство более 50 объектов (жилые дома, промышленные здания, инфраструктура)
- Экспертиза по СП, ГОСТ, СНиП - знаешь наизусть ключевые пункты
- Сертифицированный специалист по технадзору и строительному контролю
- Работал с различными конструкциями: монолит, кирпич, металлоконструкции, деревянные каркасы
- Решал тысячи проблем на стройплощадках

🎯 ПРИНЦИПЫ ОТВЕТОВ (ОБЯЗАТЕЛЬНО):

1. ТОЧНОСТЬ - оперируй РЕАЛЬНЫМИ данными из нормативов:
   - Конкретные цифры (0,3 мм для трещин, 200 мм для защитного слоя)
   - Точные пункты СП/ГОСТ (СП 63.13330.2018 п.8.2.2)
   - Формулы с единицами измерения
   - Таблицы значений

2. ПРАКТИЧНОСТЬ - как на стройке:
   - "Сначала проверь..., затем..."
   - "Берешь... и делаешь..."
   - "Если видишь X, значит Y"
   - Инструменты: рулетка, уровень, склерометр, УЗИ-дефектоскоп

3. ОТВЕТСТВЕННОСТЬ:
   - Различай КРИТИЧНО/ВАЖНО/ДОПУСТИМО
   - "Это опасно! Надо немедленно..." vs "Можно отложить"
   - Указывай последствия: "Если не устранить → обрушение/протечка/штраф"

4. ВИЗУАЛИЗАЦИЯ (если нужно):
   - Схемы узлов
   - Эскизы решений
   - Таблицы сравнения
   - Примеры расчетов

📋 СТРУКТУРА ОТВЕТА:

🔍 ОЦЕНКА СИТУАЦИИ (2-3 предложения):
- Что вижу/понимаю
- Насколько это серьезно (с эмоджи: 🟢 норма / 🟡 внимание / 🔴 опасно)

📐 ТЕХНИЧЕСКИЕ ДЕТАЛИ:
- Конкретные требования СП/ГОСТ с пунктами
- Цифры, параметры, допуски
- Таблицы (если применимо)

💡 ПРАКТИЧЕСКИЕ ДЕЙСТВИЯ (пошагово):
1. Первое что делаешь...
2. Затем проверяешь...
3. Если обнаружил X, то...

📚 НОРМАТИВНАЯ БАЗА:
- СП 63.13330.2018 п.X.Y.Z - конкретное требование
- Связанные документы

⚠️ КРИТИЧНЫЕ МОМЕНТЫ:
- НА ЧТО ОБРАТИТЬ ОСОБОЕ ВНИМАНИЕ (заглавными)
- Частые ошибки
- Что точно нельзя делать

🛠️ РЕКОМЕНДАЦИИ:
- Материалы (конкретные марки)
- Инструменты
- Сроки и объемы

ПРАВИЛА:
❌ НЕ говори "я AI модель" - ты ПРОРАБ
❌ НЕ используй общие фразы - только конкретика
❌ НЕ давай советы "проконсультируйтесь" - ты САМ эксперт
✅ Говори от первого лица: "Я бы сделал...", "По моему опыту..."
✅ Используй профессиональный жаргон: "марка бетона", "армокаркас", "продухи"
✅ Приводи примеры из практики: "Был случай на объекте..."

БАЗА НОРМАТИВОВ (знаешь наизусть):
{normatives_context}

Отвечай как НАСТОЯЩИЙ прораб - четко, ясно, по делу. Жизнь людей зависит от правильных решений!"""

        logger.info("ClaudeServiceV2 initialized with Claude Sonnet 4.5")

    async def analyze_with_rag(
        self,
        db: Session,
        user_id: int,
        question: str,
        use_context: bool = True
    ) -> str:
        """
        Анализ вопроса с RAG и контекстом

        Args:
            db: Database session
            user_id: ID пользователя
            question: Вопрос
            use_context: Использовать историю

        Returns:
            str: Ответ эксперта
        """
        start_time = time.time()

        try:
            # 1. RAG - поиск в векторной БД
            relevant_docs = self.vector_service.search(
                query=question,
                n_results=3
            )

            # 2. База знаний
            knowledge_context = get_knowledge_context(question)

            # 3. Формируем контекст нормативов
            rag_context = ""
            if relevant_docs:
                rag_context = "\n\n📚 РЕЛЕВАНТНЫЕ ДАННЫЕ ИЗ БАЗЫ НОРМАТИВОВ:\n"
                for doc in relevant_docs:
                    rag_context += f"\n{doc['document']}\n"

            # 4. История разговора
            conversation_history = []
            if use_context:
                conversation_history = self.context_service.get_conversation_history(
                    db, user_id, limit=3
                )

            # 5. Системный промпт с контекстом
            system_prompt = self.expert_system_prompt.format(
                normatives_context=knowledge_context + rag_context
            )

            # 6. Формируем сообщения для Claude
            messages = []

            # Добавляем историю
            if conversation_history:
                for msg in conversation_history[-6:]:
                    messages.append({
                        "role": "user" if msg['role'] == 'user' else "assistant",
                        "content": msg['content']
                    })

            # Текущий вопрос
            messages.append({
                "role": "user",
                "content": question
            })

            # 7. Запрос к Claude
            response = await self.async_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=messages
            )

            answer = response.content[0].text
            processing_time = time.time() - start_time

            # 8. Сохраняем в контекст
            self.context_service.add_message(user_id, "user", question)
            self.context_service.add_message(user_id, "assistant", answer)

            logger.info(f"Claude RAG analysis completed in {processing_time:.2f}s")
            return answer

        except Exception as e:
            logger.error(f"Error in Claude RAG analysis: {e}", exc_info=True)
            raise

    async def analyze_photo_with_context(
        self,
        db: Session,
        user_id: int,
        photo_base64: str,
        caption: Optional[str] = None
    ) -> str:
        """
        Анализ фото с контекстом

        Args:
            db: Database session
            user_id: ID пользователя
            photo_base64: Фото в base64
            caption: Подпись

        Returns:
            str: Экспертный анализ
        """
        start_time = time.time()

        try:
            # История разговора
            conversation_history = self.context_service.get_conversation_history(
                db, user_id, limit=2
            )

            # Формируем сообщение
            user_message = "Проанализируй строительный объект/дефект на фото. Дай экспертную оценку."
            if caption:
                user_message += f"\n\nКонтекст: {caption}"

            # Релевантные нормативы
            search_query = caption if caption else "анализ конструкций дефекты"
            knowledge_context = get_knowledge_context(search_query)

            # Промпт с контекстом
            photo_prompt = self.expert_system_prompt.format(
                normatives_context=knowledge_context
            )

            # Формируем сообщения
            messages = []

            # История (только текст)
            if conversation_history:
                for msg in conversation_history[-4:]:
                    if len(msg['content']) < 500:  # Короткие сообщения
                        messages.append({
                            "role": "user" if msg['role'] == 'user' else "assistant",
                            "content": msg['content'][:200]
                        })

            # Текущее фото
            messages.append({
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
            })

            # Запрос к Claude
            response = await self.async_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=photo_prompt,
                messages=messages
            )

            analysis = response.content[0].text
            processing_time = time.time() - start_time

            # Сохраняем в контекст
            self.context_service.add_message(user_id, "user", f"[Фото] {caption or 'Анализ фото'}")
            self.context_service.add_message(user_id, "assistant", analysis)

            logger.info(f"Claude photo analysis completed in {processing_time:.2f}s")
            return analysis

        except Exception as e:
            logger.error(f"Error in Claude photo analysis: {e}", exc_info=True)
            raise

    async def transcribe_voice(self, audio_file_path: str) -> str:
        """
        Распознавание голоса через Claude (если доступно)
        Альтернатива: использовать другой сервис для транскрипции

        Args:
            audio_file_path: Путь к аудио файлу

        Returns:
            str: Распознанный текст
        """
        # Claude пока не поддерживает audio transcription
        # Нужно использовать другой сервис (например, Whisper API отдельно)
        logger.warning("Voice transcription not available with Claude, need separate service")
        raise NotImplementedError("Voice transcription requires separate service")

    # ===== МЕТОДЫ ДЛЯ СОВМЕСТИМОСТИ С СУЩЕСТВУЮЩИМ КОДОМ =====

    async def analyze_text_question(
        self,
        question: str,
        user_id: Optional[int] = None,
        db: Optional[Session] = None
    ) -> str:
        """
        Анализ текстового вопроса (совместимость с openai_service)

        Args:
            question: Вопрос пользователя
            user_id: ID пользователя (опционально)
            db: Database session (опционально)

        Returns:
            str: Ответ
        """
        if db and user_id:
            return await self.analyze_with_rag(db, user_id, question)
        else:
            # Без контекста - простой запрос
            try:
                knowledge_context = get_knowledge_context(question)
                system_prompt = self.expert_system_prompt.format(
                    normatives_context=knowledge_context
                )

                response = await self.async_client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": question}]
                )

                return response.content[0].text
            except Exception as e:
                logger.error(f"Error in analyze_text_question: {e}")
                raise

    async def analyze_photo(
        self,
        photo_base64: str,
        caption: Optional[str] = None,
        user_id: Optional[int] = None,
        db: Optional[Session] = None
    ) -> str:
        """
        Анализ фотографии (совместимость с openai_service)

        Args:
            photo_base64: Фото в base64
            caption: Подпись к фото
            user_id: ID пользователя (опционально)
            db: Database session (опционально)

        Returns:
            str: Анализ
        """
        if db and user_id:
            return await self.analyze_photo_with_context(db, user_id, photo_base64, caption)
        else:
            # Без контекста - простой анализ
            try:
                knowledge_context = get_knowledge_context(caption or "анализ конструкций дефекты")
                photo_prompt = self.expert_system_prompt.format(
                    normatives_context=knowledge_context
                )

                user_message = caption if caption else "Проанализируй это фото с точки зрения строительных норм. Найди дефекты и дай рекомендации."

                messages = [{
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
                }]

                response = await self.async_client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=photo_prompt,
                    messages=messages
                )

                return response.content[0].text
            except Exception as e:
                logger.error(f"Error in analyze_photo: {e}")
                raise


# Singleton
_claude_service_instance: Optional[ClaudeServiceV2] = None


def get_claude_service() -> ClaudeServiceV2:
    """Получить singleton ClaudeServiceV2"""
    global _claude_service_instance
    if _claude_service_instance is None:
        _claude_service_instance = ClaudeServiceV2()
    return _claude_service_instance
