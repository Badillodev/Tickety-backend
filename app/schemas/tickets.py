from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
# =========================
class TicketCreate(BaseModel):
    event_id: int
    venue_id: int
    user_id: int
    price: float
    seat_number: Optional[str] = None
    buyer_email: Optional[str] = None


class Event(BaseModel):
    id: int
    title: Optional[str]
    artist: Optional[str]
    genre: Optional[str]
    #price:Optional[Decimal] = None
    event_date: Optional[datetime]
    location: Optional[str]
    venue: Optional[str]
    venue_id: Optional[int]
    image:str
    event_type: Optional[str]

    # seat_map: Optional[Any]


    model_config = ConfigDict(from_attributes=True)

class TicketSeat(BaseModel):
    row_label: Optional[str] = None
    seat_label: Optional[str] = None
    zone_name: Optional[str] = None

class Pack(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    capacity: Optional[int] = None
    event_id: int

    model_config = ConfigDict(from_attributes=True)

# =========================
# RESPONSE
# =========================
class Ticket(BaseModel):
    id: int
    event_id: int
    venue_id: Optional[int]
    price: float
    seat_number: Optional[str] = None
    ticket_code: str
    attendee_name: Optional[str]
    attendee_surname: Optional[str]
    attendee_email: Optional[str]
    attendee_phone: Optional[str]
    qr_code: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    pack: Optional[Pack] = None
    event: Event 
    seat: Optional[TicketSeat] = None
     # 👇 importante para SQLAlchemy
    model_config = ConfigDict(from_attributes=True)
    
class SelectedSeat(BaseModel):
    seat_id: int
    zone_id: int
    


class TicketSeat(BaseModel):
    row_label: str | None
    seat_label: str | None
    zone_name: str | None


class TicketMeResponse(BaseModel):
    id: int
    event_id: int
    venue_id: Optional[int]
    price: float
    seat_number: Optional[str] = None
    ticket_code: str
    attendee_name: Optional[str]
    attendee_surname: Optional[str]
    attendee_email: Optional[str]
    attendee_phone: Optional[str]
    pack_name: Optional[str] = None
    pack_description: Optional[str] = None
    qr_code: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    event: Event 
    seat: Optional[TicketSeat] = None
     # 👇 importante para SQLAlchemy
    model_config = ConfigDict(from_attributes=True)
    
class TicketGroup(BaseModel):
    event: Event
    tickets: list[Ticket]

    class Config:
        from_attributes = True