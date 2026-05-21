from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
import app.models.models as models
import app.schemas.events as schemas
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload
from sqlalchemy import desc, asc, func, case
from app.routers.auth import get_current_user
import logging

router = APIRouter(prefix="/events", tags=["Events"])


# =========================
# 🔍 GET PAGINADO
# =========================
@router.get("", response_model=List[schemas.EventResponse])
def get_events(
    skip: int = 0,
    limit: int = 10,
    title: Optional[str] = None,
    artist: Optional[str] = None,
    genre: Optional[str] = None,
    event_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # ================================
    # 1️⃣ BASE QUERY (solo IDs paginados)
    # ================================
    base_query = db.query(models.Event.id).filter(models.Event.deleted == 0)

    if title:
        base_query = base_query.filter(models.Event.title.ilike(f"%{title}%"))

    if artist:
        base_query = base_query.filter(models.Event.artist.ilike(f"%{artist}%"))

    if genre:
        base_query = base_query.filter(models.Event.genre == genre)

    if event_type:
        base_query = base_query.filter(models.Event.event_type == event_type)

    base_query = base_query.order_by(
        desc(models.Event.sales_active),
        asc(models.Event.event_date)
    )

    paged_ids = base_query.offset(skip).limit(limit).subquery()

    # ================================
    # 2️⃣ SUBQUERY PRECIO MÍNIMO (TicketPack)
    # ================================
    sub_min_pass = (
        db.query(
            models.TicketPack.event_id,
            func.min(models.TicketPack.price).label("min_price")
        )
        .filter(models.TicketPack.deleted == 0)
        .group_by(models.TicketPack.event_id)
        .subquery()
    )
    
    # ================================
    # 2️⃣ SUBQUERY PRECIO MÍNIMO (SEATED)
    # ================================
    sub_min_seated = (
        db.query(
            models.TicketZonePricing.event_id,
            func.min(models.TicketZonePricing.price).label("min_price")
        )
        .filter(models.TicketZonePricing.deleted == 0)
        .group_by(models.TicketZonePricing.event_id)
        .subquery()
    )

    # ================================
    # 3️⃣ QUERY FINAL (solo eventos paginados)
    # ================================
    query = (
    db.query(
        models.Event,
        case(
            # 🎫 PASS
            (
                models.Event.event_type == "PASS",
                sub_min_pass.c.min_price
            ),

            # 💺 SEATED
            (
                models.Event.event_type == "SEATED",
                sub_min_seated.c.min_price
            ),

            # 🎟 GENERAL (default)
            else_=models.Event.price
        ).label("final_price")
    )
    .join(paged_ids, models.Event.id == paged_ids.c.id)
    .outerjoin(sub_min_pass, models.Event.id == sub_min_pass.c.event_id)
    .outerjoin(sub_min_seated, models.Event.id == sub_min_seated.c.event_id)
    .order_by(
        desc(models.Event.sales_active),
        asc(models.Event.event_date)
    )
)
    results = query.all()

    # ================================
    # 4️⃣ SERIALIZACIÓN
    # ================================
    response = []
    for event, final_price in results:
        event_dict = {
            **event.__dict__,
            "price": float(final_price) if final_price is not None else None
        }

        event_dict.pop("_sa_instance_state", None)
        response.append(event_dict)

    return response

@router.get("/my_events", response_model=List[schemas.EventResponse])
def my_events(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    logging.info(f"events - my_events - start ")
    query = db.query(models.Event).filter(
        models.Event.deleted == 0,
        models.Event.created_by == current_user["id"]
    ).order_by(
        desc(models.Event.sales_active),   
        asc(models.Event.event_date)       
    )

    return query.offset(skip).limit(limit).all()


# =========================
# 🔍 GET BY ID
# =========================
@router.get("/{event_id}", response_model=schemas.GetEventWithRecurring)
def get_event(event_id: int, db: Session = Depends(get_db)):

    event = db.query(models.Event).options(
        joinedload(models.Event.ticket_packs),
        joinedload(models.Event.zone_pricing),
        joinedload(models.Event.pricing_rules)
    ).filter(
        models.Event.id == event_id,
        models.Event.deleted == False
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return event



# =========================
# ✏️ UPDATE
# =========================
@router.put("/{event_id}", response_model=schemas.EventResponse)
def update_event(
    event_id: int,
    event_data: schemas.EventUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    event = db.query(models.Event).filter(
        models.Event.id == event_id,
        models.Event.deleted == False
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
     # ✅ CHECK DE PROPIEDAD
    if str(event.created_by) != str(current_user["id"]):
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para eliminar este evento"
        )

    data = event_data.dict(exclude_unset=True)

    # =========================
    # 1. CAMPOS BÁSICOS
    # =========================
    simple_fields = [
        "title", "artist", "event_date", "location",
        "venue", "venue_id", "event_type",
        "price", "image", "genre", "seat_map"
    ]

    for field in simple_fields:
        if field in data:
            setattr(event, field, data[field])


    # =========================
    # 2. ZONE PRICING (SEATED)
    # =========================
    if "zone_pricing" in data:
        # borrar antiguos
        db.query(models.TicketZonePricing).filter(
            models.TicketZonePricing.event_id == event_id
        ).delete()

        # crear nuevos
        if data["zone_pricing"]:
            for zone in data["zone_pricing"]:
                db.add(models.TicketZonePricing(
                    event_id=event_id,
                    zone_id=zone["zone_id"],
                    zone_name=zone.get("zone_name"),
                    price=zone["price"]
                ))

    # =========================
    # 3. TICKET PACKS (PASS)
    # =========================
    if "ticket_packs" in data:
        db.query(models.TicketPack).filter(
            models.TicketPack.event_id == event_id
        ).delete()

        if data["ticket_packs"]:
            for pack in data["ticket_packs"]:
                db.add(models.TicketPack(
                    event_id=event_id,
                    name=pack["name"],
                    description=pack.get("description"),
                    price=pack["price"],
                    capacity=pack["capacity"]
                ))

    db.commit()
    db.refresh(event)

    return event


# =========================
# 🗑 SOFT DELETE
# =========================
@router.delete("/{event_id}")
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # ✅ CHECK DE PROPIEDAD
    if str(event.created_by) != str(current_user["id"]):
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para eliminar este evento"
        )

    event.deleted = True
    db.commit()

    return {"message": "Event deleted (soft delete)"}

# =========================
# 🔁 TOGGLE SALES
# =========================
@router.patch("/{event_id}/toggle_sales", response_model=schemas.EventResponse)
def toggle_sales(event_id: int, db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)):

    event = db.query(models.Event).filter(
        models.Event.id == event_id,
        models.Event.deleted == 0
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # ✅ CHECK DE PROPIEDAD
    if str(event.created_by) != str(current_user["id"]):
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para eliminar este evento"
        )
    # 🔥 Toggle (invertir valor)
    event.sales_active = 0 if event.sales_active == 1 else 1

    db.commit()
    db.refresh(event)

    return event

# =========================
# 🔁 CREATE EVENT
# =========================
@router.post("/bulk")
def create_events_bulk(
    data: List[schemas.EventCreateWithRecurring] = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)

):
    created = []

    for event in data:

        recurring = event.recurring or schemas.RecurringConfig(enabled=False)
        base_date = event.event_date

        # =========================
        # CREATE FIRST EVENT
        # =========================
        new_event = models.Event(
            title=event.title,
            artist=event.artist,
            genre=event.genre,
            event_date=base_date,
            location=event.location,
            venue=event.venue,
            venue_id=event.venue_id,
            event_type=models.EventType(event.event_type),
            price=event.price,
            image=event.image,
            seat_map=event.seat_map,
            created_by=current_user["id"]
        )

        db.add(new_event)
        db.flush()  # obtener ID

        # =========================
        # INSERT TICKET PACKS
        # =========================
        if event.ticket_packs:
            for pack in event.ticket_packs:
                new_pack = models.TicketPack(
                    event_id=new_event.id,
                    name=pack.name,
                    description=pack.description or "",
                    price=pack.price,
                    capacity=pack.capacity
                )
                db.add(new_pack)

        # =========================
        # INSERT ZONE PRICING ⭐ NUEVO
        # =========================
        if getattr(event, "zone_pricing", None):
            for zone in event.zone_pricing:
                new_zone_price = models.TicketZonePricing(
                    event_id=new_event.id,
                    zone_id=zone.zone_id,
                    zone_name=zone.zone_name,
                    price=zone.price
                )
                db.add(new_zone_price)

        created.append(new_event)
        generate_event_seats(db,new_event.id,event.venue_id)

        # =========================
        # RECURRING LOGIC
        # =========================
        if recurring.enabled and recurring.days_of_week and recurring.end_date:

            current_date = base_date

            if isinstance(recurring.end_date, str):
                end_date = datetime.fromisoformat(recurring.end_date)
            else:
                end_date = recurring.end_date

            while current_date <= end_date:

                current_date += timedelta(days=1)

                if current_date.weekday() in recurring.days_of_week:

                    repeat_event = models.Event(
                        title=event.title,
                        artist=event.artist,
                        genre=event.genre,
                        event_date=current_date,
                        location=event.location,
                        venue=event.venue,
                        venue_id=event.venue_id,
                        event_type=models.EventType(event.event_type),
                        price=event.price,
                        image=event.image,
                        seat_map=event.seat_map,
                        created_by=current_user["id"]
                    )

                    db.add(repeat_event)
                    db.flush()

                    # =========================
                    # INSERT TICKET PACKS (REPEAT)
                    # =========================
                    if event.ticket_packs:
                        for pack in event.ticket_packs:
                            new_pack = models.TicketPack(
                                event_id=repeat_event.id,
                                name=pack.name,
                                description=pack.description or "",
                                price=pack.price,
                                capacity=pack.capacity
                            )
                            db.add(new_pack)

                    # =========================
                    # INSERT ZONE PRICING (REPEAT) ⭐
                    # =========================
                    if getattr(event, "zone_pricing", None):
                        for zone in event.zone_pricing:
                            new_zone_price = models.TicketZonePricing(
                                event_id=repeat_event.id,
                                zone_id=zone.zone_id,
                                zone_name=zone.zone_name,
                                price=zone.price
                            )
                            db.add(new_zone_price)

                    created.append(repeat_event)
                    generate_event_seats(db,repeat_event.id,repeat_event.venue_id)

    db.commit()

    return {
        "success": True,
        "created": len(created),
        "events": created
    }


@router.get("/{event_id}/pricing-rules", response_model=list[schemas.PricingRule])
def get_pricing_rules(event_id: int, db: Session = Depends(get_db)):

    # Verificar que el evento existe y no está borrado
    event = db.query(models.Event).filter(
        models.Event.id == event_id,
        models.Event.deleted == 0
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Obtener las reglas de pricing
    pricing_rules = db.query(models.PricingRule).filter(
        models.PricingRule.event_id == event_id,
        models.PricingRule.deleted == 0
    ).order_by(models.PricingRule.days_before.desc()).all()

    return pricing_rules


@router.post("/{event_id}/pricing-rules", response_model=schemas.PricingRule)
def create_pricing_rule(
    event_id: int,
    rule: schemas.PricingRuleCreate,
    db: Session = Depends(get_db)
):

    # 1. Verificar evento
    event = db.query(models.Event).filter(
        models.Event.id == event_id,
        models.Event.deleted == 0
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # 2. VALIDAR DUPLICADO (event_id + days_before)
    existing_rule = db.query(models.PricingRule).filter(
        models.PricingRule.event_id == event_id,
        models.PricingRule.days_before == rule.days_before
    ).first()

    if existing_rule:
        raise HTTPException(
            status_code=409,
            detail="Ya existe una regla con esos días de antelación para este evento"
        )

    # 3. Crear regla
    db_rule = models.PricingRule(
        event_id=event_id,
        days_before=rule.days_before,
        price_multiplier=rule.price_multiplier,
        description=rule.description
    )

    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)

    return db_rule


@router.delete("/pricing-rules/{rule_id}", status_code=204)
def delete_pricing_rule(rule_id: int, db: Session = Depends(get_db)):

    # 1. Buscar la regla
    rule = db.query(models.PricingRule).filter(
        models.PricingRule.id == rule_id,
        models.PricingRule.deleted == 0
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")

    # 2. Soft delete
    rule.deleted = 1

    db.commit()

    return



def generate_event_seats(db, event_id: int, venue_id: int):

    seats = db.query(models.Seat).filter(
        models.Seat.venue_id == venue_id
    ).all()

    for seat in seats:
        db.add(models.EventSeat(
            event_id=event_id,
            seat_id=seat.id,
            status=models.SeatStatus.AVAILABLE
        ))

    db.commit()