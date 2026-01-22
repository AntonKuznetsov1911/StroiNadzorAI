"""
СтройНадзорAI - Normative RAG System
=====================================
Retrieval-Augmented Generation для нормативных документов РФ

Компоненты:
- Vector DB (ChromaDB) для хранения эмбеддингов
- PDF Parser для извлечения текста из нормативов
- Chunker для разбиения на пункты
- Semantic Search для поиска релевантных норм
- Integration API для использования в боте
"""

import os
import json
import hashlib
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

RAG_CONFIG = {
    "chunk_size": 500,           # Размер чанка в символах
    "chunk_overlap": 50,         # Перекрытие чанков
    "top_k": 5,                  # Количество результатов поиска
    "min_relevance_score": 0.7,  # Минимальный порог релевантности
    "embedding_model": "text-embedding-3-small",  # OpenAI модель
    "collection_name": "stroinadzor_norms",
}

# Путь к базе нормативов
NORMS_DIR = Path(__file__).parent / "norms_database"
CHROMA_DIR = Path(__file__).parent / "chroma_db"


# ============================================================================
# МОДЕЛИ ДАННЫХ
# ============================================================================

@dataclass
class NormativeDocument:
    """Нормативный документ"""
    id: str                      # Уникальный ID (hash)
    code: str                    # Код документа (СП 63.13330.2018)
    title: str                   # Название
    category: str                # Категория (СП, ГОСТ, СНиП, ФЗ)
    status: str                  # Статус (active, superseded, cancelled)
    effective_date: Optional[str]  # Дата введения
    source_file: Optional[str]   # Исходный файл


@dataclass
class NormativeChunk:
    """Фрагмент нормативного документа"""
    id: str                      # Уникальный ID чанка
    document_id: str             # ID родительского документа
    document_code: str           # Код документа
    section: str                 # Раздел/пункт (например "5.2.1")
    content: str                 # Текст чанка
    page: Optional[int]          # Номер страницы
    metadata: Dict               # Дополнительные метаданные


@dataclass
class SearchResult:
    """Результат поиска"""
    chunk: NormativeChunk
    relevance_score: float
    document: NormativeDocument


# ============================================================================
# VECTOR DATABASE (ChromaDB)
# ============================================================================

class NormativeVectorDB:
    """Векторная база данных для нормативов"""

    def __init__(self):
        self.client = None
        self.collection = None
        self.openai_client = None
        self._initialized = False

    def initialize(self) -> bool:
        """Инициализация базы данных"""
        try:
            import chromadb
            from chromadb.config import Settings

            # Создаём директорию если не существует
            CHROMA_DIR.mkdir(parents=True, exist_ok=True)

            # Инициализируем ChromaDB с персистентным хранилищем
            self.client = chromadb.PersistentClient(
                path=str(CHROMA_DIR),
                settings=Settings(anonymized_telemetry=False)
            )

            # Получаем или создаём коллекцию
            self.collection = self.client.get_or_create_collection(
                name=RAG_CONFIG["collection_name"],
                metadata={"description": "СтройНадзорAI нормативные документы РФ"}
            )

            # Инициализируем OpenAI для эмбеддингов
            from openai import OpenAI
            self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            self._initialized = True
            logger.info(f"✅ NormativeVectorDB инициализирована. Документов: {self.collection.count()}")
            return True

        except ImportError as e:
            logger.error(f"❌ Требуется установка: pip install chromadb openai")
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации VectorDB: {e}")
            return False

    def _get_embedding(self, text: str) -> List[float]:
        """Получение эмбеддинга текста через OpenAI"""
        if not self.openai_client:
            raise RuntimeError("OpenAI client не инициализирован")

        response = self.openai_client.embeddings.create(
            model=RAG_CONFIG["embedding_model"],
            input=text
        )
        return response.data[0].embedding

    def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Получение эмбеддингов для списка текстов"""
        if not self.openai_client:
            raise RuntimeError("OpenAI client не инициализирован")

        response = self.openai_client.embeddings.create(
            model=RAG_CONFIG["embedding_model"],
            input=texts
        )
        return [item.embedding for item in response.data]

    def add_chunks(self, chunks: List[NormativeChunk]) -> int:
        """Добавление чанков в базу"""
        if not self._initialized:
            raise RuntimeError("VectorDB не инициализирована")

        if not chunks:
            return 0

        # Подготавливаем данные
        ids = [chunk.id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [
            {
                "document_id": chunk.document_id,
                "document_code": chunk.document_code,
                "section": chunk.section,
                "page": chunk.page or 0,
                **chunk.metadata
            }
            for chunk in chunks
        ]

        # Получаем эмбеддинги батчами
        batch_size = 100
        embeddings = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batch_embeddings = self._get_embeddings_batch(batch)
            embeddings.extend(batch_embeddings)

        # Добавляем в коллекцию
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        logger.info(f"✅ Добавлено {len(chunks)} чанков в VectorDB")
        return len(chunks)

    def search(self, query: str, top_k: int = None, filter_dict: Dict = None) -> List[Dict]:
        """Семантический поиск по базе"""
        if not self._initialized:
            raise RuntimeError("VectorDB не инициализирована")

        top_k = top_k or RAG_CONFIG["top_k"]

        # Получаем эмбеддинг запроса
        query_embedding = self._get_embedding(query)

        # Выполняем поиск
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_dict,
            include=["documents", "metadatas", "distances"]
        )

        # Форматируем результаты
        search_results = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                # Конвертируем distance в relevance score (ChromaDB использует L2)
                distance = results["distances"][0][i] if results["distances"] else 0
                relevance = 1 / (1 + distance)  # Преобразование в score 0-1

                if relevance >= RAG_CONFIG["min_relevance_score"]:
                    search_results.append({
                        "id": doc_id,
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "relevance_score": round(relevance, 3)
                    })

        return search_results

    def get_stats(self) -> Dict:
        """Статистика базы данных"""
        if not self._initialized:
            return {"status": "not_initialized"}

        return {
            "status": "active",
            "total_chunks": self.collection.count(),
            "collection_name": RAG_CONFIG["collection_name"]
        }


# ============================================================================
# PDF PARSER
# ============================================================================

class NormativePDFParser:
    """Парсер PDF нормативных документов"""

    @staticmethod
    def parse_pdf(file_path: str) -> Tuple[str, List[Dict]]:
        """
        Извлечение текста из PDF
        Returns: (full_text, pages_list)
        """
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(file_path)
            pages = []
            full_text = ""

            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                pages.append({
                    "page": page_num,
                    "text": text
                })
                full_text += f"\n--- Страница {page_num} ---\n{text}"

            doc.close()
            return full_text, pages

        except ImportError:
            logger.error("❌ Требуется: pip install pymupdf")
            return "", []
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга PDF {file_path}: {e}")
            return "", []

    @staticmethod
    def extract_document_info(text: str, filename: str) -> Dict:
        """Извлечение метаданных документа из текста"""
        import re

        info = {
            "code": "",
            "title": "",
            "category": "unknown",
            "effective_date": None
        }

        # Определяем категорию по имени файла или тексту
        filename_upper = filename.upper()
        if "СП " in filename_upper or "SP " in filename_upper:
            info["category"] = "СП"
        elif "ГОСТ" in filename_upper or "GOST" in filename_upper:
            info["category"] = "ГОСТ"
        elif "СНИП" in filename_upper or "SNIP" in filename_upper:
            info["category"] = "СНиП"
        elif "ФЗ" in filename_upper or "FZ" in filename_upper:
            info["category"] = "ФЗ"
        elif "ПУЭ" in filename_upper:
            info["category"] = "ПУЭ"

        # Извлекаем код документа
        patterns = [
            r"(СП\s*\d+\.\d+\.\d+)",
            r"(ГОСТ\s*[\d\.\-]+)",
            r"(СНиП\s*[\d\.\-]+)",
            r"(ФЗ[\-\s]*\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text[:2000], re.IGNORECASE)
            if match:
                info["code"] = match.group(1).strip()
                break

        if not info["code"]:
            # Используем имя файла
            info["code"] = Path(filename).stem

        return info


# ============================================================================
# CHUNKER
# ============================================================================

class NormativeChunker:
    """Разбиение нормативных документов на чанки"""

    @staticmethod
    def chunk_by_sections(text: str, document_id: str, document_code: str) -> List[NormativeChunk]:
        """Разбиение текста на чанки по разделам/пунктам"""
        import re

        chunks = []

        # Паттерны для определения пунктов
        section_pattern = r"(\d+\.\d+(?:\.\d+)?)\s+"

        # Разбиваем по пунктам
        parts = re.split(section_pattern, text)

        current_section = "0"
        current_text = ""

        for i, part in enumerate(parts):
            if re.match(r"^\d+\.\d+", part):
                # Это номер пункта
                if current_text.strip():
                    chunk_id = hashlib.md5(
                        f"{document_id}_{current_section}_{current_text[:50]}".encode()
                    ).hexdigest()[:16]

                    chunks.append(NormativeChunk(
                        id=chunk_id,
                        document_id=document_id,
                        document_code=document_code,
                        section=current_section,
                        content=current_text.strip(),
                        page=None,
                        metadata={"type": "section"}
                    ))

                current_section = part
                current_text = ""
            else:
                current_text += part

        # Добавляем последний чанк
        if current_text.strip():
            chunk_id = hashlib.md5(
                f"{document_id}_{current_section}_{current_text[:50]}".encode()
            ).hexdigest()[:16]

            chunks.append(NormativeChunk(
                id=chunk_id,
                document_id=document_id,
                document_code=document_code,
                section=current_section,
                content=current_text.strip(),
                page=None,
                metadata={"type": "section"}
            ))

        # Если разбиение по пунктам не сработало, делаем по размеру
        if len(chunks) < 3:
            chunks = NormativeChunker.chunk_by_size(
                text, document_id, document_code,
                chunk_size=RAG_CONFIG["chunk_size"],
                overlap=RAG_CONFIG["chunk_overlap"]
            )

        return chunks

    @staticmethod
    def chunk_by_size(
        text: str,
        document_id: str,
        document_code: str,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[NormativeChunk]:
        """Разбиение текста на чанки фиксированного размера"""
        chunks = []

        # Разбиваем по предложениям для более естественного разделения
        sentences = text.replace('\n', ' ').split('. ')

        current_chunk = ""
        chunk_num = 0

        for sentence in sentences:
            if len(current_chunk) + len(sentence) < chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk.strip():
                    chunk_id = hashlib.md5(
                        f"{document_id}_chunk_{chunk_num}".encode()
                    ).hexdigest()[:16]

                    chunks.append(NormativeChunk(
                        id=chunk_id,
                        document_id=document_id,
                        document_code=document_code,
                        section=f"chunk_{chunk_num}",
                        content=current_chunk.strip(),
                        page=None,
                        metadata={"type": "size_chunk", "chunk_num": chunk_num}
                    ))
                    chunk_num += 1

                # Начинаем новый чанк с перекрытием
                words = current_chunk.split()
                overlap_text = " ".join(words[-overlap:]) if len(words) > overlap else ""
                current_chunk = overlap_text + " " + sentence + ". "

        # Добавляем последний чанк
        if current_chunk.strip():
            chunk_id = hashlib.md5(
                f"{document_id}_chunk_{chunk_num}".encode()
            ).hexdigest()[:16]

            chunks.append(NormativeChunk(
                id=chunk_id,
                document_id=document_id,
                document_code=document_code,
                section=f"chunk_{chunk_num}",
                content=current_chunk.strip(),
                page=None,
                metadata={"type": "size_chunk", "chunk_num": chunk_num}
            ))

        return chunks


# ============================================================================
# RAG SEARCH API
# ============================================================================

class NormativeRAG:
    """Основной класс RAG системы для нормативов"""

    def __init__(self):
        self.vector_db = NormativeVectorDB()
        self.documents: Dict[str, NormativeDocument] = {}
        self._initialized = False

    def initialize(self) -> bool:
        """Инициализация RAG системы"""
        if self.vector_db.initialize():
            self._initialized = True
            self._load_documents_index()
            logger.info("✅ NormativeRAG инициализирована")
            return True
        return False

    def _load_documents_index(self):
        """Загрузка индекса документов"""
        index_file = NORMS_DIR / "documents_index.json"
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for doc_data in data.get("documents", []):
                    doc = NormativeDocument(**doc_data)
                    self.documents[doc.id] = doc

    def _save_documents_index(self):
        """Сохранение индекса документов"""
        NORMS_DIR.mkdir(parents=True, exist_ok=True)
        index_file = NORMS_DIR / "documents_index.json"

        data = {
            "documents": [
                {
                    "id": doc.id,
                    "code": doc.code,
                    "title": doc.title,
                    "category": doc.category,
                    "status": doc.status,
                    "effective_date": doc.effective_date,
                    "source_file": doc.source_file
                }
                for doc in self.documents.values()
            ]
        }

        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def ingest_pdf(self, file_path: str, title: str = None, status: str = "active") -> bool:
        """Загрузка PDF документа в базу"""
        if not self._initialized:
            logger.error("RAG не инициализирована")
            return False

        try:
            # Парсим PDF
            full_text, pages = NormativePDFParser.parse_pdf(file_path)
            if not full_text:
                return False

            # Извлекаем метаданные
            filename = Path(file_path).name
            info = NormativePDFParser.extract_document_info(full_text, filename)

            # Создаём документ
            doc_id = hashlib.md5(f"{info['code']}_{filename}".encode()).hexdigest()[:16]

            document = NormativeDocument(
                id=doc_id,
                code=info["code"],
                title=title or info["code"],
                category=info["category"],
                status=status,
                effective_date=info.get("effective_date"),
                source_file=filename
            )

            # Разбиваем на чанки
            chunks = NormativeChunker.chunk_by_sections(full_text, doc_id, info["code"])

            # Добавляем в vector DB
            added = self.vector_db.add_chunks(chunks)

            # Сохраняем в индекс
            self.documents[doc_id] = document
            self._save_documents_index()

            logger.info(f"✅ Загружен документ {info['code']}: {added} чанков")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки {file_path}: {e}")
            return False

    def ingest_text(
        self,
        text: str,
        code: str,
        title: str,
        category: str = "manual",
        status: str = "active"
    ) -> bool:
        """Загрузка текстового документа в базу"""
        if not self._initialized:
            logger.error("RAG не инициализирована")
            return False

        try:
            doc_id = hashlib.md5(f"{code}_{title}".encode()).hexdigest()[:16]

            document = NormativeDocument(
                id=doc_id,
                code=code,
                title=title,
                category=category,
                status=status,
                effective_date=None,
                source_file=None
            )

            chunks = NormativeChunker.chunk_by_sections(text, doc_id, code)
            added = self.vector_db.add_chunks(chunks)

            self.documents[doc_id] = document
            self._save_documents_index()

            logger.info(f"✅ Загружен текстовый документ {code}: {added} чанков")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки текста {code}: {e}")
            return False

    def search(
        self,
        query: str,
        top_k: int = 5,
        category: str = None
    ) -> List[Dict]:
        """
        Поиск релевантных нормативов

        Args:
            query: Поисковый запрос
            top_k: Количество результатов
            category: Фильтр по категории (СП, ГОСТ, СНиП, ФЗ)

        Returns:
            Список результатов с релевантностью
        """
        if not self._initialized:
            logger.error("RAG не инициализирована")
            return []

        # Формируем фильтр
        filter_dict = None
        if category:
            filter_dict = {"category": category}

        # Выполняем поиск
        results = self.vector_db.search(query, top_k, filter_dict)

        # Обогащаем результаты информацией о документе
        enriched_results = []
        for result in results:
            doc_id = result["metadata"].get("document_id")
            document = self.documents.get(doc_id)

            enriched_results.append({
                "content": result["content"],
                "section": result["metadata"].get("section", ""),
                "document_code": result["metadata"].get("document_code", ""),
                "document_title": document.title if document else "",
                "document_category": document.category if document else "",
                "document_status": document.status if document else "",
                "relevance_score": result["relevance_score"]
            })

        return enriched_results

    def get_norm_citation(self, query: str) -> Optional[str]:
        """
        Получение цитаты из норматива для ответа

        Returns:
            Форматированная цитата или None
        """
        results = self.search(query, top_k=1)

        if not results:
            return None

        best = results[0]
        citation = (
            f"📚 **{best['document_code']}**"
            f"{' (п. ' + best['section'] + ')' if best['section'] else ''}\n\n"
            f"_{best['content'][:500]}{'...' if len(best['content']) > 500 else ''}_\n\n"
            f"📊 Релевантность: {best['relevance_score']:.0%}"
        )

        return citation

    def get_stats(self) -> Dict:
        """Статистика RAG системы"""
        db_stats = self.vector_db.get_stats()

        return {
            "initialized": self._initialized,
            "total_documents": len(self.documents),
            "documents_by_category": self._count_by_category(),
            "vector_db": db_stats
        }

    def _count_by_category(self) -> Dict[str, int]:
        """Подсчёт документов по категориям"""
        counts = {}
        for doc in self.documents.values():
            counts[doc.category] = counts.get(doc.category, 0) + 1
        return counts


# ============================================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ============================================================================

_rag_instance: Optional[NormativeRAG] = None


def get_normative_rag() -> Optional[NormativeRAG]:
    """Получение глобального экземпляра RAG"""
    global _rag_instance
    return _rag_instance


def init_normative_rag() -> bool:
    """Инициализация глобального RAG"""
    global _rag_instance

    _rag_instance = NormativeRAG()
    return _rag_instance.initialize()


# ============================================================================
# INTEGRATION API
# ============================================================================

async def search_norms_for_query(query: str, top_k: int = 3) -> List[Dict]:
    """
    API для поиска нормативов (для использования в боте)

    Args:
        query: Вопрос пользователя
        top_k: Количество результатов

    Returns:
        Список найденных нормативов
    """
    rag = get_normative_rag()
    if not rag:
        return []

    return rag.search(query, top_k)


async def get_norm_for_answer(query: str) -> Optional[str]:
    """
    Получение норматива для включения в ответ

    Args:
        query: Вопрос пользователя

    Returns:
        Форматированная цитата норматива или None
    """
    rag = get_normative_rag()
    if not rag:
        return None

    return rag.get_norm_citation(query)


def is_rag_available() -> bool:
    """Проверка доступности RAG системы"""
    rag = get_normative_rag()
    return rag is not None and rag._initialized
