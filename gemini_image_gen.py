"""
Модуль для генерации изображений и визуализации с помощью Gemini API
Поддерживает Imagen 3 для генерации изображений
"""

import os
import logging
import base64
import requests
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

        # Используем Gemini 2.5 Flash для быстрой визуализации и анализа
        # Flash модель оптимальна для генерации схем и описаний
        self.vision_model = genai.GenerativeModel('models/gemini-2.5-flash')
        logger.info("✅ Используется модель: gemini-2.5-flash")

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

    async def generate_schematic_image(
        self,
        description: str,
        image_type: str = "technical"
    ) -> Optional[BytesIO]:
        """
        Генерирует простое схематическое изображение с помощью Pillow

        Args:
            description: Описание для генерации
            image_type: Тип изображения (technical, diagram, layout)

        Returns:
            BytesIO с изображением или None
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
            import textwrap

            # Создаем изображение
            width, height = 1024, 1024
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)

            # Рисуем рамку
            draw.rectangle([20, 20, width-20, height-20], outline='black', width=3)

            # Заголовок
            title = "СТРОИТЕЛЬНАЯ СХЕМА"
            draw.text((width//2, 50), title, fill='black', anchor="mm")

            # Используем Gemini для создания описания схемы
            prompt = f"""
            Создай простое текстовое описание для схемы:
            {description}

            Опиши в 3-5 пунктах ключевые элементы, которые должны быть на схеме.
            Формат: короткие пункты, каждый с новой строки.
            """

            response = self.vision_model.generate_content(prompt)
            schema_text = response.text

            # Разбиваем текст на строки
            lines = schema_text.split('\n')
            y_position = 150

            for line in lines[:8]:  # Максимум 8 строк
                if line.strip():
                    # Оборачиваем длинные строки
                    wrapped = textwrap.wrap(line, width=60)
                    for wrapped_line in wrapped:
                        draw.text((60, y_position), wrapped_line, fill='black')
                        y_position += 40

            # Добавляем технические детали в нижней части
            draw.text(
                (width//2, height-80),
                "Создано с помощью Gemini AI",
                fill='gray',
                anchor="mm"
            )

            draw.text(
                (width//2, height-50),
                f"Описание: {description[:50]}...",
                fill='gray',
                anchor="mm"
            )

            # Сохраняем изображение
            output = BytesIO()
            img.save(output, format='PNG')
            output.seek(0)

            logger.info("✅ Схематическое изображение создано")
            return output

        except Exception as e:
            logger.error(f"❌ Ошибка создания схемы: {e}")
            return None

    async def improve_prompt_for_generation(
        self,
        user_request: str,
        language: str = "en"
    ) -> Optional[str]:
        """
        Улучшает промпт пользователя для генерации изображения

        Args:
            user_request: Запрос пользователя на русском
            language: Язык результата (en или ru)

        Returns:
            Улучшенный промпт или None
        """
        try:
            prompt = f"""
            Ты - эксперт по созданию промптов для генерации изображений.
            Пользователь запросил: "{user_request}"

            Создай детальный промпт для генерации технического изображения на {'английском' if language == 'en' else 'русском'} языке.

            Промпт должен включать:
            1. Тип изображения (фото, схема, 3D-визуализация)
            2. Ключевые объекты и их расположение
            3. Технические детали и размеры
            4. Стиль (реалистичный, схематичный, технический чертеж)
            5. Ракурс и перспективу
            6. Освещение и цветовую схему

            Сделай промпт максимально точным и детальным для строительной тематики.
            Ответ должен быть в одном абзаце, без нумерации.
            """

            response = self.vision_model.generate_content(prompt)
            improved_prompt = response.text.strip()

            logger.info(f"✅ Промпт улучшен: {improved_prompt[:100]}...")
            return improved_prompt

        except Exception as e:
            logger.error(f"❌ Ошибка улучшения промпта: {e}")
            return None

    async def generate_construction_diagram(
        self,
        description: str,
        elements: List[str] = None
    ) -> Optional[BytesIO]:
        """
        Генерирует строительную диаграмму с элементами

        Args:
            description: Описание конструкции
            elements: Список элементов для отображения

        Returns:
            BytesIO с изображением или None
        """
        try:
            from PIL import Image, ImageDraw, ImageFont

            # Создаем изображение
            width, height = 1200, 800
            img = Image.new('RGB', (width, height), color='#f5f5f5')
            draw = ImageDraw.Draw(img)

            # Заголовок
            title = "СТРОИТЕЛЬНАЯ КОНСТРУКЦИЯ"
            draw.text((width//2, 40), title, fill='black', anchor="mm")

            # Описание
            draw.text((width//2, 80), description, fill='#333333', anchor="mm")

            if elements:
                # Рисуем элементы
                element_height = 100
                start_y = 150
                element_width = 300

                for i, element in enumerate(elements[:5]):  # Максимум 5 элементов
                    y = start_y + i * element_height
                    x = width // 2

                    # Рисуем прямоугольник элемента
                    draw.rectangle(
                        [x - element_width//2, y, x + element_width//2, y + 60],
                        outline='#2196F3',
                        fill='white',
                        width=2
                    )

                    # Текст элемента
                    draw.text((x, y + 30), element, fill='#333333', anchor="mm")

                    # Соединительная линия (если не последний)
                    if i < len(elements) - 1:
                        draw.line([x, y + 60, x, y + 100], fill='#666666', width=2)

            # Подпись
            draw.text(
                (width//2, height-30),
                "Сгенерировано с помощью Gemini AI • StroiNadzorAI",
                fill='#999999',
                anchor="mm"
            )

            # Сохраняем изображение
            output = BytesIO()
            img.save(output, format='PNG')
            output.seek(0)

            logger.info("✅ Строительная диаграмма создана")
            return output

        except Exception as e:
            logger.error(f"❌ Ошибка создания диаграммы: {e}")
            return None


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
