@echo off
chcp 65001 > nul
echo ========================================
echo   Запуск Telegram бота СтройНадзорAI
echo ========================================
echo.
cd /d "%~dp0"
python bot.py
pause
