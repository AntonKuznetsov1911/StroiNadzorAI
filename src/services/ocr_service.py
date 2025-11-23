"""
OCR Service для распознавания текста из изображений и PDF
"""

import logging
from pathlib import Path
from typing import Optional

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logging.warning("Tesseract/PIL not installed. OCR will be disabled.")

try:
    import pdf2image
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logging.warning("pdf2image not installed. PDF OCR will be disabled.")

logger = logging.getLogger(__name__)


class OCRService:
    """Сервис для распознавания текста"""

    def __init__(self):
        """Инициализация сервиса"""
        if not TESSERACT_AVAILABLE:
            logger.warning("OCR service initialized without Tesseract")

    def extract_text_from_image(self, image_path: str, language: str = "rus+eng") -> str:
        """
        Извлечение текста из изображения

        Args:
            image_path: Путь к изображению
            language: Язык распознавания

        Returns:
            str: Распознанный текст
        """
        if not TESSERACT_AVAILABLE:
            raise RuntimeError("Tesseract is not installed")

        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, lang=language)
            logger.info(f"OCR extracted {len(text)} characters from image")
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            raise

    def extract_text_from_pdf(self, pdf_path: str, language: str = "rus+eng") -> str:
        """
        Извлечение текста из PDF

        Args:
            pdf_path: Путь к PDF файлу
            language: Язык распознавания

        Returns:
            str: Распознанный текст
        """
        if not TESSERACT_AVAILABLE or not PDF2IMAGE_AVAILABLE:
            raise RuntimeError("Tesseract or pdf2image is not installed")

        try:
            # Конвертируем PDF в изображения
            images = pdf2image.convert_from_path(pdf_path)

            # Распознаем текст с каждой страницы
            all_text = []
            for i, image in enumerate(images):
                logger.debug(f"Processing PDF page {i+1}/{len(images)}")
                text = pytesseract.image_to_string(image, lang=language)
                all_text.append(text)

            result = "\n\n".join(all_text)
            logger.info(f"OCR extracted {len(result)} characters from PDF")
            return result.strip()

        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise

    def is_available(self) -> bool:
        """
        Проверка доступности OCR

        Returns:
            bool: True если OCR доступен
        """
        return TESSERACT_AVAILABLE


# Singleton instance
_ocr_service_instance: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    """
    Получить экземпляр OCR service (singleton)

    Returns:
        OCRService: Экземпляр сервиса
    """
    global _ocr_service_instance
    if _ocr_service_instance is None:
        _ocr_service_instance = OCRService()
    return _ocr_service_instance
