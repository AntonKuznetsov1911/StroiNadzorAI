# 🏗️ StroiNadzorAI v3.0 - Профессиональный Строительный AI-Помощник

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**StroiNadzorAI** - это продвинутый AI-консультант по строительным нормативам России на базе Claude AI (Anthropic) с полной интеграцией Telegram Bot.

## 🌟 Основные возможности

### 🤖 Telegram Bot
- **📸 Анализ фотографий дефектов** с помощью Claude Sonnet 4.5 Vision
- **💬 Консультации по нормативам** (СП, ГОСТ, СНиП) с RAG
- **🧠 Экспертная система** - виртуальный Главный Прораб с 25-летним опытом
- **📄 Генерация PDF отчетов** профессионального качества
- **📍 Геолокация объектов** и привязка дефектов к карте
- **⚡ Стриминг ответов** для мгновенной обратной связи
- **🔍 RAG система** с векторной БД ChromaDB для точных ответов
- **💭 Context Memory** - запоминание истории разговоров

### 💾 Базовые функции
- **PostgreSQL** база данных с полной историей запросов
- **Redis** кеширование и контекст разговоров
- **Rate Limiting** защита от спама и злоупотреблений
- **Многопользовательские проекты** для командной работы
- **Система ролей** (User, Premium, Admin)
- **Celery** фоновые задачи (PDF, email, аналитика)

### 🔧 DevOps & Production Ready
- **Docker & Docker Compose** для легкого развертывания
- **Kubernetes (K8s)** манифесты с auto-scaling
- **Prometheus** мониторинг метрик
- **Structured Logging** с ротацией
- **Автоматические тесты** (pytest)

## 📚 База нормативов (13 документов)

**Основные нормативы:**
- СП 63.13330.2018 - Бетонные и железобетонные конструкции
- СП 28.13330.2017 - Защита от коррозии
- СП 13-102-2003 - Правила обследования конструкций
- СП 22.13330.2016 - Основания зданий и сооружений
- СП 70.13330.2012 - Несущие и ограждающие конструкции

**Специализированные:**
- СП 17.13330.2017 - Кровли
- СП 50.13330.2012 - Тепловая защита зданий
- СП 60.13330.2020 - Отопление, вентиляция и кондиционирование
- СП 71.13330.2017 - Изоляционные и отделочные покрытия

**ГОСТы:**
- ГОСТ 23055-78 - Контроль сварки металлов
- ГОСТ 10180-2012 - Методы определения прочности бетона

## 🚀 Быстрый старт

### Требования
- Python 3.11+
- Docker & Docker Compose (опционально)
- PostgreSQL 15+ (или Docker)
- Redis 7+ (или Docker)
- Tesseract OCR (для распознавания текста)

### Установка через Docker (Рекомендуется)

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/yourusername/StroiNadzorAI.git
cd StroiNadzorAI

# 2. Создайте .env файл
cp .env.example .env
# Отредактируйте .env и добавьте TELEGRAM_BOT_TOKEN и ANTHROPIC_API_KEY

# 3. Запустите все сервисы
docker-compose up -d

# 4. Проверьте статус
docker-compose ps

# 5. Просмотр логов
docker-compose logs -f bot
```

Бот запущен! 🎉

### Установка без Docker

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/yourusername/StroiNadzorAI.git
cd StroiNadzorAI

# 2. Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# 3. Установите зависимости
pip install -r requirements.txt

# 4. Установите системные зависимости
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr tesseract-ocr-rus poppler-utils

# macOS:
brew install tesseract tesseract-lang poppler

# 5. Настройте PostgreSQL и Redis
# Создайте БД: stroinadzor
# Запустите Redis на порту 6379

# 6. Создайте .env файл
cp .env.example .env
# Отредактируйте .env

# 7. Инициализируйте базу данных
python -c "from src.database import init_db; init_db()"

# 8. Запустите бота
python -m src.bot.bot_main
```

## 📖 Использование

### Команды бота

```
/start - Начало работы
/help - Подробная справка
/regulations - Список нормативов
/stats - Ваша статистика
/projects - Управление проектами
/report - Создать PDF отчет
```

### Примеры использования

**1. Анализ фотографии:**
```
Отправьте фото дефекта → Получите анализ с рекомендациями
```

**2. Вопрос по нормативам:**
```
Вопрос: Какая допустимая ширина трещины в несущей стене?
Ответ: Подробный ответ со ссылками на СП
```

**3. Голосовое сообщение:**
```
Запишите голосовое → Автоматическое распознавание → Ответ
```

**4. PDF Отчет:**
```
Проанализируйте дефект → /report → Скачайте PDF
```

## 🏗️ Архитектура проекта

```
StroiNadzorAI/
├── src/
│   ├── bot/                    # Telegram Bot
│   │   ├── bot_main.py
│   │   └── handlers.py
│   ├── services/               # Business Logic
│   │   ├── claude_service.py   # Claude AI integration
│   │   ├── vector_service.py   # RAG with ChromaDB
│   │   ├── context_service.py  # Conversation memory
│   │   ├── pdf_service.py
│   │   ├── payment_service.py
│   │   └── rate_limiter.py
│   ├── database/               # Database Models
│   │   ├── models.py
│   │   ├── session.py
│   │   └── base.py
│   ├── cache/                  # Redis Cache
│   │   └── redis_cache.py
│   ├── monitoring/             # Prometheus metrics
│   │   └── metrics.py
│   ├── tasks/                  # Celery background tasks
│   │   └── background_tasks.py
│   └── utils/                  # Utilities
│       ├── helpers.py
│       └── logger.py
├── data/                       # Knowledge Base
│   └── construction_knowledge.py  # 1000+ lines of СП/ГОСТ/СНиП
├── config/                     # Configuration
│   └── settings.py
├── k8s/                        # Kubernetes manifests
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── hpa.yaml
│   └── configmap.yaml
├── tests/                      # Tests
│   ├── unit/
│   └── integration/
├── logs/                       # Logs
├── uploads/                    # User uploads
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## 🔧 Конфигурация

### Основные переменные окружения

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_token_here
USE_WEBHOOK=False

# Anthropic Claude AI
ANTHROPIC_API_KEY=your_api_key_here
CLAUDE_MODEL=claude-sonnet-4-5-20250929
CLAUDE_MAX_TOKENS=4000

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/db

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Rate Limiting
RATE_LIMIT_REQUESTS=50
RATE_LIMIT_PREMIUM_REQUESTS=200

# Features
ENABLE_PDF_REPORTS=True
ENABLE_STREAMING=True
ENABLE_GEOLOCATION=True
```

Полный список переменных см. в [.env.example](.env.example)

## 📊 Мониторинг

### Prometheus метрики

Бот экспортирует метрики для Prometheus:
- Количество запросов по типам
- Время обработки запросов
- Использование Claude API
- Ошибки и исключения

Метрики доступны для сбора Prometheus.

## 🧪 Тестирование

```bash
# Запустить все тесты
pytest

# С coverage
pytest --cov=src --cov-report=html

# Только unit тесты
pytest tests/unit/
```

## 🤝 Contributing

Мы приветствуем вклад в проект!

1. Fork проект
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📝 License

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE)

## 📞 Поддержка

- 📧 Email: support@stroinadzor.ai
- 💬 Telegram: @stroinadzor_support
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/StroiNadzorAI/issues)

---

**Версия:** 3.0.0
**Дата:** Ноябрь 2025
**Статус:** ✅ Production Ready

Made with ❤️ for the construction industry
