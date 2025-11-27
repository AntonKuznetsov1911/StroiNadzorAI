# Email Templates

Профессиональные HTML шаблоны для email уведомлений StroiNadzorAI.

## Структура

```
templates/
└── email/
    ├── base.html                      # Базовый шаблон (header, footer, стили)
    ├── defect_report.html             # Отчет о дефекте
    ├── daily_summary.html             # Ежедневная сводка
    └── premium_notification.html      # Уведомления о Premium подписке
```

## Используемые технологии

- **Jinja2** - шаблонизатор
- **HTML/CSS** - адаптивный дизайн
- **Inline CSS** - для совместимости с почтовыми клиентами

## Шаблоны

### 1. base.html

Базовый шаблон со стилями и структурой письма.

**Блоки:**
- `content` - основное содержимое письма

**Стили:**
- Адаптивный дизайн (max-width: 600px)
- Брендированный header с логотипом
- Категоризированные badges (critical, warning, info, success)
- Таблицы со стилями
- Кнопки с hover эффектами

### 2. defect_report.html

Отчет о выявленном дефекте.

**Переменные:**
- `defect_type` - тип дефекта
- `severity` - критичность (CRITICAL, HIGH, MEDIUM, LOW)
- `description` - описание проблемы
- `location` - местоположение (опционально)
- `date` - дата обнаружения
- `recommendations` - рекомендации (опционально)
- `normatives` - список нормативов (опционально)
- `has_attachment` - есть ли PDF вложение

**Пример использования:**

```python
await email_service.send_defect_report(
    to="engineer@example.com",
    defect_type="Трещина в несущей стене",
    severity="CRITICAL",
    description="Обнаружена вертикальная трещина шириной 0,5 мм...",
    location="1 этаж, ось А-Б",
    recommendations="Требуется немедленное обследование конструктором...",
    normatives=["СП 63.13330.2018 п.8.2.2", "СП 13-102-2003"],
    pdf_path="/path/to/report.pdf"
)
```

### 3. daily_summary.html

Ежедневная сводка по использованию системы.

**Переменные:**
- `date` - дата отчета
- `stats` - словарь со статистикой:
  - `total_requests` - всего запросов
  - `photo_requests` - анализов фото
  - `text_requests` - текстовых вопросов
  - `voice_requests` - голосовых сообщений
  - `new_users` - новых пользователей
  - `critical_defects` - критических дефектов
- `top_defects` - топ дефектов (опционально)
- `active_users` - активные пользователи (опционально)

**Пример использования:**

```python
await email_service.send_daily_summary(
    to="admin@example.com",
    stats={
        'total_requests': 156,
        'photo_requests': 45,
        'text_requests': 89,
        'voice_requests': 22,
        'new_users': 5,
        'critical_defects': 3
    },
    top_defects=[
        {'type': 'Трещины в бетоне', 'count': 12},
        {'type': 'Протечки кровли', 'count': 8}
    ]
)
```

### 4. premium_notification.html

Уведомления о статусе Premium подписки.

**Переменные:**
- `action` - тип действия:
  - `activated` - подписка активирована
  - `expiring` - подписка скоро истекает
  - `expired` - подписка истекла
- `plan_type` - тип плана (monthly, yearly)
- `expiry_date` - дата истечения
- `days_left` - дней до истечения
- `expired_date` - дата истечения (прошедшая)
- `renewal_link` - ссылка на продление

**Примеры использования:**

```python
# Активация подписки
await email_service.send_premium_notification(
    to="user@example.com",
    action="activated",
    plan_type="monthly",
    expiry_date="01.01.2026"
)

# Подписка истекает
await email_service.send_premium_notification(
    to="user@example.com",
    action="expiring",
    days_left=3,
    renewal_link="https://t.me/YourBot"
)

# Подписка истекла
await email_service.send_premium_notification(
    to="user@example.com",
    action="expired",
    expired_date="28.11.2025",
    renewal_link="https://t.me/YourBot"
)
```

## Кастомизация

### Цвета бренда

В `base.html` можно изменить основные цвета:

```css
.header h1 { color: #2196F3; }           /* Основной цвет заголовка */
border-bottom: 3px solid #2196F3;       /* Линия под header */
.badge-critical { background-color: #f44336; }  /* Критичный */
.badge-warning { background-color: #ff9800; }   /* Важно */
.badge-info { background-color: #2196F3; }      /* Информация */
.badge-success { background-color: #4CAF50; }   /* Успех */
```

### Добавление нового шаблона

1. Создайте файл в `templates/email/`
2. Унаследуйтесь от `base.html`
3. Переопределите блок `content`
4. Добавьте метод в `EmailService`

Пример:

```html
{% extends "email/base.html" %}

{% block content %}
<h2>Ваш заголовок</h2>
<p>{{ custom_content }}</p>
{% endblock %}
```

## Тестирование

Для тестирования шаблонов без отправки email:

```python
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

template_dir = Path("templates")
env = Environment(loader=FileSystemLoader(str(template_dir)))

template = env.get_template('email/defect_report.html')
html = template.render(
    title="Test",
    defect_type="Тест",
    severity="CRITICAL",
    description="Тестовое описание",
    date="28.11.2025"
)

# Сохранить в файл для просмотра
with open('test.html', 'w', encoding='utf-8') as f:
    f.write(html)
```

## Совместимость

Шаблоны протестированы и работают в:
- ✅ Gmail
- ✅ Outlook
- ✅ Apple Mail
- ✅ Thunderbird
- ✅ Мобильные клиенты (iOS Mail, Android Gmail)

Используются inline стили для максимальной совместимости.
