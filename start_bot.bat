@echo off
chcp 65001 > nul
echo ========================================
echo   Запуск Telegram бота ТехНадзор
echo ========================================
echo.
cd /d "%~dp0"
python bot.py
pause
