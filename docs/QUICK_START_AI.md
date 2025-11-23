# 🚀 Quick Start - Профессиональный AI

## Быстрый запуск новых возможностей

### 📦 Шаг 1: Установка зависимостей

```bash
pip install -r requirements.txt
```

Будут установлены:
- `chromadb==0.4.22` - векторная база
- `tiktoken==0.5.2` - токенизация
- и все остальные зависимости

### 🗄️ Шаг 2: Инициализация векторной БД (опционально)

Векторная БД создается автоматически при первом использовании. Но можно предварительно загрузить нормативы:

```python
python scripts/init_vector_db.py
```

Или вручную:

```python
from src.services.vector_service import get_vector_service
from data.construction_knowledge import CONSTRUCTION_KNOWLEDGE

service = get_vector_service()

# Загрузка одного документа
doc = CONSTRUCTION_KNOWLEDGE['SP63.13330.2018']
for section_name, content in doc['sections'].items():
    service.add_document(
        collection_type='sp',
        document_id=f"SP63_{section_name}",
        text=content,
        metadata={'title': doc['title'], 'section': section_name}
    )

print(f"Loaded: {service.get_collection_stats()}")
```

### 🤖 Шаг 3: Использование в коде

#### Вариант A: Простой вопрос с RAG

```python
from src.services.openai_service_v2 import get_openai_service_v2
from src.database import get_db

service = get_openai_service_v2()
db = next(get_db())

# Текстовый вопрос
answer = await service.analyze_with_rag(
    db=db,
    user_id=123456,  # Telegram user ID
    question="Какая допустимая ширина трещины в стене?",
    use_context=True  # Использовать историю разговора
)

print(answer)
```

#### Вариант B: Анализ фото

```python
# Анализ фото с контекстом
analysis = await service.analyze_photo_with_context(
    db=db,
    user_id=123456,
    photo_base64="<base64_image>",
    caption="Трещина в стене"
)

print(analysis)
```

#### Вариант C: Генерация схемы

```python
# Генерация технической схемы
diagram_url = await service.generate_diagram(
    description="Узел примыкания кровли к стене",
    diagram_type="схема"
)

print(f"Схема: {diagram_url}")
```

### 🔄 Шаг 4: Интеграция в Telegram бота

Обновите `src/bot/handlers.py`:

```python
# Старый код:
from src.services.openai_service import get_openai_service
openai_service = get_openai_service()

# Новый код:
from src.services.openai_service_v2 import get_openai_service_v2
openai_service_v2 = get_openai_service_v2()

# В handle_text:
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... проверки rate limit ...

    # СТАРЫЙ КОД:
    # answer = await openai_service.analyze_text_question(question)

    # НОВЫЙ КОД (с RAG и контекстом):
    answer = await openai_service_v2.analyze_with_rag(
        db=db,
        user_id=user.id,
        question=question,
        use_context=True
    )

    # ... остальное без изменений ...

# В handle_photo:
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... получение фото ...

    # СТАРЫЙ КОД:
    # analysis = await openai_service.analyze_photo(photo_base64, caption)

    # НОВЫЙ КОД (с контекстом):
    analysis = await openai_service_v2.analyze_photo_with_context(
        db=db,
        user_id=user.id,
        photo_base64=photo_base64,
        caption=caption
    )

    # ... остальное без изменений ...
```

### 🧹 Шаг 5: Управление контекстом

#### Очистка контекста пользователя:

```python
from src.services.context_service import get_context_service

context_service = get_context_service()

# Очистить историю конкретного пользователя
context_service.clear_context(user_id=123456)
```

#### Получение истории разговора:

```python
history = context_service.get_conversation_history(db, user_id=123456, limit=5)
for msg in history:
    print(f"{msg['role']}: {msg['content'][:100]}...")
```

### 📊 Шаг 6: Статистика векторной БД

```python
from src.services.vector_service import get_vector_service

service = get_vector_service()

# Статистика по коллекциям
stats = service.get_collection_stats()
print(f"СП: {stats['sp']} документов")
print(f"ГОСТ: {stats['gost']} документов")
print(f"СНиП: {stats['snip']} документов")
print(f"Кейсы: {stats['cases']} документов")

# Поиск
results = service.search(
    query="трещины в бетоне",
    collection_types=['sp', 'gost'],
    n_results=3
)

for result in results:
    print(f"\n{result['collection']}: {result['document'][:200]}...")
    print(f"Релевантность: {1 - result['distance']:.2%}")
```

---

## ⚙️ Настройки в .env

Добавьте в `.env`:

```bash
# Векторная БД
VECTOR_DB_PATH=./data/chromadb

# OpenAI (GPT-4o для максимального качества)
OPENAI_MODEL=gpt-4o  # Было gpt-4o-mini

# Context Memory
CONTEXT_MAX_MESSAGES=10  # Последние N сообщений
CONTEXT_TTL=7200  # TTL в секундах (2 часа)
```

---

## 🧪 Тестирование

### Тест 1: Простой вопрос

```python
answer = await service.analyze_with_rag(
    db=db,
    user_id=1,
    question="Какой класс бетона для фундамента?",
    use_context=False
)

# Ожидается: конкретный ответ с пунктами СП
assert "B20" in answer or "B25" in answer
assert "СП" in answer
```

### Тест 2: Контекст

```python
# Первый вопрос
await service.analyze_with_rag(db, 1, "Класс бетона для фундамента?", True)

# Второй вопрос (без явного упоминания фундамента)
answer = await service.analyze_with_rag(db, 1, "А если грунт слабый?", True)

# Ожидается: AI понял что речь о фундаменте
assert "фундамент" in answer.lower() or "основание" in answer.lower()
```

### Тест 3: RAG поиск

```python
results = service.search("трещины допустимая ширина", n_results=3)

# Ожидается: найден СП 63.13330.2018
assert any("СП 63" in r['metadata'].get('title', '') for r in results)
assert any("трещин" in r['document'].lower() for r in results)
```

---

## 🎯 Примеры команд бота

Добавьте команду для тестирования AI:

```python
async def test_ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /testai для проверки AI"""

    test_question = "Трещина 0.5 мм в колонне - это опасно?"

    await update.message.reply_text("🧪 Тестирую AI с RAG...")

    answer = await openai_service_v2.analyze_with_rag(
        db=next(get_db()),
        user_id=update.effective_user.id,
        question=test_question,
        use_context=False
    )

    await update.message.reply_text(
        f"📋 Вопрос: {test_question}\n\n"
        f"💡 Ответ:\n{answer}",
        parse_mode=ParseMode.MARKDOWN
    )

# Регистрация
application.add_handler(CommandHandler("testai", test_ai_command))
```

---

## 🐛 Troubleshooting

### Ошибка: "chromadb not found"

```bash
pip install chromadb==0.4.22
```

### Ошибка: "Cannot connect to OpenAI"

Проверьте API ключ в `.env`:
```bash
OPENAI_API_KEY=sk-...
```

### Векторная БД пустая

Загрузите нормативы:
```python
from data.construction_knowledge import CONSTRUCTION_KNOWLEDGE
# ... код загрузки из Шага 2 ...
```

### Контекст не работает

Проверьте Redis:
```bash
redis-cli ping
# Должно вернуть: PONG
```

---

## 📈 Мониторинг

### Проверка работы RAG:

```python
import logging
logging.basicConfig(level=logging.INFO)

# Логи покажут:
# INFO: RAG analysis completed in 2.34s
# INFO: Found 3 relevant documents
# INFO: Context: 6 messages loaded
```

### Метрики:

```python
# Статистика векторной БД
stats = service.get_collection_stats()
print(f"Всего документов: {sum(stats.values())}")

# Статистика контекста
# (количество кешированных разговоров в Redis)
```

---

## ✅ Checklist запуска

- [ ] Установлены зависимости (`pip install -r requirements.txt`)
- [ ] Обновлен `.env` с новыми настройками
- [ ] Инициализирована векторная БД (опционально)
- [ ] Обновлены handlers в боте (используют service_v2)
- [ ] Проведено тестирование на примерах
- [ ] Redis работает (для контекста)
- [ ] PostgreSQL работает (для истории)

---

## 🎓 Готово!

Теперь ваш бот работает с профессиональным AI на уровне **главного прораба**!

**Попробуйте:**
- Задайте вопрос о трещинах
- Спросите про утеплитель для вашего региона
- Отправьте фото дефекта
- Задайте несколько связанных вопросов (проверка контекста)

Наслаждайтесь точными, экспертными ответами! 🏗️
