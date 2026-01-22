# Быстрый старт

Запуск СтройНадзорAI за 5 минут.

---

## 1. Требования

- Python 3.9+
- Telegram Bot Token (от [@BotFather](https://t.me/BotFather))
- Минимум один AI API ключ (xAI, Anthropic, OpenAI или Google)

---

## 2. Установка

```bash
# Клонирование
git clone https://github.com/AntonKuznetsov1911/StroiNadzorAI.git
cd StroiNadzorAI

# Виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Зависимости
pip install -r requirements.txt
```

---

## 3. Настройка

Создайте файл `.env`:

```env
# Обязательно
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# AI модели (минимум одна)
XAI_API_KEY=your_xai_key          # Grok (основной)
ANTHROPIC_API_KEY=your_claude_key  # Claude (fallback)

# Опционально (расширенные функции)
OPENAI_API_KEY=your_openai_key     # DALL-E 3 + Whisper
GOOGLE_API_KEY=your_google_key     # Gemini Vision + Live API
```

---

## 4. Запуск

```bash
python bot.py
```

Бот запустится и будет отвечать в Telegram.

---

## 5. Проверка работы

Откройте бота в Telegram и отправьте:

```
/start
```

Должно появиться приветственное сообщение с кнопками меню.

---

## Что дальше?

| Действие | Команда/документ |
|----------|------------------|
| Список команд | `/help` |
| Калькуляторы | `/calculators` |
| Нормативы | `/regulations` |
| Развёртывание на сервере | [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) |
| Полное описание | [PROJECT_DESCRIPTION.md](PROJECT_DESCRIPTION.md) |

---

## Возможные проблемы

### Ошибка: `ModuleNotFoundError`
```bash
pip install -r requirements.txt
```

### Ошибка: `TELEGRAM_BOT_TOKEN not set`
Проверьте файл `.env` — токен должен быть без кавычек.

### Ошибка: `XAI_API_KEY not set`
Добавьте хотя бы один AI ключ в `.env`.

### Бот не отвечает
1. Проверьте логи в консоли
2. Убедитесь что токен правильный
3. Попробуйте `/start` заново

---

*СтройНадзорAI v5.0*
