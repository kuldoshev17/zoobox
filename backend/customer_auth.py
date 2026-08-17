"""
Mijoz hisoblari uchun parol xeshlash va sessiya tokenlari.

Admin panel (admin_auth.py) dagi sodda sxemadan farqli o'laroq, bu yerda
haqiqiy parol xeshlash (bcrypt) va muddati tugaydigan tokenlar (JWT)
ishlatiladi — chunki bu mijozlarga qaratilgan va server qayta ishga
tushganda ham mijoz seansi saqlanib qolishi kerak.
"""
import os
import re
import time
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from . import models

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
JWT_TTL_SECONDS = 30 * 24 * 3600  # 30 kun

# PyJWT bo'sh kalitni rad etmaydi: `JWT_SECRET` sozlanmagan bo'lsa, tokenlarni
# xohlagan odam imzolab, istalgan mijoz hisobiga kirishi mumkin edi — va bu
# hech qanday xatolik bermay, jimgina ishlab turardi. Shuning uchun ilova
# umuman ishga tushmasligi kerak.
if len(JWT_SECRET) < 32:
    raise RuntimeError(
        "JWT_SECRET sozlanmagan yoki juda qisqa (kamida 32 belgi kerak). "
        ".env fayliga qo'shing, masalan: "
        "python -c \"import secrets; print(secrets.token_hex(32))\""
    )

_PHONE_RE = re.compile(r"^\+998\d{9}$")


def normalize_phone(raw: str) -> str:
    """Telefon raqamini standart `+998XXXXXXXXX` formatiga keltiradi."""
    digits_only = re.sub(r"[^\d+]", "", raw or "")
    if not digits_only.startswith("+"):
        digits_only = "+" + digits_only.lstrip("+")
    if not _PHONE_RE.match(digits_only):
        raise HTTPException(400, "Telefon raqam noto'g'ri formatda (masalan: +998901234567)")
    return digits_only


def hash_password(password: str) -> str:
    # bcrypt 72 baytdan uzun parollarni jimgina qisqartiradi — bu yerda
    # muammo emas (oddiy foydalanuvchi paroli), lekin bilib qo'yish kerak.
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_token(customer_id: int) -> str:
    now = int(time.time())
    payload = {"sub": str(customer_id), "iat": now, "exp": now + JWT_TTL_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_bearer(authorization: str) -> int:
    token = authorization[len("Bearer "):]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(401, "Token yaroqsiz yoki muddati tugagan")
    return int(payload["sub"])


def get_current_customer(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> models.Customer:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Avtorizatsiya talab qilinadi")
    customer_id = _decode_bearer(authorization)
    customer = db.query(models.Customer).get(customer_id)
    if not customer:
        raise HTTPException(401, "Mijoz topilmadi")
    return customer
