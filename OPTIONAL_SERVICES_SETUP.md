# Настройка опциональных сервисов StroiNadzorAI

## Обзор

Бот работает **БЕЗ** настройки этих сервисов, но с ограниченным функционалом.
Данное руководство поможет настроить дополнительные возможности.

---

## 1. PostgreSQL (Рекомендуется)

### Зачем нужен?
- Хранение истории диалогов в БД (вместо JSON файлов)
- Быстрый поиск по истории
- Масштабируемость для большого количества пользователей

### Без PostgreSQL:
- ⚠️ История сохраняется в JSON файлы (медленно)
- ⚠️ Ограниченная масштабируемость

### Быстрая настройка (Railway - бесплатно)

1. **Зарегистрируйтесь на Railway**
   - Перейдите на https://railway.app
   - Войдите через GitHub

2. **Создайте PostgreSQL**
   ```
   New Project → Deploy PostgreSQL → Deploy
   ```

3. **Получите DATABASE_URL**
   ```
   PostgreSQL → Variables → DATABASE_URL → Copy
   ```

4. **Добавьте в .env**
   ```env
   DATABASE_URL=postgresql://user:password@host:port/database
   ```

5. **Перезапустите бота**
   ```bash
   python bot.py
   ```

### Проверка работы
Если в логах появилось:
```
✅ PostgreSQL модуль загружен
```
Значит все настроено правильно!

Если появилось:
```
⚠️ PostgreSQL не доступен, используется JSON
```
Проверьте правильность DATABASE_URL в .env

---

## 2. Redis (Опционально)

### Зачем нужен?
- Кэширование популярных вопросов
- Быстрые ответы (без обращения к Claude API)
- Экономия API токенов (~40%)

### Без Redis:
- ✅ Кэш работает в памяти
- ⚠️ Сбрасывается при перезапуске бота
- ⚠️ Не работает в distributed режиме

### Быстрая настройка (Railway)

1. **Создайте Redis**
   ```
   New Project → Deploy Redis → Deploy
   ```

2. **Получите REDIS_URL**
   ```
   Redis → Variables → REDIS_URL → Copy
   ```

3. **Добавьте в .env**
   ```env
   REDIS_URL=redis://default:password@host:port
   ```

4. **Перезапустите бота**

### Проверка работы
```
✅ Redis кэш инициализирован
```

---

## 3. Stable Diffusion Web UI (Для профессиональной генерации изображений)

### Зачем нужен?
- Профессиональные технические чертежи
- Фотореалистичные изображения
- 4 типа схем: technical, blueprint, isometric, diagram

### Без Stable Diffusion:
- ✅ Работает Gemini AI (схематические изображения)
- ⚠️ Упрощенное качество

### Требования
- GPU: NVIDIA GTX 1660 или выше (рекомендуется RTX 3060+)
- RAM: 8GB минимум (16GB рекомендуется)
- Место: 10GB для модели

### Быстрая настройка (Windows)

1. **Скачайте Stable Diffusion Web UI**
   ```bash
   git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
   cd stable-diffusion-webui
   ```

2. **Скачайте модель**
   - Перейдите на https://huggingface.co
   - Скачайте модель (например: Stable Diffusion 1.5 или SDXL)
   - Положите в папку `models/Stable-diffusion/`

3. **Запустите с API**

   Отредактируйте `webui-user.bat`:
   ```batch
   set COMMANDLINE_ARGS=--api --listen
   ```

   Затем запустите:
   ```bash
   webui-user.bat
   ```

4. **Добавьте в .env**
   ```env
   SD_API_URL=http://127.0.0.1:7860
   ```

5. **Перезапустите бота**

### Проверка работы
```bash
curl http://127.0.0.1:7860/sdapi/v1/sd-models
```

Если видите список моделей - все работает!

### Облачные альтернативы (если нет мощного ПК)

**Google Colab (Бесплатно)**
- GPU Tesla T4
- 12 часов лимит
- https://colab.research.google.com

**Vast.ai ($0.10-0.30/час)**
- RTX 3060+
- https://vast.ai

**RunPod ($0.20-0.50/час)**
- Готовые шаблоны SD
- https://runpod.io

---

## 4. OpenAI API (Опционально)

### Зачем нужен?
- **Whisper API**: Распознавание голосовых сообщений (высокое качество)
- **DALL-E 3**: Фотореалистичная генерация изображений

### Без OpenAI:
- ⚠️ Голосовые работают с ограничениями (базовое распознавание)
- ✅ DALL-E 3 заменен на Gemini AI (схемы)

### Быстрая настройка

1. **Получите API ключ**
   - Зарегистрируйтесь на https://platform.openai.com
   - API Keys → Create new secret key

2. **Добавьте в .env**
   ```env
   OPENAI_API_KEY=sk-...
   ```

3. **Пополните баланс**
   - Минимум $5
   - Стоимость:
     - Whisper: ~$0.006/минута
     - DALL-E 3: ~$0.04/изображение

4. **Перезапустите бота**

### Проверка работы
```
✅ OpenAI Whisper API доступен для голосовых сообщений
```

---

## 5. Gemini API (Уже настроен ✅)

### Текущий статус
- ✅ GEMINI_API_KEY настроен
- ✅ Используется для генерации схематических изображений
- ✅ Бесплатно в пределах квоты

### Если нужен новый ключ

1. **Получите ключ**
   - https://makersuite.google.com/app/apikey
   - Create API key

2. **Добавьте в .env**
   ```env
   GEMINI_API_KEY=AIza...
   ```

---

## Таблица сравнения

| Сервис | Обязателен? | Что улучшает | Стоимость |
|--------|-------------|--------------|-----------|
| **PostgreSQL** | Рекомендуется | История диалогов | Бесплатно (Railway) |
| **Redis** | Опционально | Кэширование | Бесплатно (Railway) |
| **Stable Diffusion** | Опционально | Качество изображений | Бесплатно (локально) |
| **OpenAI API** | Опционально | Голос + DALL-E 3 | ~$5-20/месяц |
| **Gemini API** | ✅ Настроен | Изображения | Бесплатно |

---

## Приоритеты настройки

### Минимальная конфигурация (работает сейчас)
```env
TELEGRAM_BOT_TOKEN=...
ANTHROPIC_API_KEY=...
GEMINI_API_KEY=... (уже есть)
```

### Рекомендуемая конфигурация
```env
TELEGRAM_BOT_TOKEN=...
ANTHROPIC_API_KEY=...
GEMINI_API_KEY=...
DATABASE_URL=... (PostgreSQL)
```

### Максимальная конфигурация
```env
TELEGRAM_BOT_TOKEN=...
ANTHROPIC_API_KEY=...
GEMINI_API_KEY=...
DATABASE_URL=... (PostgreSQL)
REDIS_URL=... (Redis)
SD_API_URL=... (Stable Diffusion)
OPENAI_API_KEY=... (OpenAI)
```

---

## Диагностика проблем

### Проблема: "PostgreSQL не доступен"
**Решение:**
1. Проверьте DATABASE_URL в .env
2. Убедитесь, что PostgreSQL запущен
3. Проверьте подключение: `psql <DATABASE_URL>`

### Проблема: "Redis не доступен"
**Решение:**
1. Проверьте REDIS_URL в .env
2. Проверьте подключение: `redis-cli -u <REDIS_URL> ping`

### Проблема: "SD API connection refused"
**Решение:**
1. Убедитесь, что SD Web UI запущен
2. Проверьте порт: `curl http://127.0.0.1:7860`
3. Убедитесь, что используется флаг --api

### Проблема: "ReportLab not available"
**Решение:**
```bash
pip install reportlab==4.0.7
```

---

## Поддержка

**Документация:**
- PostgreSQL: `POSTGRESQL_SETUP.md`
- Stable Diffusion: `SD_SETUP.md`
- Изображения: `IMAGE_GENERATION_GUIDE.md`

**Логи:**
- Проверьте `bot.log` на наличие ошибок
- Ищите строки с ⚠️ или ❌

**Тестирование:**
```bash
python bot.py
```

Смотрите в логах, какие модули загружены:
```
✅ - Модуль работает
⚠️ - Модуль не настроен (используется fallback)
❌ - Критическая ошибка
```

---

**Последнее обновление:** 2025-12-04
**Версия:** 1.0
