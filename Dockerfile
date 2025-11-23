# StroiNadzorAI Dockerfile
FROM python:3.11-slim

# Метаданные
LABEL maintainer="StroiNadzorAI Team"
LABEL description="StroiNadzorAI - AI Construction Supervisor Bot"
LABEL version="3.0.0"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-rus \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем requirements
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код
COPY . .

# Создаем необходимые директории
RUN mkdir -p /app/logs /app/uploads /app/uploads/reports

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Порт (для FastAPI админки)
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Запуск
CMD ["python", "-m", "src.bot.bot_main"]
