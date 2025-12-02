"""
Модуль для генерации изображений и визуализации с помощью Gemini API
"""

import os
import logging
import base64
from io import BytesIO
from typing import Optional, Dict, List
import google.generativeai as genai
from PIL import Image

logger = logging.getLogger(__name__)


class GeminiImageGenerator:
    """Класс для работы с Gemini API для генерации изображений и визуализации"""

    def __init__(self, api_key: str):
        """
        Инициализация генератора изображений

        Args:
            api_key: API ключ для Gemini
        """
        self.api_key = api_key
        genai.configure(api_key=api_key)

        # Используем Gemini Pro Vision для визуализации и анализа
        self.vision_model = genai.GenerativeModel('gemini-1.5-pro')

        logger.info("✅ Gemini Image Generator инициализирован")

    async def generate_defect_visualization(
        self,
        defect_description: str,
        defect_type: str = "общий",
        style: str = "technical"
    ) -> Optional[bytes]:
        """
        Генерирует визуализацию строительного дефекта

        Args:
            defect_description: Описание дефекта
            defect_type: Тип дефекта (трещина, влага, деформация и т.д.)
            style: Стиль визуализации (technical, realistic, schematic)

        Returns:
            Байты изображения или None в случае ошибки
        """
        try:
            # Формируем детальный промпт для генерации
            prompt = self._create_defect_prompt(defect_description, defect_type, style)

            logger.info(f"Генерация визуализации дефекта: {defect_type}")

            # Gemini пока не поддерживает прямую генерацию изображений
            # Вместо этого используем его для создания детального описания
            # которое можно использовать с другими инструментами
            response = self.vision_model.generate_content(prompt)

            # Возвращаем текстовое описание для визуализации
            logger.info("✅ Создано описание для визуализации дефекта")
            return response.text

        except Exception as e:
            logger.error(f"❌ Ошибка при генерации визуализации: {e}")
            return None

    async def analyze_and_visualize_defect(
        self,
        image_bytes: bytes,
        analysis_text: str
    ) -> Optional[str]:
        """
        Анализирует изображение дефекта и создает детальное описание для визуализации

        Args:
            image_bytes: Байты изображения
            analysis_text: Текст анализа дефекта от Claude

        Returns:
            Описание для визуализации или None
        """
        try:
            # Открываем изображение
            image = Image.open(BytesIO(image_bytes))

            # Создаем промпт для анализа
            prompt = f"""
            Проанализируй это изображение строительного дефекта и создай детальное техническое описание
            для визуализации проблемы. Учитывай следующий анализ:

            {analysis_text}

            Создай описание, которое включает:
            1. Точное местоположение дефекта
            2. Масштаб и размеры
            3. Характерные особенности
            4. Цветовую схему для выделения проблемных зон
            5. Рекомендуемые зоны для маркировки

            Ответ должен быть структурированным и пригодным для создания схемы или диаграммы.
            """

            # Отправляем изображение и промпт в Gemini
            response = self.vision_model.generate_content([prompt, image])

            logger.info("✅ Создан анализ для визуализации")
            return response.text

        except Exception as e:
            logger.error(f"❌ Ошибка при анализе для визуализации: {e}")
            return None

    async def create_comparison_description(
        self,
        before_image: bytes,
        after_image: Optional[bytes] = None,
        defect_info: str = ""
    ) -> Optional[str]:
        """
        Создает описание для сравнения состояния до/после

        Args:
            before_image: Изображение до
            after_image: Изображение после (опционально)
            defect_info: Информация о дефекте

        Returns:
            Описание для визуализации сравнения
        """
        try:
            before_img = Image.open(BytesIO(before_image))

            prompt = f"""
            Создай детальное описание для визуализации строительного дефекта.

            Информация о дефекте:
            {defect_info}

            Опиши:
            1. Ключевые зоны для выделения на изображении
            2. Рекомендуемую цветовую схему для маркировки
            3. Размеры и масштаб проблемных участков
            4. Важные детали для визуального представления

            Если это сравнение до/после, укажи изменения.
            """

            if after_image:
                after_img = Image.open(BytesIO(after_image))
                response = self.vision_model.generate_content([
                    "ИЗОБРАЖЕНИЕ ДО:", before_img,
                    "ИЗОБРАЖЕНИЕ ПОСЛЕ:", after_img,
                    prompt
                ])
            else:
                response = self.vision_model.generate_content([prompt, before_img])

            logger.info("✅ Создано описание для сравнительной визуализации")
            return response.text

        except Exception as e:
            logger.error(f"❌ Ошибка при создании описания сравнения: {e}")
            return None

    async def generate_regulation_diagram(
        self,
        regulation_text: str,
        diagram_type: str = "flowchart"
    ) -> Optional[str]:
        """
        Генерирует описание для создания диаграммы норматива

        Args:
            regulation_text: Текст норматива
            diagram_type: Тип диаграммы (flowchart, hierarchy, process)

        Returns:
            Описание структуры диаграммы
        """
        try:
            prompt = f"""
            На основе следующего строительного норматива создай детальное описание
            для построения диаграммы типа {diagram_type}:

            {regulation_text}

            Опиши структуру в формате:
            1. Основные блоки и их содержание
            2. Связи между блоками
            3. Иерархию элементов
            4. Цветовое кодирование (если применимо)
            5. Ключевые пункты для выделения

            Формат должен быть пригоден для создания схемы с помощью библиотек визуализации.
            """

            response = self.vision_model.generate_content(prompt)

            logger.info(f"✅ Создано описание диаграммы для норматива ({diagram_type})")
            return response.text

        except Exception as e:
            logger.error(f"❌ Ошибка при создании описания диаграммы: {e}")
            return None

    async def create_annotated_image_description(
        self,
        image_bytes: bytes,
        annotations: List[Dict[str, str]]
    ) -> Optional[str]:
        """
        Создает описание для аннотированного изображения

        Args:
            image_bytes: Байты изображения
            annotations: Список аннотаций [{"text": "...", "position": "..."}]

        Returns:
            Описание для создания аннотированного изображения
        """
        try:
            image = Image.open(BytesIO(image_bytes))

            annotations_text = "\n".join([
                f"- {ann['text']} (позиция: {ann.get('position', 'не указана')})"
                for ann in annotations
            ])

            prompt = f"""
            Проанализируй это изображение и создай техническое описание для добавления
            следующих аннотаций:

            {annotations_text}

            Опиши:
            1. Оптимальные координаты для размещения каждой аннотации
            2. Размер и стиль шрифта
            3. Цвет выделения для каждой зоны
            4. Форму маркеров (стрелки, круги, прямоугольники)
            5. Порядок наложения элементов

            Результат должен быть структурирован для программной обработки.
            """

            response = self.vision_model.generate_content([prompt, image])

            logger.info("✅ Создано описание для аннотированного изображения")
            return response.text

        except Exception as e:
            logger.error(f"❌ Ошибка при создании описания аннотаций: {e}")
            return None

    def _create_defect_prompt(
        self,
        description: str,
        defect_type: str,
        style: str
    ) -> str:
        """Создает детальный промпт для визуализации дефекта"""

        style_descriptions = {
            "technical": "технический чертеж с измерениями и маркировкой",
            "realistic": "фотореалистичное изображение",
            "schematic": "схематическая диаграмма с выделением ключевых зон"
        }

        style_desc = style_descriptions.get(style, style_descriptions["technical"])

        return f"""
        Создай детальное техническое описание для визуализации строительного дефекта.

        Тип дефекта: {defect_type}
        Описание: {description}
        Стиль: {style_desc}

        Включи в описание:
        1. Внешний вид дефекта (форма, размеры, цвет)
        2. Контекст (где обычно встречается, окружение)
        3. Масштаб и пропорции
        4. Ключевые элементы для выделения
        5. Цветовую схему для визуализации степени серьезности
        6. Рекомендуемые измерения и метки
        7. Дополнительные детали (материалы, текстуры)

        Описание должно быть максимально точным и техническим, пригодным для:
        - Создания 2D схемы дефекта
        - Разметки проблемных зон
        - Подготовки технической документации

        Формат ответа: структурированное техническое описание с конкретными параметрами.
        """


def initialize_gemini_generator() -> Optional[GeminiImageGenerator]:
    """
    Инициализирует генератор изображений Gemini

    Returns:
        Экземпляр GeminiImageGenerator или None
    """
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            logger.warning("⚠️ GEMINI_API_KEY не найден в переменных окружения")
            return None

        generator = GeminiImageGenerator(api_key)
        logger.info("✅ Gemini генератор успешно инициализирован")
        return generator

    except Exception as e:
        logger.error(f"❌ Ошибка инициализации Gemini генератора: {e}")
        return None
