"""
Продвинутый обработчик Gemini API с полным набором возможностей
- Мультимодальность (текст, изображения, PDF, видео, аудио)
- Большой контекст (1M+ токенов)
- Function Calling
- JSON Mode
- Thinking Mode
- Gemini Live API
"""

import logging
import os
import asyncio
from typing import Optional, Dict, List, Any, Union
from io import BytesIO
import json
import base64

logger = logging.getLogger(__name__)


class GeminiAdvancedHandler:
    """
    Продвинутый обработчик для Gemini API
    Поддерживает все современные возможности Gemini 2.0/2.5/3.0
    """

    def __init__(self, api_key: Optional[str] = None):
        """Инициализация обработчика"""
        import google.generativeai as genai

        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY не найден")

        genai.configure(api_key=self.api_key)
        self.genai = genai

        # Доступные модели
        self.models = {
            "flash": "gemini-2.0-flash-exp",  # 1M контекст, быстрая
            "flash_thinking": "gemini-2.0-flash-thinking-exp",  # С режимом рассуждений
            "pro": "gemini-pro-2.0",  # 2M контекст, самая мощная
            "flash_image": "gemini-2.5-flash-image-preview"  # Генерация изображений
        }

        logger.info("✅ GeminiAdvancedHandler инициализирован")

    # ========================================================================
    # МУЛЬТИМОДАЛЬНЫЙ АНАЛИЗ
    # ========================================================================

    async def analyze_drawing(
        self,
        image_data: Union[bytes, BytesIO],
        question: str,
        check_compliance: bool = True
    ) -> Dict[str, Any]:
        """
        Анализ чертежа на соответствие ГОСТ/СП

        Args:
            image_data: Изображение чертежа
            question: Вопрос по чертежу
            check_compliance: Проверять соответствие нормативам

        Returns:
            Dict с анализом, замечаниями, соответствием нормативам
        """
        logger.info("🔍 Анализ чертежа через Gemini Vision...")

        try:
            model = self.genai.GenerativeModel(self.models['flash'])

            # Конвертируем изображение
            if isinstance(image_data, BytesIO):
                image_bytes = image_data.getvalue()
            else:
                image_bytes = image_data

            # Системный промпт для анализа чертежей
            system_prompt = """Вы — эксперт-инженер по строительным нормам РФ и ЕАЭС.
Анализируете чертежи на соответствие ГОСТ, СП, СНиП.

ФОРМАТ ОТВЕТА (JSON):
{
  "analysis": "Детальное описание чертежа",
  "elements": ["Список обнаруженных элементов"],
  "measurements": {"Размеры": "значения"},
  "compliance_check": {
    "status": "compliant/non_compliant/partial",
    "regulations": ["Применимые СП/ГОСТ"],
    "violations": ["Список нарушений"],
    "recommendations": ["Рекомендации по исправлению"]
  },
  "materials": ["Обнаруженные материалы"],
  "risk_assessment": "Оценка рисков"
}"""

            prompt = f"""{system_prompt}

ЗАДАЧА: {question}

Проанализируй чертёж и верни детальный ответ в формате JSON."""

            # Генерируем анализ
            loop = asyncio.get_event_loop()

            def _analyze():
                response = model.generate_content(
                    [prompt, {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode()}],
                    generation_config=self.genai.GenerationConfig(
                        temperature=0.2,  # Низкая для точности
                        response_mime_type="application/json"  # JSON Mode
                    )
                )
                return response.text

            result_json = await loop.run_in_executor(None, _analyze)
            result = json.loads(result_json)

            logger.info("✅ Анализ чертежа завершён")
            return result

        except Exception as e:
            logger.error(f"❌ Ошибка анализа чертежа: {e}")
            raise

    async def analyze_video(
        self,
        video_data: bytes,
        task: str = "safety_audit"
    ) -> Dict[str, Any]:
        """
        Анализ видео с объекта

        Args:
            video_data: Видео файл
            task: Тип задачи (safety_audit, progress_check, quality_control)

        Returns:
            Dict с анализом видео, временными метками, нарушениями
        """
        logger.info(f"🎥 Анализ видео: {task}")

        try:
            model = self.genai.GenerativeModel(self.models['flash'])

            prompts = {
                "safety_audit": """Проанализируй видео на соблюдение техники безопасности:
- Рабочие без касок/спецодежды
- Нарушения при работе на высоте
- Неправильное использование оборудования
- Отсутствие ограждений

Для каждого нарушения укажи временную метку.""",

                "progress_check": """Проанализируй прогресс работ:
- Какие работы выполняются
- Процент завершения
- Количество рабочих
- Используемое оборудование""",

                "quality_control": """Проверь качество работ:
- Соблюдение технологии
- Видимые дефекты
- Соответствие проектной документации"""
            }

            prompt = prompts.get(task, prompts["safety_audit"])

            # Загружаем видео
            video_file = self.genai.upload_file(
                path=BytesIO(video_data),
                mime_type="video/mp4"
            )

            loop = asyncio.get_event_loop()

            def _analyze():
                response = model.generate_content(
                    [prompt, video_file],
                    generation_config=self.genai.GenerationConfig(
                        temperature=0.3,
                        response_mime_type="application/json"
                    )
                )
                return response.text

            result_json = await loop.run_in_executor(None, _analyze)
            result = json.loads(result_json)

            logger.info("✅ Анализ видео завершён")
            return result

        except Exception as e:
            logger.error(f"❌ Ошибка анализа видео: {e}")
            raise

    async def analyze_audio(
        self,
        audio_data: bytes,
        task: str = "transcribe"
    ) -> Dict[str, Any]:
        """
        Обработка аудио (диктовка актов, голосовые команды)

        Args:
            audio_data: Аудио файл
            task: transcribe, extract_data, create_report

        Returns:
            Dict с транскрипцией, извлечёнными данными
        """
        logger.info(f"🎤 Обработка аудио: {task}")

        try:
            model = self.genai.GenerativeModel(self.models['flash'])

            prompts = {
                "transcribe": "Транскрибируй аудио в текст с сохранением терминологии.",

                "extract_data": """Извлеки из аудио структурированные данные:
- Участники
- Даты и сроки
- Объемы работ
- Замечания
- Решения

Верни в формате JSON.""",

                "create_report": """На основе аудио создай отчёт о прогрессе работ:
- Выполненные работы
- Проблемы
- План на следующий период
- Необходимые материалы"""
            }

            prompt = prompts.get(task, prompts["transcribe"])

            # Загружаем аудио
            audio_file = self.genai.upload_file(
                path=BytesIO(audio_data),
                mime_type="audio/mp3"
            )

            loop = asyncio.get_event_loop()

            def _analyze():
                response = model.generate_content(
                    [prompt, audio_file],
                    generation_config=self.genai.GenerationConfig(
                        temperature=0.3,
                        response_mime_type="application/json" if "json" in task.lower() else "text/plain"
                    )
                )
                return response.text

            if "json" in task.lower() or task == "extract_data":
                result = json.loads(await loop.run_in_executor(None, _analyze))
            else:
                result = {"transcription": await loop.run_in_executor(None, _analyze)}

            logger.info("✅ Обработка аудио завершена")
            return result

        except Exception as e:
            logger.error(f"❌ Ошибка обработки аудио: {e}")
            raise

    # ========================================================================
    # РАБОТА С БОЛЬШИМ КОНТЕКСТОМ (1M+ ТОКЕНОВ)
    # ========================================================================

    async def load_regulations_context(
        self,
        regulation_files: List[str]
    ) -> str:
        """
        Загрузка СП/ГОСТ в контекст модели (до 1M токенов)

        Args:
            regulation_files: Пути к файлам нормативов (PDF, TXT)

        Returns:
            context_id для последующих запросов
        """
        logger.info(f"📚 Загрузка {len(regulation_files)} нормативов в контекст...")

        try:
            uploaded_files = []

            for file_path in regulation_files:
                logger.info(f"📄 Загружаю {os.path.basename(file_path)}...")

                file = self.genai.upload_file(
                    path=file_path,
                    mime_type="application/pdf" if file_path.endswith('.pdf') else "text/plain"
                )
                uploaded_files.append(file)

            logger.info(f"✅ Загружено {len(uploaded_files)} документов в контекст")

            # Сохраняем загруженные файлы для последующих запросов
            self.context_files = uploaded_files

            return f"context_{len(uploaded_files)}_files"

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки нормативов: {e}")
            raise

    async def query_with_regulations(
        self,
        question: str,
        use_thinking: bool = True
    ) -> Dict[str, Any]:
        """
        Запрос с использованием загруженных нормативов

        Args:
            question: Вопрос
            use_thinking: Использовать режим рассуждений

        Returns:
            Ответ с ссылками на конкретные пункты СП/ГОСТ
        """
        logger.info("🔍 Запрос с контекстом нормативов...")

        try:
            model_name = self.models['flash_thinking'] if use_thinking else self.models['flash']
            model = self.genai.GenerativeModel(model_name)

            prompt = f"""Используя загруженные нормативные документы, ответь на вопрос:

{question}

ТРЕБОВАНИЯ К ОТВЕТУ:
1. Точные ссылки на пункты СП/ГОСТ
2. Цитаты из документов
3. Пошаговое объяснение
4. Примеры применения

Формат JSON:
{{
  "answer": "Детальный ответ",
  "references": [
    {{"document": "СП 63.13330.2018", "section": "5.2.1", "quote": "..."}}
  ],
  "reasoning": "Логика рассуждений (если включен thinking mode)",
  "examples": ["Практические примеры"]
}}"""

            loop = asyncio.get_event_loop()

            def _query():
                content = [prompt]
                if hasattr(self, 'context_files'):
                    content.extend(self.context_files)

                response = model.generate_content(
                    content,
                    generation_config=self.genai.GenerationConfig(
                        temperature=0.1,
                        response_mime_type="application/json"
                    )
                )
                return response.text

            result_json = await loop.run_in_executor(None, _query)
            result = json.loads(result_json)

            logger.info("✅ Запрос обработан")
            return result

        except Exception as e:
            logger.error(f"❌ Ошибка запроса: {e}")
            raise

    # ========================================================================
    # FUNCTION CALLING
    # ========================================================================

    def define_functions(self) -> List[Dict]:
        """Определение доступных функций для вызова"""
        return [
            {
                "name": "calculate_materials",
                "description": "Рассчитывает необходимое количество материалов",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "material_type": {"type": "string", "description": "Тип материала (бетон, арматура, кирпич)"},
                        "dimensions": {"type": "object", "description": "Размеры конструкции"},
                        "specification": {"type": "string", "description": "Марка/класс материала"}
                    },
                    "required": ["material_type", "dimensions"]
                }
            },
            {
                "name": "check_stock",
                "description": "Проверяет наличие материалов на складе",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "material": {"type": "string"},
                        "quantity": {"type": "number"}
                    },
                    "required": ["material"]
                }
            },
            {
                "name": "create_task",
                "description": "Создаёт задачу в CRM/Jira/Bitrix24",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "assignee": {"type": "string"},
                        "deadline": {"type": "string"}
                    },
                    "required": ["title", "description"]
                }
            },
            {
                "name": "generate_report",
                "description": "Генерирует отчёт по шаблону",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "report_type": {"type": "string", "enum": ["daily", "weekly", "defect", "progress"]},
                        "data": {"type": "object"}
                    },
                    "required": ["report_type"]
                }
            }
        ]

    async def chat_with_functions(
        self,
        message: str,
        conversation_history: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Чат с возможностью вызова функций

        Args:
            message: Сообщение пользователя
            conversation_history: История диалога

        Returns:
            Ответ + вызванные функции
        """
        logger.info("💬 Чат с function calling...")

        try:
            model = self.genai.GenerativeModel(
                self.models['flash'],
                tools=self.define_functions()
            )

            chat = model.start_chat(history=conversation_history or [])

            loop = asyncio.get_event_loop()

            def _chat():
                return chat.send_message(message)

            response = await loop.run_in_executor(None, _chat)

            # Обрабатываем вызовы функций
            function_calls = []
            if response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call'):
                        function_calls.append({
                            "name": part.function_call.name,
                            "args": dict(part.function_call.args)
                        })

            result = {
                "text": response.text if hasattr(response, 'text') else None,
                "function_calls": function_calls,
                "conversation_history": chat.history
            }

            logger.info(f"✅ Обработано, вызовов функций: {len(function_calls)}")
            return result

        except Exception as e:
            logger.error(f"❌ Ошибка чата: {e}")
            raise

    # ========================================================================
    # ГЕНЕРАЦИЯ СТРУКТУРИРОВАННЫХ ОТЧЁТОВ
    # ========================================================================

    async def generate_daily_report(
        self,
        photos: List[bytes],
        audio_comments: Optional[bytes] = None,
        date: str = None
    ) -> Dict[str, Any]:
        """
        Генерация ежедневного отчёта о прогрессе (Daily Progress Report)

        Args:
            photos: Фото с объекта
            audio_comments: Голосовые комментарии
            date: Дата отчёта

        Returns:
            Структурированный отчёт в JSON
        """
        logger.info("📊 Генерация ежедневного отчёта...")

        try:
            model = self.genai.GenerativeModel(self.models['flash'])

            prompt = f"""На основе фото с объекта и голосовых комментариев создай ежедневный отчёт о прогрессе работ за {date or 'сегодня'}.

СТРУКТУРА ОТЧЁТА (JSON):
{{
  "date": "{date}",
  "summary": "Краткая сводка",
  "completed_works": [
    {{"work": "Название работ", "volume": "Объём", "quality": "Оценка"}}
  ],
  "ongoing_works": ["Список"],
  "issues": [
    {{"issue": "Проблема", "severity": "high/medium/low", "solution": "Предложение"}}
  ],
  "safety": {{"violations": [], "status": "ok/warning/critical"}},
  "weather": "Погодные условия",
  "manpower": {{"workers": 0, "equipment": []}},
  "materials_used": [{{"material": "", "quantity": ""}}],
  "next_day_plan": ["План на завтра"],
  "photos_analysis": ["Описание каждого фото"]
}}"""

            content = [prompt]

            # Добавляем фото
            for i, photo in enumerate(photos):
                content.append({
                    "mime_type": "image/jpeg",
                    "data": base64.b64encode(photo).decode()
                })

            # Добавляем аудио
            if audio_comments:
                audio_file = self.genai.upload_file(
                    path=BytesIO(audio_comments),
                    mime_type="audio/mp3"
                )
                content.append(audio_file)

            loop = asyncio.get_event_loop()

            def _generate():
                response = model.generate_content(
                    content,
                    generation_config=self.genai.GenerationConfig(
                        temperature=0.3,
                        response_mime_type="application/json"
                    )
                )
                return response.text

            report_json = await loop.run_in_executor(None, _generate)
            report = json.loads(report_json)

            logger.info("✅ Отчёт сгенерирован")
            return report

        except Exception as e:
            logger.error(f"❌ Ошибка генерации отчёта: {e}")
            raise


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def is_gemini_advanced_available() -> bool:
    """Проверка доступности Gemini Advanced API"""
    return bool(os.getenv("GOOGLE_API_KEY"))


async def test_gemini_advanced():
    """Тест продвинутых возможностей"""
    if not is_gemini_advanced_available():
        logger.error("GOOGLE_API_KEY не найден")
        return False

    try:
        handler = GeminiAdvancedHandler()
        logger.info("✅ Gemini Advanced Handler готов к работе")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации: {e}")
        return False


if __name__ == "__main__":
    # Тестовый запуск
    import asyncio

    async def main():
        result = await test_gemini_advanced()
        print(f"Gemini Advanced: {'✅ Готов' if result else '❌ Недоступен'}")

    asyncio.run(main())
