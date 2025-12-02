"""
Модуль для поиска актуальной информации на сайтах строительных нормативов РФ
"""

import requests
from bs4 import BeautifulSoup
import logging
import re
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


# === ПАРСИНГ DOCS.CNTD.RU (БАЗА НОРМАТИВОВ) ===

def search_regulation_cntd(regulation_code: str) -> Optional[Dict]:
    """
    Поиск норматива на docs.cntd.ru

    Args:
        regulation_code: Код норматива (например, "СП 63.13330.2018", "ГОСТ 31937-2011")

    Returns:
        Dict с информацией о нормативе или None
    """
    try:
        # Очищаем код норматива для поиска
        search_query = regulation_code.replace(" ", "+")
        search_url = f"https://docs.cntd.ru/search?q={search_query}"

        logger.info(f"🔍 Поиск норматива: {regulation_code}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Ищем первый результат поиска
        result = soup.find('div', class_='search-result-item')
        if not result:
            logger.warning(f"Норматив {regulation_code} не найден на docs.cntd.ru")
            return None

        # Извлекаем информацию
        title_elem = result.find('a', class_='link')
        if not title_elem:
            return None

        title = title_elem.get_text(strip=True)
        link = "https://docs.cntd.ru" + title_elem['href']

        # Ищем статус (действует/отменен)
        status_elem = result.find('span', class_='status')
        status = status_elem.get_text(strip=True) if status_elem else "неизвестен"

        # Дата введения
        date_pattern = r'с\s+(\d{2}\.\d{2}\.\d{4})'
        date_match = re.search(date_pattern, result.get_text())
        valid_from = date_match.group(1) if date_match else None

        result_data = {
            "code": regulation_code,
            "title": title,
            "link": link,
            "status": status,
            "valid_from": valid_from,
            "source": "docs.cntd.ru",
            "search_date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        logger.info(f"✅ Найден: {title} ({status})")
        return result_data

    except requests.RequestException as e:
        logger.error(f"Ошибка запроса к docs.cntd.ru: {e}")
        return None
    except Exception as e:
        logger.error(f"Ошибка парсинга docs.cntd.ru: {e}")
        return None


def get_regulation_text(regulation_url: str, max_chars: int = 5000) -> Optional[str]:
    """
    Получить текст норматива с docs.cntd.ru

    Args:
        regulation_url: URL страницы норматива
        max_chars: Максимальное количество символов для извлечения

    Returns:
        Текст норматива или None
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(regulation_url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Ищем основной контент
        content = soup.find('div', class_='document-content')
        if not content:
            content = soup.find('div', id='text')

        if content:
            text = content.get_text(separator='\n', strip=True)
            # Ограничиваем размер
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
            return text

        return None

    except Exception as e:
        logger.error(f"Ошибка получения текста норматива: {e}")
        return None


# === ПАРСИНГ MINSTROYRF.GOV.RU (НОВОСТИ И ИЗМЕНЕНИЯ) ===

def search_minstroy_news(keywords: List[str], max_results: int = 3) -> List[Dict]:
    """
    Поиск новостей на сайте Минстроя России

    Args:
        keywords: Ключевые слова для поиска
        max_results: Максимальное количество результатов

    Returns:
        List с новостями
    """
    try:
        # URL раздела новостей Минстроя
        news_url = "https://minstroyrf.gov.ru/trades/gospolitika/"

        logger.info(f"🔍 Поиск новостей Минстроя: {', '.join(keywords)}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(news_url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Ищем новости
        news_items = soup.find_all('div', class_='news-item', limit=max_results * 2)

        results = []
        for item in news_items:
            if len(results) >= max_results:
                break

            title_elem = item.find('a')
            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)

            # Проверяем наличие ключевых слов
            if any(keyword.lower() in title.lower() for keyword in keywords):
                date_elem = item.find('time')
                date = date_elem.get_text(strip=True) if date_elem else "Дата неизвестна"

                link = "https://minstroyrf.gov.ru" + title_elem['href']

                results.append({
                    "title": title,
                    "date": date,
                    "link": link,
                    "source": "minstroyrf.gov.ru"
                })

        logger.info(f"✅ Найдено {len(results)} новостей Минстроя")
        return results

    except Exception as e:
        logger.error(f"Ошибка поиска на minstroyrf.gov.ru: {e}")
        return []


# === ОПРЕДЕЛЕНИЕ НЕОБХОДИМОСТИ ПОИСКА ===

def should_perform_web_search(user_message: str) -> bool:
    """
    Определить, нужен ли веб-поиск для ответа на вопрос

    Args:
        user_message: Сообщение пользователя

    Returns:
        True если нужен поиск, False если нет
    """
    # Триггеры для активации поиска
    search_triggers = [
        "актуальн",
        "новый",
        "новая",
        "свежий",
        "последн",
        "2025",
        "2026",
        "2027",
        "изменени",
        "обновлен",
        "действует",
        "отменен",
        "проверь",
        "найди",
        "поищи"
    ]

    message_lower = user_message.lower()
    return any(trigger in message_lower for trigger in search_triggers)


def extract_regulation_codes(text: str) -> List[str]:
    """
    Извлечь коды нормативов из текста

    Args:
        text: Текст для анализа

    Returns:
        List с кодами нормативов
    """
    # Паттерны для разных типов нормативов
    patterns = [
        r'СП\s+[\d.]+\.[\d.]+',  # СП 63.13330.2018
        r'ГОСТ\s+[РЕ\s]*[\d.-]+',  # ГОСТ 31937-2011, ГОСТ Р 57580
        r'СНиП\s+[\d.-]+',  # СНиП 2.01.07-85
        r'ППБ\s+[\d-]+',  # ППБ 01-03
    ]

    codes = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        codes.extend(matches)

    # Убираем дубликаты
    return list(set(codes))


# === ГЛАВНАЯ ФУНКЦИЯ ПОИСКА ===

def perform_web_search(user_message: str) -> Optional[str]:
    """
    Выполнить веб-поиск на основе сообщения пользователя

    Args:
        user_message: Сообщение пользователя

    Returns:
        Результаты поиска в текстовом формате или None
    """
    if not should_perform_web_search(user_message):
        return None

    logger.info(f"🌐 Активирован веб-поиск для: {user_message[:100]}...")

    results_text = "🌐 **РЕЗУЛЬТАТЫ ВЕБ-ПОИСКА:**\n\n"
    found_anything = False

    # 1. Ищем упомянутые нормативы
    regulation_codes = extract_regulation_codes(user_message)
    if regulation_codes:
        results_text += "📚 **ПРОВЕРКА НОРМАТИВОВ:**\n"
        for code in regulation_codes[:3]:  # Максимум 3 норматива
            reg_info = search_regulation_cntd(code)
            if reg_info:
                results_text += f"\n• **{reg_info['code']}**\n"
                results_text += f"  Название: {reg_info['title']}\n"
                results_text += f"  Статус: {reg_info['status']}\n"
                if reg_info['valid_from']:
                    results_text += f"  Действует с: {reg_info['valid_from']}\n"
                results_text += f"  Ссылка: {reg_info['link']}\n"
                found_anything = True
        results_text += "\n"

    # 2. Ищем новости Минстроя (если упоминаются года 2025-2027)
    if any(year in user_message for year in ["2025", "2026", "2027"]):
        keywords = ["норматив", "СП", "строительство", "требования"]
        news = search_minstroy_news(keywords, max_results=2)
        if news:
            results_text += "📰 **АКТУАЛЬНЫЕ НОВОСТИ МИНСТРОЯ:**\n"
            for item in news:
                results_text += f"\n• **{item['title']}**\n"
                results_text += f"  Дата: {item['date']}\n"
                results_text += f"  Ссылка: {item['link']}\n"
                found_anything = True
            results_text += "\n"

    if not found_anything:
        return None

    results_text += f"*Поиск выполнен: {datetime.now().strftime('%d.%m.%Y %H:%M')}*\n"
    results_text += "*Данные актуальны на момент поиска*"

    return results_text
