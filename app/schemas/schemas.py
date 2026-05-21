from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

class TicketPackResponse(BaseModel):
    id: int
    name: Optional[str]
    capacity: Optional[int]
    description: Optional[str]
    price: Optional[float]

    class Config:
        from_attributes = True


class TicketZonePricingResponse(BaseModel):
    id: int
    zone_id: int
    zone_name: Optional[str]
    price: Optional[float]

    class Config:
        from_attributes = True


class EventResponse(BaseModel):
    id: int
    title: str
    artist: str
    date: datetime
    location: str
    venue: str
    price: Decimal
    image: Optional[str] = None
    genre: str
    created_at: datetime
    ticket_packs: List[TicketPackResponse] = []
    zone_pricing: List[TicketZonePricingResponse] = []

    class Config:
        from_attributes = True  # 👈 importante para SQLAlchemy


class EventCreate(BaseModel):
    title: str
    artist: str
    date: datetime
    location: str
    venue: str
    price: Decimal = 0
    image: Optional[str] = None
    genre: str

class EventUpdate(BaseModel):
    title: Optional[str] = None
    artist: Optional[str] = None
    date: Optional[datetime] = None
    location: Optional[str] = None
    venue: Optional[str] = None
    price: Optional[Decimal] = None
    image: Optional[str] = None
    genre: Optional[str] = None


class ZonePricingUpdate(BaseModel):
    zone_id: int
    zone_name: str | None = None
    price: float

class TicketPackUpdate(BaseModel):
    name: str
    description: str | None = None
    price: float
    capacity: int


class EventUpdate(BaseModel):
    title: Optional[str]
    artist: Optional[str]
    event_date: Optional[datetime]
    location: Optional[str]
    venue: Optional[str]
    venue_id: Optional[int]
    event_type: Optional[str]
    price: Optional[float]
    image: Optional[str]
    genre: Optional[str]

    zone_pricing: Optional[list[ZonePricingUpdate]] = None
    ticket_packs: Optional[list[TicketPackUpdate]] = None


