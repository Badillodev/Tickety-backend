from pydantic import BaseModel, EmailStr
from typing import List, Optional
class Attendee(BaseModel):
    name: str
    surname: str
    email: EmailStr
    phone: str

class SelectedSeat(BaseModel):
    seat_id: int
    
class SelectedPackRequest(BaseModel):
    pack_id: int
    quantity: int
    zone_id: Optional[int] = None
    attendees: List[Attendee]


class OrderRequest(BaseModel):
    event_id: int
    payment_method: str
    quantity: int
    selected_seats: list[SelectedSeat] = []
    selected_packs: list[SelectedPackRequest] = []
    attendees: list[Attendee] = []