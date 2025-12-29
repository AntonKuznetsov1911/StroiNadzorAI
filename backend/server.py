from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import asyncio
import websockets
import json
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="СтройНадзорAI API")

# Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

# Gemini Live API URL
GEMINI_LIVE_URL = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={GEMINI_API_KEY}" if GEMINI_API_KEY else None

# Системная инструкция для строительного помощника
SYSTEM_INSTRUCTION = """Ты — голосовой AI-ассистент "СтройНадзорAI" для прорабов и инженеров на строительной площадке.

ТВОЯ РОЛЬ:
- Консультант по строительным нормативам РФ (СП, ГОСТ, СНиП)
- Эксперт по охране труда и технике безопасности
- Помощник в расчётах (бетон, арматура, опалубка)

ПРАВИЛА:
1. Отвечай КРАТКО и ПО ДЕЛУ
2. Указывай номера нормативов (СП 63.13330, ГОСТ 10180 и т.д.)
3. Предупреждай об опасностях
4. Говори как человек, без markdown"""


@app.get("/api/health")
def health():
    return {"status": "ok", "gemini_available": bool(GEMINI_API_KEY)}


@app.get("/api/voice-assistant")
async def voice_assistant_page():
    """Страница голосового ассистента"""
    html_path = "/app/mini_app/voice_assistant.html"
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    return HTMLResponse("<h1>Voice Assistant not found</h1>", status_code=404)


@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint для голосового ассистента"""
    await websocket.accept()
    logger.info("🔌 Клиент подключился к WebSocket")
    
    gemini_ws = None
    is_active = True
    
    try:
        # Отправляем подтверждение
        await websocket.send_json({
            "type": "connected",
            "session_id": str(id(websocket)),
            "message": "Подключено к СтройНадзорAI"
        })
        
        if not GEMINI_API_KEY:
            await websocket.send_json({
                "type": "error",
                "message": "GEMINI_API_KEY не настроен"
            })
            return
        
        # Подключаемся к Gemini Live API
        logger.info("🔗 Подключение к Gemini Live API...")
        gemini_ws = await websockets.connect(GEMINI_LIVE_URL)
        
        # Отправляем Setup
        setup_msg = {
            "setup": {
                "model": "models/gemini-2.0-flash-exp",
                "generation_config": {
                    "response_modalities": ["AUDIO", "TEXT"],
                    "speech_config": {
                        "voice_config": {
                            "prebuilt_voice_config": {"voice_name": "Kore"}
                        }
                    }
                },
                "system_instruction": {
                    "parts": [{"text": SYSTEM_INSTRUCTION}]
                }
            }
        }
        await gemini_ws.send(json.dumps(setup_msg))
        
        # Ждём подтверждение
        response = await gemini_ws.recv()
        setup_response = json.loads(response)
        
        if "setupComplete" in setup_response:
            logger.info("✅ Gemini Live API готов")
            await websocket.send_json({
                "type": "ready",
                "message": "Голосовой ассистент готов"
            })
        else:
            await websocket.send_json({
                "type": "error",
                "message": "Ошибка инициализации Gemini"
            })
            return
        
        # Задача для прослушивания Gemini
        async def listen_gemini():
            nonlocal is_active
            try:
                async for message in gemini_ws:
                    if not is_active:
                        break
                    response = json.loads(message)
                    
                    server_content = response.get("serverContent")
                    if not server_content:
                        continue
                    
                    model_turn = server_content.get("modelTurn")
                    if model_turn:
                        for part in model_turn.get("parts", []):
                            if "inlineData" in part:
                                # Аудио
                                await websocket.send_json({
                                    "type": "audio",
                                    "data": part["inlineData"]["data"],
                                    "mime_type": part["inlineData"].get("mimeType", "audio/pcm")
                                })
                            elif "text" in part:
                                # Текст
                                await websocket.send_json({
                                    "type": "text",
                                    "text": part["text"]
                                })
                    
                    if server_content.get("turnComplete"):
                        await websocket.send_json({"type": "turn_complete"})
                        
            except Exception as e:
                logger.error(f"Gemini listen error: {e}")
        
        # Запускаем прослушивание Gemini
        gemini_task = asyncio.create_task(listen_gemini())
        
        # Обрабатываем сообщения от клиента
        while is_active:
            try:
                data = await websocket.receive_json()
                msg_type = data.get("type", "audio")
                
                if msg_type == "audio":
                    # Аудио данные
                    gemini_msg = {
                        "realtime_input": {
                            "media_chunks": [{
                                "mime_type": "audio/pcm",
                                "data": data.get("data", "")
                            }]
                        }
                    }
                    await gemini_ws.send(json.dumps(gemini_msg))
                    
                elif msg_type == "text":
                    # Текст
                    gemini_msg = {
                        "client_content": {
                            "turns": [{
                                "role": "user",
                                "parts": [{"text": data.get("text", "")}]
                            }],
                            "turn_complete": True
                        }
                    }
                    await gemini_ws.send(json.dumps(gemini_msg))
                    
                elif msg_type == "end_turn":
                    gemini_msg = {"client_content": {"turn_complete": True}}
                    await gemini_ws.send(json.dumps(gemini_msg))
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Client message error: {e}")
                break
        
        is_active = False
        gemini_task.cancel()
        
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        is_active = False
        if gemini_ws:
            await gemini_ws.close()
        logger.info("🔌 Клиент отключился")

