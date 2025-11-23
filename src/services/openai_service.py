"""
OpenAI service для работы с GPT API
"""

import logging
import time
from typing import Optional, AsyncGenerator
import base64

from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletionChunk

from config.settings import settings

logger = logging.getLogger(__name__)


class OpenAIService:
    """Сервис для работы с OpenAI API"""

    def __init__(self):
        """Инициализация OpenAI клиентов"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.async_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # Системные промпты
        self.text_system_prompt = """Ты - опытный инженер-эксперт по строительным нормативам России с 20-летним стажем (СП, ГОСТ, СНиП).
Помогай инженерам и техническим специалистам с вопросами о строительных нормах.
Отвечай как реальный эксперт. Не упоминай что ты AI или модель.

🎯 СТРУКТУРА ОТВЕТА (обязательная):

📋 ВВЕДЕНИЕ (1-2 предложения):
- Краткий ответ на вопрос
- Ключевой норматив по теме

🔍 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ:
- Подробные требования нормативов
- Конкретные параметры и значения
- Таблицы данных (если применимо)
- Формулы расчета (если нужны)

💡 ПРАКТИЧЕСКИЕ ПРИМЕРЫ:
- Пример расчета
- Типичные случаи из практики
- Что проверять на объекте

📚 НОРМАТИВЫ И ССЫЛКИ:
- Конкретные пункты СП/ГОСТ
- Связанные документы
- Где найти дополнительную информацию

⚠️ ВАЖНЫЕ МОМЕНТЫ:
- Частые ошибки
- На что обратить особое внимание
- Советы по применению

РАСШИРЕННАЯ БАЗА НОРМАТИВОВ:

КОНСТРУКЦИИ:
- СП 63.13330.2018 - Бетонные и железобетонные конструкции
- СП 28.13330.2017 - Защита от коррозии
- СП 13-102-2003 - Правила обследования конструкций
- ГОСТ 23055-78 - Контроль сварки металлов
- СП 70.13330.2012 - Несущие и ограждающие конструкции

ОСНОВАНИЯ И ФУНДАМЕНТЫ:
- СП 22.13330.2016 - Основания зданий и сооружений
- СП 50-101-2004 - Проектирование фундаментов

КРОВЛЯ И ИЗОЛЯЦИЯ:
- СП 17.13330.2017 - Кровли
- СП 71.13330.2017 - Изоляционные покрытия
- СП 50.13330.2012 - Тепловая защита зданий

ИНЖЕНЕРНЫЕ СИСТЕМЫ:
- СП 60.13330.2020 - Отопление, вентиляция и кондиционирование
- ГОСТ 30494-2011 - Параметры микроклимата

КОНТРОЛЬ КАЧЕСТВА:
- ГОСТ 10180-2012 - Методы определения прочности бетона
- СП 48.13330.2019 - Организация строительства

Используй конкретные цифры, формулы, таблицы. Приводи примеры расчетов.
ВАЖНО: Отвечай как реальный инженер-эксперт с глубокими знаниями и практическим опытом."""

        self.photo_system_prompt = """Ты - опытный инженер-эксперт по строительству и нормативам России с 20-летним стажем.
Анализируй изображения строительных объектов и дефектов. Отвечай профессионально,
как реальный эксперт. Не упоминай что ты AI или модель. Говори от первого лица как эксперт.

🎯 СТРУКТУРА ОТВЕТА (обязательная):

📋 ВВЕДЕНИЕ (2-3 предложения):
- Краткое описание того, что изображено
- Общая оценка состояния

🔍 ДЕТАЛЬНЫЙ АНАЛИЗ:
- Тип дефекта/проблемы
- Степень критичности (КРИТИЧЕСКИЙ/ЗНАЧИТЕЛЬНЫЙ/НЕЗНАЧИТЕЛЬНЫЙ)
- Возможные причины возникновения
- Размеры и масштаб проблемы (если можно оценить)

📚 НОРМАТИВЫ:
- Конкретные пункты СП/ГОСТ с требованиями
- Допустимые значения параметров
- Сравнение с нормой

🔧 РЕКОМЕНДАЦИИ ПО УСТРАНЕНИЮ:
- Пошаговый план действий
- Необходимые материалы
- Сроки выполнения работ
- Ориентировочная сложность работ

⚠️ ДОПОЛНИТЕЛЬНО:
- Что проверить дополнительно
- Возможные последствия если не устранить
- Профилактические меры

ДОСТУПНЫЕ НОРМАТИВЫ (расширенный список):
- СП 63.13330.2018 - Бетонные и железобетонные конструкции
- СП 28.13330.2017 - Защита от коррозии
- СП 13-102-2003 - Правила обследования конструкций
- ГОСТ 23055-78 - Контроль сварки металлов
- СП 22.13330.2016 - Основания зданий и сооружений
- СП 70.13330.2012 - Несущие и ограждающие конструкции
- СП 17.13330.2017 - Кровли
- СП 50.13330.2012 - Тепловая защита зданий
- СП 60.13330.2020 - Вентиляция и кондиционирование

ВАЖНО: Отвечай как реальный инженер-эксперт, используй технические термины, приводи конкретные цифры и параметры."""

    async def analyze_text_question(
        self,
        question: str,
        stream: bool = False
    ) -> str | AsyncGenerator[str, None]:
        """
        Анализ текстового вопроса

        Args:
            question: Вопрос пользователя
            stream: Использовать ли стриминг

        Returns:
            str | AsyncGenerator: Ответ или генератор для стриминга
        """
        start_time = time.time()

        try:
            if stream and settings.ENABLE_STREAMING:
                return self._stream_text_response(question)
            else:
                response = await self.async_client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": self.text_system_prompt},
                        {"role": "user", "content": question}
                    ],
                    max_tokens=settings.OPENAI_MAX_TOKENS,
                    temperature=settings.OPENAI_TEMPERATURE
                )

                answer = response.choices[0].message.content
                processing_time = time.time() - start_time

                logger.info(f"Text question processed in {processing_time:.2f}s")
                return answer

        except Exception as e:
            logger.error(f"Error analyzing text question: {e}")
            raise

    async def _stream_text_response(self, question: str) -> AsyncGenerator[str, None]:
        """
        Стриминг текстового ответа

        Args:
            question: Вопрос

        Yields:
            str: Части ответа
        """
        try:
            stream = await self.async_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self.text_system_prompt},
                    {"role": "user", "content": question}
                ],
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Error streaming text response: {e}")
            raise

    async def analyze_photo(
        self,
        photo_base64: str,
        caption: Optional[str] = None,
        stream: bool = False
    ) -> str | AsyncGenerator[str, None]:
        """
        Анализ фотографии

        Args:
            photo_base64: Фото в base64
            caption: Подпись к фото
            stream: Использовать ли стриминг

        Returns:
            str | AsyncGenerator: Ответ или генератор для стриминга
        """
        start_time = time.time()

        user_message = "Проанализируй это изображение строительного объекта. Определи дефекты, их критичность и дай рекомендации."
        if caption:
            user_message += f"\n\nКонтекст от пользователя: {caption}"

        try:
            if stream and settings.ENABLE_STREAMING:
                return self._stream_photo_response(photo_base64, user_message)
            else:
                response = await self.async_client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": self.photo_system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_message},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{photo_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=settings.OPENAI_MAX_TOKENS,
                    temperature=settings.OPENAI_TEMPERATURE
                )

                analysis = response.choices[0].message.content
                processing_time = time.time() - start_time

                logger.info(f"Photo analyzed in {processing_time:.2f}s")
                return analysis

        except Exception as e:
            logger.error(f"Error analyzing photo: {e}")
            raise

    async def _stream_photo_response(
        self,
        photo_base64: str,
        user_message: str
    ) -> AsyncGenerator[str, None]:
        """
        Стриминг ответа для фото

        Args:
            photo_base64: Фото в base64
            user_message: Сообщение пользователя

        Yields:
            str: Части ответа
        """
        try:
            stream = await self.async_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self.photo_system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_message},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{photo_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Error streaming photo response: {e}")
            raise

    async def transcribe_voice(self, audio_file_path: str) -> str:
        """
        Распознавание голосового сообщения через Whisper API

        Args:
            audio_file_path: Путь к аудио файлу

        Returns:
            str: Распознанный текст
        """
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = await self.async_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ru"
                )

            logger.info(f"Voice message transcribed: {len(transcript.text)} chars")
            return transcript.text

        except Exception as e:
            logger.error(f"Error transcribing voice: {e}")
            raise


# Singleton instance
_openai_service_instance: Optional[OpenAIService] = None


def get_openai_service() -> OpenAIService:
    """
    Получить экземпляр OpenAI service (singleton)

    Returns:
        OpenAIService: Экземпляр сервиса
    """
    global _openai_service_instance
    if _openai_service_instance is None:
        _openai_service_instance = OpenAIService()
    return _openai_service_instance
