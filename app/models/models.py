from sqlalchemy import (
    TIMESTAMP, Column, Integer, String, DateTime, Boolean,
    ForeignKey, Enum, JSON, DECIMAL, Text, func,BigInteger
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum
from datetime import datetime


# =========================
# ENUMS
# =========================

class EventType(str, enum.Enum):
    GENERAL = "GENERAL"
    SEATED = "SEATED"
    PASS = "PASS"


class TicketStatus(str, enum.Enum):
    VALID = "VALID"
    USED = "USED"
    CANCELLED = "CANCELLED"


class BillingCycleEnum(str, enum.Enum):
    monthly = "monthly"
    commission = "commission"


class SubscriptionStatusEnum(str, enum.Enum):
    active = "active"
    cancelled = "cancelled"
    pending_change = "pending_change"

class SeatStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    SOLD = "SOLD"

# =========================
# SUBSCRIPTIONS (PLANS)
# =========================

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    description = Column(String(255))
    price = Column(DECIMAL(10, 2), default=0.00)

    billing_cycle = Column(Enum(BillingCycleEnum), nullable=False)

    max_events = Column(Integer, nullable=True)
    max_attendees = Column(Integer, nullable=True)
    max_organizers = Column(Integer, nullable=True)

    commission_rate = Column(DECIMAL(5, 2), default=0.00)

    support_level = Column(String(50))
    features = Column(Text)
    ideal_for = Column(Text)

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    # relaciones
    user_subscriptions = relationship(
        "UserSubscription",
        back_populates="subscription",
        foreign_keys="UserSubscription.subscription_id"
    )


# =========================
# USERS
# =========================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String(255), unique=True, index=True)
    phone = Column(String(50))

    first_name = Column(String(100))
    last_name1 = Column(String(100))
    last_name2 = Column(String(100))

    google_id = Column(String(255))
    picture = Column(String(500))
    company = Column(String(100))
    is_company = Column(Integer, default=0)
    adress = Column(String(200))
    stripe_account_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, nullable=True)

    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    updated_by = Column(Integer, nullable=True)
    conected_stripe_at = Column(DateTime,default=None)
    disconected_stripe_at = Column(DateTime,default=None)
    deleted = Column(Integer, default=0)

    # relaciones
    subscriptions = relationship(
        "UserSubscription",
        back_populates="user"
    )
    tickets = relationship(
        "Ticket",
        back_populates="user"
    )
    orders = relationship("Order", back_populates="user")


# =========================
# USER SUBSCRIPTIONS
# =========================

class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)

    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)

    status = Column(
        Enum(SubscriptionStatusEnum),
        default=SubscriptionStatusEnum.active
    )

    next_subscription_id = Column(
        Integer,
        ForeignKey("subscriptions.id"),
        nullable=True
    )

    change_at = Column(DateTime, nullable=True)

    billing_day = Column(Integer, nullable=False)

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    # relaciones
    user = relationship(
        "User",
        back_populates="subscriptions"
    )

    subscription = relationship(
        "Subscription",
        foreign_keys=[subscription_id],
        back_populates="user_subscriptions"
    )

    next_subscription = relationship(
        "Subscription",
        foreign_keys=[next_subscription_id]
    )


# =========================
# EVENTS
# =========================

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    artist = Column(String(255))
    genre = Column(String(100))
    event_date = Column(DateTime)
    location = Column(String(255))
    venue = Column(String(255))

    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=True)

    event_type = Column(Enum(EventType))
    seat_map = Column(JSON)
    image = Column(Text)

    price = Column(DECIMAL)
    sales_active = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer)

    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    updated_by = Column(Integer)

    deleted = Column(Integer, default=0)

    # relaciones
    venue_rel = relationship("Venues")
    ticket_packs = relationship("TicketPack", back_populates="event")
    zone_pricing = relationship(
        "TicketZonePricing",
        back_populates="event",
        cascade="all, delete-orphan"
    )
    pricing_rules = relationship("PricingRule", back_populates="event")
    orders = relationship("Order", back_populates="event")
    tickets = relationship("Ticket", back_populates="event")
    event_seats = relationship(
        "EventSeat",
        back_populates="event",
        cascade="all, delete-orphan"
    )


# =========================
# VENUES
# =========================

class Venues(Base):
    __tablename__ = "venues"

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    location = Column(String(255))
    capacity = Column(Integer)
    seats = Column(Integer, default=0)

    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    updated_by = Column(Integer)
    updated_at = Column(DateTime, default=datetime.utcnow)

    deleted = Column(Integer, default=0)

    zones = relationship("VenueZone", back_populates="venue")
    tickets = relationship(
        "Ticket",
        back_populates="venue"
    )


class VenueZone(Base):
    __tablename__ = "venue_zones"

    id = Column(Integer, primary_key=True)
    venue_id = Column(Integer, ForeignKey("venues.id"))

    name = Column(String(100))
    capacity = Column(Integer)
    price = Column(DECIMAL)

    created_at = Column(DateTime, default=datetime.utcnow)
    deleted = Column(Integer, default=0)

    venue = relationship("Venues", back_populates="zones")

class Seat(Base):
    __tablename__ = "seats"

    id = Column(Integer, primary_key=True)
    venue_id = Column(Integer, ForeignKey("venues.id"))
    zone_id = Column(Integer, ForeignKey("venue_zones.id"))

    row_label = Column(String(10))
    seat_label = Column(String(10))

    created_at = Column(DateTime, default=datetime.utcnow)
    deleted = Column(Integer, default=0)

    zone = relationship("VenueZone")

    event_seats = relationship(
        "EventSeat",
        back_populates="seat"
    )


# =========================
# TICKETS
# =========================

class TicketPack(Base):
    __tablename__ = "ticket_packs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"))

    name = Column(String(255))
    capacity = Column(Integer)
    description = Column(String(1000))
    price = Column(DECIMAL(10, 2))

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    deleted = Column(Integer, default=0)

    event = relationship("Event", back_populates="ticket_packs")
    tickets = relationship("Ticket", back_populates="pack")


class TicketZonePricing(Base):
    __tablename__ = "ticket_zone_pricing"

    id = Column(Integer, primary_key=True)
    zone_id = Column(Integer)
    event_id = Column(Integer, ForeignKey("events.id"))

    zone_name = Column(String(100))
    price = Column(DECIMAL(10, 2))

    created_at = Column(DateTime, server_default=func.now())
    deleted = Column(Integer, default=0)

    event = relationship("Event", back_populates="zone_pricing")


class PricingRule(Base):
    __tablename__ = "pricing_rules"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"))

    days_before = Column(Integer)
    price_multiplier = Column(DECIMAL(5, 2))
    description = Column(String(255))

    deleted = Column(Integer, default=0)

    event = relationship("Event", back_populates="pricing_rules")

class Order(Base):
    __tablename__ = "orders"

    id = Column(BigInteger, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)

    status = Column(String(20), default="pending", nullable=False)
    total_amount = Column(DECIMAL(10, 2), default=0.00, nullable=False)
    payment_method = Column(String(20), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # 🔗 Relaciones
    user = relationship("User", back_populates="orders")  # 👈 NUEVO
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="order", cascade="all, delete-orphan")
    event = relationship("Event", back_populates="orders")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(BigInteger, primary_key=True, index=True)
    order_id = Column(BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)

    item_type = Column(String(20), nullable=False)  # GENERAL | PASS | SEATED
    reference_id = Column(Integer, nullable=True)   # pack_id o seat_id

    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(DECIMAL(10, 2), nullable=False)

    # 🔗 Relaciones
    order = relationship("Order", back_populates="items")

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(BigInteger, primary_key=True, index=True)

    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    order_id = Column(BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=True)

    price = Column(DECIMAL(10, 2), default=0.00, nullable=False)

    attendee_name = Column(String(255), nullable=True)
    attendee_surname = Column(String(255), nullable=True)
    attendee_email = Column(String(255), nullable=True)
    attendee_phone = Column(String(30), nullable=True)

    seat_number = Column(String(50), nullable=True)
    event_seat_id = Column(
    Integer,
    ForeignKey("event_seats.id"),
    nullable=True,
    index=True
    )

    ticket_code = Column(String(100), nullable=True)
    qr_code = Column(Text, nullable=False)

    status = Column(Enum(TicketStatus), default=TicketStatus.VALID, nullable=False)

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    validated_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    validated_by = Column(Integer)
    pack_id = Column(
    Integer,
    ForeignKey("ticket_packs.id"),
    nullable=True,
    index=True
    )


    # relations
    event = relationship("Event", back_populates="tickets")
    order = relationship("Order", back_populates="tickets")
    user = relationship("User", back_populates="tickets")
    venue = relationship("Venues", back_populates="tickets")
    event_seat = relationship("EventSeat", lazy="selectin")
    pack = relationship("TicketPack", back_populates="tickets")
   


    
    # =========================
class EventSeat(Base):
    __tablename__ = "event_seats"

    id = Column(BigInteger, primary_key=True, index=True)

    event_id = Column(
        Integer,
        ForeignKey("events.id"),
        nullable=False,
        index=True
    )

    seat_id = Column(
        Integer,
        ForeignKey("seats.id"),
        nullable=False,
        index=True
    )

    status = Column(
        Enum(SeatStatus),
        default=SeatStatus.AVAILABLE,
        nullable=False
    )

    price = Column(DECIMAL(10, 2), nullable=True)

    created_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp()
    )

    # relations
    event = relationship("Event", back_populates="event_seats")
    seat = relationship("Seat", back_populates="event_seats")
    

# =========================
# AUDIT LOG
# =========================


class ApiAuditLog(Base):
    __tablename__ = "api_audit_logs"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, nullable=True)

    endpoint = Column(String(255))
    http_method = Column(String(10))

    request_body = Column(JSON)
    response_status = Column(Integer)

    ip_address = Column(String(50))

    created_at = Column(DateTime, default=datetime.utcnow)
    