# routers/orders.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
import app.models.models as models
from sqlalchemy import and_
from datetime import datetime
import app.schemas.orders as schemas
from uuid import uuid4
from app.routers.auth import get_current_user
import logging

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/")
def create_order(
    payload: schemas.OrderRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    # =========================
    # USER
    # =========================
    db_user = db.query(models.User).filter(
        models.User.id == user["id"]
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # =========================
    # EVENT
    # =========================
    event = db.query(models.Event).filter(
        models.Event.id == payload.event_id
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    if not event.sales_active:
        raise HTTPException(status_code=400, detail="Ventas desactivadas")

    total = 0

    # =====================================================
    # 🧾 CREATE ORDER
    # =====================================================
    order = models.Order(
        event_id=event.id,
        user_id=db_user.id,
        status="pending",
        total_amount=0
    )

    db.add(order)
    db.flush()  # obtener order.id

    # =========================
    # helper pricing function
    # =========================
    def get_zone_price(event_id: int, zone_id: int):
        pricing = db.query(models.TicketZonePricing).filter(
            models.TicketZonePricing.event_id == event_id,
            models.TicketZonePricing.zone_id == zone_id
        ).first()
        print(f" get_zone_price pricing{pricing}")
        return float(pricing.price) if pricing else float(event.price or 0)
    
    
    def get_packs_price(event_id: int, pack_id: int):
        pack_pricing = db.query(models.TicketPack).filter(
            models.TicketPack.event_id == event_id,
            models.TicketPack.id == pack_id
        ).first()
        print(f" get_zone_price pricing{pack_pricing}")
        return float(pack_pricing.price) if pack_pricing else float(event.price or 0)

    try:

        # =====================================================
        # 🎟 SEATED
        # =====================================================
        if event.event_type == models.EventType.SEATED:

            selected_seats = payload.selected_seats or []

            if len(selected_seats) != payload.quantity:
                raise HTTPException(
                    status_code=400,
                    detail="Cantidad de asientos inválida"
                )

            seat_ids = [s.seat_id for s in selected_seats]

            event_seats = (
                db.query(models.EventSeat)
                .filter(
                    models.EventSeat.event_id == event.id,
                    models.EventSeat.seat_id.in_(seat_ids)
                )
                .with_for_update()
                .all()
            )

            if len(event_seats) != len(seat_ids):
                raise HTTPException(status_code=400, detail="Asientos inválidos")

            for es in event_seats:

                if es.status != models.SeatStatus.AVAILABLE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Asiento {es.seat_id} no disponible"
                    )

                seat = db.query(models.Seat).filter(
                    models.Seat.id == es.seat_id
                ).first()
                print(f"get_zone_price - start {event.id} {seat.zone_id}")
                price = get_zone_price(event.id, seat.zone_id if seat else 0)
                print(f"get_zone_price - end {price}")
                ticket = models.Ticket(
                    event_id=event.id,
                    venue_id=event.venue_id,
                    user_id=db_user.id,
                    order_id=order.id,
                    price=price,
                    attendee_name=db_user.first_name or "",
                    attendee_surname=f"{db_user.last_name1 or ''} {db_user.last_name2 or ''}".strip(),
                    attendee_email=db_user.email or "",
                    attendee_phone=db_user.phone or "",
                    seat_number=f"{seat.row_label}-{seat.seat_label}" if seat else None,
                    event_seat_id=es.id,
                    ticket_code=f"TCKS-{uuid4().hex[:10]}",
                    qr_code=str(uuid4()),
                    status=models.TicketStatus.VALID
                )

                db.add(ticket)

                # =========================
                # ORDER ITEM (SEATED)
                # =========================
                db.add(models.OrderItem(
                    order_id=order.id,
                    item_type="SEATED",
                    reference_id=es.seat_id,
                    quantity=1,
                    unit_price=price
                ))

                es.status = models.SeatStatus.SOLD

                total += price

        # =====================================================
        # 🎟 GENERAL
        # =====================================================
        elif event.event_type == models.EventType.GENERAL:

            attendees = payload.attendees or []
            price = float(event.price or 0)

            if len(attendees) != payload.quantity:
                raise HTTPException(
                    status_code=400,
                    detail="Quantity no coincide con attendees"
                )

            for attendee in attendees:

                ticket = models.Ticket(
                    event_id=event.id,
                    venue_id=event.venue_id,
                    user_id=db_user.id,
                    order_id=order.id,
                    price=price,
                    attendee_name=attendee.name,
                    attendee_surname=attendee.surname,
                    attendee_email=attendee.email,
                    attendee_phone=attendee.phone,
                    seat_number=None,
                    ticket_code=f"TCKS-{uuid4().hex[:10]}",
                    qr_code=str(uuid4()),
                    status=models.TicketStatus.VALID
                )

                db.add(ticket)

                # =========================
                # ORDER ITEM (GENERAL)
                # =========================
                db.add(models.OrderItem(
                    order_id=order.id,
                    item_type="GENERAL",
                    reference_id=None,
                    quantity=1,
                    unit_price=price
                ))

                total += price

    # =====================================================
    # 🎫 PASS
    # =====================================================
        elif event.event_type == models.EventType.PASS:

            selected_packs = payload.selected_packs or []

            for pack in selected_packs:

                qty = pack.quantity

                if qty <= 0:
                    continue

                attendees = pack.attendees or []

                if len(attendees) != qty:
                    raise HTTPException(
                        status_code=400,
                        detail="La cantidad no coincide con attendees del pack"
                    )

                price = get_packs_price(event.id, pack.pack_id)

                for attendee in attendees:

                    ticket = models.Ticket(
                        event_id=event.id,
                        venue_id=event.venue_id,
                        user_id=db_user.id,
                        order_id=order.id,
                        price=price,
                        attendee_name=attendee.name,
                        attendee_surname=attendee.surname,
                        attendee_email=attendee.email,
                        attendee_phone=attendee.phone,
                        seat_number=None,
                        ticket_code=f"PASS-{uuid4().hex[:10]}",
                        qr_code=str(uuid4()),
                        status=models.TicketStatus.VALID
                    )

                    db.add(ticket)

                    # =========================
                    # ORDER ITEM (PASS)
                    # =========================
                    db.add(models.OrderItem(
                        order_id=order.id,
                        item_type="PASS",
                        reference_id=pack.pack_id,
                        quantity=1,
                        unit_price=price
                    ))

                    total += price

        else:
            raise HTTPException(status_code=400, detail="Tipo de evento no soportado")

        # =========================
        # FINALIZE ORDER
        # =========================
        order.total_amount = total

        db.commit()

        return {
            "order_id": order.id,
            "total_amount": total
            }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        print("============== ERROR ==============")
        print("ERROR CREATE ORDER:")
        print(e)
        print("===================================")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )
    
@router.post("/{order_id}/pay")
def pay_order(order_id: int, payload: dict, db: Session = Depends(get_db)):
    """
    payload:
    {
        payment_method: "card" | "bizum" | "paypal"
    }
    """

    order = db.query(models.Order).filter(
        models.Order.id == order_id
    ).first()

    if not order:
        raise HTTPException(404, "Pedido no encontrado")

    if order.status == "paid":
        raise HTTPException(400, "Ya está pagado")

    order.status = "paid"
    order.payment_method = payload["payment_method"]
    order.paid_at = datetime.utcnow()

    db.commit()

    return {"message": "Pago completado"}


@router.get("/{order_id}/tickets")
def get_order_tickets(order_id: int, db: Session = Depends(get_db)):
    tickets = db.query(models.Ticket).filter(
        models.Ticket.order_id == order_id
    ).all()

    return tickets



