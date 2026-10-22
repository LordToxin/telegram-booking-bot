from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Category(BaseModel):
    id: Optional[int] = None
    name: str
    icon: str = "✨"


class Service(BaseModel):
    id: Optional[int] = None
    category_id: int
    name: str
    duration_minutes: int = 60
    price: float
    description: Optional[str] = ""
    is_active: bool = True


class Master(BaseModel):
    id: Optional[int] = None
    name: str
    specialization: str = "Мастер универсал"
    phone: Optional[str] = None
    is_active: bool = True


class Client(BaseModel):
    id: Optional[int] = None
    telegram_id: int
    full_name: str
    phone: str
    created_at: Optional[datetime] = None


class Booking(BaseModel):
    id: Optional[int] = None
    client_id: int
    service_id: int
    master_id: int
    booking_date: str  # YYYY-MM-DD
    start_time: str    # HH:MM
    end_time: str      # HH:MM
    status: str = "CONFIRMED"  # CONFIRMED, COMPLETED, CANCELLED
    notes: Optional[str] = ""
    created_at: Optional[datetime] = None
