from fastapi import FastAPI
from app.database import Base, engine
from app.routers import events, audit, venues, tickets, auth, orders
from app.middleware.audit import AuditMiddleware
from fastapi.middleware.cors import CORSMiddleware
from app.config import config, ENVIRONMENT, DEBUG

app = FastAPI(title="Event Ticketing API")


# =========================
# CREATE TABLES
# =========================
Base.metadata.create_all(bind=engine)


# =========================
# MIDDLEWARE
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)


# =========================
# ROUTERS
# =========================
app.include_router(events.router)
app.include_router(tickets.router)
app.include_router(audit.router)
app.include_router(venues.router)
app.include_router(auth.router)
app.include_router(orders.router)


@app.get("/")
def root():
    return {"message": "API Ticketing System Running"}