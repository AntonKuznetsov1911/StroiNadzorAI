"""
LLM Council - Совет AI моделей для СтройНадзорAI
=================================================

Реализация концепции LLM Council от Andrej Karpathy:
1. Stage 1: Получение ответов от нескольких LLM параллельно
2. Stage 2: Перекрёстная оценка ответов (peer-review)
3. Stage 3: Синтез финального ответа "Председателем"

Модели:
- Grok (xAI) - технический анализ
- Claude (Anthropic) - экспертиза и нюансы
- Gemini (Google) - практические рекомендации
"""

import os
import asyncio
import logging
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# === КОНФИГУРАЦИЯ ===

# Модели совета
COUNCIL_MODELS = {
    "grok": {
        "name": "Grok-4",
        "model_id": "grok-4-1-fast",
        "specialty": "Технический анализ, расчёты, нормативы",
        "provider": "xai"
    },
    "claude": {
        "name": "Claude Sonnet 4.5",
        "model_id": "claude-sonnet-4-5-20250929",
        "specialty": "Детальный анализ, экспертиза, нюансы",
        "provider": "anthropic"
    },
    "gemini": {
        "name": "Gemini 1.5 Flash",
        "model_id": "gemini-1.5-flash",
        "specialty": "Практические рекомендации, визуализация",
        "provider": "google"
    }
}

# Председатель совета (формирует финальный ответ)
CHAIRMAN_MODEL = "claude"  # Claude лучше всего синтезирует информацию

# Ключевые слова для определения сложных вопросов
COMPLEX_QUESTION_KEYWORDS = [
    # Технические термины
    "расчёт", "расчет", "рассчитать", "вычислить",
    "нагрузка", "напряжение", "деформация", "прочность",
    "армирование", "арматура", "бетонирование", "бетон",
    "фундамент", "несущая способность", "осадка",
    "сейсмостойкость", "огнестойкость", "теплопроводность",
    
    # Нормативы
    "СП", "ГОСТ", "СНиП", "норматив", "требования",
    "соответствие", "нарушение", "допуск", "отклонение",
    
    # Юридические
    "экспертиза", "разрешение", "ввод в эксплуатацию",
    "приёмка", "акт", "протокол", "претензия", "неустойка",
    
    # Сложные ситуации
    "проблема", "дефект", "брак", "несоответствие",
    "как устранить", "что делать если", "почему",
    "сравни", "анализ", "оценка", "проверить",
    
    # Специальные условия
    "зимнее бетонирование", "особые условия", "сложный грунт",
    "подтопление", "карстовые", "просадочные"
]

# Минимальная длина вопроса для совета (слов)
MIN_COMPLEX_QUESTION_LENGTH = 15


# === ИНИЦИАЛИЗАЦИЯ КЛИЕНТОВ ===

def get_xai_client():
    """Получить xAI клиент"""
    try:
        from xai_client import XAIClient
        api_key = os.getenv("XAI_API_KEY")
        if api_key:
            return XAIClient(api_key=api_key)
    except Exception as e:
        logger.error(f"Ошибка инициализации xAI: {e}")
    return None


def get_claude_client():
    """Получить Claude клиент"""
    try:
        from anthropic import Anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            return Anthropic(api_key=api_key)
    except Exception as e:
        logger.error(f"Ошибка инициализации Claude: {e}")
    return None


def get_gemini_model():
    """Получить Gemini модель"""
    try:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        logger.error(f"Ошибка инициализации Gemini: {e}")
    return None


# === ОПРЕДЕЛЕНИЕ СЛОЖНОСТИ ВОПРОСА ===

def is_complex_question(question: str) -> Tuple[bool, str]:
    """
    Определить, является ли вопрос сложным и требующим LLM Council
    
    Returns:
        (is_complex, reason) - кортеж: сложный ли вопрос и причина
    """
    question_lower = question.lower()
    words = question.split()
    
    # Проверка длины
    if len(words) < 5:
        return False, "Слишком короткий вопрос"
    
    # Подсчёт ключевых слов
    keyword_count = 0
    found_keywords = []
    
    for keyword in COMPLEX_QUESTION_KEYWORDS:
        if keyword.lower() in question_lower:
            keyword_count += 1
            found_keywords.append(keyword)
    
    # Критерии сложности
    is_complex = False
    reason = ""
    
    # 1. Много ключевых слов (>= 2)
    if keyword_count >= 2:
        is_complex = True
        reason = f"Технически сложный вопрос (ключевые слова: {', '.join(found_keywords[:3])})"
    
    # 2. Длинный вопрос с хотя бы 1 ключевым словом
    elif len(words) >= MIN_COMPLEX_QUESTION_LENGTH and keyword_count >= 1:
        is_complex = True
        reason = f"Развёрнутый технический вопрос"
    
    # 3. Явные маркеры сложности
    elif any(marker in question_lower for marker in ["как правильно", "почему нельзя", "в чём разница", "что лучше"]):
        is_complex = True
        reason = "Вопрос требует экспертного сравнения"
    
    # 4. Упоминание нескольких нормативов
    normative_pattern = r'(СП|ГОСТ|СНиП)\s*[\d\.\-]+'
    normatives = re.findall(normative_pattern, question, re.IGNORECASE)
    if len(normatives) >= 2:
        is_complex = True
        reason = f"Упоминание нескольких нормативов ({len(normatives)} шт.)"
    
    return is_complex, reason


# === СИСТЕМНЫЕ ПРОМПТЫ ===

COUNCIL_SYSTEM_PROMPT = """Ты — эксперт-строитель с 20-летним стажем, специализирующийся на строительных нормативах РФ.

ТВОЯ РОЛЬ: {specialty}

ЗАДАЧА: Дать профессиональный, точный и практичный ответ на вопрос пользователя.

ТРЕБОВАНИЯ К ОТВЕТУ:
1. Ссылайся на конкретные СП, ГОСТ, СНиП с номерами пунктов
2. Используй профессиональную терминологию
3. Давай практические рекомендации из опыта
4. Если есть несколько подходов — укажи все с плюсами/минусами
5. Предупреди о возможных ошибках и последствиях

ФОРМАТ: Структурированный ответ с подзаголовками и списками.
ДЛИНА: 300-500 слов (достаточно детально, но не перегружено)."""


REVIEW_SYSTEM_PROMPT = """Ты — старший эксперт строительного надзора, оценивающий качество консультаций коллег.

ЗАДАЧА: Оцени ответы на строительный вопрос от анонимных экспертов.

КРИТЕРИИ ОЦЕНКИ (по 10-балльной шкале):
1. ТОЧНОСТЬ — соответствие нормативам РФ
2. ПОЛНОТА — все ли аспекты вопроса раскрыты
3. ПРАКТИЧНОСТЬ — можно ли применить на практике
4. ЯСНОСТЬ — понятно ли изложено

ДЛЯ КАЖДОГО ОТВЕТА УКАЖИ:
- Общая оценка (1-10)
- Сильные стороны
- Слабые стороны / что упущено
- Рекомендации по улучшению

ФОРМАТ ОТВЕТА:
```
ЭКСПЕРТ A: [оценка]/10
+ [сильные стороны]
- [слабые стороны]

ЭКСПЕРТ B: [оценка]/10
+ [сильные стороны]
- [слабые стороны]

ЭКСПЕРТ C: [оценка]/10
+ [сильные стороны]
- [слабые стороны]

ЛУЧШИЙ ОТВЕТ: [A/B/C]
ПОЧЕМУ: [причина]
```"""


CHAIRMAN_SYSTEM_PROMPT = """Ты — Председатель Совета экспертов СтройНадзорAI.

ЗАДАЧА: Синтезировать финальный ответ на основе мнений трёх экспертов.

У тебя есть:
1. Исходный вопрос пользователя
2. Ответы трёх экспертов (Grok, Claude, Gemini)
3. Перекрёстные оценки экспертов друг друга

ТВОЯ ЦЕЛЬ:
1. Взять лучшее из каждого ответа
2. Устранить противоречия (если есть)
3. Добавить недостающие важные детали
4. Сформировать единый, исчерпывающий ответ

СТРУКТУРА ФИНАЛЬНОГО ОТВЕТА:

🏛️ **РЕШЕНИЕ СОВЕТА ЭКСПЕРТОВ**

📋 **КРАТКИЙ ОТВЕТ**
[2-3 предложения — суть решения]

📚 **НОРМАТИВНАЯ БАЗА**
[Список применимых СП, ГОСТ, СНиП]

🔍 **ДЕТАЛЬНЫЙ АНАЛИЗ**
[Полный разбор вопроса с учётом всех мнений]

✅ **РЕКОМЕНДАЦИИ**
[Практические шаги]

⚠️ **ВАЖНЫЕ ПРЕДУПРЕЖДЕНИЯ**
[Риски, ошибки, на что обратить внимание]

💡 **ДОПОЛНИТЕЛЬНО**
[Полезные замечания от экспертов]

---
🤖 _Ответ подготовлен Советом AI: Grok + Claude + Gemini_
_Использован метод LLM Council для повышения качества_

СТИЛЬ: Профессиональный, но понятный. Без лишней воды."""


# === КЛАСС LLM COUNCIL ===

class LLMCouncil:
    """
    Совет AI моделей для ответов на сложные вопросы
    
    Этапы работы:
    1. Параллельный опрос всех моделей
    2. Перекрёстная оценка ответов
    3. Синтез финального ответа председателем
    """
    
    def __init__(self):
        self.xai_client = get_xai_client()
        self.claude_client = get_claude_client()
        self.gemini_model = get_gemini_model()
        
        # Проверяем доступность моделей
        self.available_models = []
        if self.xai_client:
            self.available_models.append("grok")
            logger.info("✅ LLM Council: Grok доступен")
        if self.claude_client:
            self.available_models.append("claude")
            logger.info("✅ LLM Council: Claude доступен")
        if self.gemini_model:
            self.available_models.append("gemini")
            logger.info("✅ LLM Council: Gemini доступен")
        
        self.is_available = len(self.available_models) >= 2
        
        if self.is_available:
            logger.info(f"✅ LLM Council инициализирован ({len(self.available_models)} модели)")
        else:
            logger.warning("⚠️ LLM Council недоступен (нужно минимум 2 модели)")
    
    async def _call_grok(self, messages: List[Dict], max_tokens: int = 2000) -> Optional[str]:
        """Вызов Grok API"""
        if not self.xai_client:
            return None
        
        try:
            response = self.xai_client.chat_completions_create(
                model=COUNCIL_MODELS["grok"]["model_id"],
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Grok error: {e}")
            return None
    
    async def _call_claude(self, system: str, messages: List[Dict], max_tokens: int = 2000) -> Optional[str]:
        """Вызов Claude API"""
        if not self.claude_client:
            return None
        
        try:
            # Фильтруем сообщения для Claude формата
            claude_messages = [m for m in messages if m["role"] != "system"]
            
            response = self.claude_client.messages.create(
                model=COUNCIL_MODELS["claude"]["model_id"],
                max_tokens=max_tokens,
                temperature=0.7,
                system=system,
                messages=claude_messages
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude error: {e}")
            return None
    
    async def _call_gemini(self, prompt: str) -> Optional[str]:
        """Вызов Gemini API"""
        if not self.gemini_model:
            return None
        
        try:
            response = self.gemini_model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return None
    
    async def stage1_get_opinions(self, question: str, context: str = "") -> Dict[str, str]:
        """
        Этап 1: Получение мнений от всех моделей параллельно
        
        Args:
            question: Вопрос пользователя
            context: Дополнительный контекст (история диалога)
        
        Returns:
            Dict с ответами от каждой модели
        """
        opinions = {}
        
        # Формируем промпты для каждой модели
        full_question = f"{context}\n\nВОПРОС: {question}" if context else f"ВОПРОС: {question}"
        
        # Параллельные вызовы
        tasks = []
        
        # Grok
        if "grok" in self.available_models:
            grok_messages = [
                {"role": "system", "content": COUNCIL_SYSTEM_PROMPT.format(
                    specialty=COUNCIL_MODELS["grok"]["specialty"]
                )},
                {"role": "user", "content": full_question}
            ]
            tasks.append(("grok", self._call_grok(grok_messages)))
        
        # Claude
        if "claude" in self.available_models:
            claude_system = COUNCIL_SYSTEM_PROMPT.format(
                specialty=COUNCIL_MODELS["claude"]["specialty"]
            )
            claude_messages = [{"role": "user", "content": full_question}]
            tasks.append(("claude", self._call_claude(claude_system, claude_messages)))
        
        # Gemini
        if "gemini" in self.available_models:
            gemini_prompt = f"""{COUNCIL_SYSTEM_PROMPT.format(
                specialty=COUNCIL_MODELS["gemini"]["specialty"]
            )}

{full_question}"""
            tasks.append(("gemini", self._call_gemini(gemini_prompt)))
        
        # Выполняем параллельно
        results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
        
        for i, (model_name, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, Exception):
                logger.error(f"Council {model_name} failed: {result}")
                opinions[model_name] = None
            else:
                opinions[model_name] = result
                logger.info(f"✅ Council получен ответ от {model_name}")
        
        return opinions
    
    async def stage2_review(self, question: str, opinions: Dict[str, str]) -> Dict[str, str]:
        """
        Этап 2: Перекрёстная оценка ответов
        
        Args:
            question: Исходный вопрос
            opinions: Ответы от этапа 1
        
        Returns:
            Dict с оценками от каждой модели
        """
        reviews = {}
        
        # Подготовка анонимизированных ответов
        valid_opinions = {k: v for k, v in opinions.items() if v}
        if len(valid_opinions) < 2:
            return {}
        
        # Маппинг для анонимизации
        model_labels = {"grok": "A", "claude": "B", "gemini": "C"}
        
        review_content = f"""ИСХОДНЫЙ ВОПРОС:
{question}

ОТВЕТЫ ЭКСПЕРТОВ:
"""
        for model, answer in valid_opinions.items():
            label = model_labels.get(model, "X")
            review_content += f"\n--- ЭКСПЕРТ {label} ---\n{answer}\n"
        
        # Получаем оценки от каждой доступной модели
        tasks = []
        
        if "grok" in self.available_models:
            grok_messages = [
                {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": review_content}
            ]
            tasks.append(("grok", self._call_grok(grok_messages, max_tokens=1000)))
        
        if "claude" in self.available_models:
            tasks.append(("claude", self._call_claude(
                REVIEW_SYSTEM_PROMPT,
                [{"role": "user", "content": review_content}],
                max_tokens=1000
            )))
        
        if "gemini" in self.available_models:
            gemini_prompt = f"{REVIEW_SYSTEM_PROMPT}\n\n{review_content}"
            tasks.append(("gemini", self._call_gemini(gemini_prompt)))
        
        # Выполняем параллельно
        results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
        
        for i, (model_name, _) in enumerate(tasks):
            result = results[i]
            if not isinstance(result, Exception) and result:
                reviews[model_name] = result
                logger.info(f"✅ Council получена оценка от {model_name}")
        
        return reviews
    
    async def stage3_synthesize(
        self, 
        question: str, 
        opinions: Dict[str, str], 
        reviews: Dict[str, str]
    ) -> str:
        """
        Этап 3: Синтез финального ответа Председателем
        
        Args:
            question: Исходный вопрос
            opinions: Ответы от этапа 1
            reviews: Оценки от этапа 2
        
        Returns:
            Финальный синтезированный ответ
        """
        # Формируем контент для Председателя
        synthesis_content = f"""ИСХОДНЫЙ ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{question}

=== ОТВЕТЫ ЭКСПЕРТОВ ===

"""
        for model, answer in opinions.items():
            if answer:
                model_info = COUNCIL_MODELS.get(model, {})
                synthesis_content += f"### {model_info.get('name', model)} ({model_info.get('specialty', '')})\n{answer}\n\n"
        
        if reviews:
            synthesis_content += "\n=== ПЕРЕКРЁСТНЫЕ ОЦЕНКИ ===\n\n"
            for model, review in reviews.items():
                model_info = COUNCIL_MODELS.get(model, {})
                synthesis_content += f"### Оценка от {model_info.get('name', model)}\n{review}\n\n"
        
        synthesis_content += """
=== ТВОЯ ЗАДАЧА ===
Синтезируй финальный ответ, объединив лучшее из всех мнений.
Следуй структуре из системного промпта."""
        
        # Вызываем Председателя (Claude по умолчанию)
        chairman_model = CHAIRMAN_MODEL
        
        if chairman_model == "claude" and self.claude_client:
            result = await self._call_claude(
                CHAIRMAN_SYSTEM_PROMPT,
                [{"role": "user", "content": synthesis_content}],
                max_tokens=3000
            )
        elif chairman_model == "grok" and self.xai_client:
            result = await self._call_grok([
                {"role": "system", "content": CHAIRMAN_SYSTEM_PROMPT},
                {"role": "user", "content": synthesis_content}
            ], max_tokens=3000)
        elif self.gemini_model:
            result = await self._call_gemini(
                f"{CHAIRMAN_SYSTEM_PROMPT}\n\n{synthesis_content}"
            )
        else:
            # Fallback: возвращаем лучший ответ из opinions
            result = list(opinions.values())[0] if opinions else "Не удалось сформировать ответ"
        
        return result or "Ошибка синтеза ответа"
    
    async def consult(
        self, 
        question: str, 
        context: str = "",
        skip_review: bool = False
    ) -> Dict:
        """
        Полная консультация Совета
        
        Args:
            question: Вопрос пользователя
            context: Контекст диалога
            skip_review: Пропустить этап оценки (быстрый режим)
        
        Returns:
            Dict с результатами всех этапов и финальным ответом
        """
        start_time = datetime.now()
        
        result = {
            "question": question,
            "models_used": self.available_models.copy(),
            "opinions": {},
            "reviews": {},
            "final_answer": "",
            "duration_seconds": 0,
            "success": False
        }
        
        try:
            # Этап 1: Получение мнений
            logger.info("🏛️ LLM Council: Этап 1 - Сбор мнений...")
            opinions = await self.stage1_get_opinions(question, context)
            result["opinions"] = opinions
            
            valid_opinions = {k: v for k, v in opinions.items() if v}
            if not valid_opinions:
                result["final_answer"] = "❌ Не удалось получить ответы от AI моделей"
                return result
            
            # Этап 2: Перекрёстная оценка (опционально)
            reviews = {}
            if not skip_review and len(valid_opinions) >= 2:
                logger.info("🏛️ LLM Council: Этап 2 - Перекрёстная оценка...")
                reviews = await self.stage2_review(question, valid_opinions)
                result["reviews"] = reviews
            
            # Этап 3: Синтез финального ответа
            logger.info("🏛️ LLM Council: Этап 3 - Синтез ответа...")
            final_answer = await self.stage3_synthesize(question, valid_opinions, reviews)
            result["final_answer"] = final_answer
            result["success"] = True
            
        except Exception as e:
            logger.error(f"LLM Council error: {e}")
            result["final_answer"] = f"❌ Ошибка Совета AI: {str(e)}"
        
        result["duration_seconds"] = (datetime.now() - start_time).total_seconds()
        logger.info(f"🏛️ LLM Council завершён за {result['duration_seconds']:.1f} сек")
        
        return result
    
    async def quick_consult(self, question: str, context: str = "") -> str:
        """
        Быстрая консультация (без этапа оценки)
        
        Returns:
            Только финальный ответ
        """
        result = await self.consult(question, context, skip_review=True)
        return result["final_answer"]


# === ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР ===

_council_instance = None

def get_llm_council() -> Optional[LLMCouncil]:
    """Получить экземпляр LLM Council (singleton)"""
    global _council_instance
    if _council_instance is None:
        _council_instance = LLMCouncil()
    return _council_instance if _council_instance.is_available else None


def is_council_available() -> bool:
    """Проверить доступность LLM Council"""
    council = get_llm_council()
    return council is not None and council.is_available


# === ТЕСТИРОВАНИЕ ===

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    
    load_dotenv()
    
    async def test_council():
        print("=== Тест LLM Council ===\n")
        
        council = get_llm_council()
        if not council:
            print("❌ LLM Council недоступен")
            return
        
        print(f"✅ Доступные модели: {council.available_models}\n")
        
        # Тест определения сложности
        questions = [
            "Привет",
            "Какие требования к бетону B25?",
            "Как правильно рассчитать армирование плиты перекрытия по СП 63.13330 с учётом нагрузок и требований к защитному слою бетона?",
        ]
        
        print("=== Тест определения сложности ===")
        for q in questions:
            is_complex, reason = is_complex_question(q)
            status = "✅ Сложный" if is_complex else "❌ Простой"
            print(f"{status}: {q[:50]}...")
            if is_complex:
                print(f"   Причина: {reason}")
        
        # Тест консультации
        print("\n=== Тест полной консультации ===")
        test_question = "Какие требования к защитному слою бетона для арматуры в фундаменте по СП 63.13330?"
        
        print(f"Вопрос: {test_question}\n")
        print("Запуск консультации...")
        
        result = await council.consult(test_question, skip_review=True)
        
        print(f"\n✅ Консультация завершена за {result['duration_seconds']:.1f} сек")
        print(f"Использованы модели: {result['models_used']}")
        print(f"\n=== ФИНАЛЬНЫЙ ОТВЕТ ===\n{result['final_answer'][:1000]}...")
    
    asyncio.run(test_council())
