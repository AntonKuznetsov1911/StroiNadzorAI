"""
Модуль для получения актуальной погоды через Яндекс Погода API
"""

import os
import requests
import logging
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# API ключ из переменных окружения
YANDEX_WEATHER_API_KEY = os.getenv("YANDEX_WEATHER_API_KEY")

# Координаты крупных городов России
CITY_COORDINATES = {
    "москва": {"lat": 55.7558, "lon": 37.6173},
    "санкт-петербург": {"lat": 59.9311, "lon": 30.3609},
    "петербург": {"lat": 59.9311, "lon": 30.3609},
    "спб": {"lat": 59.9311, "lon": 30.3609},
    "краснодар": {"lat": 45.0355, "lon": 38.9753},
    "екатеринбург": {"lat": 56.8389, "lon": 60.6057},
    "новосибирск": {"lat": 55.0084, "lon": 82.9357},
    "казань": {"lat": 55.7887, "lon": 49.1221},
    "нижний новгород": {"lat": 56.2965, "lon": 43.9361},
    "челябинск": {"lat": 55.1644, "lon": 61.4368},
    "самара": {"lat": 53.1959, "lon": 50.1002},
    "омск": {"lat": 54.9885, "lon": 73.3242},
    "ростов-на-дону": {"lat": 47.2357, "lon": 39.7015},
    "ростов": {"lat": 47.2357, "lon": 39.7015},
    "уфа": {"lat": 54.7388, "lon": 55.9721},
    "красноярск": {"lat": 56.0153, "lon": 92.8932},
    "воронеж": {"lat": 51.6720, "lon": 39.1843},
    "пермь": {"lat": 58.0105, "lon": 56.2502},
    "волгоград": {"lat": 48.7080, "lon": 44.5133},
    "саратов": {"lat": 51.5924, "lon": 46.0348},
}

def extract_city_from_query(query: str) -> Optional[str]:
    """
    Извлечь название города из запроса пользователя

    Args:
        query: Запрос пользователя

    Returns:
        Название города или None
    """
    query_lower = query.lower()

    # Убираем общие слова
    query_clean = query_lower.replace("погода", "").replace("какая", "").replace("в", "").replace("?", "").strip()

    # Ищем город в словаре
    for city in CITY_COORDINATES.keys():
        if city in query_clean:
            return city

    return None


def get_weather_yandex(lat: float, lon: float) -> Optional[Dict]:
    """
    Получить погоду через Яндекс Погода API

    Args:
        lat: Широта
        lon: Долгота

    Returns:
        Dict с данными о погоде или None
    """
    if not YANDEX_WEATHER_API_KEY:
        logger.warning("⚠️ YANDEX_WEATHER_API_KEY не установлен")
        return None

    try:
        url = "https://api.weather.yandex.ru/v2/informers"
        headers = {
            "X-Yandex-API-Key": YANDEX_WEATHER_API_KEY
        }
        params = {
            "lat": lat,
            "lon": lon,
            "lang": "ru_RU"
        }

        logger.info(f"🌤️ Запрос погоды: lat={lat}, lon={lon}")

        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Извлекаем основную информацию
        fact = data.get("fact", {})
        forecast = data.get("forecast", {})

        # Перевод условий на русский
        condition_translation = {
            "clear": "ясно",
            "partly-cloudy": "малооблачно",
            "cloudy": "облачно",
            "overcast": "пасмурно",
            "drizzle": "морось",
            "light-rain": "небольшой дождь",
            "rain": "дождь",
            "moderate-rain": "умеренный дождь",
            "heavy-rain": "сильный дождь",
            "continuous-heavy-rain": "продолжительный сильный дождь",
            "showers": "ливень",
            "wet-snow": "дождь со снегом",
            "light-snow": "небольшой снег",
            "snow": "снег",
            "snow-showers": "снегопад",
            "hail": "град",
            "thunderstorm": "гроза",
            "thunderstorm-with-rain": "дождь с грозой",
            "thunderstorm-with-hail": "гроза с градом"
        }

        condition = fact.get("condition", "")
        condition_ru = condition_translation.get(condition, condition)

        # Направление ветра
        wind_dir_translation = {
            "nw": "северо-западный",
            "n": "северный",
            "ne": "северо-восточный",
            "e": "восточный",
            "se": "юго-восточный",
            "s": "южный",
            "sw": "юго-западный",
            "w": "западный",
            "c": "штиль"
        }

        wind_dir = fact.get("wind_dir", "")
        wind_dir_ru = wind_dir_translation.get(wind_dir, wind_dir)

        weather_data = {
            "temp": fact.get("temp"),
            "feels_like": fact.get("feels_like"),
            "condition": condition_ru,
            "wind_speed": fact.get("wind_speed"),
            "wind_dir": wind_dir_ru,
            "pressure_mm": fact.get("pressure_mm"),
            "humidity": fact.get("humidity"),
            "daytime": fact.get("daytime"),
            "polar": fact.get("polar"),
            "season": fact.get("season"),
            "obs_time": fact.get("obs_time"),
            "forecast": forecast
        }

        logger.info(f"✅ Погода получена: {weather_data['temp']}°C, {condition_ru}")
        return weather_data

    except requests.RequestException as e:
        logger.error(f"❌ Ошибка запроса к Яндекс Погода API: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка обработки данных погоды: {e}")
        return None


def format_weather_response(city: str, weather_data: Dict) -> str:
    """
    Форматировать ответ о погоде для пользователя

    Args:
        city: Название города
        weather_data: Данные о погоде

    Returns:
        Отформатированный текст
    """
    temp = weather_data["temp"]
    feels_like = weather_data["feels_like"]
    condition = weather_data["condition"]
    wind_speed = weather_data["wind_speed"]
    wind_dir = weather_data["wind_dir"]
    humidity = weather_data["humidity"]
    pressure_mm = weather_data["pressure_mm"]

    # Эмодзи в зависимости от условий
    condition_emoji = {
        "ясно": "☀️",
        "малооблачно": "🌤️",
        "облачно": "⛅",
        "пасмурно": "☁️",
        "дождь": "🌧️",
        "снег": "🌨️",
        "гроза": "⛈️",
        "град": "🌨️"
    }

    emoji = "🌤️"
    for key, em in condition_emoji.items():
        if key in condition:
            emoji = em
            break

    response = f"""{emoji} **Погода в {city.title()}**

🌡️ **Температура:** {temp}°C (ощущается как {feels_like}°C)
☁️ **Условия:** {condition}
💨 **Ветер:** {wind_dir}, {wind_speed} м/с
💧 **Влажность:** {humidity}%
🎚️ **Давление:** {pressure_mm} мм рт.ст.

💡 **Практический совет:**"""

    # Практические советы в зависимости от условий
    if temp < 0:
        response += "\n• Оденьтесь теплее! Возможно обледенение."
    elif temp > 25:
        response += "\n• Жарко! Не забудьте воду."

    if "дождь" in condition or "ливень" in condition:
        response += "\n• Возьмите зонт!"

    if "снег" in condition:
        response += "\n• Возможен снегопад, будьте осторожны на дорогах."

    if wind_speed > 10:
        response += "\n• Сильный ветер, закрепите легкие конструкции на стройке."

    response += "\n\n📊 Источник: Яндекс.Погода"

    return response


def get_weather(query: str) -> Optional[str]:
    """
    Получить погоду на основе запроса пользователя

    Args:
        query: Запрос пользователя (например, "Какая погода в Москве?")

    Returns:
        Отформатированный ответ о погоде или None
    """
    # Извлекаем город
    city = extract_city_from_query(query)

    if not city:
        return None

    # Получаем координаты
    coords = CITY_COORDINATES.get(city)

    if not coords:
        return None

    # Получаем погоду
    weather_data = get_weather_yandex(coords["lat"], coords["lon"])

    if not weather_data:
        return None

    # Форматируем ответ
    return format_weather_response(city, weather_data)


# Проверка, является ли запрос вопросом о погоде
def is_weather_query(query: str) -> bool:
    """
    Определить, является ли запрос вопросом о погоде

    Args:
        query: Запрос пользователя

    Returns:
        True если это вопрос о погоде, False иначе
    """
    query_lower = query.lower()
    weather_keywords = ["погода", "температура", "градус", "тепло", "холодно", "дождь", "снег"]

    return any(keyword in query_lower for keyword in weather_keywords)
