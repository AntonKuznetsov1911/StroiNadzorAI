# Голосовой ассистент Gemini Live API

## Описание

Real-time голосовой AI ассистент для СтройНадзорAI на базе Gemini 2.0 Flash Live API.

## Архитектура

```
┌──────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  Browser /   │  WS   │   FastAPI       │  WS   │  Gemini Live    │
│  Mini App    │◄─────►│   Backend       │◄─────►│  API            │
│              │       │   (proxy)       │       │                 │
└──────────────┘       └─────────────────┘       └─────────────────┘
     Аудио PCM              Прокси              Голос + Текст
     16kHz mono            сообщений
```

## Требования

1. **GEMINI_API_KEY** или **GOOGLE_API_KEY** в переменных окружения
2. Python библиотека `websockets`
3. Браузер с поддержкой WebRTC/getUserMedia

## Настройка

### 1. Установите API ключ

```bash
# В .env файле
GEMINI_API_KEY=your_api_key_here
```

### 2. Запустите backend

Backend уже настроен с WebSocket endpoint `/api/ws`

### 3. Откройте Mini App

- URL: `/api/voice-assistant` 
- Или используйте файл `mini_app/voice_assistant.html`

## Как это работает

### Клиент (Browser)

1. Захват аудио с микрофона (16kHz, mono, PCM)
2. Конвертация Float32 → Int16 → Base64
3. Отправка через WebSocket

### Сервер (FastAPI)

1. Принимает Base64 PCM от клиента
2. Проксирует в Gemini Live API
3. Получает аудио ответ от Gemini
4. Отправляет клиенту для воспроизведения

### Gemini Live API

1. Принимает аудио стрим
2. Транскрибирует речь
3. Генерирует ответ
4. Синтезирует голосовой ответ

## Формат сообщений

### Клиент → Сервер

```json
// Аудио чанк
{"type": "audio", "data": "base64_pcm_data"}

// Текстовое сообщение
{"type": "text", "text": "Привет"}

// Завершение речи
{"type": "end_turn"}
```

### Сервер → Клиент

```json
// Подключение
{"type": "connected", "session_id": "...", "message": "..."}

// Готов к работе
{"type": "ready", "message": "Голосовой ассистент готов"}

// Аудио ответ
{"type": "audio", "data": "base64_pcm_data", "mime_type": "audio/pcm"}

// Текстовый ответ (транскрипция)
{"type": "text", "text": "..."}

// Ответ завершён
{"type": "turn_complete"}

// Ошибка
{"type": "error", "message": "..."}
```

## Голоса Gemini

Доступные голоса (настраивается в `SYSTEM_INSTRUCTION`):
- **Kore** - мужской, нейтральный (используется по умолчанию)
- **Puck** - мужской, дружелюбный
- **Charon** - женский, профессиональный
- **Fenrir** - мужской, глубокий
- **Aoede** - женский, мягкий

## Ограничения

1. Требуется HTTPS для доступа к микрофону в браузере (кроме localhost)
2. Gemini Live API в alpha-версии
3. Лимиты на количество одновременных сессий

## Файлы

- `/app/backend/server.py` - FastAPI с WebSocket endpoint
- `/app/mini_app/voice_assistant.html` - Веб-интерфейс
- `/app/gemini_live_websocket.py` - Standalone WebSocket сервер (альтернатива)

## Тестирование

```bash
# Проверка health
curl http://localhost:8001/api/health

# Ожидаемый ответ
{"status":"ok","gemini_available":true}
```

## Интеграция с Telegram

В bot.py уже настроена кнопка для открытия Mini App:
- Кнопка "⚡ Real-time чат" открывает Mini App
- URL настраивается через `MINI_APP_URL` в .env
