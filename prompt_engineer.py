"""
Модуль промпт-инженеринга для качественной генерации строительных схем
Использует Claude/Gemini для создания детальных промптов
"""

import os
import logging
from typing import Optional, Dict
from openai import OpenAI

logger = logging.getLogger(__name__)


class ConstructionPromptEngineer:
    """Класс для создания качественных промптов для генерации строительных схем"""

    def __init__(self):
        """Инициализация промпт-инженера"""
        self.claude_api_key = os.getenv('XAI_API_KEY')

        # Словарь строительных терминов RU -> EN
        self.construction_terms = {
            # Элементы конструкций
            "фундамент": "foundation",
            "стена": "wall",
            "перекрытие": "floor slab, ceiling",
            "крыша": "roof",
            "колонна": "column, pillar",
            "балка": "beam",
            "плита": "slab, plate",
            "опора": "support, bearing",
            "ферма": "truss",
            "каркас": "frame, framework",
            "перегородка": "partition wall",
            "лестница": "staircase, stairs",
            "окно": "window",
            "дверь": "door",
            "проём": "opening",

            # Дефекты
            "трещина": "crack, fissure",
            "скол": "chip, spall",
            "отслоение": "delamination, peeling",
            "коррозия": "corrosion, rust",
            "протечка": "leak, water damage",
            "деформация": "deformation, warping",
            "разрушение": "failure, deterioration",
            "выбоина": "pothole, cavity",
            "высол": "efflorescence",
            "влага": "moisture, dampness",

            # Материалы
            "бетон": "concrete",
            "железобетон": "reinforced concrete",
            "кирпич": "brick, masonry",
            "металл": "metal, steel",
            "дерево": "wood, timber",
            "арматура": "reinforcement, rebar",
            "гипсокартон": "drywall, plasterboard",
            "штукатурка": "plaster, stucco",
            "изоляция": "insulation",

            # Виды схем
            "схема": "schematic, diagram",
            "чертёж": "drawing, blueprint",
            "разрез": "section, cross-section",
            "узел": "detail, joint",
            "план": "plan, layout",
            "фасад": "facade, elevation",
            "аксонометрия": "axonometric view",
            "изометрия": "isometric projection",

            # Технические характеристики
            "размер": "dimension, size",
            "толщина": "thickness",
            "высота": "height",
            "ширина": "width",
            "длина": "length",
            "нагрузка": "load",
            "прочность": "strength",
            "несущая способность": "load-bearing capacity",
        }

        logger.info("✅ ConstructionPromptEngineer инициализирован")

    def enhance_prompt(
        self,
        user_request: str,
        schematic_type: str = "technical",
        use_ai: bool = True
    ) -> Dict[str, str]:
        """
        Улучшает промпт пользователя для генерации

        Args:
            user_request: Запрос пользователя на русском
            schematic_type: Тип схемы (technical, blueprint, isometric)
            use_ai: Использовать ли AI для улучшения (Claude)

        Returns:
            Dict с полями: prompt, negative_prompt, style_hint
        """
        try:
            if use_ai and self.claude_api_key:
                # Используем Claude для создания продвинутого промпта
                return self._enhance_with_claude(user_request, schematic_type)
            else:
                # Используем шаблоны и словарь терминов
                return self._enhance_with_templates(user_request, schematic_type)

        except Exception as e:
            logger.error(f"❌ Ошибка улучшения промпта: {e}")
            # Fallback на простой перевод
            return self._enhance_with_templates(user_request, schematic_type)

    def _enhance_with_claude(
        self,
        user_request: str,
        schematic_type: str
    ) -> Dict[str, str]:
        """
        Использует Claude для создания детального промпта

        Args:
            user_request: Запрос на русском
            schematic_type: Тип схемы

        Returns:
            Dict с промптами
        """
        try:
            client = anthropic.OpenAI(api_key=self.claude_api_key, base_url="https://api.x.ai/v1")

            system_prompt = f"""Ты - эксперт по созданию промптов для AI-генерации технических строительных изображений.

Твоя задача: превратить запрос пользователя в детальный, точный промпт на английском языке для Stable Diffusion.

Требования:
1. Промпт должен быть НА АНГЛИЙСКОМ ЯЗЫКЕ
2. Описывать технический стиль изображения (не фотографию!)
3. Включать конкретные технические детали
4. Быть понятным для AI-модели генерации изображений
5. Тип схемы: {schematic_type}

Формат ответа (строго следуй):
PROMPT: [детальный промпт на английском]
NEGATIVE: [негативный промпт - что НЕ должно быть на изображении]
STYLE: [краткое описание стиля]"""

            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": f"Создай детальный промпт для генерации строительной схемы:\n\n\"{user_request}\""
                }],
                system=system_prompt
            )

            response_text = message.content[0].text

            # Парсим ответ
            prompt = ""
            negative_prompt = ""
            style_hint = ""

            for line in response_text.split('\n'):
                if line.startswith('PROMPT:'):
                    prompt = line.replace('PROMPT:', '').strip()
                elif line.startswith('NEGATIVE:'):
                    negative_prompt = line.replace('NEGATIVE:', '').strip()
                elif line.startswith('STYLE:'):
                    style_hint = line.replace('STYLE:', '').strip()

            # Если не распарсилось, используем весь текст как промпт
            if not prompt:
                prompt = response_text.strip()

            logger.info(f"✅ Claude создал промпт: {prompt[:100]}...")

            return {
                "prompt": prompt or self._simple_translate(user_request),
                "negative_prompt": negative_prompt or self._default_negative_prompt(schematic_type),
                "style_hint": style_hint or schematic_type
            }

        except Exception as e:
            logger.error(f"❌ Ошибка Claude промпт-инженеринга: {e}")
            return self._enhance_with_templates(user_request, schematic_type)

    def _enhance_with_templates(
        self,
        user_request: str,
        schematic_type: str
    ) -> Dict[str, str]:
        """
        Улучшает промпт с помощью шаблонов (без AI)

        Args:
            user_request: Запрос на русском
            schematic_type: Тип схемы

        Returns:
            Dict с промптами
        """
        # Переводим запрос
        translated = self._simple_translate(user_request)

        # Шаблоны для разных типов
        templates = {
            "technical": (
                "technical drawing, engineering schematic, {content}, "
                "precise lines, professional quality, monochromatic, "
                "technical illustration, clear details, measurement marks"
            ),
            "blueprint": (
                "architectural blueprint, construction plan, {content}, "
                "white lines on blue background, technical precision, "
                "professional rendering, clean composition"
            ),
            "isometric": (
                "isometric projection, 3D technical view, {content}, "
                "axonometric drawing, professional engineering style, "
                "clear perspective, technical accuracy"
            ),
            "diagram": (
                "detailed diagram, cross-section view, {content}, "
                "technical illustration, annotated, professional style, "
                "clear labeling, engineering precision"
            ),
        }

        template = templates.get(schematic_type, templates["technical"])
        prompt = template.format(content=translated)

        return {
            "prompt": prompt,
            "negative_prompt": self._default_negative_prompt(schematic_type),
            "style_hint": schematic_type
        }

    def _simple_translate(self, text: str) -> str:
        """
        Простой перевод с помощью словаря терминов

        Args:
            text: Текст на русском

        Returns:
            Переведенный текст
        """
        text_lower = text.lower()
        result = text_lower

        # Заменяем известные термины
        for ru, en in self.construction_terms.items():
            if ru in result:
                result = result.replace(ru, en)

        return result

    def _default_negative_prompt(self, schematic_type: str) -> str:
        """
        Возвращает негативный промпт по умолчанию

        Args:
            schematic_type: Тип схемы

        Returns:
            Негативный промпт
        """
        base_negative = (
            "low quality, blurry, distorted, bad anatomy, "
            "watermark, signature, text, letters, words, "
            "username, artist name"
        )

        # Для технических схем добавляем запрет на реализм
        if schematic_type in ["technical", "blueprint", "diagram"]:
            base_negative += (
                ", photo, photograph, realistic, photorealistic, "
                "people, humans, faces, portrait, "
                "colorful, vibrant colors, painting, sketch"
            )

        return base_negative

    def get_suggested_parameters(
        self,
        schematic_type: str
    ) -> Dict[str, any]:
        """
        Возвращает рекомендуемые параметры генерации для типа схемы

        Args:
            schematic_type: Тип схемы

        Returns:
            Dict с параметрами
        """
        parameters = {
            "technical": {
                "steps": 25,
                "cfg_scale": 7.0,
                "width": 1024,
                "height": 1024,
                "sampler": "DPM++ 2M Karras",
            },
            "blueprint": {
                "steps": 30,
                "cfg_scale": 7.5,
                "width": 1024,
                "height": 768,
                "sampler": "Euler a",
            },
            "isometric": {
                "steps": 28,
                "cfg_scale": 7.5,
                "width": 1024,
                "height": 1024,
                "sampler": "DPM++ 2M Karras",
            },
            "diagram": {
                "steps": 25,
                "cfg_scale": 7.0,
                "width": 1024,
                "height": 768,
                "sampler": "DPM++ 2M Karras",
            },
        }

        return parameters.get(schematic_type, parameters["technical"])


def initialize_prompt_engineer() -> ConstructionPromptEngineer:
    """
    Инициализирует промпт-инженера

    Returns:
        Экземпляр ConstructionPromptEngineer
    """
    try:
        engineer = ConstructionPromptEngineer()
        logger.info("✅ Prompt Engineer инициализирован")
        return engineer
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации Prompt Engineer: {e}")
        return None
