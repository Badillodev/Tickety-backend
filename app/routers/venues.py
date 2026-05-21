from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from collections import defaultdict
from app.database import get_db
import app.models.models as models
import app.schemas.venues as schemas
from app.routers.auth import get_current_user
from datetime import datetime
from sqlalchemy import asc
router = APIRouter(prefix="/venues", tags=["Venues"])


# =========================
# 🔍 GET PAGINADO
# =========================
@router.get("", response_model=List[schemas.VenuesResponse])
def get_venues(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(models.Venues).filter(models.Venues.deleted == 0).filter(models.Venues.created_by == current_user['id']).order_by(
        asc(models.Venues.name),         
    )

    return query.offset(skip).limit(limit).all()

# =========================
# 🔍 GET PAGINADO
# =========================
@router.get("/my_venues", response_model=List[schemas.VenuesResponse])
def my_venues(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(models.Venues).filter(models.Venues.deleted == 0).filter(models.Venues.created_by == current_user['id']).order_by(
        asc(models.Venues.name),         
    )
    return query.all()




# =========================
# 🔍 GET BY ID
# =========================

@router.get("/{venue_id}", response_model=schemas.VenuesResponse)
def get_venue_by_id(
    venue_id: int,
    db: Session = Depends(get_db)
):
    venue = (
        db.query(models.Venues)
        .filter(
            models.Venues.id == venue_id,
            models.Venues.deleted == 0
        )
        .first()
    )

    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    return venue

# =========================
# 🔍 DELETE
# =========================
@router.delete("/{venue_id}")
def delete_venue(
    venue_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    venue = (
        db.query(models.Venues)
        .filter(models.Venues.id == venue_id)
        .first()
    )

    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    if venue.deleted == 1:
        raise HTTPException(status_code=400, detail="Venue already deleted")
    
        # ✅ CHECK DE PROPIEDAD
    if str(venue.created_by) != str(current_user["id"]):
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para eliminar este evento"
        )

    venue.deleted = 1

    db.commit()

    return {"message": "Venue deleted successfully"}

@router.post("", response_model=schemas.VenuesResponse)
def create_venue(
    data: schemas.VenueCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # 1. crear venue
    venue = models.Venues(
        name=data.name,
        location=data.location,
        capacity=data.capacity,
        seats=data.seats,
        created_by=current_user['id'],
        deleted=False
    )

    db.add(venue)
    db.commit()
    db.refresh(venue)

    # 2. crear zones
    for zone in data.zones:
        db_zone = models.VenueZone(
            venue_id=venue.id,
            name=zone.name,
            capacity=zone.capacity,
            price=zone.price,
            deleted=False
        )
        db.add(db_zone)

    db.commit()

    return venue


@router.put("/{venue_id}", response_model=schemas.VenuesResponse)
def update_venue(
    venue_id: int,
    data: schemas.VenueCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    venue = (
        db.query(models.Venues)
        .filter(models.Venues.id == venue_id, models.Venues.deleted == 0)
        .first()
    )

    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")


    # 1. update venue
    venue.name = data.name
    venue.location = data.location
    venue.capacity = data.capacity
    venue.seats = data.seats
    venue.updated_by = current_user['id']
    venue.updated_at = datetime.today()
    db.commit()

    # 2. soft delete zones existentes
    db.query(models.VenueZone).filter(
        models.VenueZone.venue_id == venue_id
    ).update({"deleted": True})

    db.commit()

    # 3. crear nuevas zones
    for zone in data.zones:
        db.add(models.VenueZone(
            venue_id=venue_id,
            name=zone.name,
            capacity=zone.capacity,
            price=zone.price,
            deleted=False,
            created_at= datetime.today()
        ))

    db.commit()

    return venue



@router.get("/{venue_id}/zones", response_model=List[schemas.VenueZoneResponse])
def get_zones_by_venue(
    venue_id: int,
    db: Session = Depends(get_db)
):
    # 👇 comprobamos que el venue existe y no está eliminado
    venue = (
        db.query(models.Venues)
        .filter(
            models.Venues.id == venue_id,
            models.Venues.deleted == 0
        )
        .first()
    )

    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    # 👇 obtenemos zonas no eliminadas
    zones = (
        db.query(models.VenueZone)
        .filter(
            models.VenueZone.venue_id == venue_id,
            models.VenueZone.deleted == 0
        )
        .all()
    )

    return zones

###################
###### seats ######
###################

@router.post("/{venue_id}/seats", response_model=list[schemas.SeatResponse])
def create_seats_for_venue(
    venue_id: int,
    request: schemas.CreateSeatsRequest,
    db: Session = Depends(get_db)
):
    # -----------------------
    # check venue exists
    # -----------------------
    venue = db.query(models.Venues).filter(
        models.Venues.id == venue_id,
        models.Venues.deleted == 0
    ).first()

    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    new_seats = []

    # -----------------------
    # create seats
    # -----------------------
    for row in request.rows:
        for i in range(1, request.seats_per_row + 1):

            seat = models.Seat(
                venue_id=venue_id,
                zone_id=request.zone_id,
                row_label=row,
                seat_label=str(i),
                deleted=False
            )

            db.add(seat)
            db.flush()  # para obtener ID sin commit

            new_seats.append(seat)

    db.commit()

    return new_seats


@router.get("/{venue_id}/seats", response_model=List[schemas.VenueZoneSeatsResponse])
def get_zone_seats_by_venue(
    venue_id: int,
    db: Session = Depends(get_db)
):
    # -----------------------
    # check venue exists
    # -----------------------
    venue = (
        db.query(models.Venues)
        .filter(
            models.Venues.id == venue_id,
            models.Venues.deleted == 0
        )
        .first()
    )

    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    # -----------------------
    # zones
    # -----------------------
    zones = (
        db.query(models.VenueZone)
        .filter(
            models.VenueZone.venue_id == venue_id,
            models.VenueZone.deleted == 0
        )
        .all()
    )

    # -----------------------
    # seats
    # -----------------------
    seats = (
        db.query(models.Seat)
        .filter(
            models.Seat.venue_id == venue_id,
            models.Seat.deleted == 0
        )
        .all()
    )

    # -----------------------
    # group seats by zone
    # -----------------------
    seats_by_zone = defaultdict(list)

    for seat in seats:
        seats_by_zone[seat.zone_id].append(seat)

    # -----------------------
    # build response
    # -----------------------
    result = []

    for zone in zones:
        result.append({
            "zone_id": zone.id,
            "zone_name": zone.name,
            "seats": seats_by_zone.get(zone.id, [])
        })

    return result

@router.get("/{venue_id}/seats/{event_id}")
def get_event_zone_seats_by_venue(
    venue_id: int,
    event_id: int,
    db: Session = Depends(get_db)
):

    # -----------------------
    # check venue exists
    # -----------------------
    venue = (
        db.query(models.Venues)
        .filter(
            models.Venues.id == venue_id,
            models.Venues.deleted == 0
        )
        .first()
    )

    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    # -----------------------
    # check event exists
    # -----------------------
    event = (
        db.query(models.Event)
        .filter(models.Event.id == event_id)
        .first()
    )

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # -----------------------
    # zones
    # -----------------------
    zones = (
        db.query(models.VenueZone)
        .filter(
            models.VenueZone.venue_id == venue_id,
            models.VenueZone.deleted == 0
        )
        .all()
    )

    # -----------------------
    # all physical seats
    # -----------------------
    seats = (
        db.query(models.Seat)
        .filter(
            models.Seat.venue_id == venue_id,
            models.Seat.deleted == 0
        )
        .all()
    )

    # -----------------------
    # event seats (REAL STATUS)
    # -----------------------
    event_seats = (
        db.query(models.EventSeat)
        .filter(models.EventSeat.event_id == event_id)
        .all()
    )

    # map: seat_id -> status
    seat_status_map = {
        es.seat_id: es.status
        for es in event_seats
    }

    # -----------------------
    # zone pricing (PRICE PER ZONE)
    # -----------------------
    zone_pricing = (
        db.query(models.TicketZonePricing)
        .filter(
            models.TicketZonePricing.event_id == event_id
        )
        .all()
    )

    # map: zone_id -> price
    zone_price_map = {
        zp.zone_id: zp.price
        for zp in zone_pricing
    }

    # -----------------------
    # group by zone
    # -----------------------
    seats_by_zone = defaultdict(list)

    for seat in seats:

        seats_by_zone[seat.zone_id].append({
            "id": seat.id,
            "row_label": seat.row_label,
            "seat_label": seat.seat_label,
            "zone_id": seat.zone_id,
            "venue_id": seat.venue_id,

            # 🔥 ESTADO REAL DEL ASIENTO
            "status": seat_status_map.get(
                seat.id,
                models.SeatStatus.AVAILABLE
            ),

            # 💰 PRECIO POR ZONA
            "price": zone_price_map.get(seat.zone_id, 0)
        })

    # -----------------------
    # build response
    # -----------------------
    result = []

    for zone in zones:
        result.append({
            "zone_id": zone.id,
            "zone_name": zone.name,
            "seats": seats_by_zone.get(zone.id, [])
        })

    return result


@router.get("/{venue_id}/zones/{zone_id}/seats", response_model=List[schemas.SeatResponse])
def get_seats_by_zone(
    venue_id: int,
    zone_id: int,
    db: Session = Depends(get_db)
):
    # -----------------------
    # check venue exists
    # -----------------------
    venue = db.query(models.Venues).filter(
        models.Venues.id == venue_id,
        models.Venues.deleted == 0
    ).first()

    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    # -----------------------
    # check zone exists
    # -----------------------
    zone = db.query(models.VenueZone).filter(
        models.VenueZone.id == zone_id,
        models.VenueZone.venue_id == venue_id,
        models.VenueZone.deleted == 0
    ).first()

    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    # -----------------------
    # seats only for that zone
    # -----------------------
    seats = db.query(models.Seat).filter(
        models.Seat.venue_id == venue_id,
        models.Seat.zone_id == zone_id,
        models.Seat.deleted == 0
    ).all()

    return seats


@router.delete("/{venue_id}/seats")
def delete_venue_seats(
    venue_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    venue = db.query(models.Venues).filter(
        models.Venues.id == venue_id,
        models.Venues.deleted == 0,
        models.Venues.created_by == current_user['id']
    ).first()

    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    db.query(models.Seat).filter(
        models.Seat.venue_id == venue_id
    ).update({"deleted": True})

    db.commit()

    return {"message": "Venue seats deleted successfully"}


@router.delete("/{venue_id}/zones/{zone_id}/seats")
def delete_zone_seats(
    venue_id: int,
    zone_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    venue = db.query(models.Venues).filter(
        models.Venues.id == venue_id,
        models.Venues.deleted == 0,
        models.Venues.created_by == current_user['id']
    ).first()

    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    zone = db.query(models.VenueZone).filter(
        models.VenueZone.id == zone_id,
        models.VenueZone.venue_id == venue_id,
        models.VenueZone.deleted == 0
    ).first()

    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    db.query(models.Seat).filter(
        models.Seat.venue_id == venue_id,
        models.Seat.zone_id == zone_id
    ).update({"deleted": True})

    db.commit()

    return {"message": "Zone seats deleted successfully"}