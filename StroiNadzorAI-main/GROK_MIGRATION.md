# Миграция на xAI Grok API

## Изменения

### 1. Зависимости
- **Было**: `anthropic>=0.74.0`
- **Стало**: `openai>=1.54.0`

### 2. Переменные окружения (.env)
- **Было**: `ANTHROPIC_API_KEY=...`
- **Стало**: `XAI_API_KEY=...`

### 3. Модели AI
- **Было**: 
  - `claude-3-5-haiku-20241022`
  - `claude-sonnet-4-5-20250929`
- **Стало**: `grok-2-latest`

### 4. API Endpoints
- **Base URL**: `https://api.x.ai/v1`
- **Совместимость**: OpenAI-compatible API

### 5. Код изменений

#### Инициализация клиента
```python
# Было
from anthropic import Anthropic
client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Стало
from openai import OpenAI
client = OpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1"
)
```

#### Вызов API
```python
# Было
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=2500,
    messages=[{"role": "user", "content": "..."}]
)
answer = response.content[0].text

# Стало
response = client.chat.completions.create(
    model="grok-2-latest",
    max_tokens=2500,
    messages=[{"role": "user", "content": "..."}]
)
answer = response.choices[0].message.content
```

## Установка

```bash
# Установить новые зависимости
pip install -r requirements.txt

# Обновить .env файл
# Замените ANTHROPIC_API_KEY на XAI_API_KEY
```

## Проверка работы

```bash
# Запустить бота
python bot.py
```

## Обновленные файлы
- `bot.py` - основной файл бота
- `auto_apply.py` - автоприменение изменений
- `dev_mode.py` - режим разработки
- `dev_mode_local.py` - локальный режим разработки
- `prompt_engineer.py` - инженеринг промптов
- `requirements.txt` - зависимости
- `.env.example` - пример конфигурации
