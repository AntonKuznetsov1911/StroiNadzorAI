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
        description="StroiNadzorAI v3.0 - Professional Construction AI Assistant"
    )

    parser.add_argument(
        "command",
        choices=["bot", "api", "both", "init-db", "migrate"],
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

    elif args.command == "api":
        print("🔧 Starting Admin API...")
        import uvicorn
        uvicorn.run(
            "src.api.main:app",
            host=settings.API_HOST,
            port=settings.API_PORT,
            reload=args.debug,
            log_level=settings.LOG_LEVEL.lower()
        )

    elif args.command == "both":
        print("🚀 Starting Bot and API...")
        # Запускаем оба сервиса параллельно
        import multiprocessing

        def run_bot():
            from src.bot.bot_main import start_bot
            start_bot()

        def run_api():
            import uvicorn
            uvicorn.run(
                "src.api.main:app",
                host=settings.API_HOST,
                port=settings.API_PORT,
                log_level=settings.LOG_LEVEL.lower()
            )

        bot_process = multiprocessing.Process(target=run_bot)
        api_process = multiprocessing.Process(target=run_api)

        bot_process.start()
        api_process.start()

        try:
            bot_process.join()
            api_process.join()
        except KeyboardInterrupt:
            print("\n⏹️  Stopping services...")
            bot_process.terminate()
            api_process.terminate()

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
