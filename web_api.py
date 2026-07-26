"""
Бэкенд API для веб-чата СтройНадзорAI
Принимает вопросы, отправляет в AI с фоллбэком: Gemini → Grok → Claude → OpenAI
Деплой на Railway, ключи через переменные окружения
"""

import os
import json
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — экспертный AI-консультант по строительным нормативам Российской Федерации. Твои знания включают:
- Своды правил (СП), ГОСТ, СНиП, Федеральные законы
- Технологии строительных работ
- Расчёт конструкций и материалов
- Контроль качества и строительный надзор
- Безопасность труда в строительстве
- Проектирование зданий и сооружений
- Сметное дело и ценообразование

Правила ответа:
- Отвечай профессионально, но понятно
- Ссылайся на конкретные нормативные документы (СП, ГОСТ, СНиП) где возможно
- Если вопрос не относится к строительству, вежливо направь пользователя к строительной тематике
- Давай практические рекомендации
- Используй структурированные ответы с пунктами где уместно"""

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
XAI_API_KEY = os.getenv("XAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=60.0)
    logger.info("HTTP client created")
    keys = []
    if GOOGLE_API_KEY or GEMINI_API_KEY:
        keys.append("Gemini")
    if XAI_API_KEY:
        keys.append("Grok")
    if ANTHROPIC_API_KEY:
        keys.append("Claude")
    if OPENAI_API_KEY:
        keys.append("OpenAI")
    logger.info(f"Available AI providers: {', '.join(keys) or 'NONE'}")
    yield
    await http_client.aclose()


app = FastAPI(title="СтройНадзорAI API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://antonkuznetsov1911.github.io",
        "http://localhost",
        "http://localhost:3000",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    answer: str
    provider: str


async def call_gemini(message: str, history: List[ChatMessage]) -> str:
    key = GEMINI_API_KEY or GOOGLE_API_KEY
    if not key:
        raise ValueError("No Gemini key")

    contents = []
    for msg in history[-18:]:
        role = "user" if msg.role == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg.content}]})
    contents.append({"role": "user", "parts": [{"text": message}]})

    resp = await http_client.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}",
        json={
            "contents": contents,
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 4096,
            },
        },
    )
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


async def call_grok(message: str, history: List[ChatMessage]) -> str:
    if not XAI_API_KEY:
        raise ValueError("No xAI key")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history[-18:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": message})

    resp = await http_client.post(
        "https://api.x.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {XAI_API_KEY}"},
        json={
            "model": "grok-3-fast",
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7,
        },
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


async def call_claude(message: str, history: List[ChatMessage]) -> str:
    if not ANTHROPIC_API_KEY:
        raise ValueError("No Anthropic key")

    messages = []
    for msg in history[-18:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": message})

    resp = await http_client.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-5-20250929",
            "max_tokens": 4096,
            "system": SYSTEM_PROMPT,
            "messages": messages,
        },
    )
    resp.raise_for_status()
    data = resp.json()
    return data["content"][0]["text"]


async def call_openai(message: str, history: List[ChatMessage]) -> str:
    if not OPENAI_API_KEY:
        raise ValueError("No OpenAI key")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history[-18:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": message})

    resp = await http_client.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={
            "model": "gpt-4o-mini",
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7,
        },
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


PROVIDERS = [
    ("Gemini", call_gemini),
    ("Grok", call_grok),
    ("Claude", call_claude),
    ("OpenAI", call_openai),
]


@app.get("/")
async def health():
    return {"status": "ok", "service": "СтройНадзорAI API"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Пустое сообщение")

    errors = []
    for name, fn in PROVIDERS:
        try:
            logger.info(f"Trying {name}...")
            answer = await fn(req.message, req.history)
            if answer and answer.strip():
                logger.info(f"Success with {name} ({len(answer)} chars)")
                return ChatResponse(answer=answer, provider=name)
        except Exception as e:
            logger.warning(f"{name} failed: {e}")
            errors.append(f"{name}: {e}")

    logger.error(f"All providers failed: {errors}")
    raise HTTPException(
        status_code=503,
        detail="Все AI-провайдеры недоступны. Попробуйте позже.",
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
