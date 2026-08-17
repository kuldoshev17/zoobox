"""
Telegram Mini App orqali kelgan so'rovlarni tekshirish.

Telegram WebApp `initData`ni HMAC-SHA256 orqali tekshiradi (rasmiy sxema):
https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app

Transport: `Authorization: tma <initData>` headeri (Telegram'ning rasmiy Mini
Apps sxemasi — o'zimizcha header nomi o'ylab topmaymiz).
"""
import hashlib
import hmac
import json
import os
import time
from typing import Optional
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# `BOT_TOKEN` bo'sh bo'lsa, maxfiy kalit HMAC(b"WebAppData", b"") ga aylanadi —
# ya'ni hamma hisoblab chiqadigan doimiy qiymat. Shunda istalgan odam xohlagan
# `user.id` uchun initData soxtalashtirib, `/api/customer/me` orqali haqiqiy
# 30 kunlik JWT olishi mumkin edi. Bu ham jimgina ishlaydigan xato edi.
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN sozlanmagan. Telegram initData imzosini tekshirish mumkin emas — "
        ".env fayliga BotFather bergan tokenni qo'shing."
    )

_AUTH_SCHEME = "tma "


def verify_init_data(init_data: str, bot_token: str, max_age: int = 300) -> dict:
    """initData imzosini tekshiradi va Telegram foydalanuvchi ma'lumotini qaytaradi.

    Imzo noto'g'ri yoki eskirgan bo'lsa ValueError ko'taradi.
    """
    if not bot_token:
        raise ValueError("bot_token bo'sh — imzoni tekshirish mumkin emas")

    parsed = dict(parse_qsl(init_data, strict_parsing=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise ValueError("hash yo'q")

    check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, received_hash):
        raise ValueError("imzo noto'g'ri")

    auth_date = int(parsed.get("auth_date", 0))
    if time.time() - auth_date > max_age:
        raise ValueError("initData eskirgan")

    return json.loads(parsed["user"])


def _extract_init_data(authorization: Optional[str]) -> Optional[str]:
    if not authorization or not authorization.startswith(_AUTH_SCHEME):
        return None
    return authorization[len(_AUTH_SCHEME):]


def get_telegram_user(authorization: Optional[str] = Header(None)) -> dict:
    """`Authorization: tma <initData>` headerini talab qiladi va tekshiradi.

    Header yo'q yoki imzo/yangi-lik tekshiruvidan o'tmasa 401.
    """
    init_data = _extract_init_data(authorization)
    if not init_data:
        raise HTTPException(401, "Avtorizatsiya talab qilinadi")
    try:
        return verify_init_data(init_data, BOT_TOKEN)
    except (ValueError, KeyError):
        raise HTTPException(401, "Telegram initData yaroqsiz")
