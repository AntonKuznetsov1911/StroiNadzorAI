"""
Gemini Live API v2 - Официальный SDK от Google
Обновленная реализация с:
- google.genai.Client()
- Gemini 2.5 Flash Native Audio (декабрь 2025)
- Function Calling для калькуляторов
- Улучшенная транскрипция
"""

import asyncio
import logging
import os
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv

# Официальный SDK Google
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logging.warning("google-genai не установлен. Установите: pip install google-generativeai>=0.9.0")

load_dotenv()
logger = logging.getLogger(__name__)


# ============================================================================
# FUNCTION DECLARATIONS - Калькуляторы для строительства
# ============================================================================

CONSTRUCTION_FUNCTIONS = [
    {
        "name": "calculate_concrete_volume",
        "description": "Рассчитать объём бетона для плиты, ленточного или столбчатого фундамента",
        "parameters": {
            "type": "object",
            "properties": {
                "element_type": {
                    "type": "string",
                    "enum": ["slab", "strip_foundation", "column"],
                    "description": "Тип элемента: slab (плита), strip_foundation (лента), column (столб)"
                },
                "length": {
                    "type": "number",
                    "description": "Длина в метрах"
                },
                "width": {
                    "type": "number",
                    "description": "Ширина в метрах"
                },
                "thickness": {
                    "type": "number",
                    "description": "Толщина/высота в метрах"
                }
            },
            "required": ["element_type", "length", "width", "thickness"]
        }
    },
    {
        "name": "calculate_rebar_quantity",
        "description": "Рассчитать количество арматуры для армирования",
        "parameters": {
            "type": "object",
            "properties": {
                "length": {
                    "type": "number",
                    "description": "Длина элемента в метрах"
                },
                "width": {
                    "type": "number",
                    "description": "Ширина элемента в метрах"
                },
                "spacing": {
                    "type": "number",
                    "description": "Шаг арматуры в метрах (обычно 0.15-0.20)"
                },
                "diameter": {
                    "type": "integer",
                    "description": "Диаметр арматуры в мм (например 12, 16, 20)"
                }
            },
            "required": ["length", "width", "spacing", "diameter"]
        }
    },
    {
        "name": "search_regulation",
        "description": "Найти информацию в строительных нормативах (СП, ГОСТ, СНиП)",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Поисковый запрос (например 'защитный слой арматуры', 'класс бетона B25')"
                }
            },
            "required": ["query"]
        }
    }
]


# ============================================================================
# РЕАЛИЗАЦИЯ ФУНКЦИЙ
# ============================================================================

def calculate_concrete_volume(element_type: str, length: float, width: float, thickness: float) -> dict:
    """Расчёт объёма бетона"""
    volume = length * width * thickness

    # Добавляем запас 5%
    volume_with_margin = volume * 1.05

    return {
        "volume_m3": round(volume, 2),
        "volume_with_margin_m3": round(volume_with_margin, 2),
        "element_type": element_type,
        "dimensions": f"{length}x{width}x{thickness} м",
        "recommendation": f"Рекомендуется заказать {round(volume_with_margin, 1)} м³ бетона (с запасом 5%)"
    }


def calculate_rebar_quantity(length: float, width: float, spacing: float, diameter: int) -> dict:
    """Расчёт количества арматуры"""
    # Количество стержней по длине и ширине
    rods_length = int(width / spacing) + 1
    rods_width = int(length / spacing) + 1

    # Общая длина арматуры
    total_length_m = (rods_length * length) + (rods_width * width)

    # Вес (примерный)
    weight_per_meter = {
        8: 0.395, 10: 0.617, 12: 0.888, 14: 1.21,
        16: 1.58, 18: 2.0, 20: 2.47, 22: 2.98, 25: 3.85
    }
    weight_kg = total_length_m * weight_per_meter.get(diameter, 1.58)

    return {
        "total_length_m": round(total_length_m, 1),
        "weight_kg": round(weight_kg, 1),
        "diameter_mm": diameter,
        "spacing_m": spacing,
        "rods_count": rods_length + rods_width,
        "recommendation": f"Потребуется ~{round(total_length_m, 0)} м арматуры ∅{diameter}мм (≈{round(weight_kg, 0)} кг)"
    }


def search_regulation(query: str) -> dict:
    """Поиск по нормативам (упрощенная версия)"""
    # В реальности здесь был бы поиск по базе нормативов
    return {
        "query": query,
        "found": True,
        "message": f"Поиск по нормативам: '{query}'. Используйте /regulations для полного списка."
    }


# Мапинг функций
FUNCTION_HANDLERS = {
    "calculate_concrete_volume": calculate_concrete_volume,
    "calculate_rebar_quantity": calculate_rebar_quantity,
    "search_regulation": search_regulation
}


# ============================================================================
# GEMINI LIVE SESSION V2 - Официальный SDK
# ============================================================================

class GeminiLiveSessionV2:
    """
    Голосовая сессия с Gemini Live API v2 (официальный SDK)

    Новые возможности:
    - Официальный google.genai.Client()
    - Gemini 2.5 Flash Native Audio (декабрь 2025)
    - Function Calling для калькуляторов
    - Автоматическая транскрипция
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash-native-audio-preview-12-2025",
        voice: str = "Aoede",
        system_instruction: Optional[str] = None,
        on_audio_received: Optional[Callable] = None,
        enable_function_calling: bool = True
    ):
        """
        Инициализация Live сессии v2

        Args:
            api_key: Google API ключ
            model: Модель Gemini (2.5 flash native audio)
            voice: Голос бота
            system_instruction: Системная инструкция
            on_audio_received: Callback для аудио ответов
            enable_function_calling: Включить вызов функций
        """
        if not GENAI_AVAILABLE:
            raise ImportError("google-genai не установлен")

        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY не найден")

        self.model = model
        self.voice = voice
        self.system_instruction = system_instruction or self._get_default_system_instruction()
        self.on_audio_received = on_audio_received
        self.enable_function_calling = enable_function_calling

        # Клиент Google GenAI
        self.client = genai.Client(api_key=self.api_key)
        self.session = None
        self.is_connected = False
        self.session_id = None

        # Транскрипция разговора
        self.conversation_transcript = []
        self.current_user_text = ""
        self.current_bot_text = ""

        # Статистика
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "audio_chunks_sent": 0,
            "audio_chunks_received": 0,
            "functions_called": 0,
            "errors": 0
        }

        logger.info(f"🎤 Gemini Live Session V2 инициализирована (модель: {model}, SDK: официальный)")

    def _get_default_system_instruction(self) -> str:
        """Системная инструкция для строительного эксперта"""
        return """Вы — голосовой ассистент-эксперт по строительству для России и ЕАЭС.

ОСОБЕННОСТИ ГОЛОСОВОГО ОБЩЕНИЯ:
- Отвечайте кратко и по делу (прораб на объекте, у него мало времени)
- Используйте профессиональную терминологию
- При вопросах по нормативам называйте номер СП/ГОСТ и ключевой пункт
- При опасных ситуациях говорите чётко: "ВНИМАНИЕ! ОПАСНОСТЬ!"

ДОСТУПНЫЕ ИНСТРУМЕНТЫ:
- calculate_concrete_volume - расчёт бетона для плит, лент, столбов
- calculate_rebar_quantity - расчёт арматуры
- search_regulation - поиск по нормативам СП/ГОСТ/СНиП

ИСПОЛЬЗУЙТЕ ФУНКЦИИ когда пользователь просит:
- "сколько бетона" → вызывайте calculate_concrete_volume
- "сколько арматуры" → вызывайте calculate_rebar_quantity
- "найди в нормативах" → вызывайте search_regulation

НОРМАТИВНАЯ БАЗА:
- СП 63.13330.2018 (Бетон и железобетон)
- СП 22.13330.2016 (Основания зданий)
- СП 296.1325800.2017 (Охрана труда)
- ГОСТ 34028-2016 (Арматура)

ФОРМАТ ОТВЕТА:
1. Краткий ответ (1-2 предложения)
2. Ссылка на норматив (если применимо)
3. Важное предупреждение (если есть риски)

Говорите ясно, чётко, как опытный инженер на объекте."""

    async def start(self) -> bool:
        """Запуск Live сессии через официальный SDK"""
        try:
            self.session_id = f"live_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Конфигурация сессии
            config = {
                "response_modalities": ["AUDIO"],
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_config": {
                            "voice_name": self.voice
                        }
                    }
                },
                "system_instruction": {"parts": [{"text": self.system_instruction}]}
            }

            # Добавляем функции если включено
            if self.enable_function_calling:
                tools = [types.Tool(function_declarations=CONSTRUCTION_FUNCTIONS)]
                config["tools"] = tools
                logger.info("✅ Function Calling включен (3 функции)")

            logger.info(f"🔌 Подключение к Gemini Live API v2 (SDK)...")

            # Подключаемся через официальный SDK
            self.session = await self.client.aio.live.connect(
                model=self.model,
                config=config
            )

            self.is_connected = True
            logger.info(f"✅ Live сессия V2 запущена (ID: {self.session_id})")

            # Запускаем цикл получения сообщений
            asyncio.create_task(self._receive_loop())

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка запуска Live сессии V2: {e}")
            self.is_connected = False
            return False

    async def send_audio(self, audio_bytes: bytes, user_message: str = None) -> bool:
        """Отправка аудио через официальный SDK"""
        if not self.is_connected or not self.session:
            logger.warning("⚠️ Live сессия не активна")
            return False

        try:
            # Отправляем через официальный SDK
            await self.session.send(audio_bytes, mime_type="audio/pcm")

            self.stats["messages_sent"] += 1
            self.stats["audio_chunks_sent"] += 1

            # Сохраняем текст для транскрипции
            if user_message:
                self.current_user_text = user_message

            logger.debug(f"🎤 Отправлено аудио: {len(audio_bytes)} байт")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка отправки аудио: {e}")
            self.stats["errors"] += 1
            return False

    async def send_text(self, text: str) -> bool:
        """Отправка текста через официальный SDK"""
        if not self.is_connected or not self.session:
            logger.warning("⚠️ Live сессия не активна")
            return False

        try:
            # Отправляем текст
            await self.session.send(text)

            self.stats["messages_sent"] += 1
            self.current_user_text = text

            logger.debug(f"💬 Отправлен текст: {text[:50]}...")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка отправки текста: {e}")
            self.stats["errors"] += 1
            return False

    async def _receive_loop(self):
        """Цикл получения сообщений от Gemini"""
        try:
            async for response in self.session.receive():
                await self._handle_response(response)

        except Exception as e:
            logger.error(f"❌ Ошибка в receive_loop: {e}")
            self.is_connected = False

    async def _handle_response(self, response):
        """Обработка ответа от Gemini"""
        try:
            self.stats["messages_received"] += 1

            # Обработка аудио
            if hasattr(response, 'data') and response.data:
                audio_bytes = response.data
                self.stats["audio_chunks_received"] += 1
                logger.info(f"🔊 Получено аудио: {len(audio_bytes)} байт")

                if self.on_audio_received:
                    await self.on_audio_received(audio_bytes)

            # Обработка текста (для транскрипции)
            if hasattr(response, 'text') and response.text:
                text = response.text
                self.current_bot_text += text
                logger.info(f"💬 Получен текст: {text[:100]}...")

            # Обработка вызова функций
            if hasattr(response, 'function_calls') and response.function_calls:
                for func_call in response.function_calls:
                    await self._handle_function_call(func_call)

            # Сохраняем в транскрипцию при завершении оборота
            if hasattr(response, 'server_content') and response.server_content:
                if hasattr(response.server_content, 'turn_complete') and response.server_content.turn_complete:
                    self._save_to_transcript()

        except Exception as e:
            logger.error(f"❌ Ошибка обработки ответа: {e}")
            self.stats["errors"] += 1

    async def _handle_function_call(self, func_call):
        """Обработка вызова функции"""
        try:
            func_name = func_call.name
            func_args = func_call.args

            logger.info(f"🔧 Вызов функции: {func_name}({func_args})")
            self.stats["functions_called"] += 1

            # Вызываем функцию
            if func_name in FUNCTION_HANDLERS:
                result = FUNCTION_HANDLERS[func_name](**func_args)
                logger.info(f"✅ Результат функции: {result}")

                # Отправляем результат обратно через SDK
                if self.session:
                    try:
                        import json as json_mod
                        function_response = types.LiveClientToolResponse(
                            function_responses=[types.FunctionResponse(
                                name=func_name,
                                response={"result": json_mod.dumps(result, ensure_ascii=False, default=str)}
                            )]
                        )
                        await self.session.send(input=function_response)
                        logger.info(f"✅ Результат функции отправлен в Gemini")
                    except Exception as send_err:
                        logger.error(f"Ошибка отправки результата функции: {send_err}")

                # Добавляем в транскрипцию
                self.current_bot_text += f"\n[Вызвана функция {func_name}: {result.get('recommendation', str(result))}]"

        except Exception as e:
            logger.error(f"❌ Ошибка вызова функции {func_call.name}: {e}")

    def _save_to_transcript(self):
        """Сохранить оборот в транскрипцию"""
        if self.current_user_text or self.current_bot_text:
            self.conversation_transcript.append({
                "user": self.current_user_text,
                "bot": self.current_bot_text.strip(),
                "timestamp": datetime.now().isoformat()
            })
            logger.info(f"📝 Добавлено в транскрипт")

            # Очищаем для следующего оборота
            self.current_user_text = ""
            self.current_bot_text = ""

    async def stop(self):
        """Остановка сессии"""
        try:
            if self.session:
                await self.session.close()

            self.is_connected = False
            logger.info(f"🛑 Live сессия V2 остановлена (ID: {self.session_id})")
            logger.info(f"📊 Статистика: {self.stats}")
            logger.info(f"📝 Транскрипция: {len(self.conversation_transcript)} обменов")

        except Exception as e:
            logger.error(f"❌ Ошибка остановки сессии: {e}")

    def get_transcript(self) -> List[Dict[str, str]]:
        """Получить транскрипцию"""
        return self.conversation_transcript

    def format_transcript(self) -> str:
        """Форматировать транскрипцию для отправки в чат"""
        if not self.conversation_transcript:
            return "📝 Транскрипция пуста"

        lines = ["📝 **ТРАНСКРИПЦИЯ ГОЛОСОВОГО РАЗГОВОРА** (SDK v2)\n"]

        for i, turn in enumerate(self.conversation_transcript, 1):
            user_text = turn.get("user", "").strip()
            bot_text = turn.get("bot", "").strip()

            if user_text:
                lines.append(f"**👤 Вы #{i}:**")
                lines.append(f"{user_text}\n")

            if bot_text:
                lines.append(f"**🤖 Бот #{i}:**")
                lines.append(f"{bot_text}\n")

        lines.append(f"\n_✨ Всего обменов: {len(self.conversation_transcript)}_")
        lines.append(f"_🔧 Функций вызвано: {self.stats['functions_called']}_")

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику"""
        return {
            **self.stats,
            "is_connected": self.is_connected,
            "session_id": self.session_id,
            "sdk_version": "v2 (официальный)"
        }


# ============================================================================
# ПРОВЕРКА ДОСТУПНОСТИ
# ============================================================================

def is_gemini_live_v2_available() -> bool:
    """Проверка доступности Gemini Live API v2"""
    if not GENAI_AVAILABLE:
        return False
    return bool(os.getenv("GOOGLE_API_KEY"))


async def test_gemini_live_v2():
    """Тестовый запуск Gemini Live API v2"""
    if not is_gemini_live_v2_available():
        logger.error("❌ GOOGLE_API_KEY не найден или SDK не установлен")
        return False

    try:
        # Создаём тестовую сессию
        session = GeminiLiveSessionV2()

        # Запускаем
        success = await session.start()

        if success:
            logger.info("✅ Gemini Live API v2 работает!")

            # Отправляем тестовое сообщение
            await session.send_text("Привет! Это тест Live API v2 с Function Calling.")

            # Ждём 3 секунды
            await asyncio.sleep(3)

            # Останавливаем
            await session.stop()

            return True
        else:
            logger.error("❌ Не удалось запустить Live сессию v2")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка теста: {e}")
        return False


if __name__ == "__main__":
    # Тестовый запуск
    logging.basicConfig(level=logging.INFO)

    async def main():
        result = await test_gemini_live_v2()
        print(f"\nGemini Live API v2: {'✅ Готов' if result else '❌ Недоступен'}")

    asyncio.run(main())
