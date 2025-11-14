' Запуск Telegram бота ТехНадзор в фоновом режиме (без окна)
Set WshShell = CreateObject("WScript.Shell")

' Путь к папке с ботом
botPath = "C:\Users\PC\StroiNadzor\telegram_bot"

' Команда запуска бота
command = "cmd /c cd /d """ & botPath & """ && python bot.py"

' Запуск в фоновом режиме (0 = скрытое окно)
WshShell.Run command, 0, False

' Вывод уведомления (опционально)
' WshShell.Popup "Telegram бот ТехНадзор запущен!", 3, "Автозапуск", 64
