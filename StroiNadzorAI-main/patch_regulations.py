#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Добавление кликабельных ссылок на нормативы"""

import sys

# Новая структура REGULATIONS
new_regulations = '''# База нормативов с URL-ссылками на первоисточники
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

# Читаем bot.py
with open('bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Находим и заменяем REGULATIONS
start = None
end = None
for i, line in enumerate(lines):
    if '# База нормативов' in line:
        start = i
    if start is not None and line.strip() == '}' and i > start:
        end = i
        break

if start is None or end is None:
    sys.stderr.write("ERROR: Could not find REGULATIONS section\n")
    sys.exit(1)

# Заменяем
new_lines = lines[:start] + [new_regulations + '\n\n'] + lines[end+1:]

# Теперь обновляем regulations_command
output = []
i = 0
while i < len(new_lines):
    line = new_lines[i]

    # Ищем regulations_command
    if 'async def regulations_command' in line:
        # Добавляем новую версию функции
        output.append('async def regulations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):\n')
        output.append('    """Команда /regulations с кликабельными ссылками на нормативы"""\n')
        output.append('    text = "📚 **Доступные нормативы:**\\n\\n"\n')
        output.append('    text += "_Нажмите на название, чтобы открыть полный текст документа_\\n\\n"\n')
        output.append('\n')
        output.append('    for code, data in REGULATIONS.items():\n')
        output.append('        title = data[\'title\']\n')
        output.append('        url = data[\'url\']\n')
        output.append('        text += f"📄 [{code}]({url})\\n   _{title}_\\n\\n"\n')
        output.append('\n')
        output.append('    text += "\\n💡 Задайте вопрос по любому нормативу!"\n')
        output.append('\n')
        output.append('    await update.message.reply_text(text, parse_mode=\'Markdown\', disable_web_page_preview=True)\n')
        output.append('\n')

        # Пропускаем старую функцию до следующей функции
        i += 1
        while i < len(new_lines) and not ('async def' in new_lines[i] and 'regulations_command' not in new_lines[i]):
            i += 1
        continue

    output.append(line)
    i += 1

# Теперь обновляем упомянутые нормативы в handle_text
final_output = []
i = 0
while i < len(output):
    line = output[i]

    # Ищем секцию с упомянутыми нормативами
    if 'if mentioned_regs:' in line and 'Упомянутые нормативы' in ''.join(output[max(0,i-5):i+10]):
        final_output.append(line)  # if mentioned_regs:
        i += 1
        # Пропускаем старый код до result += "\n"
        while i < len(output):
            if 'result += "\\n"' in output[i] and 'for reg in mentioned_regs' in ''.join(output[max(0,i-5):i]):
                # Вставляем новый код
                final_output.append('            result += "📚 **Упомянутые нормативы (нажмите, чтобы открыть):**\\n"\n')
                final_output.append('            for reg in mentioned_regs:\n')
                final_output.append('                title = REGULATIONS[reg][\'title\']\n')
                final_output.append('                url = REGULATIONS[reg][\'url\']\n')
                final_output.append('                result += f"• [{reg}]({url}) - {title}\\n"\n')
                final_output.append('            result += "\\n"\n')
                i += 1
                break
            i += 1
        continue

    # Добавляем disable_web_page_preview в handle_text
    if 'await update.message.reply_text(result, parse_mode=\'Markdown\')' in line and 'handle_text' in ''.join(output[max(0,i-50):i]):
        line = line.replace(
            "await update.message.reply_text(result, parse_mode='Markdown')",
            "await update.message.reply_text(result, parse_mode='Markdown', disable_web_page_preview=True)"
        )

    final_output.append(line)
    i += 1

# Записываем результат
with open('bot.py', 'w', encoding='utf-8') as f:
    f.writelines(final_output)

print("SUCCESS: Added clickable links to regulations!")
