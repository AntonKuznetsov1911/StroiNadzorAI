"""
Pydantic schemas for API
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """User response schema"""
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    language: str
    total_requests: int
    total_photos: int
    total_voice: int
    created_at: datetime
    last_activity: datetime

    class Config:
        from_attributes = True


class RequestResponse(BaseModel):
    """Request response schema"""
    id: int
    user_id: int
    request_type: str
    message_text: Optional[str]
    caption: Optional[str]
    response_text: Optional[str]
    defect_type: Optional[str]
    defect_severity: Optional[str]
    mentioned_regulations: Optional[List[str]]
    processing_time: float
    cached: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    """Project response schema"""
    id: int
    owner_id: int
    name: str
    description: Optional[str]
    address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnalyticsResponse(BaseModel):
    """Analytics response schema"""
    id: int
    date: datetime
    period_type: str
    total_requests: int
    total_users: int
    new_users: int
    photo_requests: int
    text_requests: int
    voice_requests: int
    defects_found: int
    critical_defects: int
    major_defects: int
    minor_defects: int
    avg_response_time: float
    cache_hit_rate: float
    top_regulations: Optional[dict]
    top_defect_types: Optional[dict]

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    """Overall statistics response"""
    total_users: int
    total_requests: int
    total_projects: int
    today_requests: int
    new_users_week: int
    avg_processing_time: float
    cache_hit_rate: float
