"""
Скрипт миграции данных из JSON файлов в PostgreSQL
Запускайте ПОСЛЕ создания PostgreSQL на Railway
"""

import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Импорт database модуля
from database import init_db, save_message

async def migrate_json_to_postgres():
    """
    Миграция всех JSON файлов в PostgreSQL
    """
    print("🚀 Начинаем миграцию JSON → PostgreSQL")

    # Проверяем DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL не найден!")
        print("Создайте PostgreSQL на Railway:")
        print("1. Откройте https://railway.app")
        print("2. Выберите ваш проект StroiNadzorAI")
        print("3. New → Database → Add PostgreSQL")
        print("4. После создания скопируйте DATABASE_URL в .env")
        return False

    # Инициализируем БД
    print("📊 Инициализация PostgreSQL...")
    success = await init_db()
    if not success:
        print("❌ Не удалось инициализировать PostgreSQL")
        return False

    print("✅ PostgreSQL готов")

    # Ищем JSON файлы
    history_dir = Path("user_conversations")
    if not history_dir.exists():
        print("⚠️ Папка user_conversations не найдена. Нет данных для миграции.")
        return True

    json_files = list(history_dir.glob("user_*.json"))
    if not json_files:
        print("⚠️ JSON файлы не найдены. Нет данных для миграции.")
        return True

    print(f"📁 Найдено {len(json_files)} файлов для миграции")

    # Мигрируем каждый файл
    total_messages = 0
    migrated_users = 0

    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            user_id = data.get('user_id')
            messages = data.get('messages', [])

            if not user_id or not messages:
                print(f"⚠️ Пропускаем {json_file.name}: нет данных")
                continue

            print(f"  📝 Мигрируем user_{user_id}: {len(messages)} сообщений...")

            # Сохраняем каждое сообщение
            for msg in messages:
                role = msg.get('role')
                content = msg.get('content')
                image_analyzed = msg.get('image_analyzed', False)
                tags = msg.get('tags', [])

                if role and content:
                    await save_message(user_id, role, content, image_analyzed, tags)
                    total_messages += 1

            migrated_users += 1
            print(f"  ✅ User {user_id} мигрирован")

        except Exception as e:
            print(f"❌ Ошибка при миграции {json_file.name}: {e}")

    print("\n🎉 МИГРАЦИЯ ЗАВЕРШЕНА!")
    print(f"✅ Мигрировано пользователей: {migrated_users}")
    print(f"✅ Всего сообщений: {total_messages}")
    print("\n💡 Теперь можно:")
    print("   1. Закоммитить и запушить изменения")
    print("   2. Railway автоматически развернет обновление")
    print("   3. Бот начнет использовать PostgreSQL")

    return True


if __name__ == "__main__":
    asyncio.run(migrate_json_to_postgres())
