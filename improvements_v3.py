"""
Модуль улучшений v3.0 для СтройНадзорAI
Интерактивные кнопки, навигация, калькуляторы
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# ========================================
# 1. ИНТЕРАКТИВНЫЕ КНОПКИ ПОД ОТВЕТАМИ
# ========================================

def create_answer_buttons(context_data=None):
    """
    Создать интерактивные кнопки для ответа

    Args:
        context_data: dict с контекстом (упомянутые нормативы, теги и т.д.)

    Returns:
        InlineKeyboardMarkup
    """
    buttons = [
        [
            InlineKeyboardButton("🔍 Уточнить", callback_data="clarify"),
            InlineKeyboardButton("💡 Пример", callback_data="example")
        ],
        [
            InlineKeyboardButton("📚 Нормативы", callback_data="show_regulations"),
            InlineKeyboardButton("🧮 Калькулятор", callback_data="calculator")
        ],
        [
            InlineKeyboardButton("📎 Экспорт PDF", callback_data="export_pdf"),
            InlineKeyboardButton("💾 Сохранить", callback_data="save_query")
        ]
    ]

    return InlineKeyboardMarkup(buttons)


def create_quick_actions_menu():
    """
    Постоянное меню быстрых действий
    """
    buttons = [
        [
            InlineKeyboardButton("❓ Задать вопрос", callback_data="ask_question"),
            InlineKeyboardButton("📸 Загрузить фото", callback_data="upload_photo")
        ],
        [
            InlineKeyboardButton("📚 Нормативы", callback_data="regulations_menu"),
            InlineKeyboardButton("🧮 Калькуляторы", callback_data="calculators_menu")
        ],
        [
            InlineKeyboardButton("💾 Мои запросы", callback_data="saved_queries"),
            InlineKeyboardButton("📊 Статистика", callback_data="my_stats")
        ]
    ]

    return InlineKeyboardMarkup(buttons)


# ========================================
# 2. КОНТЕКСТНЫЕ ПОДСКАЗКИ
# ========================================

def get_contextual_suggestions(question, history=None):
    """
    Генерация контекстных подсказок на основе вопроса

    Args:
        question: str - вопрос пользователя
        history: list - история диалога

    Returns:
        list of str - варианты уточнений
    """
    suggestions = []

    # Если вопрос короткий (< 10 символов)
    if len(question) < 10:
        if history and len(history) > 0:
            last_topic = extract_topic_from_history(history)
            if last_topic:
                suggestions.append(f"Вы имеете в виду '{last_topic}'?")

        suggestions.extend([
            "Уточните: для какого типа работ?",
            "Для какого региона/климата?",
            "Какая стадия строительства?"
        ])

    # Ключевые слова для уточнений
    keywords_map = {
        'бетон': [
            "Какая марка бетона?",
            "Для каких конструкций?",
            "Зимнее или летнее бетонирование?"
        ],
        'арматура': [
            "Какой класс арматуры?",
            "Для чего: фундамент, стены, перекрытия?",
            "Нужен расчёт или нормативы?"
        ],
        'фундамент': [
            "Тип фундамента: ленточный, свайный, плитный?",
            "Глубина заложения?",
            "Тип грунта?"
        ],
        'кровля': [
            "Тип кровли: скатная, плоская?",
            "Материал покрытия?",
            "Эксплуатируемая или нет?"
        ]
    }

    question_lower = question.lower()
    for keyword, prompts in keywords_map.items():
        if keyword in question_lower:
            suggestions.extend(prompts[:2])  # Берём первые 2 подсказки
            break

    return suggestions[:3]  # Максимум 3 подсказки


def extract_topic_from_history(history):
    """Извлечь последнюю тему из истории диалога"""
    if not history:
        return None

    # Простой анализ последнего сообщения
    last_message = history[-1] if isinstance(history[-1], str) else history[-1].get('content', '')

    # Ключевые слова
    topics = ['бетон', 'арматура', 'фундамент', 'кровля', 'стены', 'перекрытия']
    for topic in topics:
        if topic in last_message.lower():
            return topic

    return None


def create_suggestion_buttons(suggestions):
    """Создать кнопки из подсказок"""
    buttons = []
    for i, suggestion in enumerate(suggestions):
        buttons.append([InlineKeyboardButton(
            f"💡 {suggestion[:50]}...",
            callback_data=f"suggest_{i}"
        )])

    # Добавляем кнопку "Уточнить самостоятельно"
    buttons.append([InlineKeyboardButton(
        "✏️ Уточнить самостоятельно",
        callback_data="clarify_manual"
    )])

    return InlineKeyboardMarkup(buttons)


# ========================================
# 3. КАТЕГОРИЗАЦИЯ НОРМАТИВОВ
# ========================================

REGULATIONS_CATEGORIES = {
    "Конструкции": {
        "СП 63.13330.2018": {
            "description": "Бетонные и железобетонные конструкции",
            "link": "https://docs.cntd.ru/document/554403082"
        },
        "СП 16.13330.2017": {
            "description": "Стальные конструкции",
            "link": "https://docs.cntd.ru/document/456054198"
        },
        "СП 64.13330.2017": {
            "description": "Деревянные конструкции",
            "link": "https://docs.cntd.ru/document/456069588"
        },
        "СП 70.13330.2012": {
            "description": "Несущие и ограждающие конструкции",
            "link": "https://docs.cntd.ru/document/1200092705"
        },
        "СП 28.13330.2017": {
            "description": "Защита строительных конструкций от коррозии",
            "link": "https://docs.cntd.ru/document/456069595"
        }
    },
    "Основания и фундаменты": {
        "СП 22.13330.2016": {
            "description": "Основания зданий и сооружений",
            "link": "https://docs.cntd.ru/document/456069569"
        },
        "СП 24.13330.2021": {
            "description": "Свайные фундаменты",
            "link": "https://docs.cntd.ru/document/573659347"
        },
        "СП 50-101-2004": {
            "description": "Проектирование и устройство оснований и фундаментов",
            "link": "https://docs.cntd.ru/document/1200035601"
        }
    },
    "Ограждающие конструкции": {
        "СП 50.13330.2012": {
            "description": "Тепловая защита зданий",
            "link": "https://docs.cntd.ru/document/1200095525"
        },
        "СП 23-101-2004": {
            "description": "Проектирование тепловой защиты зданий",
            "link": "https://docs.cntd.ru/document/1200035109"
        },
        "СП 17.13330.2017": {
            "description": "Кровли",
            "link": "https://docs.cntd.ru/document/456069588"
        }
    },
    "Инженерные системы": {
        "СП 60.13330.2020": {
            "description": "Отопление, вентиляция и кондиционирование воздуха",
            "link": "https://docs.cntd.ru/document/573659347"
        },
        "СП 30.13330.2020": {
            "description": "Внутренний водопровод и канализация зданий",
            "link": "https://docs.cntd.ru/document/573659347"
        },
        "СП 52.13330.2016": {
            "description": "Естественное и искусственное освещение",
            "link": "https://docs.cntd.ru/document/456054197"
        }
    },
    "Пожарная безопасность": {
        "СП 2.13130.2020": {
            "description": "Обеспечение огнестойкости объектов защиты",
            "link": "https://docs.cntd.ru/document/573659347"
        },
        "СП 4.13130.2013": {
            "description": "Системы противопожарной защиты. Ограничение распространения пожара",
            "link": "https://docs.cntd.ru/document/1200101593"
        }
    },
    "Контроль качества": {
        "ГОСТ 10180-2012": {
            "description": "Бетоны. Методы определения прочности по контрольным образцам",
            "link": "https://docs.cntd.ru/document/1200100908"
        },
        "ГОСТ 22690-2015": {
            "description": "Бетоны. Определение прочности механическими методами",
            "link": "https://docs.cntd.ru/document/1200133735"
        },
        "СП 48.13330.2019": {
            "description": "Организация строительства",
            "link": "https://docs.cntd.ru/document/554403082"
        },
        "ГОСТ 31937-2011": {
            "description": "Здания и сооружения. Правила обследования и мониторинга",
            "link": "https://docs.cntd.ru/document/1200100940"
        }
    },
    "Обследование": {
        "СП 13-102-2003": {
            "description": "Правила обследования несущих строительных конструкций",
            "link": "https://docs.cntd.ru/document/1200035578"
        },
        "СП 255.1325800.2016": {
            "description": "Правила эксплуатации жилищного фонда",
            "link": "https://docs.cntd.ru/document/456054198"
        }
    },
    "Доступность": {
        "СП 59.13330.2020": {
            "description": "Доступность зданий и сооружений для маломобильных групп населения",
            "link": "https://docs.cntd.ru/document/573659347"
        }
    }
}


def create_regulations_category_menu():
    """Создать меню категорий нормативов"""
    buttons = []

    # Иконки для категорий
    category_icons = {
        "Конструкции": "🏗️",
        "Основания и фундаменты": "⚓",
        "Ограждающие конструкции": "🧱",
        "Инженерные системы": "⚡",
        "Пожарная безопасность": "🔥",
        "Контроль качества": "✅",
        "Обследование": "🔍",
        "Доступность": "♿"
    }

    for category, docs in REGULATIONS_CATEGORIES.items():
        icon = category_icons.get(category, "📄")
        count = len(docs)
        # Создаём английское название категории для callback_data
        cat_id = {
            "Конструкции": "structures",
            "Основания и фундаменты": "foundations",
            "Ограждающие конструкции": "enclosures",
            "Инженерные системы": "engineering",
            "Пожарная безопасность": "fire",
            "Контроль качества": "quality",
            "Обследование": "inspection",
            "Доступность": "accessibility"
        }.get(category, category.lower())

        buttons.append([InlineKeyboardButton(
            f"{icon} {category} ({count})",
            callback_data=f"reg_cat_{cat_id}"
        )])

    # Кнопка "Показать все"
    buttons.append([InlineKeyboardButton(
        "📋 Показать все нормативы",
        callback_data="reg_cat_all"
    )])

    return InlineKeyboardMarkup(buttons)


def get_regulations_by_category(category):
    """Получить список нормативов по категории"""
    if category == "all":
        # Вернуть все нормативы
        all_regs = {}
        for cat_name, docs in REGULATIONS_CATEGORIES.items():
            all_regs.update(docs)
        return all_regs

    # Преобразуем английское название обратно в русское
    rus_cat = {
        "structures": "Конструкции",
        "foundations": "Основания и фундаменты",
        "enclosures": "Ограждающие конструкции",
        "engineering": "Инженерные системы",
        "fire": "Пожарная безопасность",
        "quality": "Контроль качества",
        "inspection": "Обследование",
        "accessibility": "Доступность"
    }.get(category, category)

    return REGULATIONS_CATEGORIES.get(rus_cat, {})


# ========================================
# 4. КАЛЬКУЛЯТОРЫ
# ========================================

CALCULATORS = {
    "concrete": {
        "name": "🏗️ Расчёт бетона",
        "description": "Объём, прочность, осадка конуса",
        "icon": "🏗️"
    },
    "reinforcement": {
        "name": "🔧 Расчёт арматуры",
        "description": "Шаг, диаметр, защитный слой",
        "icon": "🔧"
    },
    "formwork": {
        "name": "📦 Расчёт опалубки",
        "description": "Количество, оборачиваемость",
        "icon": "📦"
    },
    "electrical": {
        "name": "⚡ Электроснабжение",
        "description": "Мощность для стройплощадки",
        "icon": "⚡"
    },
    "water": {
        "name": "💧 Водоснабжение",
        "description": "Расход воды на объекте",
        "icon": "💧"
    },
    "winter": {
        "name": "❄️ Зимний прогрев",
        "description": "Прогрев бетона при -15°C",
        "icon": "❄️"
    },
    "math": {
        "name": "🧮 Математический",
        "description": "Универсальный калькулятор",
        "icon": "🧮"
    }
}


def create_calculators_menu():
    """Создать меню калькуляторов"""
    buttons = []

    for calc_id, calc_data in CALCULATORS.items():
        buttons.append([InlineKeyboardButton(
            f"{calc_data['icon']} {calc_data['name']}",
            callback_data=f"calc_{calc_id}"
        )])

    return InlineKeyboardMarkup(buttons)


# ========================================
# 5. РЕГИОНАЛЬНЫЕ НАСТРОЙКИ
# ========================================

REGIONS = {
    "moscow": {
        "name": "Москва и МО",
        "climate_zone": "II",
        "coefficients": {
            "winter": 1.2,
            "seismic": 0
        }
    },
    "spb": {
        "name": "Санкт-Петербург",
        "climate_zone": "II",
        "coefficients": {
            "winter": 1.3,
            "seismic": 0
        }
    },
    "sochi": {
        "name": "Сочи",
        "climate_zone": "IV",
        "coefficients": {
            "winter": 0.8,
            "seismic": 9
        }
    },
    "yakutsk": {
        "name": "Якутск",
        "climate_zone": "I",
        "coefficients": {
            "winter": 2.0,
            "seismic": 0
        }
    },
    "kamchatka": {
        "name": "Камчатка",
        "climate_zone": "I",
        "coefficients": {
            "winter": 1.8,
            "seismic": 9
        }
    }
}


def create_region_selection_menu():
    """Создать меню выбора региона"""
    buttons = []

    for region_id, region_data in REGIONS.items():
        buttons.append([InlineKeyboardButton(
            f"📍 {region_data['name']}",
            callback_data=f"region_{region_id}"
        )])

    # Кнопка "Другой регион"
    buttons.append([InlineKeyboardButton(
        "🌍 Другой регион",
        callback_data="region_other"
    )])

    return InlineKeyboardMarkup(buttons)


def get_region_info(region_id):
    """Получить информацию о регионе"""
    return REGIONS.get(region_id, None)


# ========================================
# 6. СОХРАНЁННЫЕ ЗАПРОСЫ
# ========================================

# Будет храниться в PostgreSQL, пока заглушка
saved_queries_db = {}

def save_user_query(user_id, query_text, answer_text):
    """Сохранить запрос пользователя"""
    if user_id not in saved_queries_db:
        saved_queries_db[user_id] = []

    saved_queries_db[user_id].append({
        "query": query_text,
        "answer": answer_text,
        "timestamp": None  # TODO: добавить время
    })

    return True


def get_saved_queries(user_id, limit=10):
    """Получить сохранённые запросы пользователя"""
    return saved_queries_db.get(user_id, [])[-limit:]


def create_saved_queries_menu(user_id):
    """Создать меню сохранённых запросов"""
    queries = get_saved_queries(user_id)

    if not queries:
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("📭 Нет сохранённых запросов", callback_data="noop")
        ]])

    buttons = []
    for i, query in enumerate(queries[-5:]):  # Последние 5
        query_preview = query['query'][:40] + "..." if len(query['query']) > 40 else query['query']
        buttons.append([InlineKeyboardButton(
            f"💾 {query_preview}",
            callback_data=f"load_query_{i}"
        )])

    return InlineKeyboardMarkup(buttons)


# ========================================
# 7. УЛУЧШЕННАЯ КОМАНДА /help
# ========================================

def get_improved_help_text():
    """Улучшенный текст справки со структурой"""
    return """📖 **СПРАВКА - СтройНадзорAI v3.0**

🎯 **БЫСТРЫЙ СТАРТ:**

1️⃣ **Задать вопрос:**
   • Просто напишите в чат
   • Бот помнит контекст диалога
   • Можно задавать уточняющие вопросы

2️⃣ **Загрузить фото:**
   • Отправьте фото дефекта
   • Можно добавить описание
   • Получите анализ и рекомендации

3️⃣ **Использовать калькуляторы:**
   • Команда /calculators
   • Выберите нужный расчёт
   • Введите параметры

📚 **ОСНОВНЫЕ КОМАНДЫ:**

🔍 **Поиск информации:**
   /regulations - Нормативы по категориям
   /search <запрос> - Поиск по истории
   /examples - Примеры вопросов

🧮 **Инструменты:**
   /calculators - Строительные калькуляторы
   /region - Выбрать регион
   /templates - Шаблоны документов

💾 **Работа с данными:**
   /history - История диалогов
   /saved - Сохранённые запросы
   /export - Экспорт в PDF/Word

📊 **Статистика:**
   /stats - Ваша статистика
   /achievements - Достижения

⚙️ **Настройки:**
   /region - Изменить регион
   /settings - Настройки бота

🆘 **ПОМОЩЬ:**
Если что-то непонятно, просто напишите "помощь" в чат!

💡 **СОВЕТ:** Используйте кнопки под ответами для быстрых действий!"""


def create_help_menu():
    """Создать интерактивное меню справки"""
    buttons = [
        [
            InlineKeyboardButton("🎯 Быстрый старт", callback_data="help_quickstart"),
            InlineKeyboardButton("📚 Команды", callback_data="help_commands")
        ],
        [
            InlineKeyboardButton("🧮 Калькуляторы", callback_data="help_calculators"),
            InlineKeyboardButton("📊 Статистика", callback_data="help_stats")
        ],
        [
            InlineKeyboardButton("💡 Советы", callback_data="help_tips"),
            InlineKeyboardButton("🆘 FAQ", callback_data="help_faq")
        ]
    ]

    return InlineKeyboardMarkup(buttons)


# ========================================
# 8. УЛУЧШЕНИЯ ЭКСПОРТА
# ========================================

def create_export_menu():
    """Меню выбора формата экспорта"""
    buttons = [
        [
            InlineKeyboardButton("📄 PDF", callback_data="export_format_pdf"),
            InlineKeyboardButton("📝 Word", callback_data="export_format_word")
        ],
        [
            InlineKeyboardButton("📊 Excel (таблица)", callback_data="export_format_excel"),
            InlineKeyboardButton("📋 Текст", callback_data="export_format_txt")
        ]
    ]

    return InlineKeyboardMarkup(buttons)


# ========================================
# 9. СИСТЕМА ДОСТИЖЕНИЙ (GAMIFICATION)
# ========================================

ACHIEVEMENTS = {
    "first_question": {
        "name": "Первый вопрос",
        "description": "Задали первый вопрос боту",
        "icon": "🎉",
        "requirement": 1
    },
    "curious": {
        "name": "Любознательный",
        "description": "Задали 10 вопросов",
        "icon": "🤔",
        "requirement": 10
    },
    "expert": {
        "name": "Эксперт",
        "description": "Задали 100 вопросов",
        "icon": "🎓",
        "requirement": 100
    },
    "photo_analyzer": {
        "name": "Инспектор",
        "description": "Загрузили 5 фото дефектов",
        "icon": "📸",
        "requirement": 5
    },
    "calculator_user": {
        "name": "Расчётчик",
        "description": "Использовали 10 калькуляторов",
        "icon": "🧮",
        "requirement": 10
    }
}


def check_achievements(user_stats):
    """Проверить новые достижения пользователя"""
    new_achievements = []

    # Логика проверки достижений
    if user_stats.get('total_messages', 0) >= 1:
        new_achievements.append('first_question')

    if user_stats.get('total_messages', 0) >= 10:
        new_achievements.append('curious')

    # TODO: добавить остальные

    return new_achievements


def create_achievements_display(user_achievements):
    """Создать отображение достижений"""
    text = "🏆 **ВАШИ ДОСТИЖЕНИЯ:**\n\n"

    for achievement_id in user_achievements:
        achievement = ACHIEVEMENTS.get(achievement_id)
        if achievement:
            text += f"{achievement['icon']} **{achievement['name']}**\n"
            text += f"   {achievement['description']}\n\n"

    locked_count = len(ACHIEVEMENTS) - len(user_achievements)
    if locked_count > 0:
        text += f"🔒 Ещё {locked_count} достижений заблокировано\n"

    return text
