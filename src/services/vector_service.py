"""
Vector Database Service для RAG (Retrieval-Augmented Generation)
Используется для поиска релевантных фрагментов из строительных нормативов
"""

import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from config.settings import settings

logger = logging.getLogger(__name__)


class VectorService:
    """
    Сервис для работы с векторной базой данных
    Используется для семантического поиска по строительным нормативам
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True

        # Путь к базе данных
        self.db_path = Path(settings.VECTOR_DB_PATH if hasattr(settings, 'VECTOR_DB_PATH') else './data/chromadb')
        self.db_path.mkdir(parents=True, exist_ok=True)

        # Инициализация ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Embedding function - используем OpenAI embeddings
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=settings.OPENAI_API_KEY,
            model_name="text-embedding-3-small"  # Более быстрая и дешевая модель
        )

        # Коллекции для разных типов документов
        self.collections = {
            'snip': self._get_or_create_collection('construction_snip'),
            'gost': self._get_or_create_collection('construction_gost'),
            'sp': self._get_or_create_collection('construction_sp'),
            'cases': self._get_or_create_collection('construction_cases'),  # Практические кейсы
        }

        logger.info("VectorService initialized successfully")

    def _get_or_create_collection(self, name: str):
        """Получить или создать коллекцию"""
        try:
            return self.client.get_or_create_collection(
                name=name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            logger.error(f"Error creating collection {name}: {e}")
            raise

    def add_document(
        self,
        collection_type: str,
        document_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Добавить документ в векторную базу

        Args:
            collection_type: Тип коллекции (snip, gost, sp, cases)
            document_id: Уникальный ID документа
            text: Текст документа
            metadata: Метаданные документа

        Returns:
            bool: Успешность операции
        """
        try:
            collection = self.collections.get(collection_type)
            if not collection:
                logger.error(f"Unknown collection type: {collection_type}")
                return False

            # Разбиваем длинный текст на чанки
            chunks = self._split_text(text, chunk_size=1000, overlap=100)

            ids = []
            documents = []
            metadatas = []

            for i, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_chunk_{i}"
                ids.append(chunk_id)
                documents.append(chunk)

                chunk_metadata = metadata.copy() if metadata else {}
                chunk_metadata.update({
                    'document_id': document_id,
                    'chunk_index': i,
                    'total_chunks': len(chunks)
                })
                metadatas.append(chunk_metadata)

            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )

            logger.info(f"Added document {document_id} to {collection_type} ({len(chunks)} chunks)")
            return True

        except Exception as e:
            logger.error(f"Error adding document: {e}", exc_info=True)
            return False

    def search(
        self,
        query: str,
        collection_types: Optional[List[str]] = None,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Поиск релевантных документов

        Args:
            query: Поисковый запрос
            collection_types: Типы коллекций для поиска (None = все)
            n_results: Количество результатов

        Returns:
            List[Dict]: Список релевантных документов
        """
        try:
            if collection_types is None:
                collection_types = list(self.collections.keys())

            all_results = []

            for coll_type in collection_types:
                collection = self.collections.get(coll_type)
                if not collection:
                    continue

                try:
                    results = collection.query(
                        query_texts=[query],
                        n_results=n_results
                    )

                    # Форматируем результаты
                    if results and results['documents'] and len(results['documents'][0]) > 0:
                        for i in range(len(results['documents'][0])):
                            all_results.append({
                                'collection': coll_type,
                                'document': results['documents'][0][i],
                                'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                                'distance': results['distances'][0][i] if results.get('distances') else 0
                            })
                except Exception as e:
                    logger.warning(f"Error searching in {coll_type}: {e}")
                    continue

            # Сортируем по релевантности (меньшее расстояние = более релевантно)
            all_results.sort(key=lambda x: x['distance'])

            return all_results[:n_results]

        except Exception as e:
            logger.error(f"Error searching: {e}", exc_info=True)
            return []

    def _split_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """
        Разбить текст на чанки с перекрытием

        Args:
            text: Исходный текст
            chunk_size: Размер чанка
            overlap: Размер перекрытия

        Returns:
            List[str]: Список чанков
        """
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + chunk_size

            # Если не последний чанк, пытаемся разбить по границе предложения
            if end < text_length:
                # Ищем конец предложения
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start:
                    end = sentence_end + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap if end < text_length else end

        return chunks

    def clear_all(self):
        """Очистить все коллекции"""
        for name, collection in self.collections.items():
            try:
                # Delete collection and recreate
                self.client.delete_collection(name=collection.name)
                logger.info(f"Cleared collection: {name}")
            except Exception as e:
                logger.warning(f"Could not clear collection {name}: {e}")

        # Recreate collections
        self.collections = {
            'snip': self._get_or_create_collection('construction_snip'),
            'gost': self._get_or_create_collection('construction_gost'),
            'sp': self._get_or_create_collection('construction_sp'),
        }

    def get_collection_stats(self) -> Dict[str, int]:
        """Получить статистику по коллекциям"""
        stats = {}
        for name, collection in self.collections.items():
            try:
                stats[name] = collection.count()
            except:
                stats[name] = 0
        return stats


# Singleton instance
_vector_service_instance = None


def get_vector_service() -> VectorService:
    """Получить singleton instance VectorService"""
    global _vector_service_instance
    if _vector_service_instance is None:
        _vector_service_instance = VectorService()
    return _vector_service_instance
