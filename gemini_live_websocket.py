"""
WebSocket прокси-сервер для Gemini Live API
============================================

Обеспечивает real-time голосовое общение между Telegram Mini App и Gemini Live API.

Архитектура:
Browser (Mini App) <-> WebSocket Server <-> Gemini Live API

Протокол:
- Входящие данные: Base64 PCM аудио (16kHz, mono)
- Исходящие данные: Base64 PCM аудио + JSON события
"""

import asyncio
import websockets
import json
import os
import logging
import base64
from typing import Dict, Set, Optional
from dataclasses import dataclass
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
HOST = "0.0.0.0"
PORT = 8765  # WebSocket порт

# Gemini Live API URL
GEMINI_LIVE_URL = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={GEMINI_API_KEY}"

# Системная инструкция для строительного помощника
SYSTEM_INSTRUCTION = """Ты — голосовой AI-ассистент "СтройНадзорAI" для прорабов и инженеров на строительной площадке.

ТВОЯ РОЛЬ:
- Консультант по строительным нормативам РФ (СП, ГОСТ, СНиП)
- Эксперт по охране труда и технике безопасности
- Помощник в расчётах (бетон, арматура, опалубка)

ПРАВИЛА ОБЩЕНИЯ:
1. Отвечай КРАТКО и ПО ДЕЛУ (на стройке некогда слушать длинные речи)
2. Всегда указывай номера нормативов (СП 63.13330, ГОСТ 10180 и т.д.)
3. Предупреждай об опасностях и рисках
4. Используй строительную терминологию

ПРИМЕРЫ ХОРОШИХ ОТВЕТОВ:
- "Защитный слой для фундамента — минимум 40 мм по СП 63.13330. При агрессивных грунтах — 50 мм."
- "Для плиты 6 на 8 толщиной 20 см нужно 9.6 кубов бетона. Рекомендую B25 с W6."

ВАЖНО: Ты общаешься голосом. Не используй markdown, списки или форматирование — говори как человек."""


@dataclass
class ClientSession:
    """Сессия клиента"""
    client_ws: websockets.WebSocketServerProtocol
    gemini_ws: Optional[websockets.WebSocketClientProtocol] = None
    user_id: Optional[str] = None
    connected_at: datetime = None
    is_active: bool = False


class GeminiLiveProxy:
    """Прокси-сервер для Gemini Live API"""
    
    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.active_connections: Set[websockets.WebSocketServerProtocol] = set()
    
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Обработка подключения клиента"""
        session_id = str(id(websocket))
        logger.info(f"🔌 Клиент подключился: {session_id}")
        
        session = ClientSession(
            client_ws=websocket,
            connected_at=datetime.now()
        )
        self.sessions[session_id] = session
        self.active_connections.add(websocket)
        
        try:
            # Отправляем подтверждение подключения
            await websocket.send(json.dumps({
                "type": "connected",
                "session_id": session_id,
                "message": "Подключено к СтройНадзорAI"
            }))
            
            # Подключаемся к Gemini
            await self._connect_to_gemini(session)
            
            # Обрабатываем сообщения от клиента
            async for message in websocket:
                await self._process_client_message(session, message)
                
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"📴 Клиент отключился: {session_id} ({e.code})")
        except Exception as e:
            logger.error(f"❌ Ошибка сессии {session_id}: {e}")
        finally:
            await self._cleanup_session(session_id)
    
    async def _connect_to_gemini(self, session: ClientSession):
        """Подключение к Gemini Live API"""
        if not GEMINI_API_KEY:
            await session.client_ws.send(json.dumps({
                "type": "error",
                "message": "GEMINI_API_KEY не настроен"
            }))
            return
        
        try:
            logger.info("🔗 Подключение к Gemini Live API...")
            
            session.gemini_ws = await websockets.connect(
                GEMINI_LIVE_URL,
                additional_headers={"Content-Type": "application/json"}
            )
            
            # Отправляем Setup сообщение
            setup_msg = {
                "setup": {
                    "model": "models/gemini-2.0-flash-exp",
                    "generation_config": {
                        "response_modalities": ["AUDIO", "TEXT"],
                        "speech_config": {
                            "voice_config": {
                                "prebuilt_voice_config": {
                                    "voice_name": "Kore"  # Мужской голос, подходит для стройки
                                }
                            }
                        }
                    },
                    "system_instruction": {
                        "parts": [{"text": SYSTEM_INSTRUCTION}]
                    }
                }
            }
            
            await session.gemini_ws.send(json.dumps(setup_msg))
            
            # Ждём подтверждение setup
            response = await session.gemini_ws.recv()
            setup_response = json.loads(response)
            
            if "setupComplete" in setup_response:
                session.is_active = True
                logger.info("✅ Gemini Live API подключен")
                
                await session.client_ws.send(json.dumps({
                    "type": "ready",
                    "message": "Голосовой ассистент готов"
                }))
                
                # Запускаем прослушивание ответов от Gemini
                asyncio.create_task(self._listen_gemini(session))
            else:
                logger.error(f"❌ Setup failed: {setup_response}")
                await session.client_ws.send(json.dumps({
                    "type": "error",
                    "message": "Ошибка инициализации Gemini"
                }))
                
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Gemini: {e}")
            await session.client_ws.send(json.dumps({
                "type": "error",
                "message": f"Не удалось подключиться к Gemini: {str(e)}"
            }))
    
    async def _process_client_message(self, session: ClientSession, message: str):
        """Обработка сообщения от клиента"""
        if not session.gemini_ws or not session.is_active:
            return
        
        try:
            data = json.loads(message)
            msg_type = data.get("type", "audio")
            
            if msg_type == "audio":
                # Аудио данные (base64 PCM)
                audio_data = data.get("data", "")
                
                gemini_msg = {
                    "realtime_input": {
                        "media_chunks": [{
                            "mime_type": "audio/pcm",
                            "data": audio_data
                        }]
                    }
                }
                await session.gemini_ws.send(json.dumps(gemini_msg))
                
            elif msg_type == "text":
                # Текстовое сообщение
                text = data.get("text", "")
                
                gemini_msg = {
                    "client_content": {
                        "turns": [{
                            "role": "user",
                            "parts": [{"text": text}]
                        }],
                        "turn_complete": True
                    }
                }
                await session.gemini_ws.send(json.dumps(gemini_msg))
                
            elif msg_type == "end_turn":
                # Сигнал окончания речи пользователя
                gemini_msg = {
                    "client_content": {
                        "turn_complete": True
                    }
                }
                await session.gemini_ws.send(json.dumps(gemini_msg))
                
        except json.JSONDecodeError:
            # Если не JSON — считаем что это raw base64 аудио
            gemini_msg = {
                "realtime_input": {
                    "media_chunks": [{
                        "mime_type": "audio/pcm",
                        "data": message
                    }]
                }
            }
            await session.gemini_ws.send(json.dumps(gemini_msg))
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")
    
    async def _listen_gemini(self, session: ClientSession):
        """Прослушивание ответов от Gemini"""
        try:
            async for message in session.gemini_ws:
                if not session.is_active:
                    break
                    
                response = json.loads(message)
                await self._process_gemini_response(session, response)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("🔌 Соединение с Gemini закрыто")
        except Exception as e:
            logger.error(f"❌ Ошибка чтения от Gemini: {e}")
        finally:
            session.is_active = False
    
    async def _process_gemini_response(self, session: ClientSession, response: dict):
        """Обработка ответа от Gemini"""
        try:
            # Проверяем serverContent
            server_content = response.get("serverContent")
            if not server_content:
                return
            
            model_turn = server_content.get("modelTurn")
            if model_turn:
                parts = model_turn.get("parts", [])
                
                for part in parts:
                    # Аудио ответ
                    if "inlineData" in part:
                        inline_data = part["inlineData"]
                        audio_data = inline_data.get("data", "")
                        mime_type = inline_data.get("mimeType", "audio/pcm")
                        
                        # Отправляем аудио клиенту
                        await session.client_ws.send(json.dumps({
                            "type": "audio",
                            "data": audio_data,
                            "mime_type": mime_type
                        }))
                    
                    # Текстовый ответ (транскрипция)
                    elif "text" in part:
                        text = part["text"]
                        await session.client_ws.send(json.dumps({
                            "type": "text",
                            "text": text
                        }))
            
            # Проверяем завершение ответа
            if server_content.get("turnComplete"):
                await session.client_ws.send(json.dumps({
                    "type": "turn_complete"
                }))
            
            # Обработка прерывания
            if server_content.get("interrupted"):
                await session.client_ws.send(json.dumps({
                    "type": "interrupted"
                }))
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки ответа Gemini: {e}")
    
    async def _cleanup_session(self, session_id: str):
        """Очистка сессии"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            
            session.is_active = False
            
            if session.gemini_ws:
                await session.gemini_ws.close()
            
            if session.client_ws in self.active_connections:
                self.active_connections.remove(session.client_ws)
            
            del self.sessions[session_id]
            logger.info(f"🧹 Сессия {session_id} очищена")
    
    async def start_server(self):
        """Запуск WebSocket сервера"""
        logger.info(f"🚀 Запуск WebSocket сервера на ws://{HOST}:{PORT}")
        
        if not GEMINI_API_KEY:
            logger.error("❌ GEMINI_API_KEY не установлен!")
            return
        
        async with websockets.serve(
            self.handle_client,
            HOST,
            PORT,
            ping_interval=30,
            ping_timeout=10
        ):
            logger.info(f"✅ WebSocket сервер запущен на ws://{HOST}:{PORT}")
            await asyncio.Future()  # Бесконечный цикл


# === ТОЧКА ВХОДА ===

proxy = GeminiLiveProxy()

async def main():
    """Главная функция"""
    await proxy.start_server()


if __name__ == "__main__":
    asyncio.run(main())
