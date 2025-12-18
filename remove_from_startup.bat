@echo off
chcp 65001 > nul
echo ========================================
echo   Удаление бота из автозагрузки
echo ========================================
echo.

set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\TehNadzor_Bot.vbs"

if exist "%SHORTCUT_PATH%" (
    del "%SHORTCUT_PATH%"
    echo ✓ Бот удален из автозагрузки!
    echo.
    echo Бот больше не будет запускаться автоматически.
    echo.
) else (
    echo ℹ Бот не найден в автозагрузке.
    echo.
)

echo Нажмите любую клавишу для выхода...
pause > nul
