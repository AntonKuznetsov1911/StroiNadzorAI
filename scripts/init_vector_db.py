"""
Скрипт для инициализации векторной БД (ChromaDB)
Загружает строительные нормативы из construction_knowledge.py
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.vector_service import get_vector_service
from data.construction_knowledge import CONSTRUCTION_KNOWLEDGE
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_vector_database():
    """Инициализация векторной базы данных"""
    logger.info("Starting vector database initialization...")

    vector_service = get_vector_service()

    # Очищаем существующие данные
    logger.info("Clearing existing data...")
    try:
        vector_service.clear_all()
    except:
        pass  # Ignore if collections don't exist

    # Загружаем нормативы
    total_documents = 0

    for code, normative in CONSTRUCTION_KNOWLEDGE.items():
        logger.info(f"Processing {code}: {normative['title']}")

        for section_name, section_content in normative['sections'].items():
            # Формируем документ
            document = f"""
{normative['title']}
РАЗДЕЛ: {section_name.replace('_', ' ').upper()}

{section_content.strip()}
"""

            # Метаданные
            metadata = {
                'code': code,
                'title': normative['title'],
                'section': section_name,
                'type': 'normative'
            }

            # Добавляем в векторную БД
            doc_id = f"{code}_{section_name}"

            try:
                vector_service.add_document(
                    doc_id=doc_id,
                    text=document,
                    metadata=metadata
                )
                total_documents += 1
                logger.info(f"  ✓ Added: {doc_id}")
            except Exception as e:
                logger.error(f"  ✗ Error adding {doc_id}: {e}")

    logger.info(f"\n✅ Vector database initialized successfully!")
    logger.info(f"📊 Total documents: {total_documents}")
    logger.info(f"📚 Normatives: {len(CONSTRUCTION_KNOWLEDGE)}")

    # Тестовый поиск
    logger.info("\n🔍 Testing search...")
    test_queries = [
        "трещины в бетоне допустимая ширина",
        "класс бетона B25 прочность",
        "защитный слой арматуры"
    ]

    for query in test_queries:
        results = vector_service.search(query, n_results=2)
        logger.info(f"\nQuery: {query}")
        logger.info(f"Found {len(results)} results")
        for i, result in enumerate(results[:1], 1):
            logger.info(f"  {i}. {result.get('metadata', {}).get('code')} - {result.get('metadata', {}).get('section')}")


if __name__ == "__main__":
    init_vector_database()
