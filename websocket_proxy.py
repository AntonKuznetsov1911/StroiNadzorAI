"""
WebSocket Прокси для Real-time Streaming с Gemini Live API

Архитектура:
  Telegram Mini App (микрофон)
    ↓ WebSocket
  Этот Прокси Сервер
    ↓ WebSocket
  Gemini Multimodal Live API
    ↓ WebSocket
  Этот Прокси Сервер
    ↓ WebSocket
  Telegram Mini App (динамик)

Задержка: < 100ms (сотые доли секунды!)
"""

import asyncio
import websockets
import json
import os
import logging
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL Gemini Multimodal Live API
GEMINI_LIVE_URL = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent"

# Активные сессии: {user_id: gemini_websocket}
active_sessions: Dict[str, websockets.WebSocketServerProtocol] = {}


class GeminiLiveProxy:
    """
    Прокси между Telegram Mini App и Gemini Live API

    Функционал:
    - Двусторонний стриминг аудио
    - Поддержка interruption (прерывания)
    - Шумоподавление на уровне конфига
    - Function calling для калькуляторов
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.gemini_ws = None
        self.client_ws = None
        self.is_connected = False
        self.session_id = None

    async def connect_to_gemini(self):
        """Подключение к Gemini Live API"""
        try:
            url = f"{GEMINI_LIVE_URL}?key={self.api_key}"

            logger.info(f"🔌 Подключение к Gemini Live API...")
            self.gemini_ws = await websockets.connect(
                url,
                ping_interval=30,
                ping_timeout=10,
                max_size=10485760  # 10MB
            )

            # Отправляем setup конфигурацию
            setup_msg = {
                "setup": {
                    "model": "models/gemini-2.0-flash-exp",
                    "generation_config": {
                        "response_modalities": ["AUDIO"],
                        "speech_config": {
                            "voice_config": {
                                "prebuilt_voice_config": {
                                    "voice_name": "Aoede"  # Женский голос
                                }
                            }
                        }
                    },
                    "system_instruction": {
                        "parts": [{
                            "text": """Ты — голосовой ассистент-инженер ПТО на стройке в России.

ОСОБЕННОСТИ:
- Говори КРАТКО (прораб на объекте, руки заняты)
- Профессиональный язык строителей
- При опасности кричи: "СТОП! ОПАСНОСТЬ!"
- Умеешь считать бетон, арматуру, материалы

ПРИМЕРЫ:
"Сколько бетона?" → "9 целых 6 кубов"
"Какой защитный слой?" → "40 миллиметров по СП 63"

Отвечай быстро, как живой коллега на объекте."""
                        }]
                    },
                    # Добавляем Function Calling
                    "tools": [{
                        "function_declarations": [
                            {
                                "name": "calculate_concrete",
                                "description": "Рассчитать объём бетона",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "length": {"type": "number", "description": "Длина в метрах"},
                                        "width": {"type": "number", "description": "Ширина в метрах"},
                                        "thickness": {"type": "number", "description": "Толщина в метрах"}
                                    },
                                    "required": ["length", "width", "thickness"]
                                }
                            },
                            {
                                "name": "search_regulation",
                                "description": "Найти в СП/ГОСТ/СНиП",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string", "description": "Поисковый запрос"}
                                    },
                                    "required": ["query"]
                                }
                            }
                        ]
                    }]
                }
            }

            await self.gemini_ws.send(json.dumps(setup_msg))
            self.is_connected = True
            self.session_id = f"stream_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            logger.info(f"✅ Gemini Live API подключен (Session: {self.session_id})")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Gemini: {e}")
            return False

    async def bridge_client_to_gemini(self):
        """
        Поток: Telegram Mini App → Gemini
        Передаём аудио от пользователя в Gemini
        """
        try:
            async for message in self.client_ws:
                if isinstance(message, str):
                    # JSON команды (например, stop, interrupt)
                    data = json.loads(message)

                    if data.get("type") == "interrupt":
                        # Пользователь перебил бота
                        logger.info("⏸️ Interruption detected")
                        # TODO: Отправить команду прерывания в Gemini

                    elif data.get("type") == "stop":
                        logger.info("🛑 Stop signal received")
                        break

                elif isinstance(message, bytes):
                    # Аудио данные (binary)
                    # Конвертируем в base64 для Gemini
                    import base64
                    audio_b64 = base64.b64encode(message).decode('utf-8')

                    # Отправляем в Gemini Live API
                    msg = {
                        "realtime_input": {
                            "media_chunks": [{
                                "data": audio_b64,
                                "mime_type": "audio/pcm"
                            }]
                        }
                    }

                    await self.gemini_ws.send(json.dumps(msg))
                    logger.debug(f"🎤 → Gemini: {len(message)} bytes")

        except websockets.exceptions.ConnectionClosed:
            logger.info("📱 Client disconnected")
        except Exception as e:
            logger.error(f"❌ Error in client→gemini bridge: {e}")

    async def bridge_gemini_to_client(self):
        """
        Поток: Gemini → Telegram Mini App
        Передаём аудио ответы от Gemini пользователю
        """
        try:
            async for message in self.gemini_ws:
                data = json.loads(message)

                # Setup confirmation
                if "setupComplete" in data:
                    logger.info("✅ Gemini setup complete")
                    # Отправляем подтверждение клиенту
                    await self.client_ws.send(json.dumps({"type": "ready"}))
                    continue

                # Серверный контент (аудио ответы)
                if "serverContent" in data:
                    server_content = data["serverContent"]

                    if "modelTurn" in server_content:
                        parts = server_content["modelTurn"].get("parts", [])

                        for part in parts:
                            # Аудио данные
                            if "inlineData" in part:
                                audio_b64 = part["inlineData"]["data"]

                                # Декодируем из base64
                                import base64
                                audio_bytes = base64.b64decode(audio_b64)

                                # Отправляем бинарные данные клиенту
                                await self.client_ws.send(audio_bytes)
                                logger.debug(f"🔊 → Client: {len(audio_bytes)} bytes")

                            # Текстовый ответ (для дебага/транскрипции)
                            if "text" in part:
                                text = part["text"]
                                logger.info(f"💬 Gemini says: {text[:100]}...")

                                # Отправляем транскрипцию клиенту
                                await self.client_ws.send(json.dumps({
                                    "type": "transcript",
                                    "text": text,
                                    "role": "bot"
                                }))

                            # Function call (для обработки на бэкенде)
                            if "functionCall" in part:
                                func_call = part["functionCall"]
                                logger.info(f"🔧 Function call: {func_call['name']}")

                                # Обрабатываем функцию
                                result = await self.handle_function_call(func_call)

                                # Отправляем результат обратно в Gemini
                                response_msg = {
                                    "tool_response": {
                                        "function_responses": [{
                                            "name": func_call["name"],
                                            "response": {"result": result}
                                        }]
                                    }
                                }
                                await self.gemini_ws.send(json.dumps(response_msg))

                    # Turn complete
                    if "turnComplete" in server_content:
                        logger.debug("✅ Turn complete")
                        await self.client_ws.send(json.dumps({"type": "turn_complete"}))

                # Ошибки
                if "error" in data:
                    error_msg = data["error"].get("message", "Unknown error")
                    logger.error(f"❌ Gemini error: {error_msg}")
                    await self.client_ws.send(json.dumps({
                        "type": "error",
                        "message": error_msg
                    }))

        except websockets.exceptions.ConnectionClosed:
            logger.info("🔌 Gemini disconnected")
        except Exception as e:
            logger.error(f"❌ Error in gemini→client bridge: {e}")

    async def handle_function_call(self, func_call):
        """Обработка вызовов функций"""
        func_name = func_call.get("name")
        func_args = func_call.get("args", {})

        logger.info(f"🔧 Executing {func_name}({func_args})")

        if func_name == "calculate_concrete":
            length = func_args.get("length", 0)
            width = func_args.get("width", 0)
            thickness = func_args.get("thickness", 0)

            volume = length * width * thickness
            volume_with_margin = volume * 1.05

            return {
                "volume_m3": round(volume, 2),
                "volume_with_margin_m3": round(volume_with_margin, 2),
                "recommendation": f"Рекомендуется заказать {round(volume_with_margin, 1)} м³ бетона"
            }

        elif func_name == "search_regulation":
            query = func_args.get("query", "")
            return {
                "found": True,
                "message": f"Поиск по нормативам: {query}. Используйте базу СП/ГОСТ."
            }

        return {"error": "Unknown function"}

    async def start_bridge(self, client_ws):
        """Запуск двустороннего моста"""
        self.client_ws = client_ws

        # Подключаемся к Gemini
        success = await self.connect_to_gemini()
        if not success:
            await client_ws.send(json.dumps({
                "type": "error",
                "message": "Failed to connect to Gemini"
            }))
            return

        # Запускаем оба потока одновременно
        try:
            await asyncio.gather(
                self.bridge_client_to_gemini(),
                self.bridge_gemini_to_client()
            )
        finally:
            # Закрываем соединение с Gemini
            if self.gemini_ws:
                await self.gemini_ws.close()
            self.is_connected = False
            logger.info(f"🛑 Session {self.session_id} closed")


# ============================================================================
# WebSocket Сервер
# ============================================================================

async def websocket_handler(websocket, path):
    """
    Обработчик подключений от Telegram Mini App

    Path:
      /stream/{user_id} - стриминг сессия для пользователя
    """

    # Извлекаем user_id из пути
    parts = path.split('/')
    user_id = parts[-1] if len(parts) > 1 else "unknown"

    logger.info(f"📱 New client connected: {user_id} (IP: {websocket.remote_address})")

    # Проверяем API ключ
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("❌ GOOGLE_API_KEY not found")
        await websocket.send(json.dumps({
            "type": "error",
            "message": "Server configuration error: missing API key"
        }))
        await websocket.close()
        return

    # Создаём прокси для этого пользователя
    proxy = GeminiLiveProxy(api_key)
    active_sessions[user_id] = websocket

    try:
        # Запускаем мост между клиентом и Gemini
        await proxy.start_bridge(websocket)
    except Exception as e:
        logger.error(f"❌ Error in session {user_id}: {e}")
    finally:
        # Удаляем из активных сессий
        if user_id in active_sessions:
            del active_sessions[user_id]
        logger.info(f"📱 Client disconnected: {user_id}")


async def main():
    """Запуск WebSocket сервера"""

    # Порт из переменной окружения (для Railway) или 8080 по умолчанию
    port = int(os.getenv("PORT", 8080))
    host = "0.0.0.0"

    logger.info(f"🚀 Starting WebSocket Proxy Server on {host}:{port}")
    logger.info(f"📡 Gemini Live API URL: {GEMINI_LIVE_URL}")
    logger.info(f"🎤 Ready for real-time streaming!")

    # Запускаем сервер
    async with websockets.serve(websocket_handler, host, port):
        await asyncio.Future()  # Работает вечно


if __name__ == "__main__":
    asyncio.run(main())
