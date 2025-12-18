"""
Скрипт для обновления URL веб-приложения в Telegram боте
"""
import sys

def update_webapp_url(new_url: str):
    """Обновить URL веб-приложения в bot.py"""
    bot_file = "bot.py"

    # Читаем текущий файл
    with open(bot_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Старый URL
    old_url = "https://antonkuznetsov1911.github.io/StroiNadzorAI/"

    # Проверяем, что URL найден
    if old_url not in content:
        print(f"❌ Старый URL не найден в файле!")
        print(f"   Искал: {old_url}")
        return False

    # Заменяем URL
    new_content = content.replace(old_url, new_url)

    # Сохраняем файл
    with open(bot_file, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ URL успешно обновлен!")
    print(f"   Старый: {old_url}")
    print(f"   Новый:  {new_url}")
    print()
    print("🔄 Не забудьте перезапустить бота:")
    print("   1. Остановите текущий процесс")
    print("   2. Запустите: python bot.py")

    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python update_webapp_url.py <новый_url>")
        print()
        print("Пример:")
        print('  python update_webapp_url.py "https://stroinadzor-production.up.railway.app/webapp"')
        sys.exit(1)

    new_url = sys.argv[1]

    # Проверяем, что URL заканчивается на /webapp
    if not new_url.endswith("/webapp"):
        print("⚠️ URL должен заканчиваться на /webapp")
        print(f"   Добавляю /webapp к URL...")
        new_url = new_url.rstrip("/") + "/webapp"

    update_webapp_url(new_url)
