from pydantic import BaseModel
from typing import Optional,List
from decimal import Decimal

class VenueBase(BaseModel):
    name: Optional[str]
    location: Optional[str]
    capacity: Optional[int]
    seats: Optional[int]


class VenuesResponse(VenueBase):
    id: int

    class Config:
        from_attributes = True


class VenueZoneResponse(BaseModel):
    id: int
    venue_id: Optional[int]
    name: Optional[str]
    price: Optional[Decimal]
    capacity: Optional[int]

    class Config:
        from_attributes = True


class VenueZoneCreate(BaseModel):
    name: str
    capacity: int
    price: Optional[Decimal] = None


class VenueCreate(BaseModel):
    name: str
    location: str
    capacity: int
    seats: int
    zones: List[VenueZoneCreate]

##  seats

class CreateSeatsRequest(BaseModel):
    venue_id: int
    zone_id: int
    rows: list[str]
    seats_per_row: int

class SeatResponse(BaseModel):
    id: int
    row_label: str
    seat_label: str
    zone_id: int
    venue_id: int

    class Config:
        from_attributes = True


class VenueZoneSeatsResponse(BaseModel):
    zone_id: int
    zone_name: str
    seats: List[SeatResponse]