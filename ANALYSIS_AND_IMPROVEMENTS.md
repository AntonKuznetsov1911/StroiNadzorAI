# Анализ проекта СтройНадзорAI v5.0 и рекомендации по улучшению

## Общая оценка

**СтройНадзорAI v5.0** — это зрелый, функционально насыщенный Telegram-бот для профессионалов строительной отрасли РФ. Проект демонстрирует глубокое понимание предметной области и грамотное использование современных AI-технологий. Ниже представлен детальный анализ с конкретными рекомендациями по улучшению.

---

## 1. АРХИТЕКТУРА И СТРУКТУРА КОДА

### 1.1 Критическая проблема: монолитный bot.py (6348 строк, 297 КБ)

**Проблема:** Главный файл `bot.py` содержит более 6000 строк кода — это существенно затрудняет навигацию, отладку и поддержку.

**Рекомендация:** Декомпозировать `bot.py` на логические модули:

```
bot/
├── __init__.py
├── main.py              # Точка входа, инициализация Application
├── config.py            # Загрузка .env, константы, настройки
├── middleware.py         # Rate limiting, логирование, аутентификация
├── handlers/
│   ├── __init__.py
│   ├── start.py         # /start, /help, /menu
│   ├── text.py          # handle_text — маршрутизация текстовых сообщений
│   ├── photo.py         # handle_photo — анализ фотографий
│   ├── voice.py         # handle_voice — голосовые сообщения
│   ├── callbacks.py     # handle_callback — обработка inline-кнопок
│   ├── commands.py      # Дополнительные команды (/norms, /calc, и т.д.)
│   └── errors.py        # error_handler
├── services/
│   ├── ai_router.py     # Маршрутизация к нужной AI-модели
│   ├── grok_service.py  # Работа с xAI Grok
│   ├── claude_service.py
│   └── gemini_service.py
└── utils/
    ├── message_splitter.py  # Разбивка длинных сообщений
    ├── formatters.py        # Форматирование ответов
    └── validators.py        # Валидация пользовательского ввода
```

**Приоритет:** Высокий
**Влияние:** Существенно упростит разработку, тестирование и онбординг новых разработчиков.

### 1.2 Чрезмерное количество try/except при импорте (25+ блоков)

**Проблема:** В `bot.py` строки 44–450 содержат более 25 блоков `try/except ImportError` для опциональных модулей. Каждый модуль порождает глобальную переменную `*_AVAILABLE`.

**Рекомендация:** Создать единый реестр модулей:

```python
# module_registry.py
class ModuleRegistry:
    """Централизованная загрузка и проверка доступности модулей"""

    def __init__(self):
        self._modules = {}

    def register(self, name: str, import_path: str, required_symbols: list):
        try:
            module = __import__(import_path, fromlist=required_symbols)
            self._modules[name] = {
                'available': True,
                'module': module,
                'symbols': {s: getattr(module, s) for s in required_symbols}
            }
            logger.info(f"Модуль {name} загружен")
        except ImportError:
            self._modules[name] = {'available': False}
            logger.warning(f"Модуль {name} не найден")

    def is_available(self, name: str) -> bool:
        return self._modules.get(name, {}).get('available', False)

    def get(self, name: str, symbol: str):
        return self._modules.get(name, {}).get('symbols', {}).get(symbol)
```

**Приоритет:** Средний

---

## 2. ДУБЛИРОВАНИЕ КОДА

### 2.1 Разбивка длинных сообщений Telegram

**Проблема:** Логика разбивки сообщений (лимит 4096 символов) дублируется минимум в 4 местах: `handle_photo`, `handle_text`, `handle_photo_with_visualization` и других обработчиках.

**Рекомендация:** Вынести в утилиту:

```python
async def send_long_message(update, text, parse_mode=None, reply_markup=None, max_length=4000):
    """Отправка длинного сообщения с автоматической разбивкой"""
    if len(text) <= max_length:
        await update.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
        return

    parts = split_text(text, max_length)
    for i, part in enumerate(parts):
        markup = reply_markup if i == len(parts) - 1 else None
        prefix = f"(продолжение {i+1}/{len(parts)})\n\n" if i > 0 else ""
        await update.message.reply_text(prefix + part, reply_markup=markup)
```

**Приоритет:** Средний

### 2.2 Дублирование в xai_client.py

**Проблема:** Синхронный метод `chat_completions_create` и асинхронный `chat_completions_create_async` содержат практически идентичную логику обработки ошибок (строки 58-76 и 103-121).

**Рекомендация:** Вынести обработку ошибок в отдельный метод:

```python
def _handle_api_error(self, e):
    """Единая обработка ошибок xAI API"""
    if isinstance(e, httpx.TimeoutException):
        raise Exception("Превышено время ожидания ответа от AI.")
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if status == 429:
            raise Exception("Превышен лимит запросов.")
        elif status == 401:
            raise Exception("Неверный API ключ xAI.")
        raise Exception(f"Ошибка xAI API: {status}")
    raise Exception("Неожиданная ошибка xAI API.")
```

**Приоритет:** Низкий

### 2.3 Калькуляторы: 4 файла-обработчика

**Проблема:** `calculator_handlers.py` (144 КБ), `calculator_handlers_extended.py`, `calculator_handlers_part2.py`, `calculator_handlers_part3.py` — четыре файла с похожей структурой обработчиков. Каждый калькулятор реализован как `ConversationHandler` с повторяющимся паттерном.

**Рекомендация:** Создать фабрику калькуляторов:

```python
class CalculatorFactory:
    """Генерация ConversationHandler из декларативного описания"""

    @staticmethod
    def create(config: dict) -> ConversationHandler:
        """
        config = {
            'name': 'concrete',
            'title': 'Калькулятор бетона',
            'steps': [
                {'key': 'length', 'prompt': 'Введите длину (м):', 'type': float},
                {'key': 'width',  'prompt': 'Введите ширину (м):', 'type': float},
                {'key': 'height', 'prompt': 'Введите высоту (м):', 'type': float},
            ],
            'calculate': calculate_concrete,
            'format_result': format_concrete_result,
        }
        """
        # Генерация ConversationHandler из конфигурации
        ...
```

**Приоритет:** Средний (при дальнейшем добавлении калькуляторов)

---

## 3. БЕЗОПАСНОСТЬ

### 3.1 SQL-инъекции: текущее состояние — безопасно

`database.py` использует параметризованные запросы (`$1`, `$2`) через `asyncpg` — это правильно и безопасно.

### 3.2 Хэш-функция MD5 в кэше

**Проблема:** В `cache_manager.py:111` используется MD5 для генерации ключей кэша. Хотя MD5 здесь не используется для безопасности, а только для генерации ключей — коллизии теоретически возможны.

**Рекомендация:** Заменить на `hashlib.sha256` для надёжности:

```python
return hashlib.sha256(normalized.encode()).hexdigest()[:32]
```

**Приоритет:** Низкий (не критично для кэша)

### 3.3 Bare except в обработчиках

**Проблема:** В нескольких местах `bot.py` встречается `except:` без указания типа исключения (например, строки 3383-3384, 5970-5971):

```python
try:
    await thinking_message.delete()
except:
    pass
```

**Рекомендация:** Всегда указывать тип исключения:

```python
except Exception:
    pass
```

Это предотвращает перехват `KeyboardInterrupt`, `SystemExit` и других системных исключений.

**Приоритет:** Средний

### 3.4 Отсутствие ограничения размера загружаемых файлов

**Проблема:** Обработчик документов (`handle_document`) не проверяет размер файла перед загрузкой. Это может привести к проблемам с памятью при загрузке больших файлов.

**Рекомендация:** Добавить проверку:

```python
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 МБ

async def handle_document(update, context):
    document = update.message.document
    if document.file_size > MAX_FILE_SIZE:
        await update.message.reply_text("Файл слишком большой. Максимум 20 МБ.")
        return
```

**Приоритет:** Средний

---

## 4. ПРОИЗВОДИТЕЛЬНОСТЬ

### 4.1 Синхронные вызовы API в async-коде

**Проблема:** В `llm_council.py` метод `_call_grok` (строка 310-325) вызывает `self.xai_client.chat_completions_create()` — синхронный метод — внутри async-функции. Это блокирует event loop.

**Рекомендация:** Использовать асинхронный метод `chat_completions_create_async` или `run_in_executor`:

```python
async def _call_grok(self, messages, max_tokens=2000):
    if not self.xai_client:
        return None
    try:
        response = await self.xai_client.chat_completions_create_async(
            model=COUNCIL_MODELS["grok"]["model_id"],
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Grok error: {e}")
        return None
```

**Приоритет:** Высокий — блокировка event loop влияет на отзывчивость бота для всех пользователей.

### 4.2 Локальный кэш без TTL

**Проблема:** В `cache_manager.py` локальный кэш (`MEMORY_CACHE`) не имеет механизма устаревания (TTL). Записи остаются в памяти навсегда (до перезапуска). Ограничение в 1000 элементов не учитывает актуальность данных.

**Рекомендация:** Добавить TTL для локального кэша:

```python
from time import time

MEMORY_CACHE[cache_key] = {
    'answer': answer,
    'question': question,
    'count': 0,
    'expires_at': time() + (ttl_hours * 3600)
}

# При чтении:
entry = MEMORY_CACHE.get(cache_key)
if entry and entry['expires_at'] > time():
    return entry['answer']
elif entry:
    del MEMORY_CACHE[cache_key]  # Удаляем просроченный
```

**Приоритет:** Средний

### 4.3 Загрузка всех знаний в память при старте

**Проблема:** Все базы знаний (`regulations_2025.py`, `practical_knowledge_2025.py`, `practical_knowledge_advanced_2025.py`, `builder_reference.py` (270 КБ)) загружаются в память при старте бота.

**Рекомендация:** Для текущего масштаба (суммарно ~1-2 МБ) это приемлемо. При росте базы знаний стоит рассмотреть ленивую загрузку или SQLite для хранения.

**Приоритет:** Низкий (на будущее)

### 4.4 N+1 проблема в get_popular_questions

**Проблема:** В `cache_manager.py:221-264` метод `get_popular_questions` делает отдельный запрос `redis.get()` для каждого найденного ключа внутри цикла сканирования. При большом количестве кэшированных вопросов это создаёт значительную нагрузку.

**Рекомендация:** Использовать `pipeline` или `mget`:

```python
keys_to_fetch = []
counts = {}

async for key in redis_client.scan_iter(match="qa:*:count", count=100):
    count = await redis_client.get(key)
    if count and int(count) > 0:
        original_key = key.replace(':count', '')
        keys_to_fetch.append(original_key)
        counts[original_key] = int(count)

# Пакетное получение ответов
if keys_to_fetch:
    answers = await redis_client.mget(*keys_to_fetch)
```

**Приоритет:** Средний

---

## 5. ОБРАБОТКА ОШИБОК

### 5.1 Глобальное перехватывание Exception

**Проблема:** Во многих местах используется широкий `except Exception as e`, который может маскировать ошибки программирования (TypeError, ValueError, AttributeError и т.д.).

**Рекомендация:** Разделять ошибки API (ожидаемые) и ошибки программирования (неожиданные):

```python
try:
    response = await api_call()
except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
    # Ожидаемые ошибки API — обрабатываем
    logger.warning(f"API ошибка: {e}")
    return fallback_response()
# Остальные ошибки (TypeError, KeyError) — пусть всплывают для отладки
```

**Приоритет:** Средний

### 5.2 Отсутствие circuit breaker для внешних API

**Проблема:** При недоступности API (Grok, Claude, Gemini) каждый запрос пользователя будет пытаться обратиться к нерабочему сервису, тратя время на таймауты.

**Рекомендация:** Реализовать паттерн Circuit Breaker:

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = None
        self.state = "closed"  # closed | open | half-open

    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
                return True
            return False
        return True  # half-open

    def record_success(self):
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
```

**Приоритет:** Средний (важно при высокой нагрузке)

---

## 6. ТЕСТИРОВАНИЕ

### 6.1 Текущее состояние

Проект содержит 18+ тестовых файлов, но большинство из них — это интеграционные тесты, требующие реальных API-ключей. Модульных тестов с моками практически нет.

**Рекомендация:** Добавить юнит-тесты для критических модулей:

```python
# test_model_selector_unit.py
import pytest
from model_selector import ModelSelector

def test_photo_defect_uses_gemini():
    selector = ModelSelector()
    result = selector.classify_request("Что за трещина на фото?", has_photo=True)
    assert result["model"] == "gemini_vision"

def test_simple_question_uses_grok():
    selector = ModelSelector()
    result = selector.classify_request("Что такое СП?", has_photo=False)
    assert result["model"] == "grok_general"

def test_technical_question_uses_claude():
    selector = ModelSelector()
    result = selector.classify_request("Рассчитай армирование плиты", has_photo=False)
    assert result["model"] == "claude_technical"
```

**Приоритет:** Высокий

### 6.2 Отсутствие тестов для калькуляторов

**Проблема:** Калькуляторы — критический функционал (20+ формул). Ошибка в расчёте может привести к серьёзным последствиям на стройке.

**Рекомендация:** Создать тесты с контрольными значениями:

```python
def test_concrete_calculation():
    result = calculate_concrete(length=6, width=6, height=0.2)
    assert result['volume'] == pytest.approx(7.2, rel=0.01)
    assert result['cement_kg'] > 0
    assert result['sand_kg'] > 0
```

**Приоритет:** Высокий (критично для строительной отрасли)

---

## 7. НЕЗАВЕРШЁННЫЕ ЗАДАЧИ (TODO)

В коде обнаружены следующие TODO, которые стоит завершить:

| Файл | Строка | Описание |
|------|--------|----------|
| `gemini_live_api.py` | 632 | Отслеживание времени последней активности сессий |
| `gemini_live_api_v2.py` | 422 | Отправка результата функции через SDK |
| `improvements_v3.py` | 671 | Добавить timestamp |
| `improvements_v3.py` | 847 | Добавить остальные элементы |
| `websocket_proxy.py` | 175 | Отправить команду прерывания в Gemini |

**Приоритет:** Средний (особенно для `gemini_live_api.py:632` — утечка сессий)

---

## 8. ОПТИМИЗАЦИЯ СТОИМОСТИ AI-ЗАПРОСОВ

### 8.1 Текущая стратегия маршрутизации

`ModelSelector` грамотно распределяет запросы: простые вопросы -> Grok (бесплатно), технические -> Claude ($3/запрос), фото -> Gemini ($0.15).

### 8.2 Рекомендации по оптимизации

1. **Использовать кэш активнее** — кэшировать не только точные совпадения, но и семантически похожие вопросы (порог в `find_similar_cached_question` = 0.7 уже реализован, но нужно убедиться, что он вызывается перед каждым API-запросом).

2. **LLM Council — дорогая операция** — каждая консультация совета использует 3 AI-модели + ещё 3 для ревью + 1 для синтеза = до 7 API-вызовов. Рекомендуется:
   - Чаще использовать `quick_consult` (без этапа ревью) — экономия ~3 вызова
   - Показывать пользователю стоимость операции перед запуском совета
   - Кэшировать результаты совета агрессивнее (TTL = 30 дней)

3. **Gemini 2.5 Flash вместо Gemini 1.5 Flash в LLM Council** — в `llm_council.py:46` указан `gemini-1.5-flash`, хотя в остальном боте используется Gemini 2.5 Flash. Рекомендуется обновить модель для консистентности и качества.

**Приоритет:** Средний

---

## 9. ДОКУМЕНТАЦИЯ И ОТЛАДКА

### 9.1 Избыток документации

**Наблюдение:** 59 файлов Markdown — это очень много. Часть из них устарела или дублируется. Папка `docs/archive/` содержит 20+ файлов, которые стоит проверить на актуальность.

**Рекомендация:** Провести ревизию и оставить:
- `README.md` — главная точка входа
- `DEPLOYMENT_GUIDE.md` — развёртывание
- `QUICK_START.md` — быстрый старт
- Все остальное — перенести в `docs/archive/` или удалить

### 9.2 Логирование

**Положительное:** Логирование настроено хорошо (`bot.log` + stdout). Используются уровни INFO, WARNING, ERROR.

**Рекомендация:** Добавить структурированное логирование (JSON) для удобства анализа в production:

```python
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'module': record.module,
            'message': record.getMessage(),
            'user_id': getattr(record, 'user_id', None),
        })
```

**Приоритет:** Низкий

---

## 10. РЕКОМЕНДАЦИИ ПО ПРИОРИТЕТУ

### Высокий приоритет (критично)

1. **Исправить блокировку event loop в LLM Council** — синхронный вызов Grok API в async-контексте (`llm_council.py:316`)
2. **Добавить юнит-тесты для калькуляторов** — ошибки в расчётах критичны для строительной отрасли
3. **Декомпозировать `bot.py`** — файл на 6348 строк невозможно эффективно поддерживать

### Средний приоритет (важно)

4. Заменить `except:` на `except Exception:` (bare except)
5. Добавить проверку размера загружаемых файлов
6. Завершить TODO (особенно очистку неактивных сессий Gemini Live)
7. Обновить модель Gemini в LLM Council (1.5 -> 2.5)
8. Добавить TTL для локального кэша
9. Реализовать Circuit Breaker для внешних API
10. Централизовать логику разбивки длинных сообщений

### Низкий приоритет (улучшения)

11. Создать единый реестр модулей вместо 25 try/except
12. Заменить MD5 на SHA-256 в кэше
13. Оптимизировать `get_popular_questions` (N+1 проблема)
14. Добавить структурированное логирование (JSON)
15. Ревизия документации (59 markdown-файлов)

---

## 11. ИТОГОВАЯ ОЦЕНКА

| Критерий | Оценка | Комментарий |
|----------|--------|-------------|
| **Функциональность** | 9/10 | Богатый набор возможностей: 20+ калькуляторов, 5 AI-моделей, голосовой ассистент, генерация чертежей |
| **Архитектура** | 6/10 | Монолитный bot.py, но хорошая модульность в остальном |
| **Безопасность** | 7/10 | Параметризованные запросы, но bare except и отсутствие валидации файлов |
| **Производительность** | 7/10 | Блокировка event loop в LLM Council, отсутствие TTL в кэше |
| **Тестирование** | 5/10 | Есть тестовые файлы, но нет юнит-тестов с моками |
| **Документация** | 8/10 | Обширная, но требует ревизии |
| **Код** | 7/10 | Понятный, хорошо комментированный, но с дублированием |
| **DevOps** | 8/10 | Docker, Railway, Vercel — все настроено |

**Общая оценка: 7.1/10** — Проект профессионального уровня с отличным функционалом. Основные точки роста — архитектура (декомпозиция), тестирование и устранение технических долгов.

---

*Дата анализа: 15 февраля 2026*
*Версия проекта: v5.0*
