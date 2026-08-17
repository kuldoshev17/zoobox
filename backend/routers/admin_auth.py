"""
Admin panel autentifikatsiyasi.

`require_admin` — haqiqiy FastAPI dependency. Uni `Depends(...)` orqali
ulash mumkin, shuning uchun yangi endpoint qo'shilganda himoyani "qo'lda
chaqirishni esdan chiqarish" xatosi yuz bermaydi (avval shunday bo'lgan:
funksiya butun kodda faqat bitta joyda chaqirilgan edi).

Default admin yaratish uchun `python -m backend.create_admin` ishlatiladi —
avvalgi ochiq `POST /api/admin/seed-default` endpointi olib tashlandi, u
parolni javob tanasida qaytarib yuborar edi.
"""
import hashlib
import hmac
import secrets
import time
from typing import Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from .. import customer_auth

router = APIRouter(prefix="/api/admin", tags=["admin"])

# token -> (admin_id, muddati tugash vaqti). Jarayon ichidagi saqlash — server
# qayta ishga tushganda sessiyalar bekor bo'ladi (admin panel buni 401 orqali
# to'g'ri qayta ishlaydi).
_active_tokens: Dict[str, Dict[str, float]] = {}

TOKEN_TTL_SECONDS = 12 * 3600  # 12 soat


def _hash(password: str) -> str:
    """Eski (tuzsiz SHA-256) xeshlar bilan moslik uchun saqlanadi."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_admin_password(admin: models.Admin, password: str, db: Session) -> bool:
    """Parolni tekshiradi; eski SHA-256 xeshni jimgina bcryptga o'tkazadi.

    Shu tufayli mavjud `admin123` qatori ham ishlashda davom etadi, lekin
    birinchi muvaffaqiyatli kirishdan keyin bazada bcrypt xeshi qoladi.
    """
    stored = admin.password_hash or ""
    if stored.startswith("$2"):  # bcrypt xeshi
        try:
            return customer_auth.verify_password(password, stored)
        except ValueError:
            return False

    if hmac.compare_digest(stored, _hash(password)):
        admin.password_hash = customer_auth.hash_password(password)
        db.commit()
        return True
    return False


def _prune_expired() -> None:
    now = time.time()
    for token in [t for t, v in _active_tokens.items() if v["expires_at"] <= now]:
        _active_tokens.pop(token, None)


@router.post("/login")
def login(payload: schemas.AdminLogin, db: Session = Depends(get_db)):
    admin = db.query(models.Admin).filter(models.Admin.username == payload.username).first()
    if not admin or not verify_admin_password(admin, payload.password, db):
        raise HTTPException(401, "Login yoki parol xato")

    _prune_expired()
    token = secrets.token_hex(24)
    _active_tokens[token] = {"admin_id": admin.id, "expires_at": time.time() + TOKEN_TTL_SECONDS}
    return {"token": token, "expires_in": TOKEN_TTL_SECONDS}


@router.post("/logout")
def logout(authorization: Optional[str] = Header(None)):
    """Tokenni serverdan ham o'chiradi (avval faqat localStorage tozalanardi)."""
    if authorization and authorization.startswith("Bearer "):
        _active_tokens.pop(authorization[len("Bearer "):].strip(), None)
    return {"ok": True}


def require_admin(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> models.Admin:
    """Amaldagi adminni qaytaradi yoki 401 ko'taradi.

    Endpointga ikki xil ulanadi:
        dependencies=[Depends(require_admin)]        — faqat himoya kerak bo'lsa
        admin: models.Admin = Depends(require_admin) — admin obyekti kerak bo'lsa
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Avtorizatsiya talab qilinadi")

    token = authorization[len("Bearer "):].strip()
    entry = _active_tokens.get(token)
    if not entry:
        raise HTTPException(401, "Avtorizatsiya talab qilinadi")
    if entry["expires_at"] <= time.time():
        _active_tokens.pop(token, None)
        raise HTTPException(401, "Sessiya muddati tugagan, qaytadan kiring")

    admin = db.query(models.Admin).get(entry["admin_id"])
    if not admin:
        _active_tokens.pop(token, None)
        raise HTTPException(401, "Avtorizatsiya talab qilinadi")
    return admin


@router.get("/me")
def admin_me(admin: models.Admin = Depends(require_admin)):
    """Admin panel yuklanganda saqlangan tokenni tekshirish uchun."""
    return {"id": admin.id, "username": admin.username}


@router.post("/change-password")
def change_password(
    payload: schemas.AdminPasswordChange,
    db: Session = Depends(get_db),
    admin: models.Admin = Depends(require_admin),
):
    """Standart `admin123` parolini almashtirish uchun (avval imkoni yo'q edi)."""
    if not verify_admin_password(admin, payload.current_password, db):
        raise HTTPException(401, "Joriy parol xato")
    if len(payload.new_password) < 10:
        raise HTTPException(400, "Yangi parol kamida 10 ta belgidan iborat bo'lishi kerak")

    admin.password_hash = customer_auth.hash_password(payload.new_password)
    db.commit()

    # Barcha eski sessiyalarni bekor qilamiz — parol o'zgargandan keyin
    # o'g'irlangan token ishlashda davom etmasligi kerak.
    for token in [t for t, v in _active_tokens.items() if v["admin_id"] == admin.id]:
        _active_tokens.pop(token, None)
    return {"ok": True}
