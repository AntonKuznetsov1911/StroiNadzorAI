# 🚀 Deployment Guide - Real-time Voice Assistant

Полная инструкция по развёртыванию Real-time голосового ассистента в продакшен.

## 📋 Что будем деплоить

1. **WebSocket прокси** (`websocket_proxy.py`) → Railway/Heroku
2. **Telegram Mini App** (frontend) → Vercel/GitHub Pages
3. **Telegram Bot** (`bot.py`) → Railway/Heroku (уже работает)

## 🎯 Архитектура после деплоя

```
┌─────────────────────────┐
│ Telegram пользователь   │
│ (на стройплощадке)      │
└────────────┬────────────┘
             │
             ↓
┌─────────────────────────┐
│ @StroiNadzorAI_bot      │
│ (Railway/Heroku)        │
│ - Кнопка Mini App       │
└────────────┬────────────┘
             │
             ↓
┌─────────────────────────┐
│ Telegram Mini App       │
│ (Vercel/GitHub Pages)   │
│ - HTML/JS/CSS           │
│ - Захват микрофона      │
│ - WebSocket клиент      │
└────────────┬────────────┘
             │ WSS
             ↓
┌─────────────────────────┐
│ WebSocket Proxy         │
│ (Railway/Heroku)        │
│ - websocket_proxy.py    │
└────────────┬────────────┘
             │ WSS
             ↓
┌─────────────────────────┐
│ Gemini Live API         │
│ (Google)                │
└─────────────────────────┘
```

---

## 🔧 Часть 1: Деплой WebSocket Proxy

### Вариант A: Railway (рекомендуется)

#### 1. Подготовка файлов

Создайте `Procfile` в корне проекта:

```bash
# Создаём Procfile для Railway
echo "web: python websocket_proxy.py" > Procfile
```

Или если уже есть Procfile, добавьте:

```
# Procfile
web: python bot.py
websocket: python websocket_proxy.py
```

#### 2. Проверка requirements.txt

Убедитесь что в `requirements.txt` есть:

```txt
websockets>=12.0
google-generativeai>=0.9.0
python-dotenv>=1.0.0
```

#### 3. Деплой на Railway

```bash
# Если ещё не залогинены
railway login

# Создайте новый сервис для WebSocket прокси
railway up

# Или создайте через веб-интерфейс:
# 1. Откройте https://railway.app/dashboard
# 2. New Project → Deploy from GitHub
# 3. Выберите репозиторий StroiNadzorAI
# 4. Add Service → WebSocket Proxy
```

#### 4. Настройка переменных окружения

В Railway Dashboard → Settings → Environment Variables:

```bash
GOOGLE_API_KEY=your_google_api_key
PORT=8080
```

#### 5. Получите URL WebSocket прокси

После деплоя Railway выдаст URL типа:
```
https://stroinadzorai-websocket-production.up.railway.app
```

Сохраните этот URL! Он понадобится для Mini App.

---

### Вариант B: Heroku

```bash
# Создайте новое приложение
heroku create stroinadzor-websocket

# Установите переменные
heroku config:set GOOGLE_API_KEY=your_key_here -a stroinadzor-websocket

# Деплой
git push heroku main

# Получите URL
heroku info -a stroinadzor-websocket
```

---

## 📱 Часть 2: Деплой Telegram Mini App

### Вариант A: Vercel (рекомендуется - БЕСПЛАТНО)

#### 1. Установка Vercel CLI

```bash
npm install -g vercel
```

#### 2. Обновление WebSocket URL в Mini App

Откройте `mini_app/app.js` и замените:

```javascript
const CONFIG = {
    WS_URL: window.location.hostname === 'localhost'
        ? 'ws://localhost:8080/stream/'
        : 'wss://stroinadzorai-websocket-production.up.railway.app/stream/',  // ← Ваш Railway URL
    // ...
};
```

#### 3. Деплой на Vercel

```bash
cd mini_app

# Первый деплой
vercel

# Ответьте на вопросы:
# - Set up and deploy? Yes
# - Which scope? Ваш аккаунт
# - Link to existing project? No
# - Project name? stroinadzor-voice-assistant
# - Directory? ./

# Production деплой
vercel --prod
```

#### 4. Получите URL Mini App

Vercel выдаст URL типа:
```
https://stroinadzor-voice-assistant.vercel.app
```

Сохраните этот URL!

---

### Вариант B: GitHub Pages (БЕСПЛАТНО)

#### 1. Создайте отдельный репозиторий

```bash
cd mini_app

# Инициализируем git
git init

# Создаём README
echo "# StroiNadzorAI Voice Assistant Mini App" > README.md

# Коммитим
git add .
git commit -m "Initial commit: Real-time Voice Assistant Mini App"

# Создаём репозиторий на GitHub
gh repo create stroinadzor-miniapp --public --source=. --remote=origin

# Пушим
git push -u origin main
```

#### 2. Включите GitHub Pages

1. Откройте https://github.com/your-username/stroinadzor-miniapp
2. Settings → Pages
3. Source: `main` branch, root directory
4. Save

Через пару минут сайт будет доступен:
```
https://your-username.github.io/stroinadzor-miniapp/
```

---

### Вариант C: Netlify

```bash
cd mini_app

# Установите Netlify CLI
npm install -g netlify-cli

# Деплой
netlify deploy --prod

# Следуйте инструкциям
# Publish directory: .
```

---

## 🤖 Часть 3: Обновление Telegram Bot

### 1. Добавьте Mini App URL в .env

```bash
# .env (локально)
MINI_APP_URL=https://stroinadzor-voice-assistant.vercel.app/

# Railway (в Environment Variables)
MINI_APP_URL=https://stroinadzor-voice-assistant.vercel.app/
```

### 2. Перезапустите бота

```bash
# Локально
python bot.py

# Railway - автоматически перезапустится после пуша
git add .
git commit -m "Добавлен Mini App URL"
git push
```

### 3. Проверьте работу кнопки

Откройте бота в Telegram:
1. Отправьте `/start`
2. Должна появиться кнопка "⚡ Real-time чат"
3. При нажатии откроется Mini App

---

## 🎯 Часть 4: Регистрация Mini App в BotFather

### 1. Откройте BotFather

```
@BotFather в Telegram
```

### 2. Зарегистрируйте Mini App

```
/newapp

# Выберите бота:
@StroiNadzorAI_bot

# Название приложения:
Voice Assistant

# Описание:
Real-time голосовой ассистент для инженеров ПТО на стройплощадке

# Фото (опционально):
Загрузите изображение 640x360px

# GIF демо (опционально):
Пропустите

# Web App URL:
https://stroinadzor-voice-assistant.vercel.app/

# Short name (для ссылки):
voice_assistant
```

### 3. Получите прямую ссылку

BotFather выдаст ссылку типа:
```
https://t.me/StroiNadzorAI_bot/voice_assistant
```

Её можно использовать для прямого запуска Mini App.

---

## ✅ Проверка работоспособности

### 1. Проверка WebSocket Proxy

```bash
# Проверьте что прокси работает
curl https://stroinadzorai-websocket-production.up.railway.app/

# Должен вернуться ответ (или 404 - это нормально, главное что сервер отвечает)
```

### 2. Проверка Mini App

1. Откройте в браузере: `https://stroinadzor-voice-assistant.vercel.app/`
2. Должна загрузиться страница с кнопкой "Начать разговор"
3. Откройте DevTools (F12) → Console
4. Не должно быть ошибок загрузки

### 3. Проверка интеграции с Telegram

1. Откройте бота: `@StroiNadzorAI_bot`
2. Отправьте `/start`
3. Нажмите "⚡ Real-time чат"
4. Должен открыться Mini App внутри Telegram
5. Нажмите "Начать разговор"
6. Разрешите доступ к микрофону
7. Скажите что-нибудь - бот должен ответить

---

## 🐛 Troubleshooting

### Ошибка: "Failed to connect to WebSocket"

**Проблема:** Mini App не может подключиться к WebSocket прокси.

**Решение:**

1. Проверьте что `websocket_proxy.py` запущен:
   ```bash
   railway logs -a stroinadzor-websocket
   ```

2. Проверьте что URL правильный в `app.js`:
   ```javascript
   WS_URL: 'wss://your-correct-url.railway.app/stream/'
   ```

3. Проверьте CORS (если нужно, добавьте в websocket_proxy.py):
   ```python
   # Добавьте в websocket_handler
   response_headers = {
       "Access-Control-Allow-Origin": "*"
   }
   ```

### Ошибка: "Microphone access denied"

**Проблема:** Telegram требует HTTPS для доступа к микрофону.

**Решение:**

1. Убедитесь что Mini App работает на HTTPS (Vercel/GitHub Pages автоматически дают HTTPS)
2. Проверьте что URL в BotFather начинается с `https://`
3. В настройках Telegram: Settings → Privacy → Microphone → Разрешить

### Ошибка: "GOOGLE_API_KEY not found"

**Проблема:** Не установлена переменная окружения.

**Решение:**

```bash
# Railway Dashboard → Settings → Environment Variables
GOOGLE_API_KEY=your_google_api_key
```

### Высокая задержка (> 500ms)

**Проблемы:**
- Медленный интернет пользователя
- Перегруженный сервер

**Решение:**

1. Проверьте логи Railway:
   ```bash
   railway logs
   ```

2. Масштабируйте сервер (Railway позволяет)

3. Уменьшите размер аудио чанков в `app.js`:
   ```javascript
   chunkDuration: 50  // Вместо 100
   ```

---

## 💰 Стоимость

### Railway (WebSocket Proxy)

- **Free tier:** $5 в месяц (500 часов)
- **Hobby plan:** $5/месяц (бесплатно первые $5)
- Для голосового ассистента хватит Free tier

### Vercel (Mini App)

- **Hobby:** БЕСПЛАТНО
- 100GB bandwidth/месяц
- Более чем достаточно

### GitHub Pages (альтернатива)

- **БЕСПЛАТНО**
- Без ограничений для публичных репозиториев

### Gemini API (Live API)

- **Бесплатно:** 1500 запросов/день
- **Pay-as-you-go:** $0.000025 за 1000 аудио чанков
- ~$0.01 за 10-минутный разговор

### ИТОГО: БЕСПЛАТНО или ~$5/месяц

---

## 📊 Мониторинг

### Railway Logs

```bash
# Смотрим логи WebSocket прокси
railway logs -a stroinadzor-websocket --tail

# Фильтруем ошибки
railway logs | grep ERROR
```

### Vercel Analytics

1. Откройте Vercel Dashboard
2. Выберите проект
3. Analytics → Смотрите статистику посещений

### Telegram Bot Logs

```bash
# Локально
tail -f bot.log

# Railway
railway logs -a stroinadzor-bot
```

---

## 🔐 Безопасность

### 1. Защита API ключей

**НЕ КОММИТЬТЕ .env в git!**

```bash
# .gitignore
.env
*.env
.env.local
```

### 2. Rate Limiting (опционально)

Добавьте в `websocket_proxy.py`:

```python
from collections import defaultdict
from datetime import datetime, timedelta

# Ограничение: 10 подключений в минуту на пользователя
rate_limits = defaultdict(list)

async def check_rate_limit(user_id):
    now = datetime.now()
    rate_limits[user_id] = [t for t in rate_limits[user_id] if now - t < timedelta(minutes=1)]

    if len(rate_limits[user_id]) >= 10:
        return False

    rate_limits[user_id].append(now)
    return True
```

### 3. Валидация user_id

```python
# В websocket_handler добавьте:
if not user_id or user_id == "unknown":
    await websocket.send(json.dumps({"type": "error", "message": "Invalid user ID"}))
    return
```

---

## 🎉 Готово!

Теперь у вас работает:

✅ **WebSocket Proxy** на Railway
✅ **Telegram Mini App** на Vercel
✅ **Real-time голосовой чат** с задержкой < 100ms
✅ **Hands-free** работа на стройплощадке
✅ **Function Calling** для автоматических расчётов

## 📞 Поддержка

Если что-то не работает:

1. Проверьте логи Railway
2. Откройте DevTools в Mini App (F12)
3. Проверьте переменные окружения
4. Убедитесь что все URL правильные

---

**Версия:** 1.0
**Дата:** Декабрь 2025
**Платформы:** Railway, Vercel, Telegram Mini Apps
