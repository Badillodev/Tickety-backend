from fastapi import APIRouter
from app.database import get_db
from google.oauth2 import id_token
from pydantic import BaseModel
from google.auth.transport import requests as google_requests
from fastapi import HTTPException
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
import app.models.models as models
from app.schemas.auth import UpdateUserRequest
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
import logging
import stripe
from app.config import GOOGLE_CLIENT_ID, JWT_SECRET, FRONTEND_URL,STRIPE_SECRET_KEY,JWT_ALGORITHM

router = APIRouter(prefix="/auth", tags=["Auth"])

# 🔐 Configuración
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/google")
COMMISSION_PLAN_ID = 1
stripe.api_key = STRIPE_SECRET_KEY



# 📩 Request body
class GoogleToken(BaseModel):
    token: str


# 🧠 Crear JWT con PyJWT
def create_jwt(user: dict):
    payload = {
        "id": str(user["id"]),              
        "email": user["email"],             
        "name": user.get("name"),
        "picture": user.get("picture"),
        "is_company":user.get('is_company'),
        "exp": datetime.utcnow() + timedelta(days=7),
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        logging.info(f"get_current_user - start token {token}")
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        user_id: str = payload.get("id")
        email: str = payload.get("email")
        print(f"get_current_user - user_id {user_id} - email {email}")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )

        return {
            "id": user_id,
            "email": email
        }

    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado"
        )

@router.post("/google")
def google_login(data: GoogleToken, db: Session = Depends(get_db)):
    try:
        # 1. Validar token
        idinfo = id_token.verify_oauth2_token(
            data.token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )

        # 2. Extraer info
        email = idinfo["email"]
        user_db = db.query(models.User).filter(models.User.email == email).first()

        if not user_db:
            # Separar nombre si no tienes campos claros
            full_name = idinfo.get("name", "")
            first_name = idinfo.get("given_name") or full_name.split(" ")[0]
            last_name = idinfo.get("family_name") or " ".join(full_name.split(" ")[1:])

            user_db = models.User(
                email=email,
                first_name=first_name,
                last_name1=last_name,
                google_id=idinfo["sub"],
                # opcional si añadiste columna
                picture=idinfo.get("picture")
            )

            db.add(user_db)
            db.commit()
            db.refresh(user_db)

        # 3. Crear JWT
        jwt_token = create_jwt({
            "id": user_db.id,
            "email": user_db.email,
            
        })

        return {
            "access_token": jwt_token,
            "token_type": "bearer",
            "user": {
                "id": user_db.id,
                "email": user_db.email,
                "name": user_db.first_name,
                "is_company":user_db.is_company,
                "picture": idinfo.get("picture")
            }
        }

    except Exception as e:
        print("❌ GOOGLE ERROR:", str(e))
        raise HTTPException(status_code=401, detail="Invalid Google token")
    
    
    
    
@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    db_user = db.query(models.User).filter(models.User.id == user["id"]).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    active_subscription = (
        db.query(models.UserSubscription)
        .filter(
            models.UserSubscription.user_id == db_user.id,
            models.UserSubscription.status == "active"
        )
        .first()
    )

    return {
        "id": db_user.id,
        "email": db_user.email,
        "name": db_user.first_name,
        "surname": db_user.last_name1,
        "company": db_user.company,
        "address": db_user.adress,
        "phone": db_user.phone,
        "is_company": db_user.is_company,
        "type": "company" if active_subscription else "customer",
        "created_at": db_user.created_at,
        "subscription": {
            "id": active_subscription.id if active_subscription else None,
            "subscription_id": active_subscription.subscription_id if active_subscription else None,
            "status": active_subscription.status if active_subscription else None,
            "start_date": active_subscription.start_date if active_subscription else None,
            "end_date": active_subscription.end_date if active_subscription else None,
            "billing_day": active_subscription.billing_day if active_subscription else None,

            # 👇 ACTUAL subscription
            "current_subscription_name": (
                active_subscription.subscription.name
                if active_subscription and active_subscription.subscription
                else None
            ),

            # 👇 NEXT subscription (lo que quieres)
            "next_subscription": (
                {
                    "id": active_subscription.next_subscription.id,
                    "name": active_subscription.next_subscription.name,
                    "price":active_subscription.next_subscription.price
                }
                if active_subscription and active_subscription.next_subscription
                else None
            ),

            "change_at": active_subscription.change_at if active_subscription else None,
        }
    }
    
@router.put("/me")
def update_me(
    data: UpdateUserRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    db_user = db.query(models.User).filter(models.User.id == user["id"]).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.name is not None:
        db_user.first_name = data.name

    if data.surname is not None:
        db_user.last_name1 = data.surname

    if data.company is not None:
        db_user.company = data.company

    if data.address is not None:
        db_user.adress = data.address

    if data.phone is not None:
        db_user.phone = data.phone

    if data.is_company is not None:
        db_user.is_company = 1 if data.is_company else 0

    db.commit()
    db.refresh(db_user)

    return {"ok": True}



@router.get("/subscriptions")
def get_subscriptions(db: Session = Depends(get_db)):
    return db.query(models.Subscription).all()

@router.post("/subscription/activate")
def activate_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    db_user = db.query(models.User).filter(
        models.User.id == user["id"]
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    current = db.query(models.UserSubscription).filter(
        models.UserSubscription.user_id == db_user.id,
        models.UserSubscription.status == "active"
    ).first()

    # 🟢 CASO 1: no tiene suscripción → crear inmediata
    if not current:
        new_sub = models.UserSubscription(
            user_id=db_user.id,
            subscription_id=subscription_id,
            start_date=datetime.utcnow(),
            status="active",
            billing_day=datetime.utcnow().day
        )
        db.add(new_sub)
        db.commit()

        return {
            "ok": True,
            "type": "new",
            "subscription_id": subscription_id
        }

    # 🟡 CASO 2: misma suscripción → no hacer nada
    if current.subscription_id == subscription_id:
        return {
            "ok": True,
            "type": "no_change",
            "subscription_id": subscription_id
        }

    # 🔵 CASO 3: cambio desde comisión → INMEDIATO
    if current.subscription_id == COMMISSION_PLAN_ID:
        current.subscription_id = subscription_id
        current.next_subscription_id = None
        current.change_at = None

        db.commit()

        return {
            "ok": True,
            "type": "immediate",
            "from": COMMISSION_PLAN_ID,
            "to": subscription_id
        }

    # 🟣 CASO 4: cambio programado (resto de planes)
    current.next_subscription_id = subscription_id

    today = datetime.utcnow()

    try:
        next_billing_date = today.replace(day=current.billing_day)

        if today.day >= current.billing_day:
            next_billing_date = (today + timedelta(days=30)).replace(
                day=current.billing_day
            )

    except ValueError:
        # fallback meses con menos días
        next_billing_date = today + timedelta(days=30)

    current.change_at = next_billing_date

    db.commit()

    return {
        "ok": True,
        "type": "scheduled",
        "change_at": current.change_at,
        "from": current.subscription_id,
        "to": subscription_id
    }

@router.post("/subscription/cancel")
def cancel_subscription(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    sub = db.query(models.UserSubscription).filter(
        models.UserSubscription.user_id == user["id"],
        models.UserSubscription.status == "active"
    ).first()

    if sub:
        sub.status = "cancelled"
        db.commit()

    return {"ok": True}



def process_subscription_changes(db: Session):
    now = datetime.utcnow()

    subs = db.query(models.UserSubscription).filter(
        models.UserSubscription.status == "active",
        models.UserSubscription.change_at != None,
        models.UserSubscription.change_at <= now
    ).all()

    for sub in subs:
        # cambiar suscripción
        sub.subscription_id = sub.next_subscription_id
        sub.next_subscription_id = None
        sub.change_at = None

        # generar factura nueva
        create_invoice(db, sub)

    db.commit()
    
def create_invoice(db, user_sub: models.UserSubscription):
    subscription = db.query(models.Subscription).filter(
        models.Subscription.id == user_sub.subscription_id
    ).first()

    start = datetime.utcnow().date()
    end = (datetime.utcnow() + timedelta(days=30)).date()

    invoice = models.Invoice(
        user_id=user_sub.user_id,
        user_subscription_id=user_sub.id,
        amount=subscription.price,
        currency="EUR",
        period_start=start,
        period_end=end,
        status="pending"
    )

    db.add(invoice)
    db.commit()
    
    
@router.post("/invoice/{invoice_id}/pay")
def pay_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()

    if not invoice:
        raise HTTPException(404, "Invoice not found")

    invoice.status = "paid"
    db.commit()

    return {"ok": True}



@router.post("/stripe/connect")
def connect_stripe(
    current_user_data: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crear o reutilizar una cuenta Stripe Connect Express
    """

    try:

        # =========================
        # VALIDAR CONFIG
        # =========================
        if not stripe.api_key:
            raise Exception("STRIPE_SECRET_KEY not configured")

        if not FRONTEND_URL:
            raise Exception("FRONTEND_URL not configured")

        # =========================
        # OBTENER USER ID DEL TOKEN
        # =========================
        user_id = current_user_data.get("id")
        print(f"user_id {user_id}")

        if not user_id:
            print(f"entra aqui")
            raise HTTPException(
                status_code=401,
                detail="Invalid token payload"
            )

        # =========================
        # BUSCAR USUARIO REAL EN DB
        # =========================
        current_user = (
            db.query(models.User)
            .filter(models.User.id == user_id)
            .first()
        )

        if not current_user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        print(
            f"Stripe connect -> user_id={current_user.id} "
            f"email={current_user.email}"
        )

        # =========================
        # SI YA EXISTE CUENTA
        # =========================
        if current_user.stripe_account_id:

            account_link = stripe.AccountLink.create(
                account=current_user.stripe_account_id,
                refresh_url=f"{FRONTEND_URL}",
                return_url=f"{FRONTEND_URL}",
                type="account_onboarding",
            )

            return {
                "url": account_link.url,
                "existing_account": True
            }

        # =========================
        # CREAR CONNECT EXPRESS
        # =========================
        account = stripe.Account.create(
            type="express",
            country="ES",
            email=current_user.email,
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
        )

        # =========================
        # GUARDAR STRIPE ACCOUNT ID
        # =========================

        current_user.stripe_account_id = account.id
        current_user.connected_stripe_at = datetime.now(timezone.utc)
        current_user.disconnected_stripe_at = None

        db.commit()
        db.refresh(current_user)

        # =========================
        # CREAR ONBOARDING LINK
        # =========================
        account_link = stripe.AccountLink.create(
            account=account.id,
            refresh_url=f"{FRONTEND_URL}",
            return_url=f"{FRONTEND_URL}",
            type="account_onboarding",
        )

        return {
            "url": account_link.url,
            "existing_account": False,
            "stripe_account_id": account.id
        }

    except HTTPException:
        raise

    except Exception as e:

        print("\n========== STRIPE ERROR ==========")
        print(type(e))
        print(str(e))
        print("==================================\n")

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )



# ==========================================
# GET STRIPE STATUS
# ==========================================
@router.get("/stripe/status")
def get_stripe_status(
    current_user_data: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    try:

        # =========================
        # OBTENER USER ID
        # =========================
        user_id = current_user_data.get("id")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token payload"
            )

        # =========================
        # BUSCAR USUARIO EN DB
        # =========================
        current_user = (
            db.query(models.User)
            .filter(models.User.id == user_id)
            .first()
        )

        if not current_user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # =========================
        # NO HAY STRIPE CONNECTADO
        # =========================
        if not current_user.stripe_account_id:
            return {
                "connected": False
            }

        # =========================
        # VALIDAR CUENTA STRIPE
        # =========================
        try:

            account = stripe.Account.retrieve(
                current_user.stripe_account_id
            )

        except stripe.error.InvalidRequestError:

            # La cuenta ya no existe
            current_user.stripe_account_id = None

            db.commit()

            return {
                "connected": False
            }

        # =========================
        # BALANCE
        # =========================
        balance = stripe.Balance.retrieve(
            stripe_account=current_user.stripe_account_id
        )

        available_balance = sum(
            item.amount for item in balance.available
        ) / 100

        pending_balance = sum(
            item.amount for item in balance.pending
        ) / 100

        # =========================
        # PAGOS ÚLTIMOS 30 DÍAS
        # =========================
        thirty_days_ago = int(
            (datetime.utcnow() - timedelta(days=30)).timestamp()
        )

        transactions = stripe.BalanceTransaction.list(
            limit=100,
            created={
                "gte": thirty_days_ago
            },
            stripe_account=current_user.stripe_account_id
        )

        total_received_month = 0
        payments_count = 0

        for tx in transactions.auto_paging_iter():

            # solo ingresos por pagos
            if tx.type == "charge":

                total_received_month += tx.amount
                payments_count += 1

        # convertir céntimos -> euros
        total_received_month = total_received_month / 100

        # =========================
        # PRÓXIMO PAYOUT
        # =========================
        payouts = stripe.Payout.list(
            limit=1,
            stripe_account=current_user.stripe_account_id
        )

        next_payout = 0

        if payouts.data:
            next_payout = payouts.data[0].amount / 100

        # =========================
        # RESPONSE
        # =========================
        return {
            "connected": True,

            "account_id": account.id,
            "email": account.email,

            "details_submitted": account.details_submitted,
            "charges_enabled": account.charges_enabled,
            "payouts_enabled": account.payouts_enabled,

            "available_balance": available_balance,
            "pending_balance": pending_balance,

            "total_received_month": total_received_month,
            "payments_count": payments_count,

            "next_payout": next_payout,

            "currency": "EUR"
        }

    except HTTPException:
        raise

    except Exception as e:

        print("\n========== STRIPE STATUS ERROR ==========")
        print(type(e))
        print(str(e))
        print("=========================================\n")

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
# ==========================================
# DISCONNECT STRIPE
# ==========================================

@router.delete("/stripe/disconnect")
def disconnect_stripe(
    current_user_data: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    try:

        # =========================
        # VALIDAR USER ID
        # =========================
        user_id = current_user_data.get("id")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token payload"
            )

        # =========================
        # BUSCAR USUARIO REAL
        # =========================
        current_user = (
            db.query(models.User)
            .filter(models.User.id == user_id)
            .first()
        )

        if not current_user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # =========================
        # SI NO TIENE STRIPE
        # =========================
        if not current_user.stripe_account_id:
            return {
                "message": "No Stripe account to disconnect"
            }

        # =========================
        # DESCONEXIÓN
        # =========================
        current_user.stripe_account_id = None
        current_user.disconnected_stripe_at = datetime.now(timezone.utc)

        db.commit()

        return {
            "message": "Stripe disconnected successfully",
            "connected": False
        }

    except HTTPException:
        raise

    except Exception as e:

        print("\n========== STRIPE DISCONNECT ERROR ==========")
        print(type(e))
        print(str(e))
        print("============================================\n")

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )