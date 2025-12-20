"""
Интеграция Gemini Advanced Handler с Telegram ботом
"""

import logging
from typing import Optional, Dict, List
from telegram import Update
from telegram.ext import ContextTypes
from io import BytesIO
import json

from gemini_advanced_handler import GeminiAdvancedHandler

logger = logging.getLogger(__name__)

# Глобальный обработчик
gemini_handler = None


def init_gemini_handler():
    """Инициализация Gemini Advanced Handler"""
    global gemini_handler
    try:
        gemini_handler = GeminiAdvancedHandler()
        logger.info("✅ Gemini Advanced Handler инициализирован для бота")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации Gemini Handler: {e}")
        return False


# ============================================================================
# ОБРАБОТЧИКИ ДЛЯ БОТА
# ============================================================================

async def handle_drawing_analysis(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    image_data: bytes,
    question: str = "Проанализируй чертёж"
) -> None:
    """
    Обработка анализа чертежа в боте

    Использование: /analyze_drawing + фото
    """
    try:
        await update.message.reply_text(
            "🔍 Анализирую чертёж...\n"
            "📐 Проверяю соответствие ГОСТ и СП\n"
            "⏳ Это может занять несколько секунд"
        )

        # Анализируем чертёж
        result = await gemini_handler.analyze_drawing(
            image_data=image_data,
            question=question,
            check_compliance=True
        )

        # Форматируем ответ
        response = f"""📋 **АНАЛИЗ ЧЕРТЕЖА**

📐 **Описание:**
{result.get('analysis', 'Не удалось проанализировать')}

🔧 **Элементы конструкции:**
{chr(10).join(f"• {elem}" for elem in result.get('elements', []))}

📏 **Размеры:**
{chr(10).join(f"• {k}: {v}" for k, v in result.get('measurements', {}).items())}

✅ **Проверка соответствия:**
Статус: {result.get('compliance_check', {}).get('status', 'unknown').upper()}

📚 **Применимые нормативы:**
{chr(10).join(f"• {reg}" for reg in result.get('compliance_check', {}).get('regulations', []))}
"""

        # Если есть нарушения
        violations = result.get('compliance_check', {}).get('violations', [])
        if violations:
            response += f"\n\n⚠️ **Обнаруженные нарушения:**\n"
            response += "\n".join(f"• {v}" for v in violations)

        # Рекомендации
        recommendations = result.get('compliance_check', {}).get('recommendations', [])
        if recommendations:
            response += f"\n\n💡 **Рекомендации:**\n"
            response += "\n".join(f"• {r}" for r in recommendations)

        response += "\n\n_✨ Gemini 2.0 Flash с анализом нормативов_"

        await update.message.reply_text(response, parse_mode="Markdown")

        logger.info("✅ Анализ чертежа отправлен пользователю")

    except Exception as e:
        logger.error(f"❌ Ошибка обработки чертежа: {e}")
        await update.message.reply_text(
            f"❌ Ошибка анализа чертежа: {str(e)}"
        )


async def handle_video_analysis(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    video_data: bytes,
    task: str = "safety_audit"
) -> None:
    """
    Обработка анализа видео в боте

    Использование: /analyze_video + видео
    """
    try:
        task_names = {
            "safety_audit": "аудит безопасности",
            "progress_check": "проверку прогресса",
            "quality_control": "контроль качества"
        }

        await update.message.reply_text(
            f"🎥 Анализирую видео: {task_names.get(task, task)}...\n"
            f"⏳ Обрабатываю... это займёт время"
        )

        # Анализируем видео
        result = await gemini_handler.analyze_video(
            video_data=video_data,
            task=task
        )

        # Форматируем ответ
        response = f"""🎥 **АНАЛИЗ ВИДЕО: {task_names.get(task, task).upper()}**\n\n"""

        if task == "safety_audit":
            violations = result.get('safety_violations', [])
            if violations:
                response += "⚠️ **Обнаруженные нарушения:**\n"
                for v in violations:
                    response += f"• {v.get('time', '??:??')} - {v.get('violation', 'Нарушение')}\n"
            else:
                response += "✅ Нарушений техники безопасности не обнаружено\n"

        elif task == "progress_check":
            response += f"📊 **Статус работ:**\n"
            response += f"• Прогресс: {result.get('progress_percent', 0)}%\n"
            response += f"• Рабочих: {result.get('workers_count', 0)}\n"
            response += f"• Оборудование: {', '.join(result.get('equipment', []))}\n"

        elif task == "quality_control":
            defects = result.get('defects', [])
            if defects:
                response += "⚠️ **Обнаруженные дефекты:**\n"
                response += "\n".join(f"• {d}" for d in defects)
            else:
                response += "✅ Критических дефектов не обнаружено\n"

        response += "\n\n_✨ Gemini 2.0 Flash с анализом видео_"

        await update.message.reply_text(response, parse_mode="Markdown")

        logger.info("✅ Анализ видео отправлен")

    except Exception as e:
        logger.error(f"❌ Ошибка анализа видео: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def handle_voice_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    audio_data: bytes
) -> None:
    """
    Обработка голосового сообщения

    Использование: отправка голосового сообщения
    """
    try:
        await update.message.reply_text("🎤 Обрабатываю голосовую команду...")

        # Обрабатываем аудио
        result = await gemini_handler.analyze_audio(
            audio_data=audio_data,
            task="extract_data"
        )

        # Форматируем ответ
        response = f"""🎤 **ГОЛОСОВАЯ КОМАНДА ОБРАБОТАНА**

📝 **Транскрипция:**
{result.get('transcription', 'Не удалось распознать')}

📊 **Извлечённые данные:**
```json
{json.dumps(result.get('extracted_data', {}), ensure_ascii=False, indent=2)}
```

_✨ Gemini 2.0 Flash с обработкой аудио_"""

        await update.message.reply_text(response, parse_mode="Markdown")

        logger.info("✅ Голосовая команда обработана")

    except Exception as e:
        logger.error(f"❌ Ошибка обработки аудио: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def generate_daily_report_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    photos: List[bytes],
    audio: Optional[bytes] = None
) -> None:
    """
    Генерация ежедневного отчёта

    Использование: /daily_report + фото + аудио (опционально)
    """
    try:
        await update.message.reply_text(
            "📊 Генерирую ежедневный отчёт...\n"
            f"📸 Анализирую {len(photos)} фото\n"
            "⏳ Это займёт время"
        )

        # Генерируем отчёт
        report = await gemini_handler.generate_daily_report(
            photos=photos,
            audio_comments=audio
        )

        # Форматируем отчёт
        response = f"""📊 **ЕЖЕДНЕВНЫЙ ОТЧЁТ О ПРОГРЕССЕ**

📅 **Дата:** {report.get('date', 'Сегодня')}

📝 **Сводка:**
{report.get('summary', '')}

✅ **Выполненные работы:**
"""
        for work in report.get('completed_works', []):
            response += f"• {work.get('work', '')} - {work.get('volume', '')}\n"

        response += f"\n🔄 **Текущие работы:**\n"
        response += "\n".join(f"• {w}" for w in report.get('ongoing_works', []))

        # Проблемы
        issues = report.get('issues', [])
        if issues:
            response += f"\n\n⚠️ **Проблемы:**\n"
            for issue in issues:
                severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                emoji = severity_emoji.get(issue.get('severity', 'low'), '⚪')
                response += f"{emoji} {issue.get('issue', '')}\n"
                response += f"   💡 {issue.get('solution', '')}\n"

        # Безопасность
        safety = report.get('safety', {})
        safety_emoji = {"ok": "✅", "warning": "⚠️", "critical": "🔴"}
        response += f"\n\n🦺 **Безопасность:** {safety_emoji.get(safety.get('status', 'ok'), '✅')}\n"

        # План на завтра
        response += f"\n📋 **План на завтра:**\n"
        response += "\n".join(f"• {p}" for p in report.get('next_day_plan', []))

        response += "\n\n_✨ Gemini 2.0 Flash - автоматический отчёт_"

        await update.message.reply_text(response, parse_mode="Markdown")

        # Отправляем JSON для экспорта
        json_report = json.dumps(report, ensure_ascii=False, indent=2)
        await update.message.reply_document(
            document=BytesIO(json_report.encode()),
            filename=f"report_{report.get('date', 'today')}.json",
            caption="📄 Полный отчёт в JSON формате"
        )

        logger.info("✅ Ежедневный отчёт отправлен")

    except Exception as e:
        logger.error(f"❌ Ошибка генерации отчёта: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


# ============================================================================
# КОМАНДЫ ДЛЯ БОТА
# ============================================================================

async def analyze_drawing_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /analyze_drawing"""
    await update.message.reply_text(
        "📐 **Анализ чертежа**\n\n"
        "Отправь фото чертежа с подписью:\n"
        "`/analyze_drawing Проверь соответствие СП 63.13330`\n\n"
        "Я проанализирую:\n"
        "• Элементы конструкции\n"
        "• Размеры и спецификации\n"
        "• Соответствие ГОСТ/СП\n"
        "• Обнаруженные нарушения\n"
        "• Рекомендации по исправлению",
        parse_mode="Markdown"
    )


async def analyze_video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /analyze_video"""
    await update.message.reply_text(
        "🎥 **Анализ видео**\n\n"
        "Отправь видео с объекта и выбери задачу:\n\n"
        "🦺 `/video_safety` - Аудит безопасности\n"
        "📊 `/video_progress` - Проверка прогресса\n"
        "🔍 `/video_quality` - Контроль качества\n\n"
        "Я найду:\n"
        "• Нарушения техники безопасности\n"
        "• Рабочих без СИЗ\n"
        "• Прогресс работ\n"
        "• Дефекты качества\n"
        "• Временные метки для каждого нарушения",
        parse_mode="Markdown"
    )


async def daily_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /daily_report"""
    await update.message.reply_text(
        "📊 **Ежедневный отчёт**\n\n"
        "Отправь:\n"
        "1️⃣ Несколько фото с объекта\n"
        "2️⃣ Голосовой комментарий (опционально)\n"
        "3️⃣ Команду `/generate_report`\n\n"
        "Я создам:\n"
        "• Анализ выполненных работ\n"
        "• Список проблем и решений\n"
        "• Оценку безопасности\n"
        "• План на следующий день\n"
        "• JSON отчёт для экспорта",
        parse_mode="Markdown"
    )


# ============================================================================
# РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ
# ============================================================================

def register_gemini_handlers(application):
    """Регистрация всех обработчиков Gemini в боте"""
    from telegram.ext import CommandHandler

    # Команды
    application.add_handler(CommandHandler("analyze_drawing", analyze_drawing_command))
    application.add_handler(CommandHandler("analyze_video", analyze_video_command))
    application.add_handler(CommandHandler("daily_report", daily_report_command))

    logger.info("✅ Gemini Advanced обработчики зарегистрированы")
