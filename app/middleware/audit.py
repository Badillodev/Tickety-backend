from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.models.models import ApiAuditLog
from app.database import SessionLocal


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # =========================
        # READ BODY (SAFE COPY)
        # =========================
        body_bytes = await request.body()

        # recrear request para que no se rompa el endpoint
        async def receive():
            return {"type": "http.request", "body": body_bytes}

        request = Request(request.scope, receive)

        response = await call_next(request)

        # =========================
        # DB INSERT
        # =========================
        db = SessionLocal()

        try:
            log = ApiAuditLog(
                user_id=1,  # luego JWT
                endpoint=str(request.url.path),
                http_method=request.method,
                response_status=response.status_code,
                ip_address=request.client.host if request.client else None,
                request_body=body_bytes.decode("utf-8") if body_bytes else None
            )

            db.add(log)
            db.commit()

        except Exception as e:
            db.rollback()
            print("Audit error:", e)

        finally:
            db.close()

        return response