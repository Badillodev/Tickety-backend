# routers/events.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session,joinedload
from typing import List
from app.database import get_db
import app.models.models as models, app.schemas.tickets as schemas
from fastapi import HTTPException
from uuid import uuid4
from datetime import datetime
from app.routers.auth import get_current_user
from sqlalchemy import or_,func
router = APIRouter(prefix="/tickets", tags=["Tickets"])# routers/orders.py

@router.get("/me", response_model=list[schemas.Ticket])
def get_user_tickets(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    db_user = db.query(models.User).filter(
        models.User.id == user["id"]
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    tickets = (
        db.query(models.Ticket)
        .options(
            joinedload(models.Ticket.event),

            joinedload(models.Ticket.event_seat)
                .joinedload(models.EventSeat.seat)
                .joinedload(models.Seat.zone)
        )
        .filter(
            (models.Ticket.user_id == db_user.id) |
            (models.Ticket.attendee_email == db_user.email)
        )
        .order_by(models.Ticket.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    # 🔥 IMPORTANTE: devolver ORM directamente (no dict manual)
    return tickets

@router.get("/me_group", response_model=list[schemas.TicketGroup])
def get_user_tickets(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    db_user = db.query(models.User).filter(
        models.User.id == user["id"]
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    tickets = (
        db.query(models.Ticket)
        .options(
            joinedload(models.Ticket.event),  # 🔥 NECESARIO para agrupar por event

            joinedload(models.Ticket.event_seat)
                .joinedload(models.EventSeat.seat)
                .joinedload(models.Seat.zone)
        )
        .filter(
            (models.Ticket.user_id == db_user.id) |
            (models.Ticket.attendee_email == db_user.email)
        )
        .order_by(models.Ticket.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    # 🔥 AGRUPACIÓN POR EVENTO
    grouped = {}

    for ticket in tickets:
        event_id = ticket.event_id

        if event_id not in grouped:
            grouped[event_id] = {
                "event": ticket.event,   # ✅ objeto completo gracias a joinedload
                "tickets": []
            }

        grouped[event_id]["tickets"].append(ticket)

    return list(grouped.values())


# @router.get("/{ticket_id}", response_model=schemas.Ticket)
# def get_ticket_by_id(
#     ticket_id: int,
#     db: Session = Depends(get_db),
#     user=Depends(get_current_user)
# ):

#     db_user = db.query(models.User).filter(
#         models.User.id == user["id"]
#     ).first()

#     if not db_user:
#         raise HTTPException(status_code=404, detail="User not found")

#     ticket = (
#         db.query(models.Ticket)
#         .options(joinedload(models.Ticket.event))
#         .filter(models.Ticket.id == ticket_id)
#         .first()
#     )

#     if not ticket:
#         raise HTTPException(status_code=404, detail="Ticket not found")

#     # 🔒 AUTH
#     if ticket.user_id != db_user.id and ticket.attendee_email != db_user.email:
#         raise HTTPException(status_code=403, detail="Not authorized")

#     # =========================
#     # 🎫 PASS LOGIC (AÑADIDO)
#     # =========================
#     pack_name = None
#     pack_description = None

#     if ticket.event.event_type == "PASS":

#         order_item = (
#             db.query(models.OrderItem)
#             .filter(
#                 models.OrderItem.order_id == ticket.order_id,
#                 models.OrderItem.item_type == "PASS",
#                 models.OrderItem.reference_id != None
#             )
#             .first()
#         )

#         if order_item:
#             pack = db.query(models.TicketPack).filter(
#                 models.TicketPack.id == order_item.reference_id
#             ).first()

#             if pack:
#                 pack_name = pack.name
#                 pack_description = pack.description

#     # =========================
#     # ATTACH EXTRA FIELD (DYNAMIC)
#     # =========================
#     ticket.pack_name = pack_name
#     ticket.pack_description = pack_description

#     return ticket

@router.get("/event/{event_id}", response_model=list[schemas.Ticket])
def get_tickets_by_event(
    event_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    db_user = db.query(models.User).filter(
        models.User.id == user["id"]
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    event = db.query(models.Event).filter(
        models.Event.id == event_id
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    tickets = (
    db.query(models.Ticket)
    .options(
        joinedload(models.Ticket.event),
        joinedload(models.Ticket.event_seat)
            .joinedload(models.EventSeat.seat)
            .joinedload(models.Seat.zone),

        joinedload(models.Ticket.pack)  
    )
    .filter(models.Ticket.event_id == event_id)
    .order_by(models.Ticket.created_at.desc())
    .offset(skip)
    .limit(limit)
    .all()
)

    return tickets

@router.get("/event_ticket/{event_id}", response_model=list[schemas.Ticket])
def get_event_tickets(
    event_id: int,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    # buscar usuario registrado (si existe)
    db_user = db.query(models.User).filter(
        models.User.id == user["id"]
    ).first()

    user_email = user.get("email")

    # validar acceso al evento:
    # - propietario del evento
    # - o tiene tickets invitados por email
    event = db.query(models.Event).join(
        models.Ticket,
        models.Ticket.event_id == models.Event.id,
        isouter=True
    ).filter(
        models.Event.id == event_id,
        or_(
            models.Event.created_by == user["id"],
            models.Ticket.attendee_email == user_email
        )
    ).first()

    if not event:
        raise HTTPException(
            status_code=403,
            detail="Not allowed to access this event"
        )

    # tickets visibles para el usuario
    tickets = (
        db.query(models.Ticket)
        .options(joinedload(models.Ticket.event))
        .filter(
            models.Ticket.event_id == event_id,
            or_(
                models.Ticket.user_id == user["id"],
                models.Ticket.attendee_email == user_email
            )
        )
        .order_by(models.Ticket.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return tickets

@router.post("/", response_model=schemas.Ticket)
def create_ticket(ticket: schemas.TicketCreate, db: Session = Depends(get_db)):

    # =========================
    # VALIDATE EVENT
    # =========================
    event = db.query(models.Event).filter(
        models.Event.id == ticket.event_id,
        models.Event.deleted == 0
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # =========================
    # VALIDATE USER
    # =========================
    user = db.query(models.User).filter(
        models.User.id == ticket.user_id,
        models.User.deleted == False
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # =========================
    # VALIDATE VENUE
    # =========================
    venue = db.query(models.Venues).filter(
        models.Venues.id == ticket.venue_id,
        models.Venues.deleted == False
    ).first()

    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    # =========================
    # GENERATE TICKET ID
    # =========================
    ticket_id = f"TICKET-{int(datetime.utcnow().timestamp())}-{uuid4().hex[:8]}"

    # =========================
    # GENERATE QR CODE
    # =========================
    qr_code = str(uuid4())

    # =========================
    # CREATE TICKET
    # =========================
    db_ticket = models.Ticket(
        ticket_id=ticket_id,
        event_id=ticket.event_id,
        venue_id=ticket.venue_id,
        user_id=ticket.user_id,
        price=ticket.price,
        seat_number=ticket.seat_number,
        qr_code=qr_code,
        status=models.TicketStatus.VALID
    )

    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)

    return db_ticket

@router.post("/{ticket_id}/transfer", response_model=schemas.Ticket)
def transfer_ticket(
    ticket_id: int,
    new_owner_email: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    # Buscar usuario autenticado
    db_user = db.query(models.User).filter(
        models.User.id == user["id"]
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Buscar ticket y comprobar propiedad
    ticket = (
        db.query(models.Ticket)
        .options(
            joinedload(models.Ticket.event),

            joinedload(models.Ticket.event_seat)
                .joinedload(models.EventSeat.seat)
                .joinedload(models.Seat.zone)
        )
        .filter(models.Ticket.id == ticket_id)
        .first()
    )

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Verificar que el ticket pertenece al usuario actual
    is_owner = (
        ticket.user_id == db_user.id or
        ticket.attendee_email == db_user.email
    )

    if not is_owner:
        raise HTTPException(
            status_code=403,
            detail="You are not the owner of this ticket"
        )

    # Buscar nuevo propietario
    new_owner = db.query(models.User).filter(
        models.User.email == new_owner_email
    ).first()

    # Si no existe, crearlo
    if not new_owner:
        new_owner = models.User(
            email=new_owner_email
        )

        db.add(new_owner)
        db.commit()
        db.refresh(new_owner)

    # Transferir ticket
    ticket.user_id = new_owner.id
    ticket.attendee_email = new_owner.email

    db.commit()
    db.refresh(ticket)

    return ticket


@router.post("/validate-ticket/{event_id}/{ticket_code}")
def validate_ticket(
    event_id: int,
    ticket_code: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    # usuario autenticado
    db_user = db.query(models.User).filter(
        models.User.id == user["id"]
    ).first()

    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # comprobar que el usuario es creador del evento
    event = db.query(models.Event).filter(
        models.Event.id == event_id,
        models.Event.created_by == db_user.id
    ).first()

    if not event:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to validate tickets for this event"
        )

    # buscar ticket por ticket_code y evento
    ticket = db.query(models.Ticket).filter(
    models.Ticket.event_id == event_id,
    or_(
        models.Ticket.qr_code == ticket_code,
        models.Ticket.ticket_code == ticket_code
    )
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    # ticket ya validado
    if ticket.status == models.TicketStatus.USED:
        raise HTTPException(
            status_code=400,
            detail="Ticket already validated"
        )

    # ticket cancelado
    if ticket.status == models.TicketStatus.CANCELLED:
        raise HTTPException(
            status_code=400,
            detail="Ticket cancelled"
        )

    # validar ticket
    ticket.status = models.TicketStatus.USED
    ticket.validated_at = func.current_timestamp()
    ticket.validated_by = db_user.id

    db.commit()
    db.refresh(ticket)

    return {
        "success": True,
        "message": "Ticket validated successfully",
        "ticket_id": ticket.id,
        "ticket_code": ticket.ticket_code,
        "event_id": ticket.event_id,
        "validated_by": db_user.id,
        "validated_at": ticket.validated_at
    }