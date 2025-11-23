"""
Database models
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float,
    ForeignKey, Enum, JSON, BigInteger, Index
)
from sqlalchemy.orm import relationship
import enum

from .base import Base


class UserRole(str, enum.Enum):
    """Роли пользователей"""
    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"


class DefectSeverity(str, enum.Enum):
    """Степень критичности дефекта"""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class RequestType(str, enum.Enum):
    """Тип запроса"""
    TEXT = "text"
    PHOTO = "photo"
    VOICE = "voice"
    DOCUMENT = "document"


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    language = Column(String(10), default="ru", nullable=False)

    # Статистика
    total_requests = Column(Integer, default=0)
    total_photos = Column(Integer, default=0)
    total_voice = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)

    # Relationships
    requests = relationship("Request", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    project_members = relationship("ProjectMember", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.telegram_id} ({self.username})>"


class Request(Base):
    """Модель запроса пользователя"""
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Тип и содержимое запроса
    request_type = Column(Enum(RequestType), nullable=False)
    message_text = Column(Text, nullable=True)
    caption = Column(Text, nullable=True)

    # Файлы
    photo_url = Column(String(500), nullable=True)
    voice_url = Column(String(500), nullable=True)
    document_url = Column(String(500), nullable=True)

    # Ответ
    response_text = Column(Text, nullable=True)
    response_tokens = Column(Integer, default=0)

    # Анализ дефекта
    defect_type = Column(String(100), nullable=True)
    defect_severity = Column(Enum(DefectSeverity), nullable=True)
    mentioned_regulations = Column(JSON, nullable=True)  # Список упомянутых нормативов

    # Геолокация
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(String(500), nullable=True)

    # Метаданные
    processing_time = Column(Float, default=0)  # Время обработки в секундах
    cached = Column(Boolean, default=False)  # Был ли ответ из кеша

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="requests")

    # Indexes
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_defect_type', 'defect_type'),
    )

    def __repr__(self):
        return f"<Request {self.id} by User {self.user_id}>"


class Project(Base):
    """Модель проекта (для групповой работы)"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    address = Column(String(500), nullable=True)

    # Геолокация проекта
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Статус
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="projects")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    defects = relationship("Defect", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project {self.id}: {self.name}>"


class ProjectMember(Base):
    """Модель участника проекта"""
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    role = Column(String(50), default="member")  # owner, admin, member, viewer

    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_members")

    __table_args__ = (
        Index('idx_project_user', 'project_id', 'user_id', unique=True),
    )

    def __repr__(self):
        return f"<ProjectMember project={self.project_id} user={self.user_id}>"


class Defect(Base):
    """Модель дефекта в проекте"""
    __tablename__ = "defects"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    # Основная информация
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    defect_type = Column(String(100), nullable=True)
    severity = Column(Enum(DefectSeverity), nullable=False)

    # Статус
    status = Column(String(50), default="open")  # open, in_progress, resolved, closed

    # Файлы
    photo_urls = Column(JSON, nullable=True)  # Массив URL фотографий

    # Геолокация
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_description = Column(String(500), nullable=True)

    # Нормативы
    regulations = Column(JSON, nullable=True)
    recommendations = Column(Text, nullable=True)

    # Назначение
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="defects")

    __table_args__ = (
        Index('idx_project_status', 'project_id', 'status'),
        Index('idx_severity', 'severity'),
    )

    def __repr__(self):
        return f"<Defect {self.id}: {self.title}>"


class Analytics(Base):
    """Модель для аналитики и статистики"""
    __tablename__ = "analytics"

    id = Column(Integer, primary_key=True, index=True)

    # Период
    date = Column(DateTime, nullable=False, index=True)
    period_type = Column(String(20), nullable=False)  # hourly, daily, weekly, monthly

    # Метрики
    total_requests = Column(Integer, default=0)
    total_users = Column(Integer, default=0)
    new_users = Column(Integer, default=0)
    photo_requests = Column(Integer, default=0)
    text_requests = Column(Integer, default=0)
    voice_requests = Column(Integer, default=0)

    # Дефекты
    defects_found = Column(Integer, default=0)
    critical_defects = Column(Integer, default=0)
    major_defects = Column(Integer, default=0)
    minor_defects = Column(Integer, default=0)

    # Производительность
    avg_response_time = Column(Float, default=0)
    cache_hit_rate = Column(Float, default=0)

    # Top нормативы (JSON: {"СП 63.13330.2018": 15, ...})
    top_regulations = Column(JSON, nullable=True)

    # Top типы дефектов
    top_defect_types = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_date_period', 'date', 'period_type', unique=True),
    )

    def __repr__(self):
        return f"<Analytics {self.date} ({self.period_type})>"


class PDFReport(Base):
    """Модель PDF отчета"""
    __tablename__ = "pdf_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)

    # Информация об отчете
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Файл
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0)  # В байтах

    # Содержимое отчета (JSON)
    content_data = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<PDFReport {self.id}: {self.title}>"
