"""
Gemini Live API - Голосовой ассистент в реальном времени

Позволяет создавать интерактивных голосовых ассистентов с низкой задержкой.
Прораб может общаться с ботом голосом, находясь в каске и перчатках.

Особенности:
- Низкая задержка (< 500ms)
- Двусторонняя голосовая связь
- Возможность прерывать бота
- Потоковая передача аудио
- Мультимодальность (можно отправлять фото во время разговора)
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

logger = logging.getLogger(__name__)


class GeminiLiveSession:
    """
    Сессия голосового общения с Gemini Live API

    Использование:
        session = GeminiLiveSession(api_key="...")
        await session.start()
        await session.send_audio(audio_bytes)
        await session.stop()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash-exp",
        voice: str = "Aoede",  # Голос бота (Aoede, Charon, Fenrir, Kore, Puck)
        system_instruction: Optional[str] = None,
        on_text_received: Optional[Callable] = None,
        on_audio_received: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ):
        """
        Инициализация Live сессии

        Args:
            api_key: Google API ключ
            model: Модель Gemini (только 2.0-flash-exp поддерживает Live)
            voice: Голос бота
            system_instruction: Системная инструкция для бота
            on_text_received: Callback для текстовых ответов
            on_audio_received: Callback для аудио ответов
            on_error: Callback для ошибок
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY не найден")

        self.model = model
        self.voice = voice
        self.system_instruction = system_instruction or self._get_default_system_instruction()

        # Callbacks
        self.on_text_received = on_text_received
        self.on_audio_received = on_audio_received
        self.on_error = on_error

        # WebSocket соединение
        self.ws = None
        self.is_connected = False
        self.session_id = None

        # Статистика
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "audio_chunks_sent": 0,
            "audio_chunks_received": 0,
            "errors": 0,
            "latency_ms": []
        }

        logger.info(f"🎤 Gemini Live Session инициализирована (модель: {model}, голос: {voice})")

    def _get_default_system_instruction(self) -> str:
        """Системная инструкция по умолчанию для строительного эксперта"""
        return """Вы — голосовой ассистент-эксперт по строительству для России и ЕАЭС.

ОСОБЕННОСТИ ГОЛОСОВОГО ОБЩЕНИЯ:
- Отвечайте кратко и по делу (прораб на объекте, у него мало времени)
- Используйте профессиональную терминологию
- При вопросах по нормативам называйте номер СП/ГОСТ и ключевой пункт
- Если нужно детальное объяснение, предложите отправить текстовую версию
- При опасных ситуациях говорите чётко и громко: "ВНИМАНИЕ! ОПАСНОСТЬ!"

БЕЗОПАСНОСТЬ ПРЕЖДЕ ВСЕГО:
- При вопросах о несущих конструкциях ВСЕГДА напоминайте о необходимости проектного расчёта
- Предупреждайте о рисках для жизни
- Рекомендуйте СИЗ и технику безопасности

НОРМАТИВНАЯ БАЗА:
- СП 63.13330.2018 (Бетон и железобетон)
- СП 22.13330.2016 (Основания зданий)
- СП 43.13330.2012 (Сооружения промышленных предприятий)
- ГОСТ 34028-2016 (Арматура)
- СП 296.1325800.2017 (Охрана труда)

ФОРМАТ ОТВЕТА:
1. Краткий ответ (1-2 предложения)
2. Ссылка на норматив (если применимо)
3. Важное предупреждение (если есть риски)

Говорите ясно, чётко, как опытный инженер на объекте."""

    async def start(self) -> bool:
        """
        Запуск Live сессии

        Returns:
            True если соединение установлено
        """
        try:
            # WebSocket URL для Gemini Live API
            ws_url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={self.api_key}"

            logger.info(f"🔌 Подключение к Gemini Live API...")

            # Устанавливаем WebSocket соединение
            self.ws = await websockets.connect(
                ws_url,
                ping_interval=30,
                ping_timeout=10,
                max_size=10485760  # 10MB для аудио стриминга
            )

            self.is_connected = True
            self.session_id = f"live_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Отправляем конфигурацию сессии
            setup_message = {
                "setup": {
                    "model": f"models/{self.model}",
                    "generation_config": {
                        "response_modalities": ["AUDIO"],  # Голосовые ответы
                        "speech_config": {
                            "voice_config": {
                                "prebuilt_voice_config": {
                                    "voice_name": self.voice
                                }
                            }
                        }
                    },
                    "system_instruction": {
                        "parts": [{"text": self.system_instruction}]
                    }
                }
            }

            await self.ws.send(json.dumps(setup_message))
            logger.info(f"✅ Live сессия запущена (ID: {self.session_id})")

            # Запускаем цикл получения сообщений
            asyncio.create_task(self._receive_loop())

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка запуска Live сессии: {e}")
            self.is_connected = False
            if self.on_error:
                await self.on_error(str(e))
            return False

    async def send_audio(self, audio_bytes: bytes, mime_type: str = "audio/pcm") -> bool:
        """
        Отправка аудио в реальном времени

        Args:
            audio_bytes: Аудио данные (PCM 16kHz mono рекомендуется)
            mime_type: MIME тип аудио

        Returns:
            True если отправлено успешно
        """
        if not self.is_connected or not self.ws:
            logger.warning("⚠️ Live сессия не активна")
            return False

        try:
            # Кодируем аудио в base64
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')

            message = {
                "realtime_input": {
                    "media_chunks": [
                        {
                            "data": audio_b64,
                            "mime_type": mime_type
                        }
                    ]
                }
            }

            await self.ws.send(json.dumps(message))

            self.stats["messages_sent"] += 1
            self.stats["audio_chunks_sent"] += 1

            logger.debug(f"🎤 Отправлено аудио: {len(audio_bytes)} байт")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка отправки аудио: {e}")
            self.stats["errors"] += 1
            if self.on_error:
                await self.on_error(str(e))
            return False

    async def send_text(self, text: str) -> bool:
        """
        Отправка текстового сообщения в Live режиме

        Args:
            text: Текст сообщения

        Returns:
            True если отправлено успешно
        """
        if not self.is_connected or not self.ws:
            logger.warning("⚠️ Live сессия не активна")
            return False

        try:
            message = {
                "client_content": {
                    "turns": [
                        {
                            "role": "user",
                            "parts": [{"text": text}]
                        }
                    ],
                    "turn_complete": True
                }
            }

            await self.ws.send(json.dumps(message))

            self.stats["messages_sent"] += 1
            logger.debug(f"💬 Отправлен текст: {text[:50]}...")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка отправки текста: {e}")
            self.stats["errors"] += 1
            if self.on_error:
                await self.on_error(str(e))
            return False

    async def send_image(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> bool:
        """
        Отправка фото во время разговора (мультимодальность)

        Args:
            image_bytes: Изображение
            mime_type: MIME тип изображения

        Returns:
            True если отправлено успешно
        """
        if not self.is_connected or not self.ws:
            logger.warning("⚠️ Live сессия не активна")
            return False

        try:
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')

            message = {
                "client_content": {
                    "turns": [
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "inline_data": {
                                        "mime_type": mime_type,
                                        "data": image_b64
                                    }
                                }
                            ]
                        }
                    ],
                    "turn_complete": True
                }
            }

            await self.ws.send(json.dumps(message))

            self.stats["messages_sent"] += 1
            logger.debug(f"📸 Отправлено фото: {len(image_bytes)} байт")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка отправки фото: {e}")
            self.stats["errors"] += 1
            if self.on_error:
                await self.on_error(str(e))
            return False

    async def interrupt(self) -> bool:
        """
        Прервать текущий ответ бота

        Returns:
            True если команда отправлена
        """
        if not self.is_connected or not self.ws:
            return False

        try:
            message = {"tool_response": {"function_responses": []}}
            await self.ws.send(json.dumps(message))

            logger.info("⏸️ Отправлена команда прерывания")
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
            self.stats["messages_received"] += 1

            # Обработка setup подтверждения
            if "setupComplete" in data:
                logger.info("✅ Setup подтверждён сервером")
                return

            # Обработка серверного контента
            if "serverContent" in data:
                server_content = data["serverContent"]

                # Текстовый ответ
                if "modelTurn" in server_content:
                    parts = server_content["modelTurn"].get("parts", [])
                    for part in parts:
                        if "text" in part:
                            text = part["text"]
                            logger.info(f"💬 Получен текст: {text[:100]}...")
                            if self.on_text_received:
                                await self.on_text_received(text)

                        # Аудио ответ
                        if "inlineData" in part:
                            audio_data = part["inlineData"]["data"]
                            audio_bytes = base64.b64decode(audio_data)

                            self.stats["audio_chunks_received"] += 1
                            logger.info(f"🔊 Получено аудио: {len(audio_bytes)} байт")

                            if self.on_audio_received:
                                await self.on_audio_received(audio_bytes)

                # Обновление latency
                if "turnComplete" in server_content:
                    logger.debug("✅ Turn complete")

            # Обработка ошибок
            if "error" in data:
                error_msg = data["error"].get("message", "Unknown error")
                logger.error(f"❌ Ошибка от сервера: {error_msg}")
                self.stats["errors"] += 1
                if self.on_error:
                    await self.on_error(error_msg)

        except json.JSONDecodeError as e:
            logger.error(f"❌ Ошибка парсинга JSON: {e}")
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")

    async def stop(self):
        """Остановка Live сессии"""
        try:
            if self.ws:
                await self.ws.close()

            self.is_connected = False
            logger.info(f"🛑 Live сессия остановлена (ID: {self.session_id})")
            logger.info(f"📊 Статистика: {self.stats}")

        except Exception as e:
            logger.error(f"❌ Ошибка остановки сессии: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику сессии"""
        return {
            **self.stats,
            "is_connected": self.is_connected,
            "session_id": self.session_id
        }


# ============================================================================
# ИНТЕГРАЦИЯ С TELEGRAM БОТОМ
# ============================================================================

class TelegramVoiceAssistant:
    """
    Голосовой ассистент для Telegram с Gemini Live API

    Использование:
        assistant = TelegramVoiceAssistant()
        await assistant.start_conversation(user_id)
        await assistant.process_voice(user_id, audio_bytes)
    """

    def __init__(self):
        self.active_sessions: Dict[int, GeminiLiveSession] = {}
        logger.info("🎤 Telegram Voice Assistant инициализирован")

    async def start_conversation(
        self,
        user_id: int,
        on_audio_ready: Callable[[bytes], Any]
    ) -> bool:
        """
        Начать голосовой разговор с пользователем

        Args:
            user_id: ID пользователя Telegram
            on_audio_ready: Callback для отправки аудио ответа

        Returns:
            True если сессия запущена
        """
        # Если уже есть активная сессия, остановим её
        if user_id in self.active_sessions:
            await self.stop_conversation(user_id)

        # Создаём новую сессию
        session = GeminiLiveSession(
            on_audio_received=on_audio_ready
        )

        success = await session.start()

        if success:
            self.active_sessions[user_id] = session
            logger.info(f"✅ Голосовая сессия запущена для пользователя {user_id}")
            return True
        else:
            logger.error(f"❌ Не удалось запустить сессию для {user_id}")
            return False

    async def process_voice(
        self,
        user_id: int,
        audio_bytes: bytes,
        mime_type: str = "audio/ogg"
    ) -> bool:
        """
        Обработка голосового сообщения пользователя

        Args:
            user_id: ID пользователя
            audio_bytes: Аудио данные
            mime_type: MIME тип аудио

        Returns:
            True если обработано успешно
        """
        session = self.active_sessions.get(user_id)

        if not session:
            logger.warning(f"⚠️ Нет активной сессии для пользователя {user_id}")
            return False

        return await session.send_audio(audio_bytes, mime_type)

    async def process_image(
        self,
        user_id: int,
        image_bytes: bytes,
        caption: Optional[str] = None
    ) -> bool:
        """
        Обработка фото во время разговора

        Args:
            user_id: ID пользователя
            image_bytes: Изображение
            caption: Подпись к фото

        Returns:
            True если обработано успешно
        """
        session = self.active_sessions.get(user_id)

        if not session:
            logger.warning(f"⚠️ Нет активной сессии для пользователя {user_id}")
            return False

        # Отправляем фото
        success = await session.send_image(image_bytes)

        # Если есть подпись, отправляем её
        if success and caption:
            await session.send_text(caption)

        return success

    async def stop_conversation(self, user_id: int) -> bool:
        """
        Остановить разговор с пользователем

        Args:
            user_id: ID пользователя

        Returns:
            True если остановлено успешно
        """
        session = self.active_sessions.get(user_id)

        if session:
            await session.stop()
            del self.active_sessions[user_id]
            logger.info(f"🛑 Сессия остановлена для пользователя {user_id}")
            return True

        return False

    def get_session_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить статистику сессии пользователя"""
        session = self.active_sessions.get(user_id)
        return session.get_stats() if session else None

    async def cleanup_inactive_sessions(self, max_idle_minutes: int = 5):
        """Очистка неактивных сессий"""
        # TODO: Реализовать отслеживание времени последней активности
        pass


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def is_gemini_live_available() -> bool:
    """Проверка доступности Gemini Live API"""
    return bool(os.getenv("GOOGLE_API_KEY"))


async def test_gemini_live():
    """Тестовый запуск Gemini Live API"""
    if not is_gemini_live_available():
        logger.error("❌ GOOGLE_API_KEY не найден")
        return False

    try:
        # Создаём тестовую сессию
        session = GeminiLiveSession()

        # Запускаем
        success = await session.start()

        if success:
            logger.info("✅ Gemini Live API работает!")

            # Отправляем тестовое сообщение
            await session.send_text("Привет! Это тест Live API.")

            # Ждём 3 секунды для получения ответа
            await asyncio.sleep(3)

            # Останавливаем
            await session.stop()

            return True
        else:
            logger.error("❌ Не удалось запустить Live сессию")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка теста: {e}")
        return False


if __name__ == "__main__":
    # Тестовый запуск
    logging.basicConfig(level=logging.INFO)

    async def main():
        result = await test_gemini_live()
        print(f"\nGemini Live API: {'✅ Готов' if result else '❌ Недоступен'}")

    asyncio.run(main())
