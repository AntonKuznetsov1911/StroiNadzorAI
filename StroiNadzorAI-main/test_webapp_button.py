"""
Тестовый скрипт для проверки кнопки WebApp
"""
import os
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
import asyncio

load_dotenv()

async def test_webapp_button():
    """Отправить сообщение с кнопкой WebApp"""
    bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))

    # Получаем информацию о боте
    bot_info = await bot.get_me()
    print(f"Бот: @{bot_info.username}")
    print(f"ID: {bot_info.id}")

    # Получаем обновления (чтобы найти chat_id)
    updates = await bot.get_updates(limit=1)

    if not updates:
        print("\nОШИБКА: Не найдены сообщения от пользователей.")
        print("Отправьте любое сообщение боту в Telegram и запустите скрипт снова.")
        return

    chat_id = updates[-1].message.chat_id
    print(f"\nОтправляю тестовое сообщение в чат: {chat_id}")

    # Создаем кнопку с WebApp
    keyboard = [
        [InlineKeyboardButton("🏗️ Открыть полную версию", web_app=WebAppInfo(url="https://antonkuznetsov1911.github.io/StroiNadzorAI/"))],
        [InlineKeyboardButton("📚 Список нормативов", callback_data="regulations")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем сообщение
    message = await bot.send_message(
        chat_id=chat_id,
        text="🧪 **Тест кнопки WebApp**\n\nНажмите кнопку 'Открыть полную версию' ниже.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

    print(f"✅ Сообщение отправлено! ID: {message.message_id}")
    print("\nПроверьте Telegram - должна появиться кнопка WebApp")

if __name__ == "__main__":
    asyncio.run(test_webapp_button())
