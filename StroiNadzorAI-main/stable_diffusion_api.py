"""
Модуль для работы с Stable Diffusion Web UI API
Поддерживает генерацию технических схем и строительных диаграмм
"""

import os
import base64
import logging
import requests
from io import BytesIO
from typing import Optional, Dict, List
from PIL import Image

logger = logging.getLogger(__name__)


class StableDiffusionGenerator:
    """Класс для работы с Stable Diffusion Web UI API"""

    def __init__(self, api_url: str = None, api_key: str = None):
        """
        Инициализация генератора Stable Diffusion

        Args:
            api_url: URL API Stable Diffusion Web UI (например: http://127.0.0.1:7860)
            api_key: API ключ (если требуется)
        """
        self.api_url = api_url or os.getenv('SD_API_URL', 'http://127.0.0.1:7860')
        self.api_key = api_key or os.getenv('SD_API_KEY')
        self.timeout = 120  # 2 минуты таймаут для генерации

        # Убираем trailing slash
        self.api_url = self.api_url.rstrip('/')

        logger.info(f"✅ Stable Diffusion API инициализирован: {self.api_url}")

    def check_connection(self) -> bool:
        """
        Проверка доступности API

        Returns:
            True если API доступен, False если нет
        """
        try:
            response = requests.get(
                f"{self.api_url}/sdapi/v1/sd-models",
                timeout=5
            )
            if response.status_code == 200:
                models = response.json()
                logger.info(f"✅ SD API доступен. Доступно моделей: {len(models)}")
                return True
            else:
                logger.warning(f"⚠️ SD API вернул код: {response.status_code}")
                return False
        except Exception as e:
            logger.warning(f"⚠️ SD API недоступен: {e}")
            return False

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = None,
        width: int = 1024,
        height: int = 1024,
        steps: int = 30,
        cfg_scale: float = 7.5,
        sampler: str = "DPM++ 2M Karras",
        seed: int = -1,
        batch_size: int = 1
    ) -> Optional[BytesIO]:
        """
        Генерация изображения через SD Web UI API

        Args:
            prompt: Промпт для генерации
            negative_prompt: Негативный промпт
            width: Ширина изображения
            height: Высота изображения
            steps: Количество шагов (10-50, рекомендуется 20-30)
            cfg_scale: Classifier Free Guidance Scale (3-15, рекомендуется 7-8)
            sampler: Название сэмплера
            seed: Seed для воспроизводимости (-1 для случайного)
            batch_size: Количество изображений за раз

        Returns:
            BytesIO с изображением или None
        """
        try:
            # Дефолтный негативный промпт для технических изображений
            if negative_prompt is None:
                negative_prompt = (
                    "low quality, blurry, distorted, watermark, text, "
                    "signature, username, artist name, lowres, bad anatomy, "
                    "bad proportions, deformed, ugly, disfigured"
                )

            # Формируем запрос к API
            payload = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "steps": steps,
                "cfg_scale": cfg_scale,
                "sampler_name": sampler,
                "seed": seed,
                "batch_size": batch_size,
                "n_iter": 1,
                "restore_faces": False,
                "tiling": False,
            }

            logger.info(f"🎨 Генерация изображения SD: {prompt[:50]}...")

            # Отправляем запрос
            response = requests.post(
                f"{self.api_url}/sdapi/v1/txt2img",
                json=payload,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"❌ SD API ошибка: {response.status_code}")
                return None

            result = response.json()

            # Получаем первое изображение
            if 'images' in result and len(result['images']) > 0:
                # Декодируем base64
                image_data = base64.b64decode(result['images'][0])
                image_buffer = BytesIO(image_data)

                logger.info("✅ Изображение успешно сгенерировано через SD")
                return image_buffer
            else:
                logger.error("❌ SD не вернул изображения")
                return None

        except requests.exceptions.Timeout:
            logger.error("❌ Таймаут запроса к SD API")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка генерации SD: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def generate_construction_schematic(
        self,
        description: str,
        schematic_type: str = "technical",
        style: str = "blueprint"
    ) -> Optional[BytesIO]:
        """
        Специализированная генерация строительных схем

        Args:
            description: Описание схемы на русском
            schematic_type: Тип схемы (technical, diagram, isometric, blueprint)
            style: Стиль (blueprint, technical_drawing, architectural, engineering)

        Returns:
            BytesIO с изображением или None
        """
        try:
            # Улучшаем промпт для строительной тематики
            enhanced_prompt = self._enhance_construction_prompt(
                description, schematic_type, style
            )

            # Негативный промпт для технических чертежей
            negative_prompt = (
                "photo, photograph, realistic, people, humans, faces, "
                "text, words, letters, watermark, signature, frame, border, "
                "low quality, blurry, distorted, bad lines, messy, chaotic, "
                "colorful, vibrant colors, cartoon, anime, sketch, painting"
            )

            logger.info(f"🏗️ Генерация строительной схемы: {description}")

            # Генерируем с оптимальными параметрами для технических схем
            return await self.generate_image(
                prompt=enhanced_prompt,
                negative_prompt=negative_prompt,
                width=1024,
                height=1024,
                steps=25,
                cfg_scale=7.0,
                sampler="DPM++ 2M Karras"
            )

        except Exception as e:
            logger.error(f"❌ Ошибка генерации строительной схемы: {e}")
            return None

    def _enhance_construction_prompt(
        self,
        description: str,
        schematic_type: str,
        style: str
    ) -> str:
        """
        Улучшение промпта для строительной тематики

        Args:
            description: Описание на русском
            schematic_type: Тип схемы
            style: Стиль

        Returns:
            Улучшенный промпт на английском
        """
        # Базовые префиксы для разных типов
        type_prefixes = {
            "technical": "technical drawing, engineering schematic,",
            "diagram": "detailed diagram, cross-section view,",
            "isometric": "isometric projection, 3D technical view,",
            "blueprint": "architectural blueprint, construction plan,",
            "engineering": "engineering drawing, precise measurements,"
        }

        # Стилевые префиксы
        style_prefixes = {
            "blueprint": "blueprint style, white lines on blue background, technical precision,",
            "technical_drawing": "black and white technical drawing, precise lines, professional,",
            "architectural": "architectural style, clean lines, professional rendering,",
            "engineering": "engineering drawing style, technical annotation, measurement marks,"
        }

        # Получаем префиксы
        type_prefix = type_prefixes.get(schematic_type, type_prefixes["technical"])
        style_prefix = style_prefixes.get(style, style_prefixes["technical_drawing"])

        # Строим финальный промпт
        # Переводим описание на английский (упрощенно)
        # В реальном проекте можно добавить API перевода

        # Базовый словарь для строительных терминов
        translations = {
            "трещина": "crack",
            "стена": "wall",
            "фундамент": "foundation",
            "перекрытие": "floor slab",
            "колонна": "column",
            "балка": "beam",
            "крыша": "roof",
            "дефект": "defect",
            "схема": "schematic",
            "узел": "joint detail",
            "соединение": "connection",
            "армирование": "reinforcement",
            "бетон": "concrete",
            "кирпич": "brick"
        }

        # Простой перевод через словарь
        description_en = description.lower()
        for ru, en in translations.items():
            description_en = description_en.replace(ru, en)

        # Формируем финальный промпт
        final_prompt = (
            f"{style_prefix} {type_prefix} "
            f"{description_en}, "
            f"high detail, precise lines, professional quality, "
            f"technical accuracy, clean composition, "
            f"construction details, engineering precision, "
            f"monochromatic, technical illustration style"
        )

        logger.info(f"📝 Промпт: {final_prompt[:100]}...")
        return final_prompt

    async def img2img(
        self,
        image_bytes: bytes,
        prompt: str,
        negative_prompt: str = None,
        denoising_strength: float = 0.5,
        steps: int = 20
    ) -> Optional[BytesIO]:
        """
        Image-to-Image генерация (улучшение существующего изображения)

        Args:
            image_bytes: Исходное изображение
            prompt: Промпт для преобразования
            negative_prompt: Негативный промпт
            denoising_strength: Сила изменения (0-1, рекомендуется 0.3-0.7)
            steps: Количество шагов

        Returns:
            BytesIO с результатом или None
        """
        try:
            # Кодируем изображение в base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            if negative_prompt is None:
                negative_prompt = "low quality, blurry, distorted"

            payload = {
                "init_images": [image_base64],
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "denoising_strength": denoising_strength,
                "steps": steps,
                "cfg_scale": 7.0,
            }

            logger.info(f"🎨 Img2Img обработка...")

            response = requests.post(
                f"{self.api_url}/sdapi/v1/img2img",
                json=payload,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"❌ SD Img2Img ошибка: {response.status_code}")
                return None

            result = response.json()

            if 'images' in result and len(result['images']) > 0:
                image_data = base64.b64decode(result['images'][0])
                logger.info("✅ Img2Img успешно завершен")
                return BytesIO(image_data)

            return None

        except Exception as e:
            logger.error(f"❌ Ошибка Img2Img: {e}")
            return None

    def get_available_models(self) -> List[Dict]:
        """
        Получить список доступных моделей

        Returns:
            Список моделей
        """
        try:
            response = requests.get(
                f"{self.api_url}/sdapi/v1/sd-models",
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка получения моделей: {e}")
            return []

    def get_available_samplers(self) -> List[str]:
        """
        Получить список доступных сэмплеров

        Returns:
            Список названий сэмплеров
        """
        try:
            response = requests.get(
                f"{self.api_url}/sdapi/v1/samplers",
                timeout=5
            )
            if response.status_code == 200:
                samplers = response.json()
                return [s['name'] for s in samplers]
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка получения сэмплеров: {e}")
            return []


def initialize_sd_generator() -> Optional[StableDiffusionGenerator]:
    """
    Инициализирует Stable Diffusion генератор

    Returns:
        Экземпляр StableDiffusionGenerator или None
    """
    try:
        api_url = os.getenv('SD_API_URL')

        if not api_url:
            logger.warning("⚠️ SD_API_URL не найден в переменных окружения")
            return None

        generator = StableDiffusionGenerator(api_url)

        # Проверяем доступность API
        if generator.check_connection():
            logger.info("✅ Stable Diffusion генератор успешно инициализирован")
            return generator
        else:
            logger.warning("⚠️ Stable Diffusion API недоступен")
            return None

    except Exception as e:
        logger.error(f"❌ Ошибка инициализации SD генератора: {e}")
        return None
