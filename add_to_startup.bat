@echo off
chcp 65001 > nul
echo ========================================
echo   Добавление бота в автозагрузку
echo ========================================
echo.

set "SCRIPT_PATH=%~dp0start_bot_silent.vbs"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\TehNadzor_Bot.vbs"

echo Копирую скрипт в автозагрузку...
copy "%SCRIPT_PATH%" "%SHORTCUT_PATH%" > nul

if %errorlevel% == 0 (
    echo.
    echo ✓ Успешно! Бот добавлен в автозагрузку!
    echo.
    echo Бот будет автоматически запускаться при входе в Windows.
    echo.
) else (
    echo.
    echo ✗ Ошибка при копировании файла.
    echo.
)

echo Нажмите любую клавишу для выхода...
pause > nul
