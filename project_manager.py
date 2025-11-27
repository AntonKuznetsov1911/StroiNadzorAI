"""
Модуль для работы с проектами и файлами
Загрузка, хранение и анализ проектной документации
"""

import os
import logging
from pathlib import Path
from datetime import datetime
import json
import hashlib
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Папка для проектов
PROJECTS_DIR = Path("user_projects")
PROJECTS_DIR.mkdir(exist_ok=True)


class Project:
    """Класс для работы с проектом"""
    
    def __init__(self, user_id: int, project_name: str):
        self.user_id = user_id
        self.project_name = project_name
        self.project_dir = PROJECTS_DIR / str(user_id) / project_name
        self.project_dir.mkdir(parents=True, exist_ok=True)
        
        self.metadata_file = self.project_dir / "metadata.json"
        self.files_dir = self.project_dir / "files"
        self.files_dir.mkdir(exist_ok=True)
        
        self.load_metadata()
    
    def load_metadata(self):
        """Загрузка метаданных проекта"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                "name": self.project_name,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "files": [],
                "description": "",
                "tags": []
            }
            self.save_metadata()
    
    def save_metadata(self):
        """Сохранение метаданных"""
        self.metadata["updated_at"] = datetime.now().isoformat()
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
    
    def add_file(self, file_path: str, file_type: str, description: str = "") -> Dict:
        """
        Добавление файла в проект
        
        Args:
            file_path: путь к файлу
            file_type: тип файла (image, pdf, dwg, doc, etc)
            description: описание файла
            
        Returns:
            dict: информация о добавленном файле
        """
        try:
            # Генерируем уникальное имя файла
            file_hash = hashlib.md5(open(file_path, 'rb').read()).hexdigest()[:8]
            original_name = Path(file_path).name
            extension = Path(file_path).suffix
            new_filename = f"{file_hash}_{original_name}"
            
            # Копируем файл в проект
            new_filepath = self.files_dir / new_filename
            
            import shutil
            shutil.copy2(file_path, new_filepath)
            
            # Добавляем в метаданные
            file_info = {
                "id": file_hash,
                "original_name": original_name,
                "filename": new_filename,
                "type": file_type,
                "description": description,
                "added_at": datetime.now().isoformat(),
                "size_bytes": os.path.getsize(new_filepath)
            }
            
            self.metadata["files"].append(file_info)
            self.save_metadata()
            
            logger.info(f"✅ Файл добавлен в проект: {new_filename}")
            return {"success": True, "file_info": file_info}
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления файла: {e}")
            return {"success": False, "error": str(e)}
    
    def list_files(self) -> List[Dict]:
        """Список всех файлов проекта"""
        return self.metadata.get("files", [])
    
    def get_file_path(self, file_id: str) -> Optional[str]:
        """Получить путь к файлу по ID"""
        for file_info in self.metadata.get("files", []):
            if file_info["id"] == file_id:
                filepath = self.files_dir / file_info["filename"]
                if filepath.exists():
                    return str(filepath)
        return None
    
    def get_project_summary(self) -> str:
        """Получить краткую информацию о проекте"""
        files_count = len(self.metadata.get("files", []))
        total_size = sum(f["size_bytes"] for f in self.metadata.get("files", []))
        
        summary = f"""
📁 Проект: {self.project_name}
📅 Создан: {self.metadata.get("created_at", "")}
📅 Обновлён: {self.metadata.get("updated_at", "")}
📄 Файлов: {files_count}
💾 Размер: {total_size / 1024 / 1024:.2f} МБ
📝 Описание: {self.metadata.get("description", "Нет описания")}
🏷️ Теги: {', '.join(self.metadata.get("tags", []))}
        """
        return summary.strip()
    
    def update_description(self, description: str):
        """Обновить описание проекта"""
        self.metadata["description"] = description
        self.save_metadata()
    
    def add_tag(self, tag: str):
        """Добавить тег к проекту"""
        if "tags" not in self.metadata:
            self.metadata["tags"] = []
        if tag not in self.metadata["tags"]:
            self.metadata["tags"].append(tag)
            self.save_metadata()

    def add_conversation_entry(self, question: str, answer: str, entry_type: str = "qa"):
        """
        Добавить запись диалога в проект

        Args:
            question: вопрос пользователя
            answer: ответ AI
            entry_type: тип записи (qa, note, calculation, etc)
        """
        if "conversation_log" not in self.metadata:
            self.metadata["conversation_log"] = []

        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": entry_type,
            "question": question,
            "answer": answer
        }

        self.metadata["conversation_log"].append(entry)
        self.save_metadata()

    def get_conversation_log(self) -> List[Dict]:
        """Получить журнал работы над проектом"""
        return self.metadata.get("conversation_log", [])

    def get_log_summary(self) -> str:
        """Получить краткую сводку по журналу"""
        log = self.get_conversation_log()
        if not log:
            return "Журнал работы пуст"

        total_entries = len(log)
        first_date = log[0]["timestamp"][:10] if log else ""
        last_date = log[-1]["timestamp"][:10] if log else ""

        return f"Записей: {total_entries} | С {first_date} по {last_date}"


def get_user_projects(user_id: int) -> List[str]:
    """Получить список проектов пользователя"""
    user_dir = PROJECTS_DIR / str(user_id)
    if not user_dir.exists():
        return []
    
    projects = []
    for item in user_dir.iterdir():
        if item.is_dir():
            projects.append(item.name)
    
    return projects


def create_project(user_id: int, project_name: str) -> Dict:
    """Создать новый проект"""
    try:
        project = Project(user_id, project_name)
        return {
            "success": True,
            "project": project,
            "message": f"Проект {project_name} создан"
        }
    except Exception as e:
        logger.error(f"❌ Ошибка создания проекта: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def load_project(user_id: int, project_name: str) -> Optional[Project]:
    """Загрузить существующий проект"""
    try:
        project = Project(user_id, project_name)
        return project
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки проекта: {e}")
        return None
