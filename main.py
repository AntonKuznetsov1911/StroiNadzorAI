#!/usr/bin/env python3
"""
StroiNadzorAI - Main Entry Point
Точка входа для запуска приложения
"""

import sys
import argparse
import asyncio
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import setup_logging
from config.settings import settings


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description="StroiNadzorAI v3.0 - Telegram Bot Construction AI Assistant"
    )

    parser.add_argument(
        "command",
        choices=["bot", "init-db", "migrate"],
        help="Команда для выполнения"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Включить debug режим"
    )

    args = parser.parse_args()

    # Настройка логирования
    setup_logging()

    if args.command == "bot":
        print("🤖 Starting Telegram Bot...")
        from src.bot.bot_main import start_bot
        start_bot()

    elif args.command == "init-db":
        print("💾 Initializing database...")
        from src.database import init_db
        init_db()
        print("✅ Database initialized!")

    elif args.command == "migrate":
        print("🔄 Running database migrations...")
        import subprocess
        subprocess.run(["alembic", "upgrade", "head"])
        print("✅ Migrations completed!")


if __name__ == "__main__":
    main()
