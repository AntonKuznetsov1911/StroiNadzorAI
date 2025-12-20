# -*- coding: utf-8 -*-
"""
Скрипт для добавления кликабельных ссылок на нормативы в bot.py
"""

import re

# Читаем файл
with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем старую структуру REGULATIONS на новую с URL
old_regs_pattern = r'# База нормативов \(расширенная\)\nREGULATIONS = \{[^}]+\}'

new_regs = '''# База нормативов с URL-ссылками на первоисточники
REGULATIONS = {
    "СП 63.13330.2018": {
        "title": "Бетонные и железобетонные конструкции",
        "url": "https://docs.cntd.ru/document/554403082"
    },
    "СП 28.13330.2017": {
        "title": "Защита от коррозии",
        "url": "https://docs.cntd.ru/document/456054198"
    },
    "СП 13-102-2003": {
        "title": "Правила обследования конструкций",
        "url": "https://docs.cntd.ru/document/1200035173"
    },
    "ГОСТ 23055-78": {
        "title": "Контроль сварки металлов",
        "url": "https://docs.cntd.ru/document/1200012783"
    },
    "СП 22.13330.2016": {
        "title": "Основания зданий и сооружений",
        "url": "https://docs.cntd.ru/document/456054206"
    },
    "СП 70.13330.2012": {
        "title": "Несущие и ограждающие конструкции",
        "url": "https://docs.cntd.ru/document/1200092705"
    },
    "ГОСТ 10180-2012": {
        "title": "Методы определения прочности бетона",
        "url": "https://docs.cntd.ru/document/1200100908"
    },
    "СП 50-101-2004": {
        "title": "Проектирование фундаментов",
        "url": "https://docs.cntd.ru/document/1200035505"
    },
    "СП 48.13330.2019": {
        "title": "Организация строительства",
        "url": "https://docs.cntd.ru/document/564477582"
    },
    "СП 17.13330.2017": {
        "title": "Кровли",
        "url": "https://docs.cntd.ru/document/456054206"
    },
    "СП 50.13330.2012": {
        "title": "Тепловая защита зданий",
        "url": "https://docs.cntd.ru/document/1200095525"
    },
    "СП 60.13330.2020": {
        "title": "Отопление, вентиляция и кондиционирование",
        "url": "https://docs.cntd.ru/document/573659347"
    },
    "СП 71.13330.2017": {
        "title": "Изоляционные и отделочные покрытия",
        "url": "https://docs.cntd.ru/document/456054235"
    },
}'''

content = re.sub(old_regs_pattern, new_regs, content, flags=re.DOTALL)

# Заменяем функцию regulations_command
old_reg_func = r'async def regulations_command.*?await update\.message\.reply_text\(text, parse_mode=\'Markdown\'\)'

new_reg_func = '''async def regulations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /regulations с кликабельными ссылками на нормативы"""
    text = "📚 **Доступные нормативы:**\\n\\n"
    text += "_Нажмите на название, чтобы открыть полный текст документа_\\n\\n"

    for code, data in REGULATIONS.items():
        title = data['title']
        url = data['url']
        # Используем Markdown ссылки в формате [текст](URL)
        text += f"📄 [{code}]({url})\\n   _{title}_\\n\\n"

    text += "\\n💡 Задайте вопрос по любому нормативу!"

    await update.message.reply_text(text, parse_mode='Markdown', disable_web_page_preview=True)'''

content = re.sub(old_reg_func, new_reg_func, content, flags=re.DOTALL)

# Заменяем логику в handle_text для упомянутых нормативов
old_mentioned = r'        # Определяем упомянутые нормативы\s+mentioned_regs = \[\]\s+for reg_code in REGULATIONS\.keys\(\):\s+if reg_code in answer:\s+mentioned_regs\.append\(reg_code\)\s+# Формируем ответ\s+result = f"💬 \*\*Ответ\*\* \(Claude 3\.5 Haiku\):\\\\n\\\\n\{answer\}\\\\n\\\\n"\s+if mentioned_regs:\s+result \+= "📚 \*\*Упомянутые нормативы:\*\*\\\\n"\s+for reg in mentioned_regs:\s+result \+= f"• \{reg\}\\\\n"\s+result \+= "\\\\n"'

new_mentioned = '''        # Определяем упомянутые нормативы
        mentioned_regs = []
        for reg_code in REGULATIONS.keys():
            if reg_code in answer:
                mentioned_regs.append(reg_code)

        # Формируем ответ
        result = f"💬 **Ответ** (Claude 3.5 Haiku):\\n\\n{answer}\\n\\n"

        if mentioned_regs:
            result += "📚 **Упомянутые нормативы (нажмите, чтобы открыть):**\\n"
            for reg in mentioned_regs:
                title = REGULATIONS[reg]['title']
                url = REGULATIONS[reg]['url']
                result += f"• [{reg}]({url}) - {title}\\n"
            result += "\\n"'''

content = re.sub(old_mentioned, new_mentioned, content, flags=re.DOTALL)

# Добавляем disable_web_page_preview в handle_text если его нет
if "disable_web_page_preview=True" not in content:
    content = content.replace(
        "await update.message.reply_text(result, parse_mode='Markdown')",
        "await update.message.reply_text(result, parse_mode='Markdown', disable_web_page_preview=True)",
        1  # Заменяем только первое вхождение в handle_text
    )

# Записываем обратно
with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Успешно добавлены кликабельные ссылки на нормативы!")
print("📄 Обновлены:")
print("   - REGULATIONS (добавлены URL)")
print("   - regulations_command (кликабельные ссылки)")
print("   - handle_text (кликабельные упомянутые нормативы)")
