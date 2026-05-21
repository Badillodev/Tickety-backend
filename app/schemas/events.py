from pydantic import BaseModel,field_validator,ConfigDict
from datetime import datetime
from typing import Optional, Any, List
from enum import Enum
from decimal import Decimal


class EventType(str, Enum):
    GENERAL = "GENERAL"
    SEATED = "SEATED"
    PASS = "PASS"


class EventCreate(BaseModel):
    title: str
    artist: str
    genre: str
    event_date: datetime
    location: str
    venue: str
    event_type: EventType
    seat_map: Optional[Any] = None
    created_by: int

class TicketPackCreate(BaseModel):
    name: str
    description: Optional[str]
    price: float
    capacity: int
    
class TicketPack(BaseModel):
    id:int
    name: str
    description: Optional[str]
    price: float
    capacity: int

class ZonePricingCreate(BaseModel):
    zone_id: int
    zone_name: Optional[str] = None
    price: float
    
class ZonePricing(BaseModel):
    id:int
    zone_id: int
    zone_name: Optional[str] = None
    price: float
    

class EventUpdate(BaseModel):
    title: Optional[str]
    artist: Optional[str]
    genre: Optional[str]
    image: Optional[str]
    price:Optional[Decimal] = None
    event_date: Optional[datetime]
    location: Optional[str]
    venue: Optional[str]
    venue_id: Optional[int]
    event_type: Optional[EventType]
    seat_map: Optional[Any]
    zone_pricing: Optional[List[ZonePricingCreate]] = None
    ticket_packs: Optional[List[TicketPackCreate]] = None

    


# 👇 IMPORTANTE: NO auditoría aquí
class EventResponse(BaseModel):
    id: int
    title: str
    artist: str
    genre: str
    event_date: datetime
    location: str
    venue: str
    event_type: Optional[EventType]
    price: Optional[float]
    venue_id: Optional[int]
    seat_map: Optional[Any]
    image:Optional[str]
    sales_active:Optional[int]

    class Config:
        from_attributes = True



class RecurringConfig(BaseModel):
    enabled: bool = False
    days_of_week: Optional[List[int]] = None
    end_date: Optional[str] = None



class GetEventWithRecurring(BaseModel):
    id:int
    title: str
    artist: str
    event_date: datetime
    location: Optional[str] = None
    venue: Optional[str] = None
    venue_id: Optional[int] = None
    event_type: Optional[str] = None
    price: Optional[float] = None
    genre: Optional[str] = None
    image: Optional[str] = None
    seat_map: Optional[Any] = None
    zone_pricing: Optional[List[ZonePricingCreate]] = []
    created_by: Optional[int] = None
    ticket_packs: Optional[List[TicketPack]] = []
    recurring: Optional[RecurringConfig] = None

    @field_validator("event_date", mode="before")
    @classmethod
    def parse_event_date(cls, value):
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value



class EventCreateWithRecurring(BaseModel):
    title: str
    artist: str
    event_date: datetime
    location: Optional[str] = None
    venue: Optional[str] = None
    venue_id: Optional[int] = None
    event_type: Optional[str] = None
    price: Optional[float] = None
    genre: Optional[str] = None
    image: Optional[str] = None
    seat_map: Optional[Any] = None
    zone_pricing: Optional[List[ZonePricingCreate]] = []
    created_by: Optional[int] = None
    ticket_packs: Optional[List[TicketPackCreate]] = []
    recurring: Optional[RecurringConfig] = None

    @field_validator("event_date", mode="before")
    @classmethod
    def parse_event_date(cls, value):
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value
    


class PricingRuleCreate(BaseModel):
    days_before: int
    price_multiplier: float
    description: str

class PricingRule(BaseModel):
    id: int
    event_id: int
    days_before: int
    price_multiplier: float
    description: Optional[str]

    model_config = ConfigDict(from_attributes=True)