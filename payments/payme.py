"""
PAYME to'lov tizimi integratsiyasi (STUB).

Ishga tushirish uchun https://business.payme.uz dan quyidagilarni oling
va .env fayliga qo'shing:

    PAYME_MERCHANT_ID=...
    PAYME_SECRET_KEY=...

Payme oqimi:
1. generate_pay_link() orqali checkout havolasi yaratiladi (base64 params).
2. Payme server JSON-RPC so'rovlar yuboradi: CheckPerformTransaction,
   CreateTransaction, PerformTransaction, CancelTransaction, CheckTransaction.
3. Har bir metod handle_* funksiyalarda ishlanishi kerak (hozircha skelet).

Rasmiy hujjat: https://developer.help.paycom.uz
"""
import base64
import os
from typing import Optional

PAYME_MERCHANT_ID = os.getenv("PAYME_MERCHANT_ID", "")
PAYME_SECRET_KEY = os.getenv("PAYME_SECRET_KEY", "")

PAYME_CHECKOUT_URL = "https://checkout.paycom.uz"


def generate_pay_link(order_id: int, amount_som: float) -> str:
    """
    Payme checkout sahifasiga havola yaratadi.
    Amount tiyinlarda (so'm * 100) yuborilishi kerak.
    """
    if not PAYME_MERCHANT_ID:
        return "#payme-not-configured"

    amount_tiyin = int(amount_som * 100)
    raw = f"m={PAYME_MERCHANT_ID};ac.order_id={order_id};a={amount_tiyin}"
    encoded = base64.b64encode(raw.encode()).decode()
    return f"{PAYME_CHECKOUT_URL}/{encoded}"


def verify_auth(auth_header: str) -> bool:
    """Payme so'rovlaridagi Basic auth headerini PAYME_SECRET_KEY bilan solishtiradi."""
    if not PAYME_SECRET_KEY:
        return False
    expected = base64.b64encode(f"Paycom:{PAYME_SECRET_KEY}".encode()).decode()
    return auth_header == f"Basic {expected}"


def handle_check_perform_transaction(order_amount_tiyin: int, request_amount: int) -> dict:
    """Buyurtma summasi to'g'riligini tekshiradi."""
    if order_amount_tiyin != request_amount:
        return {"error": {"code": -31001, "message": "Incorrect amount"}}
    return {"result": {"allow": True}}


def handle_create_transaction(order_id: int) -> dict:
    """Yangi tranzaksiya yaratish - real integratsiyada DBga yozing."""
    return {"result": {"create_time": 0, "transaction": str(order_id), "state": 1}}


def handle_perform_transaction(order_id: int) -> dict:
    """To'lovni yakunlash - shu yerda order.payment_status = PAID qilinadi."""
    return {"result": {"transaction": str(order_id), "perform_time": 0, "state": 2}}
