"""
ZooPet — uy hayvonlari mahsulotlari yetkazib berish platformasi.
FastAPI asosiy ilova fayli.

Ishga tushirish:
    uvicorn backend.main:app --reload --port 8000
"""
import os

from dotenv import load_dotenv

load_dotenv()  # .env dagi BOT_TOKEN, ADMIN_CHAT_ID va to'lov kalitlarini yuklash

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .database import SessionLocal
from .routers import catalog, orders, admin_auth, customer_auth, subscriptions

app = FastAPI(title="ZooPet API", version="1.0.0")

# Mini App va admin panel shu serverdan xizmat qiladi (bir xil origin), shuning
# uchun standart holatda CORS umuman kerak emas. Avval `allow_origins=["*"]`
# turgan edi — bu internetdagi har qanday sahifaga API javoblarini o'qishga
# ruxsat berardi. Boshqa origin kerak bo'lsa, .env dagi ALLOWED_ORIGINS ga
# vergul bilan ajratib yozing.
_allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
if _allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

# Telegram WebView `telegram-web-app.js` ni telegram.org dan yuklaydi, shriftlar
# Google Fonts dan keladi. `connect-src 'self'` muhim: XSS yuz bersa ham
# tokenni tashqi manzilga `fetch` qilib yuborishga to'sqinlik qiladi.
_CSP = (
    "default-src 'self'; "
    "script-src 'self' https://telegram.org 'unsafe-inline'; "
    "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' https://res.cloudinary.com data:; "
    "connect-src 'self'; "
    "frame-ancestors 'self'; "
    "base-uri 'none'; "
    "object-src 'none'"
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """422 javobini kiritilgan qiymatni qaytarmasdan shakllantiradi.

    FastAPI ning standart ishlovchisi xato tanasiga `input` (foydalanuvchi
    yuborgan qiymat) ni ham qo'shadi. Bu ikki muammo tug'dirardi:
      1. `{"price": NaN}` yuborilganda xato tanasining o'zi JSON ga
         aylantirilmay, 422 o'rniga 500 qaytardi;
      2. ro'yxatdan o'tishda parol juda qisqa bo'lsa, parol javobda
         qaytib kelardi.
    """
    errors = [
        {
            "loc": list(err.get("loc", [])),
            "msg": err.get("msg", "Noto'g'ri qiymat"),
            "type": err.get("type", ""),
        }
        for err in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("Content-Security-Policy", _CSP)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    # Mijoz PII qaytaruvchi javoblar keshda qolmasligi kerak
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response

app.include_router(catalog.router)
app.include_router(orders.router)
app.include_router(admin_auth.router)
app.include_router(customer_auth.router)
app.include_router(subscriptions.router)


@app.get("/api/health")
def health():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "service": "ZooPet API", "database": "ok"}
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "service": "ZooPet API", "database": "unavailable"},
        )
    finally:
        db.close()


# Serve uploaded images
_UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", "uploads")
os.makedirs(_UPLOADS_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_UPLOADS_DIR), name="uploads")

# Web storefront va admin panelni bevosita shu server orqali xizmat qilish
_WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
if os.path.isdir(_WEB_DIR):
    app.mount("/", StaticFiles(directory=_WEB_DIR, html=True), name="web")
