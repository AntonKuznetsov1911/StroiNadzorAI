"""
OpenAI Realtime API - Голосовой ассистент в реальном времени

Альтернатива Gemini Live API с использованием OpenAI.
Позволяет создавать интерактивных голосовых ассистентов с низкой задержкой.

Особенности:
- Низкая задержка (< 500ms)
- Двусторонняя голосовая связь
- Возможность прерывать бота
- Потоковая передача аудио
- Модель: gpt-4o-realtime-preview
"""

import asyncio
import logging
import os
import json
import base64
from typing import Optional, Callable, Dict, Any, List
from io import BytesIO
import websockets
from datetime import datetime
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

logger = logging.getLogger(__name__)


class OpenAIRealtimeSession:
    """
    Сессия голосового общения с OpenAI Realtime API

    Использование:
        session = OpenAIRealtimeSession(api_key="...")
        await session.start()
        await session.send_audio(audio_bytes)
        await session.stop()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-realtime-preview-2024-12-17",
        voice: str = "alloy",  # alloy, echo, fable, onyx, nova, shimmer
        system_instruction: Optional[str] = None,
        on_text_received: Optional[Callable] = None,
        on_audio_received: Optional[Callable] = None,
        on_transcript_received: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ):
        """
        Инициализация Realtime сессии

        Args:
            api_key: OpenAI API ключ
            model: Модель (gpt-4o-realtime-preview)
            voice: Голос бота (alloy, echo, fable, onyx, nova, shimmer)
            system_instruction: Системная инструкция для бота
            on_text_received: Callback для текстовых ответов
            on_audio_received: Callback для аудио ответов
            on_transcript_received: Callback для транскрипции
            on_error: Callback для ошибок
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY не найден")

        self.model = model
        self.voice = voice
        self.system_instruction = system_instruction or self._get_default_system_instruction()

        # Callbacks
        self.on_text_received = on_text_received
        self.on_audio_received = on_audio_received
        self.on_transcript_received = on_transcript_received
        self.on_error = on_error

        # WebSocket соединение
        self.ws = None
        self.is_connected = False
        self.session_id = None

        # Буфер для аудио
        self.audio_buffer = BytesIO()
        self.current_response_id = None

        # Статистика
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "audio_chunks_sent": 0,
            "audio_chunks_received": 0,
            "errors": 0,
            "latency_ms": []
        }

        # Транскрипция разговора
        self.conversation_transcript = []
        self.current_user_text = ""
        self.current_bot_text = ""

        logger.info(f"🎤 OpenAI Realtime Session инициализирована (модель: {model}, голос: {voice})")

    def _get_default_system_instruction(self) -> str:
        """Системная инструкция по умолчанию для строительного эксперта"""
        return """Вы — голосовой ассистент-эксперт по строительству для России и ЕАЭС.

ОСОБЕННОСТИ ГОЛОСОВОГО ОБЩЕНИЯ:
- Отвечайте кратко и по делу (прораб на объекте, у него мало времени)
- Используйте профессиональную терминологию
- При вопросах по нормативам называйте номер СП/ГОСТ и ключевой пункт
- Если нужно детальное объяснение, предложите отправить текстовую версию
- При опасных ситуациях говорите чётко: "ВНИМАНИЕ! ОПАСНОСТЬ!"

БЕЗОПАСНОСТЬ ПРЕЖДЕ ВСЕГО:
- При вопросах о несущих конструкциях ВСЕГДА напоминайте о необходимости проектного расчёта
- Предупреждайте о рисках для жизни
- Рекомендуйте СИЗ и технику безопасности

НОРМАТИВНАЯ БАЗА:
- СП 63.13330.2018 (Бетон и железобетон)
- СП 22.13330.2016 (Основания зданий)
- СП 70.13330.2012 (Несущие и ограждающие конструкции)
- ГОСТ 34028-2016 (Арматура)
- СП 296.1325800.2017 (Охрана труда)

ФОРМАТ ОТВЕТА:
1. Краткий ответ (1-2 предложения)
2. Ссылка на норматив (если применимо)
3. Важное предупреждение (если есть риски)

Говорите ясно, чётко, как опытный инженер на объекте. Язык — русский."""

    async def start(self) -> bool:
        """
        Запуск Realtime сессии

        Returns:
            True если соединение установлено
        """
        try:
            # WebSocket URL для OpenAI Realtime API
            ws_url = f"wss://api.openai.com/v1/realtime?model={self.model}"

            logger.info(f"🔌 Подключение к OpenAI Realtime API...")

            # Устанавливаем WebSocket соединение с авторизацией
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "OpenAI-Beta": "realtime=v1"
            }

            self.ws = await websockets.connect(
                ws_url,
                extra_headers=headers,
                ping_interval=30,
                ping_timeout=10,
                max_size=10485760  # 10MB для аудио
            )

            self.is_connected = True
            self.session_id = f"realtime_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Ждём подтверждения сессии
            response = await self.ws.recv()
            data = json.loads(response)

            if data.get("type") == "session.created":
                logger.info(f"✅ Realtime сессия создана (ID: {data.get('session', {}).get('id')})")

                # Настраиваем сессию
                await self._configure_session()

                # Запускаем цикл получения сообщений
                asyncio.create_task(self._receive_loop())

                return True
            else:
                logger.error(f"❌ Неожиданный ответ: {data}")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка запуска Realtime сессии: {e}")
            self.is_connected = False
            if self.on_error:
                await self.on_error(str(e))
            return False

    async def _configure_session(self):
        """Настройка параметров сессии"""
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": self.system_instruction,
                "voice": self.voice,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                }
            }
        }

        await self.ws.send(json.dumps(config))
        logger.info("✅ Сессия настроена")

    async def send_audio(self, audio_bytes: bytes, user_text: Optional[str] = None) -> bool:
        """
        Отправка аудио в реальном времени

        Args:
            audio_bytes: Аудио данные (PCM16 24kHz mono)
            user_text: Текст для транскрипции

        Returns:
            True если отправлено успешно
        """
        if not self.is_connected or not self.ws:
            logger.warning("⚠️ Realtime сессия не активна")
            return False

        try:
            # Кодируем аудио в base64
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')

            # Добавляем аудио в буфер
            message = {
                "type": "input_audio_buffer.append",
                "audio": audio_b64
            }

            await self.ws.send(json.dumps(message))

            self.stats["messages_sent"] += 1
            self.stats["audio_chunks_sent"] += 1

            if user_text:
                self.current_user_text = user_text

            logger.debug(f"🎤 Отправлено аудио: {len(audio_bytes)} байт")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка отправки аудио: {e}")
            self.stats["errors"] += 1
            if self.on_error:
                await self.on_error(str(e))
            return False

    async def commit_audio(self) -> bool:
        """Завершить отправку аудио и получить ответ"""
        if not self.is_connected or not self.ws:
            return False

        try:
            # Коммитим буфер
            await self.ws.send(json.dumps({"type": "input_audio_buffer.commit"}))

            # Запрашиваем ответ
            await self.ws.send(json.dumps({"type": "response.create"}))

            logger.debug("✅ Аудио буфер отправлен, ожидаем ответ")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка коммита аудио: {e}")
            return False

    async def send_text(self, text: str) -> bool:
        """
        Отправка текстового сообщения

        Args:
            text: Текст сообщения

        Returns:
            True если отправлено успешно
        """
        if not self.is_connected or not self.ws:
            logger.warning("⚠️ Realtime сессия не активна")
            return False

        try:
            # Создаём conversation item с текстом
            message = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": text
                        }
                    ]
                }
            }

            await self.ws.send(json.dumps(message))

            # Запрашиваем ответ
            await self.ws.send(json.dumps({"type": "response.create"}))

            self.stats["messages_sent"] += 1
            self.current_user_text = text

            logger.debug(f"💬 Отправлен текст: {text[:50]}...")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка отправки текста: {e}")
            self.stats["errors"] += 1
            if self.on_error:
                await self.on_error(str(e))
            return False

    async def cancel_response(self) -> bool:
        """Прервать текущий ответ"""
        if not self.is_connected or not self.ws:
            return False

        try:
            await self.ws.send(json.dumps({"type": "response.cancel"}))
            logger.info("⏸️ Ответ прерван")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка прерывания: {e}")
            return False

    async def _receive_loop(self):
        """Цикл получения сообщений от сервера"""
        try:
            async for message in self.ws:
                await self._handle_message(message)

        except websockets.exceptions.ConnectionClosed:
            logger.info("🔌 WebSocket соединение закрыто")
            self.is_connected = False
        except Exception as e:
            logger.error(f"❌ Ошибка в receive_loop: {e}")
            self.is_connected = False
            if self.on_error:
                await self.on_error(str(e))

    async def _handle_message(self, message: str):
        """Обработка входящего сообщения"""
        try:
            data = json.loads(message)
            event_type = data.get("type", "")
            self.stats["messages_received"] += 1

            # Аудио дельта (часть ответа)
            if event_type == "response.audio.delta":
                audio_b64 = data.get("delta", "")
                if audio_b64:
                    audio_bytes = base64.b64decode(audio_b64)
                    self.audio_buffer.write(audio_bytes)
                    self.stats["audio_chunks_received"] += 1

            # Аудио завершено
            elif event_type == "response.audio.done":
                if self.audio_buffer.tell() > 0:
                    self.audio_buffer.seek(0)
                    audio_data = self.audio_buffer.read()

                    logger.info(f"🔊 Получено аудио: {len(audio_data)} байт")

                    if self.on_audio_received:
                        await self.on_audio_received(audio_data)

                    # Очищаем буфер
                    self.audio_buffer = BytesIO()

            # Текстовая дельта
            elif event_type == "response.audio_transcript.delta":
                text = data.get("delta", "")
                if text:
                    self.current_bot_text += text

            # Транскрипция завершена
            elif event_type == "response.audio_transcript.done":
                transcript = data.get("transcript", "")
                logger.info(f"💬 Транскрипция бота: {transcript[:100]}...")

                if self.on_text_received:
                    await self.on_text_received(transcript)

            # Транскрипция пользователя
            elif event_type == "conversation.item.input_audio_transcription.completed":
                user_transcript = data.get("transcript", "")
                if user_transcript:
                    self.current_user_text = user_transcript
                    logger.info(f"🎤 Распознано: {user_transcript[:100]}...")

                    if self.on_transcript_received:
                        await self.on_transcript_received(user_transcript)

            # Ответ завершён
            elif event_type == "response.done":
                logger.debug("✅ Ответ завершён")

                # Сохраняем в транскрипцию
                if self.current_user_text or self.current_bot_text:
                    self.conversation_transcript.append({
                        "user": self.current_user_text,
                        "bot": self.current_bot_text.strip(),
                        "timestamp": datetime.now().isoformat()
                    })

                    self.current_user_text = ""
                    self.current_bot_text = ""

            # Ошибка
            elif event_type == "error":
                error_msg = data.get("error", {}).get("message", "Unknown error")
                logger.error(f"❌ Ошибка от сервера: {error_msg}")
                self.stats["errors"] += 1

                if self.on_error:
                    await self.on_error(error_msg)

            # Rate limit
            elif event_type == "rate_limits.updated":
                logger.debug(f"📊 Rate limits: {data.get('rate_limits', [])}")

        except json.JSONDecodeError as e:
            logger.error(f"❌ Ошибка парсинга JSON: {e}")
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")

    async def stop(self):
        """Остановка Realtime сессии"""
        try:
            if self.ws:
                await self.ws.close()

            self.is_connected = False
            logger.info(f"🛑 Realtime сессия остановлена (ID: {self.session_id})")
            logger.info(f"📊 Статистика: {self.stats}")
            logger.info(f"📝 Транскрипция: {len(self.conversation_transcript)} обменов")

        except Exception as e:
            logger.error(f"❌ Ошибка остановки сессии: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику сессии"""
        return {
            **self.stats,
            "is_connected": self.is_connected,
            "session_id": self.session_id
        }

    def get_transcript(self) -> List[Dict[str, str]]:
        """Получить полную транскрипцию разговора"""
        return self.conversation_transcript

    def format_transcript(self) -> str:
        """Форматировать транскрипцию для отправки в чат"""
        if not self.conversation_transcript:
            return "📝 Транскрипция пуста"

        lines = ["📝 **ТРАНСКРИПЦИЯ ГОЛОСОВОГО РАЗГОВОРА**\n"]

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

        return "\n".join(lines)


# ============================================================================
# ИНТЕГРАЦИЯ С TELEGRAM БОТОМ
# ============================================================================

class TelegramRealtimeAssistant:
    """
    Голосовой ассистент для Telegram с OpenAI Realtime API

    Использование:
        assistant = TelegramRealtimeAssistant()
        await assistant.start_conversation(user_id)
        await assistant.process_voice(user_id, audio_bytes)
    """

    def __init__(self):
        self.active_sessions: Dict[int, OpenAIRealtimeSession] = {}
        logger.info("🎤 Telegram Realtime Assistant (OpenAI) инициализирован")

    async def start_conversation(
        self,
        user_id: int,
        on_audio_ready: Callable[[bytes], Any],
        on_text_ready: Optional[Callable[[str], Any]] = None
    ) -> bool:
        """
        Начать голосовой разговор с пользователем

        Args:
            user_id: ID пользователя Telegram
            on_audio_ready: Callback для отправки аудио ответа
            on_text_ready: Callback для отправки текста

        Returns:
            True если сессия запущена
        """
        # Если уже есть активная сессия, остановим её
        if user_id in self.active_sessions:
            await self.stop_conversation(user_id)

        try:
            # Создаём новую сессию
            session = OpenAIRealtimeSession(
                on_audio_received=on_audio_ready,
                on_text_received=on_text_ready
            )

            success = await session.start()

            if success:
                self.active_sessions[user_id] = session
                logger.info(f"✅ Realtime сессия запущена для пользователя {user_id}")
                return True
            else:
                logger.error(f"❌ Не удалось запустить сессию для {user_id}")
                return False

        except ValueError as e:
            logger.error(f"❌ Ошибка: {e}")
            return False

    async def process_voice(
        self,
        user_id: int,
        audio_bytes: bytes,
        commit: bool = True
    ) -> bool:
        """
        Обработка голосового сообщения

        Args:
            user_id: ID пользователя
            audio_bytes: Аудио данные
            commit: Отправить на обработку после добавления

        Returns:
            True если обработано успешно
        """
        session = self.active_sessions.get(user_id)

        if not session:
            logger.warning(f"⚠️ Нет активной сессии для {user_id}")
            return False

        success = await session.send_audio(audio_bytes)

        if success and commit:
            await session.commit_audio()

        return success

    async def process_text(self, user_id: int, text: str) -> bool:
        """Обработка текстового сообщения"""
        session = self.active_sessions.get(user_id)

        if not session:
            logger.warning(f"⚠️ Нет активной сессии для {user_id}")
            return False

        return await session.send_text(text)

    async def stop_conversation(self, user_id: int) -> bool:
        """Остановить разговор"""
        session = self.active_sessions.get(user_id)

        if session:
            await session.stop()
            del self.active_sessions[user_id]
            logger.info(f"🛑 Сессия остановлена для {user_id}")
            return True

        return False

    def get_session_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить статистику сессии"""
        session = self.active_sessions.get(user_id)
        return session.get_stats() if session else None

    def get_session_transcript(self, user_id: int) -> Optional[str]:
        """Получить транскрипцию"""
        session = self.active_sessions.get(user_id)
        return session.format_transcript() if session else None


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def is_openai_realtime_available() -> bool:
    """Проверка доступности OpenAI Realtime API"""
    return bool(os.getenv("OPENAI_API_KEY"))


async def test_openai_realtime():
    """Тестовый запуск OpenAI Realtime API"""
    if not is_openai_realtime_available():
        logger.error("❌ OPENAI_API_KEY не найден")
        return False

    try:
        session = OpenAIRealtimeSession()
        success = await session.start()

        if success:
            logger.info("✅ OpenAI Realtime API работает!")

            # Отправляем тестовое сообщение
            await session.send_text("Привет! Это тест Realtime API. Ответь одним предложением.")

            # Ждём ответа
            await asyncio.sleep(5)

            await session.stop()
            return True
        else:
            logger.error("❌ Не удалось запустить сессию")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка теста: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    async def main():
        result = await test_openai_realtime()
        print(f"\nOpenAI Realtime API: {'✅ Готов' if result else '❌ Недоступен'}")

    asyncio.run(main())
