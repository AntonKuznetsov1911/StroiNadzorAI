#!/bin/bash

# StroiNadzorAI Quick Start Script
# Быстрый запуск проекта

set -e

echo "🏗️  StroiNadzorAI v3.0 - Quick Start"
echo "===================================="
echo ""

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен!"
    echo "Установите Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен!"
    echo "Установите Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Проверка .env файла
if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден!"
    echo "Создаю .env из .env.example..."
    cp .env.example .env
    echo "✅ Файл .env создан"
    echo ""
    echo "⚠️  ВАЖНО: Отредактируйте .env и добавьте:"
    echo "   - TELEGRAM_BOT_TOKEN"
    echo "   - OPENAI_API_KEY"
    echo ""
    read -p "Продолжить без настройки .env? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Отменено. Настройте .env и запустите снова."
        exit 1
    fi
fi

# Запуск Docker Compose
echo "🚀 Запуск сервисов..."
docker-compose up -d

echo ""
echo "✅ Сервисы запущены!"
echo ""
echo "📊 Статус сервисов:"
docker-compose ps
echo ""
echo "🔗 Доступные endpoints:"
echo "   - Telegram Bot: работает в фоне"
echo "   - Admin API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo ""
echo "📝 Просмотр логов:"
echo "   docker-compose logs -f bot"
echo ""
echo "🛑 Остановка сервисов:"
echo "   docker-compose down"
echo ""
echo "✨ Готово! Бот запущен и готов к работе!"
